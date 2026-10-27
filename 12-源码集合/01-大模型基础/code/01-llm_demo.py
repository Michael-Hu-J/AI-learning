import math

def softmax(scores):
    """将分数转换为概率分布"""
    max_score = max(scores)
    exp_scores = [math.exp(s - max_score) for s in scores]
    total = sum(exp_scores)
    return [e / total for e in exp_scores]

def self_attention(query, keys, values):
    """
    简化版自注意力计算
    query: 当前词的向量表示
    keys: 所有词的向量表示
    values: 所有词的值向量
    返回: 加权后的上下文向量
    """
    # 第一步：计算注意力分数（query 和每个 key 的点积）
    scores = [sum(q * k for q, k in zip(query, key))
              for key in keys]

    # 第二步：缩放（防止梯度消失）
    d_k = len(query)
    scaled_scores = [s / math.sqrt(d_k) for s in scores]

    # 第三步：转换为概率
    weights = softmax(scaled_scores)

    # 第四步：加权求和
    context = [0.0] * len(values[0])
    for w, v in zip(weights, values):
        for i in range(len(context)):
            context[i] += w * v[i]

    return context, weights

# 示例：用"苹果"的 query 对四个 key 算一次注意力
# 简化向量（实际模型中维度为数百到数千）
query_apple = [0.8, 0.2, 0.6]  # "苹果"的查询向量
keys = [
    [0.9, 0.1, 0.5],  # "我"
    [0.8, 0.2, 0.6],  # "苹果"
    [0.3, 0.9, 0.1],  # "吃"
    [0.1, 0.8, 0.7],  # "水果"
]
values = [
    [1.0, 0.0, 0.0],  # "我"的值
    [0.0, 1.0, 0.0],  # "苹果"的值
    [0.0, 0.0, 1.0],  # "吃"的值
    [0.5, 0.5, 0.0],  # "水果"的值
]

context, weights = self_attention(query_apple, keys, values)
print("注意力权重:", [round(w, 3) for w in weights])
# 输出: 注意力权重: [0.284, 0.284, 0.205, 0.228]
# 顺序对应"我、苹果、吃、水果"
# "我"和"苹果"自己并列最高(0.284)，其次"水果"(0.228)，"吃"最低(0.205)

import time
from dataclasses import dataclass
from typing import List

@dataclass
class InferenceStep:
    """推理单步的记录"""
    step: int
    token_id: int
    token_text: str
    probability: float
    latency_ms: float

class SimpleInferenceSimulator:
    """
    简化推理模拟器——展示大模型逐 Token 生成的过程
    实际模型的推理远比这复杂，但核心流程一致
    """

    def __init__(self, vocab: dict, temperature: float = 1.0):
        self.vocab = vocab  # token_id -> text
        self.temperature = temperature
        self.steps: List[InferenceStep] = []

    def _sample(self, probabilities: dict) -> tuple:
        """按概率采样下一个 Token"""
        import random

        if self.temperature <= 0.01:
            # greedy decoding：选概率最高的
            best_token = max(probabilities, key=probabilities.get)
            return best_token, probabilities[best_token]

        # temperature 采样：调整概率分布
        adjusted = {}
        for token_id, prob in probabilities.items():
            adjusted[token_id] = prob ** (1.0 / self.temperature)

        total = sum(adjusted.values())
        adjusted = {k: v / total for k, v in adjusted.items()}

        # 加权随机采样
        token_id = random.choices(
            list(adjusted.keys()),
            weights=adjusted.values(),
            k=1
        )[0]
        return token_id, adjusted[token_id]

    def generate(self, prompt_tokens: List[int], max_steps: int = 10) -> List[InferenceStep]:
        """
        模拟逐 Token 生成过程
        实际调用中，prompt_tokens 由分词器产生，
        概率分布由模型前向传播计算
        """
        self.steps = []
        current_tokens = list(prompt_tokens)

        for step in range(max_steps):
            start = time.time()

            # 模拟模型前向传播，产生下一个 Token 的概率分布
            # 实际项目中这里是一次 GPU 计算
            mock_probs = self._mock_next_token_probs(current_tokens)
            token_id, prob = self._sample(mock_probs)

            elapsed = (time.time() - start) * 1000
            self.steps.append(InferenceStep(
                step=step + 1,
                token_id=token_id,
                token_text=self.vocab.get(token_id, "<UNK>"),
                probability=round(prob, 4),
                latency_ms=round(elapsed, 2)
            ))
            current_tokens.append(token_id)

            if self.vocab.get(token_id) == "<EOS>":
                break

        return self.steps

    def _mock_next_token_probs(self, tokens: List[int]) -> dict:
        """模拟模型输出的概率分布（实际由模型计算）"""
        import random
        mock_vocab = {
            101: "你好", 102: "世界", 103: "，", 104: "。",
            105: "今天", 106: "天气", 107: "不错", 108: "<EOS>"
        }
        probs = {tid: random.random() for tid in mock_vocab}
        total = sum(probs.values())
        return {tid: p / total for tid, p in probs.items()}

