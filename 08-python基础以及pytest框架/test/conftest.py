# conftest.py — pytest 自愈系统集成
import logging
import os
import shutil
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

from self_healing import api_report_recorder as api_recorder
from self_healing.diagnostic import classify_failure, extract_root_cause, suggest_fix
from self_healing.flaky_detector import flaky_detector
from self_healing.health_checker import HealthChecker
from self_healing.health_checker import pytest_exit as health_check_exit
from self_healing.retry_engine import retry_tracker
from self_healing.scene_collector import scene_collector


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

    if rep.when == "call" and rep.failed:
        nodeid = item.nodeid
        category = classify_failure(rep)
        root_cause = extract_root_cause(rep)
        fix_suggestion = suggest_fix(category, root_cause)

        logger.info("用例失败: %s", nodeid)
        logger.info("   分类: %s", category)
        if root_cause:
            logger.info("   根因: %s", root_cause[:150])
        logger.info("   建议: %s", fix_suggestion[:150])

        collected = scene_collector.collect(
            nodeid=nodeid,
            driver=None,
            category=category,
        )
        scene_collector.attach_to_allure(collected, nodeid)
        flaky_detector.record_result(nodeid, "failed")


@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    if report.when == "call":
        flaky_detector.record_result(report.nodeid, report.outcome)

        if api_recorder.is_enabled():
            api_recorder.end_case(report.nodeid, report.outcome, report.duration)

        retry_tracker.record_attempt(
            nodeid=report.nodeid,
            attempt=1,
            outcome=report.outcome,
        )

        logger.info(
            "用例 %s 结果: %s (耗时: %.2fs)",
            report.nodeid,
            report.outcome,
            report.duration,
        )


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    try:
        flaky_detector.save_history()
    except Exception as e:
        logger.debug("保存 flaky 历史失败: %s", e)

    try:
        flaky_detector.save_report()
    except Exception as e:
        logger.debug("生成 flaky 报告失败: %s", e)

    if api_recorder.is_enabled():
        try:
            report_path = os.environ.get(
                "API_REPORT_PATH",
                str(Path(session.config.rootpath) / "reports" / "api_test_report.json"),
            )
            api_recorder.save_report(report_path)
        except Exception as e:
            logger.warning("生成 API JSON 报告失败: %s", e)

    summary = retry_tracker.get_summary()
    if summary["saved_by_retry"] > 0:
        logger.info("=" * 50)
        logger.info("  自愈系统摘要")
        logger.info("  总用例: %s", summary["total_tests"])
        logger.info("  重试用例: %s", summary["retried_tests"])
        logger.info("  重试救回: %s", summary["saved_by_retry"])
        logger.info("  重试后仍失败: %s", summary["failed_after_retry"])
        logger.info("=" * 50)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    if os.environ.get("ALLURE_APPEND", "").strip().lower() in ("1", "true", "yes"):
        return
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return
    if getattr(session.config.option, "collectonly", False):
        return

    opt_dir = getattr(session.config.option, "allure_report_dir", None)
    if not opt_dir:
        return

    results_dir = Path(opt_dir).expanduser().resolve()
    try:
        if results_dir.is_dir():
            shutil.rmtree(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning("清空 Allure 结果目录失败（将继续执行测试）: %s", e)


@pytest.fixture(autouse=True)
def log_test_info(request):
    if api_recorder.is_enabled():
        api_recorder.begin_case(request.node.nodeid, request.node.name)

    logger.info("")
    logger.info("开始执行测试用例: %s", request.node.name)
    logger.info("测试用例文件: %s", request.fspath)
    yield
    logger.info("测试用例执行完成: %s", request.node.name)
    logger.info("=" * 50)


def pytest_configure(config):
    if api_recorder.is_enabled():
        api_recorder.install_patch()
        api_recorder.reset_session()

    if os.getenv("SKIP_HEALTH_CHECK", "").strip().lower() in ("1", "true", "yes"):
        logger.info("健康检查已跳过（SKIP_HEALTH_CHECK=1）")
        return

    base_url = os.getenv("SECKILL_BASE_URL", os.getenv("TEST_BASE_URL", "")).strip()
    if not base_url:
        return

    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    checker = HealthChecker()
    checker.register_check(
        "api_server",
        lambda: checker.ping_host(host, port),
    )
    results = checker.run_all_checks()
    if any(not r.passed for r in results):
        health_check_exit()
