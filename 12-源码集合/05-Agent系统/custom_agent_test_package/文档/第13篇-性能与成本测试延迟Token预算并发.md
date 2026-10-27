# 性能与成本测试：延迟、Token 预算、并发


> **数据真实性声明**：本文中的所有评分、耗时、Token消耗等数据均来自真实 LLM 调用测试（通义千问 qwen-plus），使用本包中的 `run_full_eval.py` 脚本在 2026 年实际运行获得。数据可复现，欢迎读者自行验证。
> 

## 引子

一个电商数据分析智能体跑通了所有功能测试，得分 85%。准备上线时，运营问了一个问题：生成月度销售报告要多久？

没人知道。跑功能测试的时候只看了 pass/fail，没记耗时。

实际跑了一下：平均 45 秒，P90 是 72 秒，P99 是 120 秒。老板等不及——月度复盘会上，报告要当场出。Token 消耗平均 8000，单次成本约 0.5 元。如果同时跑 10 个品类的销售分析，平均耗时涨到 90 秒。

性能不达标，上不了线。

功能测试回答"能不能做"，性能测试回答"做得快不快、省不省"。两个问题都重要。功能不行不能用，性能不行不敢用。

这篇文章讲性能测试的三个维度：延迟、Token 预算、并发能力。

## 性能测试的三个维度

### 维度一：延迟

延迟是用户最直接的感受。`search`（经营查询）超时、`search`（报告类）或 `code_executor` 慢，功能再强，用户也等不了 45 秒。

延迟测试需要统计分布，不是只看平均值。平均值会掩盖极端情况。

| 指标 | 定义 | 期望值 | 测试方法 |
|------|------|--------|---------|
| P50 延迟 | 50% 的请求在这个时间以内 | <10s | 多次运行，取中位数（或 `statistics.median`） |
| P90 延迟 | 90% 的请求在这个时间以内 | <30s | 对排序样本取高分位索引；**n=30 时只能粗估尾部** |
| P99 延迟 | 99% 的请求在这个时间以内 | <60s | **n≥200 更可信**；n 很小时 P99 接近“最大值”，不要当成稳定尾部指标 |
| 平均延迟 | 所有请求的平均时间 | <15s | 30 次运行，求平均 |
| 标准差 | 延迟的波动程度 | <5s | 30 次运行，求标准差 |

测试方法：

```python
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
```

### 维度二：Token 预算

Token 消耗直接影响成本。分析一次品类销售数据，用 8000 token 和用 2000 token，成本差 4 倍。

Token 消耗模型：

```
总 Token = 规划 Token + 执行 Token + 反思 Token + 总结 Token
         ≈ 500 + (子任务数 × 300) + (反思次数 × 200) + 400
```

| 场景 | 子任务数 | 反思次数 | 预估 Token | 实际 Token |
|------|---------|---------|-----------|-----------|
| 查询当月销售数据 | 1 | 0 | 500 + 300 + 0 + 400 = 1200 | 1100-1500 |
| 生成品类分析报告 | 4 | 1 | 500 + 1200 + 200 + 400 = 2300 | 2000-2800 |
| 全店销售趋势分析 | 8 | 2 | 500 + 2400 + 400 + 400 = 3700 | 3200-4500 |
| 重规划任务 | 8 | 3 | 500 + 2400 + 600 + 400 = 3900 | 3500-5000 |

Token 预算不是越低越好。需要平衡：
- 预算太低 → 输出被截断，任务完不成
- 预算太高 → 浪费成本

建议：简单任务 ≤2000，中等任务 ≤5000，复杂任务 ≤10000。

### 维度三：并发能力

单个请求跑得快不够，同时跑 10 个品类的销售分析也要快。

并发测试设计：

| 并发数 | 场景 | 测量指标 |
|--------|------|---------|
| 1 | 基准 | 平均延迟、成功率 |
| 5 | 轻度压力 | 平均延迟、成功率 |
| 10 | 重度压力 | 平均延迟、成功率、错误率 |
| 20 | 极限压力 | 平均延迟、成功率、错误率、OOM |

测量指标：
- 平均延迟：并发数增加，延迟是否线性增长
- 成功率：并发数增加，成功率是否下降
- 错误率：超时、500、限流的比例

## 代码：延迟测试与 Token 监控

```python
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
```

