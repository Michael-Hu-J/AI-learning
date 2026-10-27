#!/usr/bin/env python3
"""
代码能力测试（电商数据分析场景）

功能：
1. 代码自动执行验证
2. 边界测试生成（聚合计算、同比环比、数据清洗、移动平均）
3. 效率启发式评分
4. 代码风格检查
"""

import subprocess
import re
import os
import sys
import json
import tempfile
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CodeTestResult:
    """代码测试结果"""
    total_cases: int
    passed_cases: int
    failed_cases: List[Dict]
    accuracy: float
    efficiency_score: float
    style_score: float
    debug_rounds: int
    total_score: float


def verify_code(code: str, test_cases: List[Dict],
                timeout: int = 10) -> Dict:
    """
    自动验证代码正确性

    Args:
        code: 代码字符串
        test_cases: 测试用例列表 [{input, expected, desc}]
        timeout: 超时秒数

    Returns:
        {
            "total": 总用例数,
            "passed": 通过数,
            "accuracy": 准确率,
            "details": 详细结果,
        }
    """
    results = []

    for tc in test_cases:
        try:
            # 构造完整可执行代码
            full_code = f"""
{code}

# 测试用例
input_data = {tc['input']}
try:
    result = solution(input_data)
    print(result)
except Exception as e:
    print(f"ERROR: {{e}}")
"""
            # 写入临时文件执行
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(full_code)
                temp_path = f.name

            proc = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True, text=True, timeout=timeout,
            )
            os.unlink(temp_path)

            output = proc.stdout.strip()
            expected = str(tc['expected']).strip()

            # 宽松匹配（允许格式差异）
            correct = normalize(output) == normalize(expected)

            results.append({
                "input": str(tc['input']),
                "expected": expected,
                "actual": output,
                "correct": correct,
                "error": proc.stderr.strip() if not correct else "",
            })

        except subprocess.TimeoutExpired:
            results.append({
                "input": str(tc['input']),
                "expected": str(tc['expected']),
                "actual": "TIMEOUT",
                "correct": False,
                "error": "执行超时",
            })
        except Exception as e:
            results.append({
                "input": str(tc['input']),
                "expected": str(tc['expected']),
                "actual": f"ERROR: {e}",
                "correct": False,
                "error": str(e),
            })

    passed = sum(1 for r in results if r["correct"])
    total = len(results)

    return {
        "total": total,
        "passed": passed,
        "accuracy": passed / total if total > 0 else 0,
        "details": results,
    }


def normalize(value: str) -> str:
    """标准化输出（去除空格、换行、引号差异）"""
    value = value.strip()
    value = re.sub(r'\s+', '', value)
    value = value.replace("'", '"')
    return value


def generate_boundary_tests(func_type: str) -> List[Dict]:
    """
    生成边界测试用例

    Args:
        func_type: 函数类型（aggregate/year_over_year/cleaning/moving_avg）

    Returns:
        边界测试用例列表
    """
    boundaries = {
        "aggregate": [
            {"input": [], "expected": {}, "desc": "空记录"},
            {"input": [{"category": "服饰", "amount": 100}], "expected": {"服饰": 100}, "desc": "单条记录"},
            {"input": [{"category": "服饰", "amount": 100}, {"category": "服饰", "amount": 200}], "expected": {"服饰": 300}, "desc": "同品类多条"},
            {"input": [{"category": "A", "amount": 0}], "expected": {"A": 0}, "desc": "零金额"},
            {"input": [{"category": "A", "amount": 0}, {"category": "B", "amount": 0}], "expected": {"A": 0, "B": 0}, "desc": "全零金额"},
            {"input": [{"category": f"品类{i}", "amount": i} for i in range(1000)], "expected": {f"品类{i}": i for i in range(1000)}, "desc": "大量数据"},
        ],
        "year_over_year": [
            {"input": ({"2024-01": 100}, {"2023-01": 80}), "expected": {"2024-01": 0.25}, "desc": "正常同比"},
            {"input": ({"2024-01": 100}, {"2023-01": 0}), "expected": {"2024-01": None}, "desc": "去年同期为0"},
            {"input": ({"2024-01": 100}, {}), "expected": {"2024-01": None}, "desc": "去年数据缺失"},
            {"input": ({}, {"2023-01": 80}), "expected": {}, "desc": "今年数据为空"},
        ],
        "cleaning": [
            {"input": [], "expected": [], "desc": "空数据"},
            {"input": [{"amount": None}], "expected": [], "desc": "全空值"},
            {"input": [{"amount": 100}, {"amount": None}, {"amount": 200}], "expected": [{"amount": 100}, {"amount": 200}], "desc": "部分空值"},
            {"input": [{"amount": 100}, {"amount": 100}], "expected": [{"amount": 100}], "desc": "重复记录"},
        ],
        "moving_avg": [
            {"input": ([], 7), "expected": [], "desc": "空数据"},
            {"input": ([100], 7), "expected": [100], "desc": "单天数据"},
            {"input": ([100, 200, 300], 7), "expected": [100, 150, 200], "desc": "数据不足窗口"},
            {"input": ([100, 200, 300, 400, 500, 600, 700], 7), "expected": [100, 150, 200, 250, 300, 350, 400], "desc": "正常窗口"},
        ],
    }

    return boundaries.get(func_type, [])


