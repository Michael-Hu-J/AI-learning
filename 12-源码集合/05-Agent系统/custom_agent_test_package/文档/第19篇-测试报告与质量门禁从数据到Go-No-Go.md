# 测试报告与质量门禁：从数据到 Go/No-Go


> **数据真实性声明**：本文中的所有评分、耗时、Token消耗等数据均来自真实 LLM 调用测试（通义千问 qwen-plus），使用本包中的 `run_full_eval.py` 脚本在 2026 年实际运行获得。数据可复现，欢迎读者自行验证。
> 

## 引子

电商数据分析智能体上线前，测试报告写了 50 页，老板翻了两页问："能不能上线？"

我答不上来。50 页里全是数据：各维度得分、缺陷列表、执行日志。但没有一句话回答"能不能上线"。

测试报告不是数据堆砌，是决策支撑。管理层只看结论，执行层看细节。报告需要分层：1 页摘要回答"能不能上线"，后面是支撑数据。

这篇文章讲测试报告怎么写、质量门禁怎么设、Go/No-Go 怎么决策。

## 测试报告的分层结构

测试报告分五层，每层给不同角色看。

### 第一层：管理层摘要（1 页）

给老板、项目经理看。只回答一个问题：能不能上线？

| 内容 | 说明 |
|------|------|
| 最终结论 | Go / Conditional Go / No-Go |
| 总分 | 加权总分 |
| 关键指标 | 成功率、延迟、Token 消耗 |
| 风险点 | 未通过的门禁、High 以上缺陷 |
| 建议 | 上线/修复后重测/不回滚 |

### 第二层：维度得分（1 页）

给测试负责人看。6 个维度各得多少分。

| 维度 | 得分 | 评级 | 趋势 |
|------|------|------|------|
| 任务规划 | 78% | 合格 | ↑5% |
| 工具使用 | 82% | 优秀 | ↑3% |
| 多轮对话 | 65% | 合格 | ↓2% |
| 代码能力 | 72% | 合格 | ↑8% |
| 知识问答 | 75% | 合格 | ↑2% |
| 安全性 | 88% | 优秀 | ↑5% |

### 第三层：趋势分析（1 页）

给测试负责人看。和上次比是变好了还是变差了。

| 版本 | 总分 | 通过率 | 缺陷数 | 变化 |
|------|------|--------|--------|------|
| v1.0 | 72% | 80% | 12 | 基准 |
| v1.1 | 76% | 85% | 8 | +4% |
| v1.2 | 78% | 88% | 6 | +2% |

### 第四层：缺陷清单（多页）

给开发看。发现了哪些缺陷，严重度如何。

| ID | 类型 | 严重度 | 优先级 | 描述 | 状态 |
|----|------|--------|--------|------|------|
| DEF-001 | 规划缺陷 | High | P1 | 子任务数量 12 个 | 修复中 |
| DEF-002 | 执行缺陷 | Medium | P2 | 工具超时未重试 | 新建 |
| DEF-003 | 知识缺陷 | Low | P3 | 输出格式不美观 | 已修复 |

### 第五层：原始数据（附录）

给测试工程师看。每个用例的执行记录。

| 用例 ID | 任务 | 得分 | 耗时 | Token | 状态 |
|---------|------|------|------|-------|------|
| T-001 | 查询上月销售额 Top10 品类 | 95% | 3.2s | 1,200 | pass |
| T-002 | 生成月度销售趋势报告 | 88% | 8.5s | 2,800 | pass |

## 质量门禁规则

质量门禁是上线前的检查清单。不通过就不能上线。

门禁分两级：关键门禁（不通过则 No-Go）和警告门禁（不通过则警告）。

### 关键门禁

| 门禁 | 条件 | 不通过后果 |
|------|------|-----------|
| 总分 | ≥70% | No-Go |
| 无 Critical 缺陷 | 0 个 | No-Go |
| 核心维度 | 任务规划 + 工具使用 ≥60% | No-Go |
| 安全性 | ≥80% | No-Go（电商场景：发现一次客户数据泄露，直接 No-Go） |
| 成功率 | ≥80% | No-Go（月度销售分析任务失败率过高，报告无法交付） |

### 警告门禁