# 运行示例
if __name__ == "__main__":
    vocab = {
        101: "你好", 102: "世界", 103: "，", 104: "。",
        105: "今天", 106: "天气", 107: "不错", 108: "<EOS>"
    }
    simulator = SimpleInferenceSimulator(vocab, temperature=0.5)
    steps = simulator.generate(prompt_tokens=[105])  # 以"今天"开头

    print("=== 逐 Token 生成过程 ===")
    for s in steps:
        print(f"步骤 {s.step}: Token={s.token_text} "
              f"(ID={s.token_id}) 概率={s.probability:.4f} 延迟={s.latency_ms:.2f}ms")

    generated = "".join(s.token_text for s in steps)
    print(f"\n生成结果: {generated}")

def test_output_stability(llm_call, prompt: str, n: int = 20) -> dict:
    """
    测试同一 Prompt 多次调用的输出稳定性
    返回结果分布，而非单次结果
    """
    results = []
    for _ in range(n):
        response = llm_call(prompt)
        results.append(response)

    unique = set(results)
    from collections import Counter
    freq = Counter(results)

    return {
        "total_runs": n,
        "unique_outputs": len(unique),
        "most_common": freq.most_common(3),
        "stability_score": 1.0 - (len(unique) - 1) / n,
    }

# 使用示例
# result = test_output_stability(my_llm, "解释什么是机器学习", n=20)
# stability_score 越接近 1，输出越稳定

def test_temperature_effect(llm_call, prompt: str):
    """对比不同 temperature 下的输出差异"""
    temperatures = [0.0, 0.3, 0.7, 1.0, 1.5]
    results = {}

    for temp in temperatures:
        responses = [llm_call(prompt, temperature=temp) for _ in range(5)]
        unique_count = len(set(responses))
        results[temp] = {
            "unique_outputs": unique_count,
            "responses": responses,
        }

    return results
    # 预期：temperature=0 时 5 次输出完全相同
    # temperature=1.5 时 5 次输出可能全部不同

def test_context_window(llm_call, max_tokens: int):
    """测试模型在长上下文下的信息保持能力"""
    secret = "测试密码：XYZ-789"
    prefix = "这是无关内容。" * 500  # 大量前置文本
    question = "请找出上文中的测试密码。"

    prompt = f"{prefix}\n{secret}\n{question}"

    response = llm_call(prompt)
    contains_secret = "XYZ-789" in response

    return {
        "prompt_length": len(prompt),
        "contains_secret": contains_secret,
        "response": response,
    }
    # 如果模型忽略了中间位置的 secret，说明存在"中间丢失"现象

def llm_as_judge(evaluator_llm, question, response, criteria):
    eval_prompt = f"""评估标准：{criteria}
问题：{question}
回答：{response}
请从准确性、完整性、相关性、可读性四个维度打分（1-5分），
最后给出总体评分和简短评语。严格按 JSON 格式输出。"""
    result = evaluator_llm(eval_prompt)
    import json
    try:
        return json.loads(result)
    except Exception:
        return {"error": "解析失败", "raw": result}