def score_efficiency(code: str) -> float:
    """
    效率启发式评分

    Args:
        code: 代码字符串

    Returns:
        效率得分（0-100）
    """
    score = 100.0

    # 嵌套循环超过 3 层
    lines = code.strip().split('\n')
    max_depth = 0
    current_depth = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('for ') or stripped.startswith('while '):
            current_depth += 1
            max_depth = max(max_depth, current_depth)
        elif stripped and not stripped.startswith('#'):
            if current_depth > 0 and not (stripped.startswith('for ') or stripped.startswith('while ') or stripped.startswith('if ')):
                current_depth = max(0, current_depth - 1)

    if max_depth > 3:
        score -= 40
    elif max_depth > 2:
        score -= 20

    # 重复计算（简单启发式：相同表达式出现多次）
    expr_counts = {}
    for line in lines:
        stripped = line.strip()
        if '=' in stripped and 'for' not in stripped:
            expr = stripped.split('=')[1].strip()
            expr_counts[expr] = expr_counts.get(expr, 0) + 1
    for expr, count in expr_counts.items():
        if count > 3 and len(expr) > 10:
            score -= 10
            break

    # 使用内置函数/库（加分）
    builtin_funcs = ['sorted', 'sum', 'min', 'max', 'len', 'range', 'map', 'filter']
    uses_builtin = any(func in code for func in builtin_funcs)
    if uses_builtin:
        score = min(score + 10, 100)

    return max(score, 0)


def score_style(code: str) -> float:
    """
    代码风格评分

    Args:
        code: 代码字符串

    Returns:
        风格得分（0-100）
    """
    score = 100.0
    lines = code.strip().split('\n')

    # 变量名含单字母（除 i/j/k）
    single_letter_vars = re.findall(r'\b(?![ijk])[a-z]\b(?!=)', code)
    if len(single_letter_vars) > 3:
        score -= 20

    # 函数超过 50 行
    if len(lines) > 50:
        score -= 20

    # 无注释
    comment_lines = [l for l in lines if l.strip().startswith('#')]
    if len(comment_lines) < len(lines) * 0.05:  # 注释少于 5%
        score -= 15

    # 魔法数字
    magic_numbers = re.findall(r'(?<!\w)\d{2,}(?!\w)', code)
    if len(magic_numbers) > 5:
        score -= 15

    # 缩进不一致
    indents = set()
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            indents.add(indent)
    if len(indents) > 5:
        score -= 10

    return max(score, 0)


def debug_code(original_code: str, error_message: str,
               test_cases: List[Dict], max_rounds: int = 5) -> Dict:
    """
    调试代码（模拟智能体调试过程）

    Args:
        original_code: 原始有 bug 的代码
        error_message: 错误信息
        test_cases: 测试用例
        max_rounds: 最大调试轮数

    Returns:
        {
            "fixed": 是否修复,
            "rounds": 修复轮数,
            "final_code": 最终代码,
        }
    """
    # 实际使用时，这里调用智能体的 run() 方法
    # 每次传入错误信息，智能体返回修改后的代码
    # 这里只返回框架

    return {
        "fixed": False,
        "rounds": 0,
        "final_code": original_code,
        "note": "实际使用时调用智能体调试",
    }


def run_demo():
    """演示"""
    print("=" * 60)
    print("代码能力测试演示（电商数据分析场景）")
    print("=" * 60)

    # 测试代码：计算各品类销售额
    category_sales_code = """
def solution(records):
    '''
    计算各品类销售额
    
    Args:
        records: 销售记录列表，每条记录包含 category 和 amount 字段
    
    Returns:
        按品类聚合的销售额字典
    '''
    result = {}
    for record in records:
        category = record['category']
        amount = record['amount']
        if category in result:
            result[category] += amount
        else:
            result[category] = amount
    return result
"""

    # 测试用例
    test_cases = [
        {"input": [{'category': '服饰', 'amount': 100}, {'category': '数码', 'amount': 200}, {'category': '服饰', 'amount': 150}], "expected": "{'服饰': 250, '数码': 200}", "desc": "正常聚合"},
        {"input": [], "expected": "{}", "desc": "空记录"},
        {"input": [{'category': '食品', 'amount': 50}], "expected": "{'食品': 50}", "desc": "单条记录"},
        {"input": [{'category': '服饰', 'amount': 100}, {'category': '服饰', 'amount': 200}, {'category': '服饰', 'amount': 300}], "expected": "{'服饰': 600}", "desc": "同品类多条"},
        {"input": [{'category': 'A', 'amount': 0}, {'category': 'B', 'amount': 0}], "expected": "{'A': 0, 'B': 0}", "desc": "零金额"},
    ]

    # 验证
    print("\n--- 代码验证 ---")
    result = verify_code(category_sales_code, test_cases)
    print(f"总用例: {result['total']}")
    print(f"通过: {result['passed']}")
    print(f"准确率: {result['accuracy']:.0%}")

    for detail in result['details']:
        icon = "" if detail['correct'] else ""
        print(f"  {icon} {detail.get('desc', '')}: 输入={detail['input']}, 期望={detail['expected']}, 实际={detail['actual']}")

    # 效率评分
    print(f"\n--- 效率评分 ---")
    efficiency = score_efficiency(category_sales_code)
    print(f"效率得分: {efficiency:.0f}/100")

    # 风格评分
    print(f"\n--- 风格评分 ---")
    style = score_style(category_sales_code)
    print(f"风格得分: {style:.0f}/100")

    # 边界测试
    print(f"\n--- 边界测试生成 ---")
    boundaries = generate_boundary_tests("aggregate")
    print(f"生成 {len(boundaries)} 个边界用例")
    for b in boundaries:
        print(f"  {b['desc']}: 输入={b['input']}, 期望={b['expected']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_demo()