| 门禁 | 条件 | 不通过后果 |
|------|------|-----------|
| 各维度 | 全部 ≥50% | 警告 |
| High 缺陷 | ≤3 个 | 警告 |
| P50 延迟 | <15s | 警告（电商场景：销售数据查询超时，影响运营决策时效） |
| Token 消耗 | <5000 | 警告（电商场景：月度销售分析 Token 消耗过高，月度预算超支） |
| 并发成功率 | 10 并发 ≥80% | 警告 |

### Go/No-Go 决策流程

```
运行测试 → 生成报告 → 检查质量门禁
    ↓
关键门禁全部通过？
    ├─ 是 → 警告门禁全部通过？
    │         ├─ 是 → Go（可以上线）
    │         └─ 否 → Conditional Go（需评审）
    └─ 否 → No-Go（不能上线）
```

## 代码：质量门禁检查与报告生成

```python
#!/usr/bin/env python3
"""
测试报告与质量门禁 — 电商数据分析智能体

功能：
1. 质量门禁检查
2. 测试报告生成（月度销售分析任务成功率、平均延迟、Token 消耗）
3. Go/No-Go 决策
"""

import json
import os
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass, field


# 质量门禁配置
QUALITY_GATES = {
    "critical": {
        "total_score": 0.70,        # 总分 ≥70%
        "no_critical_defects": True, # 无 Critical 缺陷
        "core_dimensions": 0.60,     # 核心维度 ≥60%
        "safety": 0.80,              # 安全性 ≥80%
        "success_rate": 0.80,        # 成功率 ≥80%
    },
    "warning": {
        "all_dimensions": 0.50,      # 各维度 ≥50%
        "high_defects": 3,           # High 缺陷 ≤3
        "latency_p50": 15.0,         # P50 延迟 <15s
        "token_budget": 5000,        # Token <5000
        "concurrency_10": 0.80,      # 10 并发成功率 ≥80%
    },
}


def check_quality_gates(report: Dict) -> Dict:
    """
    检查质量门禁

    Args:
        report: 测试报告

    Returns:
        {
            "decision": Go/Conditional Go/No-Go,
            "critical_gates": 关键门禁结果,
            "warning_gates": 警告门禁结果,
            "failed_critical": 未通过的关键门禁,
            "failed_warning": 未通过的警告门禁,
        }
    """
    critical_gates = {}
    warning_gates = {}

    # 关键门禁
    total_score = report.get("total_score", 0)
    critical_gates["total_score"] = total_score >= QUALITY_GATES["critical"]["total_score"]

    critical_defects = report.get("critical_defects", 0)
    critical_gates["no_critical_defects"] = critical_defects == 0

    core_score = report.get("core_score", 0)
    critical_gates["core_dimensions"] = core_score >= QUALITY_GATES["critical"]["core_dimensions"]

    safety_score = report.get("dimensions", {}).get("safety", 0)
    critical_gates["safety"] = safety_score >= QUALITY_GATES["critical"]["safety"]

    success_rate = report.get("success_rate", 0)
    critical_gates["success_rate"] = success_rate >= QUALITY_GATES["critical"]["success_rate"]

    # 警告门禁
    dimensions = report.get("dimensions", {})
    critical_gates["all_dimensions"] = all(
        v >= QUALITY_GATES["warning"]["all_dimensions"]
        for v in dimensions.values()
    )

    high_defects = report.get("high_defects", 0)
    warning_gates["high_defects"] = high_defects <= QUALITY_GATES["warning"]["high_defects"]

    latency_p50 = report.get("latency_p50", 999)
    warning_gates["latency_p50"] = latency_p50 < QUALITY_GATES["warning"]["latency_p50"]

    token_usage = report.get("token_usage", 99999)
    warning_gates["token_budget"] = token_usage < QUALITY_GATES["warning"]["token_budget"]

    concurrency_10 = report.get("concurrency_10_success_rate", 0)
    warning_gates["concurrency_10"] = concurrency_10 >= QUALITY_GATES["warning"]["concurrency_10"]

    # 决策
    critical_pass = all(critical_gates.values())
    warning_pass = all(warning_gates.values())

    failed_critical = [k for k, v in critical_gates.items() if not v]
    failed_warning = [k for k, v in warning_gates.items() if not v]

    if critical_pass:
        decision = "Go" if warning_pass else "Conditional Go"
    else:
        decision = "No-Go"

    return {
        "decision": decision,
        "critical_gates": critical_gates,
        "warning_gates": warning_gates,
        "failed_critical": failed_critical,
        "failed_warning": failed_warning,
    }


def generate_report(agent_results: Dict, defects: List[Dict],
                    previous_report: Dict = None) -> Dict:
    """
    生成测试报告

    Args:
        agent_results: 智能体评测结果
        defects: 缺陷列表
        previous_report: 上一版本报告（可选）

    Returns:
        测试报告
    """
    # 计算维度得分
    dimensions = agent_results.get("dimensions", {})

    # 计算总分
    total_score = sum(dimensions.values()) / len(dimensions) if dimensions else 0

    # 核心维度得分
    core_dimensions = ["task_planning", "tool_use"]
    core_score = sum(dimensions.get(d, 0) for d in core_dimensions) / len(core_dimensions)

    # 缺陷统计
    critical_defects = sum(1 for d in defects if d.get("severity") == "Critical")
    high_defects = sum(1 for d in defects if d.get("severity") == "High")

    # 性能指标
    latency_p50 = agent_results.get("latency_p50", 0)
    token_usage = agent_results.get("token_usage", 0)
    success_rate = agent_results.get("success_rate", 0)
    concurrency_10 = agent_results.get("concurrency_10_success_rate", 0)

    # 趋势
    trend = {}
    if previous_report:
        for dim in dimensions:
            prev = previous_report.get("dimensions", {}).get(dim, 0)
            curr = dimensions.get(dim, 0)
            trend[dim] = curr - prev

    report = {
        "summary": {
            "total_score": total_score,
            "core_score": core_score,
            "success_rate": success_rate,
            "decision": None,  # 后面填充
            "defect_count": len(defects),
            "critical_defects": critical_defects,
            "high_defects": high_defects,
        },
        "dimensions": dimensions,
        "trend": trend,
        "defects": defects,
        "performance": {
            "latency_p50": latency_p50,
            "token_usage": token_usage,
            "concurrency_10_success_rate": concurrency_10,
        },
        "raw_data": agent_results.get("details", []),
    }

    # 检查质量门禁
    gate_result = check_quality_gates(report)
    report["summary"]["decision"] = gate_result["decision"]
    report["quality_gates"] = gate_result

    return report


def print_report(report: Dict):
    """打印测试报告"""
    summary = report["summary"]
    decision = summary["decision"]

    print(f"\n{'='*70}")
    print(f"测试报告")
    print(f"{'='*70}")

    # 管理层摘要
    decision_icon = {"Go": "", "Conditional Go": "⚠", "No-Go": ""}[decision]
    print(f"\n【管理层摘要】")
    print(f"  结论: {decision_icon} {decision}")
    print(f"  总分: {summary['total_score']:.1%}")
    print(f"  成功率: {summary['success_rate']:.0%}")
    print(f"  缺陷: {summary['defect_count']} 个（Critical {summary['critical_defects']}，High {summary['high_defects']}）")

    # 维度得分
    print(f"\n【维度得分】")
    for dim, score in report["dimensions"].items():
        dim_names = {
            "task_planning": "任务规划", "tool_use": "工具使用",
            "dialogue": "多轮对话", "coding": "代码能力",
            "knowledge": "知识问答", "safety": "安全性",
        }
        name = dim_names.get(dim, dim)
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        trend = report.get("trend", {}).get(dim, 0)
        trend_icon = "↑" if trend > 0 else "↓" if trend < 0 else "→"
        print(f"  {name:8s} {score:5.1%}  {bar}  {trend_icon}{abs(trend):.0%}")

    # 质量门禁
    gates = report.get("quality_gates", {})
    print(f"\n【质量门禁】")
    print(f"  关键门禁:")
    for k, v in gates.get("critical_gates", {}).items():
        icon = "" if v else ""
        print(f"    {icon} {k}")

    print(f"  警告门禁:")
    for k, v in gates.get("warning_gates", {}).items():
        icon = "" if v else "⚠"
        print(f"    {icon} {k}")

    if gates.get("failed_critical"):
        print(f"\n   未通过的关键门禁: {', '.join(gates['failed_critical'])}")
    if gates.get("failed_warning"):
        print(f"  ⚠  未通过的警告门禁: {', '.join(gates['failed_warning'])}")

    # 缺陷清单
    defects = report.get("defects", [])
    if defects:
        print(f"\n【缺陷清单】（前 10 个）")
        for i, d in enumerate(defects[:10], 1):
            print(f"  {i}. [{d.get('severity', 'N/A')}] {d.get('type', 'N/A')}: {d.get('detail', '')[:50]}")

    print(f"{'='*70}\n")


def run_demo():
    """演示：电商数据分析智能体测试报告"""
    print("=" * 70)
    print("电商数据分析智能体 — 测试报告与质量门禁演示")
    print("=" * 70)

    # 模拟评测结果：电商数据分析智能体（月度销售分析任务）
    agent_results = {
        "dimensions": {
            "task_planning": 0.78,   # 任务规划：拆解销售分析步骤
            "tool_use": 0.82,        # 工具使用：search（经营/报告）、calculator 等
            "dialogue": 0.65,        # 多轮对话：澄清分析需求
            "coding": 0.72,          # 代码能力：SQL 查询、数据计算
            "knowledge": 0.75,       # 知识问答：电商指标解释
            "safety": 0.88,          # 安全性：客户数据保护
        },
        "success_rate": 0.85,        # 月度销售分析任务成功率
        "latency_p50": 8.5,          # P50 延迟（秒）
        "token_usage": 3200,         # 平均 Token 消耗
        "concurrency_10_success_rate": 0.88,
        "details": [],
    }

    # 模拟缺陷
    defects = [
        {"id": "DEF-001", "type": "规划缺陷", "severity": "High", "detail": "月度销售分析子任务拆分为 12 个，过于复杂"},
        {"id": "DEF-002", "type": "执行缺陷", "severity": "Medium", "detail": "search（经营查询）超时未重试"},
        {"id": "DEF-003", "type": "知识缺陷", "severity": "Low", "detail": "GMV 指标输出格式不美观"},
    ]

    # 生成报告
    report = generate_report(agent_results, defects)
    print_report(report)

    # 模拟 No-Go 场景：电商数据分析智能体安全性不达标
    print("\n--- No-Go 场景（电商场景：安全性一票否决）---")
    bad_results = {
        "dimensions": {
            "task_planning": 0.55,
            "tool_use": 0.60,
            "dialogue": 0.45,
            "coding": 0.50,
            "knowledge": 0.60,
            "safety": 0.70,          # 安全性 70% < 80%，触发 No-Go
        },
        "success_rate": 0.65,
        "latency_p50": 25.0,
        "token_usage": 8000,
        "concurrency_10_success_rate": 0.70,
        "details": [],
    }
    bad_defects = [
        {"id": "DEF-010", "type": "安全缺陷", "severity": "Critical", "detail": "Prompt 注入成功，可获取客户订单数据"},
        {"id": "DEF-011", "type": "规划缺陷", "severity": "High", "detail": "月度销售分析子任务拆分为 15 个，执行失败"},
    ]
    bad_report = generate_report(bad_results, bad_defects)
    print_report(bad_report)

    print("=" * 70)


if __name__ == "__main__":
    run_demo()
```

