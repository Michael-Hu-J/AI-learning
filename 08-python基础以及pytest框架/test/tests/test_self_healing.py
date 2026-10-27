# test_self_healing.py - 自愈系统功能验证
"""
自愈系统单元测试 — 不依赖 Appium/API/Allure，纯 Python 验证
"""
import os
import sys
import json
import logging
from pathlib import Path

# 确保 self_healing 模块可导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from self_healing.retry_engine import (
    RetryConfig,
    RetryTracker,
    retry_tracker,
    is_timeout_or_network,
    is_logic_error,
    RETRYABLE_EXCEPTIONS,
    NON_RETRYABLE_EXCEPTIONS,
)
from self_healing.diagnostic import (
    classify_failure,
    extract_root_cause,
    suggest_fix,
    FailureCategory,
)
from self_healing.scene_collector import SceneCollector
from self_healing.flaky_detector import FlakyDetector
from self_healing.health_checker import HealthChecker


# ============================================================
#  RetryEngine 测试
# ============================================================

class TestRetryConfig:
    """测试重试配置"""

    def test_default_config(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 2.0
        assert config.backoff_factor == 2.0

    def test_exponential_backoff(self):
        config = RetryConfig(base_delay=2.0, backoff_factor=2.0, max_delay=30.0)
        assert config.get_delay(1) == 2.0   # 第1次等2秒
        assert config.get_delay(2) == 4.0   # 第2次等4秒
        assert config.get_delay(3) == 8.0   # 第3次等8秒
        assert config.get_delay(4) == 16.0  # 第4次等16秒
        assert config.get_delay(5) == 30.0  # 超过max_delay，兜底30秒

    def test_should_retry_logic_error(self):
        config = RetryConfig()
        # 逻辑错误不应该重试
        assert config.should_retry(AssertionError("assert 1 == 2"), 0) is False
        assert config.should_retry(ValueError("invalid value"), 0) is False
        assert config.should_retry(KeyError("missing_key"), 0) is False

    def test_should_retry_network_error(self):
        config = RetryConfig()
        # 网络错误应该重试
        assert config.should_retry(ConnectionError("refused"), 0) is True
        assert config.should_retry(TimeoutError("timed out"), 0) is True
        assert config.should_retry(ConnectionRefusedError(), 0) is True

    def test_should_retry_max_retries(self):
        config = RetryConfig(max_retries=3)
        # 超过最大重试次数
        assert config.should_retry(ConnectionError(), 3) is False
        assert config.should_retry(ConnectionError(), 2) is True  # 第3次还能试


class TestRetryTracker:
    """测试重试跟踪器"""

    def test_record_and_summary(self):
        tracker = RetryTracker()
        tracker.record_attempt("test_a", 1, "passed")
        tracker.record_attempt("test_b", 1, "failed")
        tracker.record_attempt("test_b", 2, "passed")  # 重试救回
        tracker.record_attempt("test_c", 1, "failed")
        tracker.record_attempt("test_c", 2, "failed")  # 重试后仍失败

        summary = tracker.get_summary()
        assert summary["total_tests"] == 3
        assert summary["retried_tests"] == 2
        assert summary["saved_by_retry"] == 1   # test_b
        assert summary["failed_after_retry"] == 1  # test_c


class TestExceptionClassification:
    """测试异常分类"""

    def test_network_exceptions(self):
        assert is_timeout_or_network(ConnectionError()) is True
        assert is_timeout_or_network(TimeoutError()) is True
        assert is_timeout_or_network(ConnectionRefusedError()) is True

    def test_logic_exceptions(self):
        assert is_logic_error(AssertionError()) is True
        assert is_logic_error(ValueError()) is True
        assert is_logic_error(KeyError()) is True
        assert is_logic_error(TypeError()) is True


# ============================================================
#  Diagnostic 测试
# ============================================================

class TestDiagnostic:
    """测试失败诊断"""

    def test_classify_environment_error(self):
        class FakeReport:
            longreprtext = "Connection refused: 127.0.0.1:8222"
        assert classify_failure(FakeReport()) == FailureCategory.ENVIRONMENT

    def test_classify_timeout(self):
        class FakeReport:
            longreprtext = "Timeout waiting for element 'login_button'"
        assert classify_failure(FakeReport()) == FailureCategory.TIMEOUT

    def test_classify_assertion_error(self):
        class FakeReport:
            longreprtext = "AssertionError: assert 200 == 500"
        assert classify_failure(FakeReport()) == FailureCategory.CODE_BUG

    def test_classify_data_issue(self):
        class FakeReport:
            longreprtext = "IntegrityError: duplicate key 'user@example.com'"
        assert classify_failure(FakeReport()) == FailureCategory.DATA_ISSUE

    def test_extract_root_cause_assertion(self):
        class FakeReport:
            longreprtext = "Traceback (most recent call last):\n  File 'test.py', line 10\nAssertionError: assert 200 == 500"
        cause = extract_root_cause(FakeReport())
        assert "AssertionError" in cause

    def test_extract_root_cause_exception(self):
        class FakeReport:
            longreprtext = "Traceback (most recent call last):\n  File 'test.py', line 10\nConnectionError: Connection refused"
        cause = extract_root_cause(FakeReport())
        assert "ConnectionError" in cause

    def test_suggest_fix(self):
        assert "环境" in suggest_fix(FailureCategory.ENVIRONMENT)
        assert "逻辑" in suggest_fix(FailureCategory.CODE_BUG)
        assert "超时" in suggest_fix(FailureCategory.TIMEOUT)
        assert "数据" in suggest_fix(FailureCategory.DATA_ISSUE)


# ============================================================
#  SceneCollector 测试
# ============================================================

class TestSceneCollector:
    """测试现场收集"""

    def test_collect_without_driver(self, tmp_path):
        collector = SceneCollector(report_dir=str(tmp_path))
        collected = collector.collect(
            nodeid="test_login.py::test_login_success",
            response='{"code": 500, "message": "Internal Server Error"}',
            extra_logs="DEBUG: starting test\nINFO: login attempt",
            category="environment",
        )

        assert collected["category"] == "environment"
        assert collected["nodeid"] == "test_login.py::test_login_success"
        # 有 response 和 logs，没有截图（没提供 driver）
        file_types = [ft for ft, _ in collected["files"]]
        assert "response" in file_types
        assert "log" in file_types
        assert "screenshot" not in file_types

    def test_scene_dir_created(self, tmp_path):
        collector = SceneCollector(report_dir=str(tmp_path))
        collector.collect(
            nodeid="test_api.py::test_get_user",
            response='{"error": "not found"}',
        )
        # 场景目录应该被创建
        assert any(tmp_path.iterdir())


# ============================================================
#  FlakyDetector 测试
# ============================================================

class TestFlakyDetector:
    """测试 flaky 检测"""

    def test_detect_flaky(self, tmp_path):
        detector = FlakyDetector(history_file=str(tmp_path / "history.json"))

        # 模拟一个 flaky 用例：跑了10次，过了6次（60%通过率）
        for i in range(10):
            if i < 6:
                detector.record_result("test_flaky_case", "passed")
            else:
                detector.record_result("test_flaky_case", "failed")

        detector.save_history()
        flaky = detector.get_flaky_tests(min_runs=5)

        assert len(flaky) == 1
        assert flaky[0]["nodeid"] == "test_flaky_case"
        assert flaky[0]["pass_rate"] == 0.6
        assert flaky[0]["total_runs"] == 10

    def test_not_flaky_stable_pass(self, tmp_path):
        detector = FlakyDetector(history_file=str(tmp_path / "history.json"))

        # 稳定通过：10次全过
        for i in range(10):
            detector.record_result("test_stable", "passed")

        detector.save_history()
        flaky = detector.get_flaky_tests(min_runs=5)
        assert len(flaky) == 0

    def test_not_flaky_stable_fail(self, tmp_path):
        detector = FlakyDetector(history_file=str(tmp_path / "history.json"))

        # 稳定失败：10次全失败
        for i in range(10):
            detector.record_result("test_always_fail", "failed")

        detector.save_history()
        flaky = detector.get_flaky_tests(min_runs=5)
        assert len(flaky) == 0

    def test_insufficient_runs(self, tmp_path):
        detector = FlakyDetector(history_file=str(tmp_path / "history.json"))

        # 只跑了3次，不够 min_runs=5
        detector.record_result("test_new", "passed")
        detector.record_result("test_new", "failed")
        detector.record_result("test_new", "passed")

        detector.save_history()
        flaky = detector.get_flaky_tests(min_runs=5)
        assert len(flaky) == 0

    def test_generate_report(self, tmp_path):
        detector = FlakyDetector(history_file=str(tmp_path / "history.json"))

        for i in range(10):
            if i < 4:
                detector.record_result("test_a", "passed")
            else:
                detector.record_result("test_a", "failed")

        detector.save_history()
        report = detector.generate_report()
        assert report["status"] == "flaky_detected"
        assert report["flaky_count"] == 1
        assert report["flaky_tests"][0]["nodeid"] == "test_a"

    def test_save_report_json(self, tmp_path):
        detector = FlakyDetector(history_file=str(tmp_path / "history.json"))
        report_path = tmp_path / "flaky_report.json"

        for _ in range(10):
            detector.record_result("test_stable", "passed")
        detector.save_history()
        detector.save_report(str(report_path))

        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["status"] == "stable"
        assert data["flaky_count"] == 0
        assert data["flaky_tests"] == []


# ============================================================
#  HealthChecker 测试
# ============================================================

class TestHealthChecker:
    """测试健康检查"""

    def test_ping_localhost(self):
        checker = HealthChecker()
        # 127.0.0.1:99999 不可能通，用来验证失败情况
        passed, msg = checker.ping_host("127.0.0.1", 99999)
        assert passed is False
        assert "99999" in msg

    def test_ping_loopback(self):
        checker = HealthChecker()
        # 端口 22 (ssh) 可能通也可能不通，但至少不会崩溃
        passed, msg = checker.ping_host("127.0.0.1", 22)
        # 不管通不通，返回值格式正确就行
        assert isinstance(passed, bool)
        assert isinstance(msg, str)

    def test_check_python_module(self):
        checker = HealthChecker()
        # os 是内置模块，一定存在
        passed, msg = checker.check_python_module("os")
        assert passed is True
        assert "已安装" in msg

        # 不存在的模块
        passed, msg = checker.check_python_module("this_module_does_not_exist_xyz")
        assert passed is False
        assert "未安装" in msg

    def test_check_env_var(self):
        checker = HealthChecker()
        # 设置一个环境变量
        os.environ["TEST_HEALTH_CHECK_VAR"] = "hello_world"
        passed, msg = checker.check_env_var("TEST_HEALTH_CHECK_VAR")
        assert passed is True

        # 未设置的环境变量
        passed, msg = checker.check_env_var("NONEXISTENT_VAR_XYZ_12345")
        assert passed is False

    def test_register_and_run_checks(self):
        checker = HealthChecker()
        checker._abort_on_fail = False  # 测试时不退出

        checker.register_check("always_pass", lambda: (True, "一切正常"))
        checker.register_check("always_fail", lambda: (False, "服务挂了"))

        results = checker.run_all_checks()
        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False

    def test_check_command(self):
        checker = HealthChecker()
        # python --version 应该可用
        passed, msg = checker.check_command("python3", "--version")
        assert isinstance(passed, bool)
