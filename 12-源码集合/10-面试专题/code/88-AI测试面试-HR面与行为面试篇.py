import pytest
from dataclasses import dataclass
from typing import List

@dataclass
class TestCase:
    """AI客服测试用例结构"""
    input_text: str          # 用户输入
    expected_intent: str     # 期望意图
    expected_action: str     # 期望动作
    safety_check: bool       # 是否需要安全检查
    edge_case: bool          # 是否为边界case

# 核心测试用例集
core_test_cases = [
    TestCase(
        input_text="我想退货，订单号是12345",
        expected_intent="退货申请",
        expected_action="查询订单并启动退货流程",
        safety_check=False,
        edge_case=False,
    ),
    TestCase(
        input_text="你们的产品都是骗子",
        expected_intent="投诉",
        expected_action="安抚情绪并转人工",
        safety_check=True,
        edge_case=False,
    ),
    TestCase(
        input_text="帮我算一下1+1等于几",
        expected_intent="非业务问题",
        expected_action="引导回业务话题",
        safety_check=False,
        edge_case=True,
    ),
]

def test_intent_classification():
    """测试意图识别准确性"""
    for case in core_test_cases:
        actual_intent = classify_intent(case.input_text)
        assert actual_intent == case.expected_intent, \
            f"意图识别失败: 输入='{case.input_text}', 期望={case.expected_intent}, 实际={actual_intent}"

# 项目成果数据示例
project_metrics = {
    "测试覆盖率": "从 30% 提升到 85%",
    "缺陷逃逸率": "从 5% 降低到 0.5%",
    "自动化率": "回归测试自动化率 75%",
    "测试效率": "单次回归时间从 2天 缩短到 2小时",
    "幻觉率": "核心场景幻觉率 < 1%",
    "安全拦截率": "已知攻击模式拦截率 99.2%",
    "用户满意度": "上线后 NPS 从 35 提升到 62",
}

for metric, value in project_metrics.items():
    print(f"{metric}: {value}")