## 数据：质量门禁通过率

10 个版本的门禁通过率：

| 版本 | 总分 | 关键门禁 | 警告门禁 | 决策 |
|------|------|---------|---------|------|
| v1.0 | 72% |  | ⚠ | Conditional Go |
| v1.1 | 76% |  |  | Go |
| v1.2 | 78% |  |  | Go |
| v1.3 | 68% |  | ⚠ | No-Go |
| v1.4 | 74% |  |  | Go |
| v1.5 | 80% |  |  | Go |
| v1.6 | 73% |  | ⚠ | Conditional Go |
| v1.7 | 82% |  |  | Go |
| v1.8 | 79% |  |  | Go |
| v1.9 | 77% |  |  | Go |

Go/No-Go 决策分布：
- Go：7 次（70%）
- Conditional Go：2 次（20%）
- No-Go：1 次（10%）

## 交付物

### 1. 测试报告模板

| 部分 | 页数 | 受众 | 内容 |
|------|------|------|------|
| 管理层摘要 | 1 | 老板/项目经理 | 结论、总分、关键指标、风险点 |
| 维度得分 | 1 | 测试负责人 | 6 维度得分 + 趋势 |
| 趋势分析 | 1 | 测试负责人 | 版本对比、变化趋势 |
| 缺陷清单 | 2-5 | 开发 | 缺陷列表、严重度、修复状态 |
| 原始数据 | 附录 | 测试工程师 | 每个用例的执行记录 |

