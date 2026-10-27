# flaky_detector.py - Flaky 测试检测器
"""
Flaky 测试检测器

功能：
1. 记录每个用例的历史执行结果（pass/fail）
2. 统计通过率，自动标记 flaky 用例
3. 生成 flaky JSON 报告

原理：
- 一个用例累计跑了 N 次（默认 >= 5），但失败次数 >= X 次且 <= Y 次
  （既不是稳定通过也不是稳定失败），属于 flaky
- 阈值可配置
"""
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytest

logger = logging.getLogger(__name__)


class FlakyDetector:
    """
    Flaky 测试检测器。

    使用方式（在 conftest.py 中集成）：
        detector = FlakyDetector()
        
        # 每次用例执行完记录结果
        detector.record_result("test_login", "passed")
        
        # 检测 flaky 用例
        flaky_tests = detector.get_flaky_tests()
        
        # 生成报告
        detector.generate_report()
    """

    # 默认存储路径
    HISTORY_FILE = "reports/flaky_history.json"

    def __init__(self, history_file: Optional[str] = None):
        self.history_file = history_file or self.HISTORY_FILE
        self._results = []  # [(nodeid, outcome, timestamp)]

    def record_result(self, nodeid: str, outcome: str):
        """
        记录一个用例的执行结果。
        outcome 取值：'passed', 'failed', 'skipped'
        """
        self._results.append((
            nodeid,
            outcome,
            datetime.now().isoformat(),
        ))

    def save_history(self):
        """将本次会话的结果持久化到文件"""
        history_path = Path(self.history_file)
        history_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取已有历史
        existing = []
        if history_path.exists():
            try:
                existing = json.loads(history_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                existing = []

        # 追加新结果
        existing.extend([
            {"nodeid": r[0], "outcome": r[1], "timestamp": r[2]}
            for r in self._results
        ])

        # 只保留最近 30 天的记录
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        existing = [
            r for r in existing
            if r.get("timestamp", "") >= thirty_days_ago
        ]

        history_path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_history(self) -> list:
        """从文件加载历史结果"""
        history_path = Path(self.history_file)
        if not history_path.exists():
            return []
        try:
            return json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            logger.warning(f"flaky 历史文件读取失败: {self.history_file}")
            return []

    def get_flaky_tests(self, min_runs: int = 5,
                        fail_threshold: float = 0.2,
                        pass_threshold: float = 0.95) -> list:
        """
        检测 flaky 测试。

        参数：
        - min_runs: 最少执行次数（小于此数不判断 flaky）
        - fail_threshold: flaky 的失败率下限（低于此值视为稳定通过）
        - pass_threshold: pass 率低于此值视为稳定失败

        返回 flaky 用例列表：[{nodeid, pass_rate, total_runs, failed_runs, ...}]
        """
        history = self.load_history()

        # 按用例聚合
        stats = defaultdict(lambda: {"pass": 0, "fail": 0, "skip": 0, "total": 0})
        for record in history:
            nodeid = record["nodeid"]
            outcome = record["outcome"]
            stats[nodeid]["total"] += 1
            if outcome == "passed":
                stats[nodeid]["pass"] += 1
            elif outcome == "failed":
                stats[nodeid]["fail"] += 1
            else:
                stats[nodeid]["skip"] += 1

        # 判断 flaky
        flaky_tests = []
        for nodeid, s in stats.items():
            if s["total"] < min_runs:
                continue
            pass_rate = s["pass"] / s["total"] if s["total"] > 0 else 0

            # flaky 判断：既不是稳定通过也不是稳定失败
            is_flaky = pass_threshold > pass_rate > fail_threshold

            if is_flaky:
                flaky_tests.append({
                    "nodeid": nodeid,
                    "pass_rate": round(pass_rate, 2),
                    "total_runs": s["total"],
                    "passed_runs": s["pass"],
                    "failed_runs": s["fail"],
                    "skipped_runs": s["skip"],
                })

        # 按失败率降序排列
        flaky_tests.sort(key=lambda x: x["pass_rate"])
        return flaky_tests

    def generate_report(self) -> dict:
        """生成 flaky 报告（结构化 dict，便于序列化为 JSON）"""
        flaky_tests = self.get_flaky_tests()
        generated_at = datetime.now().isoformat(timespec="seconds")

        if not flaky_tests:
            return {
                "generated_at": generated_at,
                "status": "stable",
                "flaky_count": 0,
                "flaky_tests": [],
                "message": "未检测到 flaky 测试用例，所有用例运行稳定。",
            }

        return {
            "generated_at": generated_at,
            "status": "flaky_detected",
            "flaky_count": len(flaky_tests),
            "flaky_tests": flaky_tests,
            "message": f"检测到 {len(flaky_tests)} 个 flaky 测试用例。",
        }

    def save_report(self, output_path: str = "reports/flaky_report.json"):
        """保存 flaky 报告到 JSON 文件"""
        report = self.generate_report()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if report["flaky_count"] > 0:
            logger.info(
                f"Flaky 报告已生成: {output_path} "
                f"（{report['flaky_count']} 个不稳定用例）"
            )
        else:
            logger.debug(f"Flaky 报告已更新: {output_path}（全部稳定）")

    def mark_skipped_flaky(self, nodeid: str, session) -> bool:
        """
        将 flaky 测试标记为 xfail（预期失败）。
        返回 True 表示标记成功。
        """
        try:
            # 尝试找到该用例并标记
            for item in session.items:
                if item.nodeid == nodeid:
                    item.add_marker(pytest.mark.xfail(
                        reason="flaky: 通过率不稳定",
                        strict=False,
                    ))
                    logger.info(f"已将 flaky 用例标记为 xfail: {nodeid}")
                    return True
        except Exception as e:
            logger.warning(f"标记 flaky 用例失败: {e}")
        return False


# 全局 flaky 检测器
flaky_detector = FlakyDetector()
