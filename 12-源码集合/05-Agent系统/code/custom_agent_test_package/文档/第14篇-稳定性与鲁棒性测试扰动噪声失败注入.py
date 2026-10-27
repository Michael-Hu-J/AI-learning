#!/usr/bin/env python3
"""
稳定性与鲁棒性测试 — Chaos 测试框架

功能：
1. 扰动注入（网络延迟、工具失败、输入截断等）
2. 随机种子扰动
3. 稳定性指标计算
"""

import os
import sys
import time
import random
import statistics
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class ChaosConfig:
    """Chaos 配置"""
    network_delay_min_ms: int = 0
    network_delay_max_ms: int = 0
    tool_failure_rate: float = 0.0
    input_truncate_ratio: float = 0.0
    enable_concurrent: bool = False
    memory_limit_mb: int = 0


@dataclass
class ChaosResult:
    """Chaos 测试结果"""
    config: ChaosConfig
    n_runs: int
    successes: List[bool] = field(default_factory=list)
    latencies: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if not self.successes:
            return 0.0
        return sum(self.successes) / len(self.successes)

    @property
    def mean_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0

    @property
    def p50_latency(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0


class ChaosTester:
    """Chaos 测试框架"""

    def __init__(self, agent_factory: Callable):
        """
        Args:
            agent_factory: 智能体工厂函数，每次返回新实例
        """
        self.agent_factory = agent_factory

    def inject_network_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """注入网络延迟"""
        delay = random.uniform(min_ms, max_ms) / 1000
        time.sleep(delay)

    def inject_tool_failure(self, failure_rate: float = 0.3) -> bool:
        """
        随机让工具失败

        Returns:
            True = 工具失败, False = 工具正常
        """
        return random.random() < failure_rate

    def inject_input_truncate(self, task: str, ratio: float = 0.5) -> str:
        """
        截断输入

        Args:
            task: 原始任务
            ratio: 截断比例（0.5 = 截断前 50%）

        Returns:
            截断后的任务
        """
        if ratio <= 0 or ratio >= 1:
            return task
        truncate_len = int(len(task) * ratio)
        return task[truncate_len:]

    def run_chaos_test(self, task: str, config: ChaosConfig,
                       n_runs: int = 30) -> ChaosResult:
        """
        运行 Chaos 测试

        Args:
            task: 任务描述
            config: Chaos 配置
            n_runs: 运行次数

        Returns:
            ChaosResult
        """
        result = ChaosResult(config=config, n_runs=n_runs)

        for i in range(n_runs):
            agent = self.agent_factory()

            # 注入网络延迟
            if config.network_delay_max_ms > 0:
                self.inject_network_delay(
                    config.network_delay_min_ms,
                    config.network_delay_max_ms,
                )

            # 截断输入
            actual_task = self.inject_input_truncate(task, config.input_truncate_ratio)

            # 执行任务
            start = time.time()
            try:
                # 注入工具失败（如果配置了）
                if config.tool_failure_rate > 0:
                    # 这里需要在智能体执行过程中注入
                    # 实际使用时需要修改智能体的工具调用逻辑
                    pass

                run_result = agent.run(actual_task)
                elapsed = time.time() - start

                result.successes.append(run_result.get("success", False))
                result.latencies.append(elapsed)

                if not run_result.get("success"):
                    result.errors.append(run_result.get("error", "未知错误"))

            except Exception as e:
                elapsed = time.time() - start
                result.successes.append(False)
                result.latencies.append(elapsed)
                result.errors.append(str(e))

        return result

    def compare_baseline(self, task: str, n_runs: int = 30) -> Dict:
        """
        对比基准（无扰动）vs 有扰动

        Args:
            task: 任务描述
            n_runs: 运行次数

        Returns:
            {
                "baseline": 基准结果,
                "chaos": 有扰动结果,
                "delta": 差异,
            }
        """
        # 基准测试（无扰动）
        baseline_config = ChaosConfig()
        baseline = self.run_chaos_test(task, baseline_config, n_runs)

        # Chaos 测试（有扰动）
        chaos_config = ChaosConfig(
            network_delay_min_ms=500,
            network_delay_max_ms=2000,
            tool_failure_rate=0.3,
            input_truncate_ratio=0.3,
        )
        chaos = self.run_chaos_test(task, chaos_config, n_runs)

        return {
            "baseline": {
                "success_rate": baseline.success_rate,
                "mean_latency": baseline.mean_latency,
                "p50_latency": baseline.p50_latency,
            },
            "chaos": {
                "success_rate": chaos.success_rate,
                "mean_latency": chaos.mean_latency,
                "p50_latency": chaos.p50_latency,
            },
            "delta": {
                "success_rate_delta": chaos.success_rate - baseline.success_rate,
                "latency_delta": chaos.mean_latency - baseline.mean_latency,
            },
        }


def test_seed_stability(agent_factory, task: str,
                        seeds: range = range(1, 51)) -> Dict:
    """
    随机种子扰动测试

    Args:
        agent_factory: 智能体工厂函数
        task: 任务描述
        seeds: 种子范围

    Returns:
        {
            "seeds_tested": 测试种子数,
            "success_rates": 各种子成功率列表,
            "mean_success_rate": 平均成功率,
            "std_success_rate": 成功率标准差,
            "min_success_rate": 最低成功率,
            "max_success_rate": 最高成功率,
        }
    """
    success_rates = []

    for seed in seeds:
        agent = agent_factory()
        # 设置种子（如果智能体支持）
        if hasattr(agent, 'set_seed'):
            agent.set_seed(seed)

        # 每个种子跑 5 次
        n_sub_runs = 5
        successes = 0
        for _ in range(n_sub_runs):
            agent.reset()
            result = agent.run(task)
            if result.get("success"):
                successes += 1

        rate = successes / n_sub_runs
        success_rates.append(rate)

    return {
        "seeds_tested": len(seeds),
        "success_rates": success_rates,
        "mean_success_rate": statistics.mean(success_rates),
        "std_success_rate": statistics.stdev(success_rates) if len(success_rates) > 1 else 0,
        "min_success_rate": min(success_rates),
        "max_success_rate": max(success_rates),
    }


def print_chaos_report(baseline: Dict, chaos_result: Dict):
    """打印 Chaos 测试报告"""
    print(f"\n{'='*60}")
    print(f"Chaos 测试报告")
    print(f"{'='*60}")

    print(f"\n基准（无扰动）:")
    print(f"  成功率: {baseline['baseline']['success_rate']:.0%}")
    print(f"  平均延迟: {baseline['baseline']['mean_latency']:.1f}s")
    print(f"  P50 延迟: {baseline['baseline']['p50_latency']:.1f}s")

    print(f"\n有扰动:")
    print(f"  成功率: {baseline['chaos']['success_rate']:.0%}")
    print(f"  平均延迟: {baseline['chaos']['mean_latency']:.1f}s")
    print(f"  P50 延迟: {baseline['chaos']['p50_latency']:.1f}s")

    print(f"\n差异:")
    delta = baseline['delta']
    print(f"  成功率变化: {delta['success_rate_delta']:+.0%}")
    print(f"  延迟变化: {delta['latency_delta']:+.1f}s")

    if delta['success_rate_delta'] < -0.2:
        print(f"  ⚠  成功率下降超过 20%，鲁棒性不足")
    elif delta['success_rate_delta'] < -0.1:
        print(f"  ⚠  成功率下降 10-20%，需要优化")
    else:
        print(f"   成功率下降 <10%，鲁棒性良好")

    print(f"{'='*60}\n")


def run_demo():
    """演示"""
    print("=" * 60)
    print("稳定性与鲁棒性测试演示")
    print("=" * 60)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from agents.custom_agent.agent import CustomAgent

    def agent_factory():
        return CustomAgent(temperature=0.3)

    tester = ChaosTester(agent_factory)

    # 对比基准 vs 有扰动
    print("\n--- 基准 vs 有扰动对比 ---")
    baseline = tester.compare_baseline("查询本月销售额并生成趋势报告", n_runs=10)
    print_chaos_report(baseline, {})

    # 种子扰动测试（简化版）
    print("\n--- 随机种子扰动测试（5 个种子）---")
    seed_result = test_seed_stability(agent_factory, "查询本月销售额并生成趋势报告", seeds=range(1, 6))
    print(f"  测试种子数: {seed_result['seeds_tested']}")
    print(f"  平均成功率: {seed_result['mean_success_rate']:.0%}")
    print(f"  成功率标准差: {seed_result['std_success_rate']:.0%}")
    print(f"  最低成功率: {seed_result['min_success_rate']:.0%}")
    print(f"  最高成功率: {seed_result['max_success_rate']:.0%}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_demo()
