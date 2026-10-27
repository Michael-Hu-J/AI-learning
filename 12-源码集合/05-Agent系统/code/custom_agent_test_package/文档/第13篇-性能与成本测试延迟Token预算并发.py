import statistics

latencies = []
for _ in range(30):
    start = time.time()
    agent.run(task)
    latencies.append(time.time() - start)

s = sorted(latencies)
n = len(s)
p50 = statistics.median(s)  # n 为偶数时取中间两值平均
# 离散样本的粗分位：与文中 PerformanceReport 一致，用 int(p * n) 并夹到合法下标
idx90 = min(int(n * 0.9), n - 1)
idx99 = min(int(n * 0.99), n - 1)
p90 = s[idx90]
p99 = s[idx99]  # n=30 时 idx99=29，本质是近“最大值”，报告 P99 需更大 n 或插值

#!/usr/bin/env python3
"""
性能与成本测试

功能：
1. 延迟分布测试（P50/P90/P99）
2. Token 消耗监控
3. 并发压力测试
"""

import time
import statistics
import os
import sys
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class PerformanceReport:
    """性能报告"""
    task: str
    n_runs: int
    latencies: List[float] = field(default_factory=list)
    tokens: List[int] = field(default_factory=list)
    successes: List[bool] = field(default_factory=list)

    @property
    def p50(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0

    @property
    def p90(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.9)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def mean_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0

    @property
    def std_latency(self) -> float:
        return statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0

    @property
    def mean_tokens(self) -> int:
        return int(statistics.mean(self.tokens)) if self.tokens else 0

    @property
    def success_rate(self) -> float:
        if not self.successes:
            return 0
        return sum(self.successes) / len(self.successes)


def test_latency(agent, task: str, n_runs: int = 30) -> PerformanceReport:
    """
    延迟测试

    Args:
        agent: 智能体实例
        task: 任务描述
        n_runs: 运行次数

    Returns:
        PerformanceReport
    """
    report = PerformanceReport(task=task, n_runs=n_runs)

    for i in range(n_runs):
        agent.reset()
        start = time.time()
        result = agent.run(task)
        elapsed = time.time() - start

        report.latencies.append(elapsed)
        report.tokens.append(result.get("_meta", {}).get("tokens", 0))
        report.successes.append(result.get("success", False))

    return report


def test_concurrency(agent_factory, task: str,
                     concurrency: int = 5,
                     n_runs: int = 3) -> Dict:
    """
    并发压力测试

    Args:
        agent_factory: 智能体工厂函数（每次返回新实例）
        task: 任务描述
        concurrency: 并发数
        n_runs: 每组并发运行次数

    Returns:
        {
            "concurrency": 并发数,
            "total_requests": 总请求数,
            "success_rate": 成功率,
            "mean_latency": 平均延迟,
            "p50_latency": P50 延迟,
            "p90_latency": P90 延迟,
            "errors": 错误列表,
        }
    """
    results = []
    errors = []

    def run_task():
        agent = agent_factory()
        start = time.time()
        try:
            result = agent.run(task)
            elapsed = time.time() - start
            return {
                "success": result.get("success", False),
                "latency": elapsed,
                "tokens": result.get("_meta", {}).get("tokens", 0),
            }
        except Exception as e:
            elapsed = time.time() - start
            errors.append({"error": str(e), "latency": elapsed})
            return {"success": False, "latency": elapsed, "tokens": 0}

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for _ in range(n_runs * concurrency):
            futures.append(executor.submit(run_task))

        for future in as_completed(futures):
            results.append(future.result())

    latencies = [r["latency"] for r in results]
    tokens = [r["tokens"] for r in results]
    successes = [r["success"] for r in results]

    return {
        "concurrency": concurrency,
        "total_requests": len(results),
        "success_rate": sum(successes) / len(successes) if successes else 0,
        "mean_latency": statistics.mean(latencies) if latencies else 0,
        "p50_latency": statistics.median(latencies) if latencies else 0,
        "p90_latency": sorted(latencies)[int(len(latencies) * 0.9)] if latencies else 0,
        "mean_tokens": int(statistics.mean(tokens)) if tokens else 0,
        "errors": errors,
    }


def print_performance_report(report: PerformanceReport):
    """打印性能报告"""
    print(f"\n{'='*60}")
    print(f"性能报告 — {report.task[:50]}")
    print(f"{'='*60}")
    print(f"  运行次数: {report.n_runs}")
    print(f"  成功率: {report.success_rate:.0%}")
    print(f"  平均延迟: {report.mean_latency:.1f}s")
    print(f"  P50 延迟: {report.p50:.1f}s")
    print(f"  P90 延迟: {report.p90:.1f}s")
    print(f"  P99 延迟: {report.p99:.1f}s")
    print(f"  延迟标准差: {report.std_latency:.1f}s")
    print(f"  平均 Token: {report.mean_tokens}")
    print(f"{'='*60}\n")


def run_demo():
    """演示"""
    print("=" * 60)
    print("性能与成本测试演示")
    print("=" * 60)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from agents.custom_agent.agent import CustomAgent

    # 简单任务
    print("\n--- 简单任务：查询当月销售数据 ---")
    agent = CustomAgent(temperature=0.3)
    report1 = test_latency(agent, "查询当月销售数据", n_runs=10)
    print_performance_report(report1)

    # 中等任务
    print("\n--- 中等任务：生成品类分析报告 ---")
    agent = CustomAgent(temperature=0.3)
    report2 = test_latency(agent, "生成本月品类销售分析报告", n_runs=10)
    print_performance_report(report2)

    # 并发测试
    print("\n--- 并发测试（5 并发）---")
    concurrency_result = test_concurrency(
        lambda: CustomAgent(temperature=0.3),
        "查询当月销售数据",
        concurrency=5,
        n_runs=3,
    )
    print(f"  并发数: {concurrency_result['concurrency']}")
    print(f"  总请求: {concurrency_result['total_requests']}")
    print(f"  成功率: {concurrency_result['success_rate']:.0%}")
    print(f"  平均延迟: {concurrency_result['mean_latency']:.1f}s")
    print(f"  P50 延迟: {concurrency_result['p50_latency']:.1f}s")
    print(f"  P90 延迟: {concurrency_result['p90_latency']:.1f}s")
    print(f"  平均 Token: {concurrency_result['mean_tokens']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_demo()
