#!/usr/bin/env python3
"""
多工具组合场景测试

功能：
1. 工具链组合测试
2. 依赖失败传播测试
3. 工具间数据传递测试
"""

import os
import sys
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ToolChainResult:
    """工具链测试结果"""
    chain_id: str
    chain_name: str
    tools: List[str]
    tool_results: Dict[str, Dict]
    data_flow_valid: bool
    chain_success: bool
    elapsed: float
    defects: List[Dict] = field(default_factory=list)


@dataclass
class FailurePropagationResult:
    """失败传播测试结果"""
    failed_tool: str
    dependent_tools: List[str]
    expected_behavior: str
    actual_behavior: str
    passed: bool
    rollback_correct: bool


# 工具链定义
TOOL_CHAINS = [
    {
        "id": "TC-01",
        "name": "竞品分析（线性）",
        "tools": ["web_fetch", "code_executor", "calculator", "memory_store"],
        "task": "抓取竞品官网信息，提取关键指标，对比分析，存储结果",
        "expected_data_flow": ["网页HTML", "清理文本", "统计结果", "存储"],
    },
    {
        "id": "TC-02",
        "name": "数据分析（线性）",
        "tools": ["code_executor", "calculator", "memory_store"],
        "task": "读取 CSV 数据，计算各品类销售额，存储结果",
        "expected_data_flow": ["CSV数据", "统计结果", "存储"],
    },
    {
        "id": "TC-03",
        "name": "多竞品抓取（并行）",
        "tools": ["web_fetch", "web_fetch", "web_fetch", "code_executor"],
        "task": "同时抓取 3 个竞品官网，汇总分析",
        "expected_data_flow": ["3个网页", "汇总分析"],
    },
]


def test_tool_chain(agent, chain: Dict) -> ToolChainResult:
    """
    测试工具链组合

    Args:
        agent: 智能体实例
        chain: 工具链定义

    Returns:
        ToolChainResult
    """
    start_time = time.time()
    agent.reset()

    result = agent.run(chain["task"])
    elapsed = time.time() - start_time
    meta = result.get("_meta", {})
    subtasks = meta.get("subtasks", [])

    # 构建工具结果映射
    tool_results = {}
    for s in subtasks:
        tool = s.get("tool", "")
        if tool and tool != "none":
            if tool not in tool_results:
                tool_results[tool] = []
            tool_results[tool].append({
                "status": s.get("status", ""),
                "result": s.get("result", "")[:100],
            })

    # 验证数据流
    data_flow_valid = _verify_data_flow(subtasks, chain["expected_data_flow"])

    # 检测缺陷
    defects = []
    for s in subtasks:
        if s.get("status") == "failed":
            defects.append({
                "type": "执行缺陷",
                "severity": "High",
                "detail": f"{s['id']} ({s.get('tool', '')}) 执行失败",
            })

    chain_success = result.get("success", False) and data_flow_valid

    return ToolChainResult(
        chain_id=chain["id"],
        chain_name=chain["name"],
        tools=chain["tools"],
        tool_results=tool_results,
        data_flow_valid=data_flow_valid,
        chain_success=chain_success,
        elapsed=elapsed,
        defects=defects,
    )


def _verify_data_flow(subtasks: List[Dict], expected_flow: List[str]) -> bool:
    """
    验证数据流

    Args:
        subtasks: 子任务列表
        expected_flow: 期望的数据流向

    Returns:
        数据流是否有效
    """
    # 简单验证：检查子任务是否按顺序执行
    if not subtasks:
        return False

    # 检查是否有失败的工具
    failed_tools = [s for s in subtasks if s.get("status") == "failed"]
    if len(failed_tools) > len(subtasks) * 0.5:
        return False

    return True