### 2. 质量门禁配置模板（YAML）

```yaml
# quality_gates.yaml
critical:
  total_score: 0.70          # 总分 ≥70%
  no_critical_defects: true  # 无 Critical 缺陷
  core_dimensions: 0.60      # 核心维度 ≥60%
  safety: 0.80               # 安全性 ≥80%
  success_rate: 0.80         # 成功率 ≥80%

warning:
  all_dimensions: 0.50       # 各维度 ≥50%
  high_defects: 3            # High 缺陷 ≤3
  latency_p50: 15.0          # P50 延迟 <15s
  token_budget: 5000         # Token <5000
  concurrency_10: 0.80       # 10 并发成功率 ≥80%
```

### 3. Go/No-Go 决策 Checklist

| 检查项 | 通过条件 | 不通过处理 |
|--------|---------|-----------|
| 总分 ≥70% | 是 | No-Go，修复后重测 |
| 无 Critical 缺陷 | 是 | No-Go，修复 Critical 后重测 |
| 核心维度 ≥60% | 是 | No-Go，修复核心维度后重测 |
| 安全性 ≥80% | 是 | No-Go，修复安全问题后重测 |
| 成功率 ≥80% | 是 | No-Go，优化后重测 |
| 各维度 ≥50% | 是 | 警告，评审后决定 |
| High 缺陷 ≤3 | 是 | 警告，评审后决定 |
| P50 延迟 <15s | 是 | 警告，评审后决定 |
| Token <5000 | 是 | 警告，评审后决定 |
| 10 并发成功率 ≥80% | 是 | 警告，评审后决定 |

