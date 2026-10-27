#!/usr/bin/env python3
"""
数据分析任务完整流程测试

测试流程：
1. 准备测试数据（CSV 文件）
2. 执行智能体
3. 验证结果
4. 生成测试报告
"""

import os
import sys
import csv
import json
import time
import random
from typing import Dict, List, Optional
from dataclasses import dataclass, field


# 生成测试 CSV 文件
def generate_test_csv(path: str, rows: int = 100, cols: int = 5,
                      has_nulls: bool = False, encoding: str = "utf-8"):
    """
    生成测试 CSV 文件

    Args:
        path: 文件路径
        rows: 行数
        cols: 列数
        has_nulls: 是否包含缺失值
        encoding: 文件编码
    """
    headers = ["日期", "品类", "销售额", "订单量", "利润"][:cols]

    categories = ["电子产品", "服装", "食品", "家居", "图书"]
    months = [f"2024-{i:02d}" for i in range(1, 13)]

    with open(path, "w", encoding=encoding, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i in range(rows):
            row = [
                random.choice(months),
                random.choice(categories),
                random.randint(100, 10000) if not (has_nulls and random.random() < 0.1) else "",
                random.randint(1, 100) if not (has_nulls and random.random() < 0.1) else "",
                random.randint(10, 2000) if not (has_nulls and random.random() < 0.1) else "",
            ]
            writer.writerow(row)


@dataclass
class FullChainTestResult:
    """完整流程测试结果"""
    test_id: str
    task: str
    difficulty: str
    planning_score: float
    tool_usage_score: float
    coding_score: float
    knowledge_score: float
    total_score: float
    passed: bool
    defects: List[Dict] = field(default_factory=list)
    elapsed: float = 0.0
    tokens: int = 0


def run_full_chain_test(agent, test_cases: List[Dict]) -> List[FullChainTestResult]:
    """
    运行完整流程测试

    Args:
        agent: 智能体实例
        test_cases: 测试用例列表

    Returns:
        测试结果列表
    """
    results = []

    for case in test_cases:
        start_time = time.time()
        agent.reset()

        result = agent.run(case["task"])
        elapsed = time.time() - start_time
        meta = result.get("_meta", {})

        # 规划评分
        planning_score = _score_planning(meta)
        # 工具使用评分
        tool_usage_score = _score_tool_usage(meta)
        # 代码能力评分
        coding_score = _score_coding(meta)
        # 知识问答评分
        knowledge_score = _score_knowledge(result)

        total_score = (planning_score * 0.25 + tool_usage_score * 0.25 +
                       coding_score * 0.25 + knowledge_score * 0.25)

        defects = _detect_defects(result, case)

        results.append(FullChainTestResult(
            test_id=case["id"],
            task=case["task"][:50],
            difficulty=case["difficulty"],
            planning_score=planning_score,
            tool_usage_score=tool_usage_score,
            coding_score=coding_score,
            knowledge_score=knowledge_score,
            total_score=total_score,
            passed=total_score >= 0.6,
            defects=defects,
            elapsed=elapsed,
            tokens=meta.get("tokens", 0),
        ))

    return results


def _score_planning(meta: Dict) -> float:
    """规划评分"""
    subtasks = meta.get("subtasks", [])
    n = len(subtasks)

    score = 0.0
    # 子任务数量（20 分）
    if 3 <= n <= 8:
        score += 0.20
    elif 1 <= n <= 10:
        score += 0.10

    # 依赖准确性（30 分）
    task_ids = {s["id"] for s in subtasks}
    deps_correct = sum(1 for s in subtasks for d in s.get("depends_on", []) if d in task_ids)
    deps_total = sum(len(s.get("depends_on", [])) for s in subtasks)
    if deps_total > 0:
        score += (deps_correct / deps_total) * 0.30
    else:
        score += 0.30

    # 工具选择（25 分）
    tools_correct = sum(1 for s in subtasks if s.get("tool") in ("code_executor", "calculator", "none"))
    tools_total = len(subtasks)
    if tools_total > 0:
        score += (tools_correct / tools_total) * 0.25

    # 执行完成（25 分）
    success = meta.get("subtasks_success", 0)
    total = meta.get("subtasks_total", len(subtasks))
    if total > 0:
        score += (success / total) * 0.25

    return min(score, 1.0)


def _score_tool_usage(meta: Dict) -> float:
    """工具使用评分"""
    subtasks = meta.get("subtasks", [])
    tools_correct = sum(1 for s in subtasks if s.get("tool") in ("code_executor", "calculator", "none", "memory_store"))
    tools_total = len([s for s in subtasks if s.get("tool") != "none"])

    if tools_total > 0:
        return min((tools_correct / tools_total) * 1.0, 1.0)
    return 1.0


def _score_coding(meta: Dict) -> float:
    """代码能力评分"""
    subtasks = meta.get("subtasks", [])
    code_tasks = [s for s in subtasks if s.get("tool") == "code_executor"]
    if code_tasks:
        success = sum(1 for s in code_tasks if s.get("status") == "success")
        return success / len(code_tasks)
    return 0.5


def _score_knowledge(result: Dict) -> float:
    """知识问答评分"""
    output = result.get("output", "")
    # 检查是否包含分析关键词
    keywords = ["同比", "环比", "趋势", "分析", "品类", "销售额"]
    matched = sum(1 for kw in keywords if kw in output)
    return min(matched / len(keywords), 1.0)


def _detect_defects(result: Dict, case: Dict) -> List[Dict]:
    """检测缺陷"""
    defects = []
    meta = result.get("_meta", {})

    # 规划缺陷
    subtasks = meta.get("subtasks", [])
    n = len(subtasks)
    if n > 10:
        defects.append({"type": "规划缺陷", "severity": "Medium", "detail": f"子任务数量 {n} 个，超过 10 个"})
    if n < 2:
        defects.append({"type": "规划缺陷", "severity": "Low", "detail": f"子任务数量 {n} 个，少于 2 个"})

    # 工具缺陷
    for s in subtasks:
        if s.get("tool") not in ("code_executor", "calculator", "none", "memory_store", "web_fetch", "safety_checker", "search"):
            defects.append({"type": "工具缺陷", "severity": "High", "detail": f"未知工具 '{s.get('tool')}'"})

    # 执行缺陷
    failed = meta.get("subtasks_failed", 0)
    if failed > 0:
        defects.append({"type": "执行缺陷", "severity": "High", "detail": f"{failed} 个子任务失败"})

    # 知识缺陷
    output = result.get("output", "")
    if len(output) < 50:
        defects.append({"type": "知识缺陷", "severity": "Medium", "detail": "输出过短，可能分析不完整"})

    return defects


def print_test_report(results: List[FullChainTestResult]):
    """打印测试报告"""
    print(f"\n{'='*70}")
    print(f"数据分析任务完整流程测试报告")
    print(f"{'='*70}")

    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    avg_score = sum(r.total_score for r in results) / total if total > 0 else 0
    avg_elapsed = sum(r.elapsed for r in results) / total if total > 0 else 0
    avg_tokens = sum(r.tokens for r in results) / total if total > 0 else 0

    # 缺陷统计
    all_defects = []
    for r in results:
        all_defects.extend(r.defects)
    defect_types = {}
    for d in all_defects:
        t = d["type"]
        if t not in defect_types:
            defect_types[t] = 0
        defect_types[t] += 1

    print(f"\n汇总:")
    print(f"  总用例: {total}")
    print(f"  通过: {passed} ({passed/total:.0%})")
    print(f"  失败: {failed} ({failed/total:.0%})")
    print(f"  平均得分: {avg_score:.1%}")
    print(f"  平均耗时: {avg_elapsed:.1f}s")
    print(f"  平均 Token: {avg_tokens:.0f}")
    print(f"  缺陷总数: {len(all_defects)}")

    if defect_types:
        print(f"\n缺陷分布:")
        for t, count in defect_types.items():
            print(f"  {t}: {count} 个")

    # 详细结果
    print(f"\n详细结果:")
    print(f"{'ID':8s} | {'难度':6s} | {'得分':6s} | {'耗时':6s} | {'Token':6s} | {'缺陷数':6s}")
    print("-" * 70)
    for r in results:
        icon = "" if r.passed else ""
        print(f"{r.test_id:8s} | {r.difficulty:6s} | {r.total_score:5.1%} | {r.elapsed:5.1f}s | {r.tokens:6d} | {len(r.defects):6d} {icon}")

    # 缺陷详情
    if all_defects:
        print(f"\n缺陷详情:")
        for i, d in enumerate(all_defects[:10], 1):
            print(f"  {i}. [{d['severity']}] {d['type']}: {d['detail']}")

    print(f"{'='*70}\n")


def run_demo():
    """演示"""
    print("=" * 70)
    print("数据分析任务完整流程测试演示")
    print("=" * 70)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from agents.custom_agent.agent import CustomAgent

    # 生成测试 CSV
    os.makedirs("/tmp/test_data", exist_ok=True)
    generate_test_csv("/tmp/test_data/simple.csv", rows=10, cols=3)
    generate_test_csv("/tmp/test_data/medium.csv", rows=1000, cols=5, has_nulls=True)
    generate_test_csv("/tmp/test_data/complex.csv", rows=100, cols=5, has_nulls=True)

    # 测试用例
    test_cases = [
        {"id": "T-01", "task": "读取 /tmp/test_data/simple.csv，统计各品类的销售额", "difficulty": "简单"},
        {"id": "T-02", "task": "读取 /tmp/test_data/medium.csv，按月份统计销售额，计算同比增长率", "difficulty": "中等"},
        {"id": "T-03", "task": "读取 /tmp/test_data/complex.csv，分析销售趋势并生成报告", "difficulty": "困难"},
        {"id": "T-04", "task": "读取 /tmp/test_data/simple.csv，找出销售额最高的品类", "difficulty": "简单"},
        {"id": "T-05", "task": "读取 /tmp/test_data/medium.csv，计算各品类的平均利润", "difficulty": "中等"},
    ]

    # 运行测试
    agent = CustomAgent(temperature=0.3)
    results = run_full_chain_test(agent, test_cases)

    # 打印报告
    print_test_report(results)

    print("=" * 70)


if __name__ == "__main__":
    run_demo()