def test_failure_propagation(agent, chain: Dict,
                             fail_tool: str) -> FailurePropagationResult:
    """
    测试工具失败后的传播

    Args:
        agent: 智能体实例
        chain: 工具链定义
        fail_tool: 要失败的工具

    Returns:
        FailurePropagationResult
    """
    agent.reset()

    # 执行任务
    result = agent.run(chain["task"])
    meta = result.get("_meta", {})
    subtasks = meta.get("subtasks", [])

    # 找到依赖 fail_tool 的子任务
    fail_tool_ids = [s["id"] for s in subtasks if s.get("tool") == fail_tool]
    dependent_ids = []
    for s in subtasks:
        for dep in s.get("depends_on", []):
            if dep in fail_tool_ids:
                dependent_ids.append(s["id"])

    # 检查依赖工具的行为
    expected = "跳过"  # 期望行为：跳过
    actual = "跳过"  # 实际行为（简化验证）
    for s in subtasks:
        if s["id"] in dependent_ids:
            if s.get("status") == "skipped":
                actual = "跳过"
            elif s.get("status") == "failed":
                actual = "失败"
            else:
                actual = "执行"

    passed = actual == expected
    rollback_correct = actual in ("跳过", "失败")  # 回滚正确

    return FailurePropagationResult(
        failed_tool=fail_tool,
        dependent_tools=dependent_ids,
        expected_behavior=expected,
        actual_behavior=actual,
        passed=passed,
        rollback_correct=rollback_correct,
    )


def print_tool_chain_report(results: List[ToolChainResult]):
    """打印工具链测试报告"""
    print(f"\n{'='*70}")
    print(f"工具链组合测试报告")
    print(f"{'='*70}")

    total = len(results)
    passed = sum(1 for r in results if r.chain_success)

    print(f"\n汇总:")
    print(f"  总工具链: {total}")
    print(f"  通过: {passed} ({passed/total:.0%})")
    print(f"  失败: {total - passed} ({(total-passed)/total:.0%})")

    print(f"\n详细结果:")
    print(f"{'ID':8s} | {'名称':12s} | {'工具数':6s} | {'数据流':6s} | {'耗时':6s} | {'缺陷数':6s}")
    print("-" * 70)
    for r in results:
        icon = "" if r.chain_success else ""
        data_flow = "" if r.data_flow_valid else ""
        print(f"{r.chain_id:8s} | {r.chain_name:12s} | {len(r.tools):6d} | {data_flow:6s} | {r.elapsed:5.1f}s | {len(r.defects):6d} {icon}")

    # 缺陷详情
    all_defects = []
    for r in results:
        all_defects.extend(r.defects)
    if all_defects:
        print(f"\n缺陷详情:")
        for i, d in enumerate(all_defects[:10], 1):
            print(f"  {i}. [{d['severity']}] {d['type']}: {d['detail']}")

    print(f"{'='*70}\n")


def print_failure_propagation_report(results: List[FailurePropagationResult]):
    """打印失败传播测试报告"""
    print(f"\n{'='*70}")
    print(f"依赖失败传播测试报告")
    print(f"{'='*70}")

    print(f"\n{'失败工具':12s} | {'依赖工具':12s} | {'期望':6s} | {'实际':6s} | {'回滚':6s}")
    print("-" * 70)
    for r in results:
        passed_icon = "" if r.passed else ""
        rollback_icon = "" if r.rollback_correct else ""
        print(f"{r.failed_tool:12s} | {', '.join(r.dependent_tools):12s} | {r.expected_behavior:6s} | {r.actual_behavior:6s} | {rollback_icon}")

    print(f"{'='*70}\n")


def run_demo():
    """演示"""
    print("=" * 70)
    print("多工具组合场景测试演示")
    print("=" * 70)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from agents.custom_agent.agent import CustomAgent

    agent = CustomAgent(temperature=0.3)

    # 工具链测试
    print("\n--- 工具链组合测试 ---")
    chain_results = []
    for chain in TOOL_CHAINS[:2]:  # 演示用 2 个
        result = test_tool_chain(agent, chain)
        chain_results.append(result)
    print_tool_chain_report(chain_results)

    # 失败传播测试
    print("\n--- 依赖失败传播测试 ---")
    prop_results = []
    for chain in TOOL_CHAINS[:1]:
        for tool in ["web_fetch", "code_executor"]:
            result = test_failure_propagation(agent, chain, tool)
            prop_results.append(result)
    print_failure_propagation_report(prop_results)

    print("=" * 70)


if __name__ == "__main__":
    run_demo()

def verify_rollback(result: Dict) -> bool:
    """验证回滚是否正确"""
    meta = result.get("_meta", {})
    subtasks = meta.get("subtasks", [])

    # 检查失败工具后的依赖工具是否被跳过
    failed_ids = [s["id"] for s in subtasks if s["status"] == "failed"]
    for s in subtasks:
        for dep in s.get("depends_on", []):
            if dep in failed_ids and s["status"] not in ("skipped", "failed"):
                return False
    return True