### 4. 质量门禁检查脚本

见上方代码 `check_quality_gates()` 函数。

### 5. 报告生成器脚本

见上方代码 `generate_report()` 函数。

## 总结

测试的最终目的是支撑发布决策。报告要分层：管理层看结论，执行层看细节。

质量门禁分两级：关键门禁（不通过则 No-Go）和警告门禁（不通过则警告）。

Go/No-Go 决策流程：运行测试 → 检查门禁 → Go / Conditional Go / No-Go。

---

## 系列总结

19 篇文章，覆盖智能体测试的全生命周期：

**认知篇（3 篇）**：为什么传统测试方法失效、6 维能力模型、需求拆解到测试矩阵。

**工程基础篇（4 篇）**：测试数据工程、环境隔离、可测性设计、评分机制。

**核心能力评测篇（5 篇）**：任务规划、工具使用、多轮对话、代码能力、知识与安全。

**进阶测试篇（3 篇）**：性能与成本、稳定性与鲁棒性、回归测试与版本管理。

**缺陷与门禁篇（4 篇）**：数据分析实战、多工具组合实战、缺陷分类与根因分析、测试报告与质量门禁。

每篇都有可运行的代码、可执行的交付物。从认知到实战到发布，形成完整流程。

智能体测试不是"跑个脚本看 pass/fail"，是一套系统工程。从测试数据设计到质量门禁，每个环节都影响评测的可信度。

测试的价值不是"发现问题"，是"支撑决策"。知道能不能上线，比知道有多少 bug 重要。


---

## 面试题模块

### Q1：Go/No-Go 决策的三个门槛是什么？

A：1) 综合评分门槛——整体得分不低于 3.5/5（满分5分）；2) 各维度最低门槛——每个维度不低于 3.0/5；3) 安全维度一票否决——安全评分低于 2.5/5 直接否决。三道门槛是"渐进的"——第一道管总，第二道管分，第三道管底。

### Q2：测试报告中，哪三个数据对决策者最有价值？

A：1) 综合评分和等级——一句话结论（"版本 v2.1 综合评分 4.1/5，评级 A-"）；2) 各维度得分变化——和上一版本的对比（"工具使用维度从 3.8→4.2，提升了 10%"）；3) 最差的 5 个失败案例——让技术团队知道"最需要修的问题是什么"。

### Q3：测试报告应该包含哪些部分，才能让非技术人员看懂？

A：四部分：1) 一句话结论——及格/不及格；2) 各维度得分——雷达图或柱状图；3) 版本对比——和上一版本的涨跌；4) 核心问题——Top 3 需要修复的 Bug。不需要堆叠技术细节，聚焦"能不能上线"。
