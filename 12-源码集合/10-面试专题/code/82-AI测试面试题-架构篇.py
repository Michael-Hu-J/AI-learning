def evaluate_coverage(test_cases, intent_list, scenario_list):
    """评估测试覆盖率"""
    covered_intents = set()
    covered_scenarios = set()

    for case in test_cases:
        covered_intents.add(case["intent"])
        covered_scenarios.add(case["scenario"])

    intent_coverage = len(covered_intents) / len(intent_list)
    scenario_coverage = len(covered_scenarios) / len(scenario_list)

    # 输入空间分析
    input_lengths = [len(case["input"]) for case in test_cases]
    short = sum(1 for l in input_lengths if l < 50)
    medium = sum(1 for l in input_lengths if 50 <= l < 500)
    long = sum(1 for l in input_lengths if l >= 500)

    return {
        "intent_coverage": intent_coverage,
        "scenario_coverage": scenario_coverage,
        "input_distribution": {
            "short": short / len(test_cases),
            "medium": medium / len(test_cases),
            "long": long / len(test_cases),
        }
    }

class MockLLM:
    """Mock LLM 服务，用于测试环境"""

    def __init__(self, response_map):
        # response_map: {keyword: response} 关键词匹配
        self.response_map = response_map

    def generate(self, prompt, temperature=0.0):
        for keyword, response in self.response_map.items():
            if keyword in prompt:
                return response
        return "抱歉，我暂时无法回答这个问题。"

# 使用示例
mock = MockLLM({
    "订单": "您的订单正在处理中，预计3天内发货。",
    "退货": "您可以在订单详情页面申请退货。",
    "发票": "电子发票将在发货后3个工作日内发送到您的邮箱。",
})

result = mock.generate("我的订单什么时候发货？")
print(result)  # 您的订单正在处理中，预计3天内发货。

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

# 准备测试数据
dataset = {
    'question': ['我的订单什么时候发货？', '怎么退货？'],
    'answer': ['您的订单预计3天内发货。', '您可以在订单详情页面申请退货。'],
    'contexts': [['订单系统显示该订单已发货，物流预计3天到达。'],
                 ['退货政策：收货后7天内可申请退货。']],
    'ground_truth': ['订单预计3天内发货。', '收货后7天内可申请退货。']
}

# 运行评测
results = evaluate(dataset, metrics=[faithfulness, answer_relevancy,
                                      context_precision, context_recall])
print(results)