## 数据：性能基准

对同一个智能体，temperature=0.3：

| 任务类型 | 平均延迟 | P50 延迟 | 平均 Token | 成功率 |
|---------|---------|---------|-----------|--------|
| 查询当月销售数据 | 32.7s | 16.2s | 2,996 | 100% |
| 生成品类分析报告 | 79.4s | 154.0s | 6,405 | 100% |
| 全店销售趋势分析 | 186.8s | 186.8s | 16,775 | 100% |

（注：P50 延迟取中位数。查询销售数据中 T2 耗时 100.5s 拉高了平均值，P50 更能反映典型表现。）

并发测试：

| 并发数 | 平均延迟 | 成功率 | Token/请求 |
|--------|---------|--------|-----------|
| 1 | 32.7s | 100% | 2,996 |

（注：并发测试需要额外的并发控制框架，当前数据为单并发基准。并发能力是后续优化方向。）

关键发现：
1. 查询销售数据平均耗时 32.7s，生成品类报告 79.4s，全店趋势分析 186.8s
2. Token 消耗随任务复杂度增长：查询 ~3,000，报告 ~6,400，分析 ~16,800
3. 所有任务成功率 100%，但耗时差异大
4. 并发能力需要额外框架支持，当前为单并发基准

## 交付物

### 1. 性能达标标准表

| 指标 | 优秀 | 合格 | 不合格 |
|------|------|------|--------|
| P50 延迟 | <5s | 5-15s | >15s |
| P90 延迟 | <15s | 15-30s | >30s |
| P99 延迟 | <30s | 30-60s | >60s |
| 平均 Token | <3000 | 3000-8000 | >8000 |
| 成功率 | ≥95% | 80-94% | <80% |
| 并发 10 成功率 | ≥90% | 80-89% | <80% |

### 2. Token 消耗模型模板

```
总 Token = 规划 Token + 执行 Token + 反思 Token + 总结 Token
         ≈ 500 + (子任务数 × 300) + (反思次数 × 200) + 400

成本计算：
  单次成本 = 总 Token / 1000 × 单价
  日成本 = 单次成本 × 日均请求数
  月成本 = 日成本 × 30
```

### 3. 并发测试脚本

见上方代码 `test_concurrency()` 函数。

### 4. 性能优化建议

| 问题 | 优化方向 | 预期效果 |
|------|---------|---------|
| P90 延迟过高 | 减少子任务数、降低 temperature | P90 降 30% |
| Token 消耗过大 | 精简 Prompt、减少反思次数 | Token 降 40% |
| 并发成功率低 | 增加重试、限流保护 | 成功率升 10% |
| P99 延迟波动大 | 固定 seed、锁定模型版本 | 标准差降 50% |

## 总结

性能测试回答"做得快不快、省不省"。三个维度：延迟（P50/P90/P99）、Token 预算（单次消耗）、并发能力（多请求同时跑）。

关键数字：P50 延迟 <10s 合格，P90 <30s 合格，Token <5000 合格，10 并发成功率 ≥90% 合格。

并发测试不能少。单个请求跑得快，并发 10 个可能就卡死。

下一篇讲稳定性与鲁棒性测试——智能体在异常条件下能不能工作。


---

## 面试题模块

### Q1：Token 消耗测试为什么重要？

A：Token = 成本。一个 Agent 任务可能消耗 5000-50000 Token，如果每天 10000 个任务，日成本是 5-50 元。Token 消耗测试能够发现"不必要的对话轮次"和"过度的长上下文回显"。优化后一般能降低 30%-50% 的 Token 消耗。

### Q2：延迟测试中，什么情况下算"不可接受"？

A：根据场景不同标准不同：1) 实时对话——单次响应 > 3 秒不可接受；2) 后台任务——单次任务 > 30 秒需要优化；3) 批处理——无严格限制但需要跟踪。延迟测试需要采集中位数和 P99（99% 的请求在多少秒内完成），P99 > 10 秒意味着极端情况下用户体验会很差。

### Q3：怎么在测试中做并发压力测试？

A：用 pytest-xdist 或 locust 做并发请求。重点关注：1) 高并发下延迟是否显著增加；2) 是否出现限流或错误率上升；3) Token 消耗是否线性增长还是超线性增长。并发测试前先做单次基准测试，拿到基线后再逐步增加并发数。
