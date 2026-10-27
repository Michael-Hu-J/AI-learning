# 无示例（Zero-Shot）——格式不稳定
prompt_zero = """
分析这段文本的情感，输出 JSON。
文本：今天天气真好
"""
# 典型输出：好的，分析结果：{'sentiment': 'positive'}  ← json.loads() 失败

# 有示例（Few-Shot）——格式一致
prompt_few = """
根据示例，完成以下任务：

示例 1：
输入："今天天气真好"
输出：{"sentiment": "positive"}

示例 2：
输入："心情很糟糕"
输出：{"sentiment": "negative"}

示例 3：
输入："吃了一顿饭"
输出：{"sentiment": "neutral"}

请分析：
输入："这个产品太棒了"
输出：
"""
# 典型输出：{"sentiment": "positive"}

def test_few_shot_examples(test_data, build_prompt_with_examples, call_llm, parse_response):
    """测试示例数量对准确率的影响"""
    for n in range(0, 6):  # 0～5 个示例
        prompt_template = build_prompt_with_examples(n)
        correct = 0
        for item in test_data:
            response = call_llm(prompt_template.format(text=item["text"]))
            parsed = parse_response(response)
            if parsed.get("sentiment") == item["expected"]:
                correct += 1
        accuracy = correct / len(test_data)
        print(f"示例数={n}: 准确率={accuracy:.1%}")

    # 典型结果（情感分析任务）
    # 示例数=0: 65% | 1: 78% | 2: 85% | 3: 88% | 5: 89% ← 收益递减

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class DynamicFewShot:
    def __init__(self, example_pool):
        self.pool = example_pool
        self.vectorizer = TfidfVectorizer()
        self.vectors = self.vectorizer.fit_transform([e["input"] for e in example_pool])

    def get_examples(self, query, k=3):
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.vectors)[0]
        top_indices = similarities.argsort()[-k:][::-1]
        return [self.pool[i] for i in top_indices]

    def build_prompt(self, query, k=3):
        examples = self.get_examples(query, k)
        prompt = "请对以下文本分类：投诉/咨询/建议/其他\n\n"
        for ex in examples:
            prompt += f"示例：{ex['input']} → {ex['output']}\n"
        prompt += f"\n请分类：{query}"
        return prompt

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random

class DynamicFewShotSelector:
    """动态少样本示例选择器"""
    
    def __init__(self, example_pool, similarity_metric="cosine"):
        """
        example_pool: [{"input": "...", "output": "...", "category": "..."}, ...]
        """
        self.pool = example_pool
        self.vectorizer = TfidfVectorizer(
            analyzer='char',  # 中文字符级分词
            ngram_range=(1, 3)  # 1-3元语法，捕获更多语义
        )
        self.vectors = self.vectorizer.fit_transform(
            [e["input"] for e in example_pool]
        )
    
    def get_examples(self, query, k=3, min_similarity=0.1):
        """根据query选出最相关的k个示例，过滤相似度低于阈值的"""
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.vectors)[0]
        
        # 过滤低相似度
        valid_indices = [i for i, s in enumerate(similarities) if s >= min_similarity]
        
        if len(valid_indices) < k:
            # 相似度不够时，从所有示例中随机选，保证多样性
            selected = random.sample(range(len(self.pool)), k)
        else:
            # 从高相似度中选，加入多样性去重
            candidates = sorted(valid_indices, key=lambda i: similarities[i], reverse=True)
            selected = self._diverse_select(candidates, k)
        
        return [self.pool[i] for i in selected]
    
    def _diverse_select(self, candidates, k):
        """从候选中选出k个语义不同的示例"""
        selected = [candidates[0]]
        while len(selected) < k and len(selected) < len(candidates):
            best_idx = candidates[len(selected)]
            selected.append(best_idx)
        return selected[:k]
    
    def build_prompt(self, query, task_instruction, k=3):
        """构建完整的prompt"""
        examples = self.get_examples(query, k)
        prompt = f"{task_instruction}\n\n"
        for i, ex in enumerate(examples, 1):
            prompt += f"示例{i}：\n输入：{ex['input']}\n输出：{ex['output']}\n\n"
        prompt += f"请处理：\n输入：{query}\n输出："
        return prompt

pool = [
    {"input": "产品质量太差了", "output": "投诉", "category": "投诉"},
    {"input": "快递太慢了", "output": "投诉", "category": "投诉"},
    {"input": "怎么申请退款", "output": "咨询", "category": "咨询"},
    {"input": "营业时间是多少", "output": "咨询", "category": "咨询"},
    {"input": "建议增加夜间配送", "output": "建议", "category": "建议"},
    {"input": "希望优化搜索功能", "output": "建议", "category": "建议"},
]

selector = DynamicFewShotSelector(pool)
prompt = selector.build_prompt(
    query="你们能货到付款吗？",
    task_instruction="请对以下客户反馈分类：投诉/咨询/建议/其他",
    k=3
)

def evaluate_example_quality(example_pool, test_set, call_llm):
    """评估示例质量：覆盖率、一致性、区分度"""
    results = {
        "coverage": {},
        "consistency": {},
        "discrimination": {}
    }
    
    # 1. 覆盖率评估
    categories = set(e["category"] for e in example_pool if "category" in e)
    for cat in categories:
        cat_examples = [e for e in example_pool if e.get("category") == cat]
        results["coverage"][cat] = {
            "count": len(cat_examples),
            "diversity": compute_diversity([e["input"] for e in cat_examples])
        }
    
    # 2. 一致性评估
    consistency_scores = []
    for case in test_set:
        outputs = []
        for _ in range(3):
            examples = random.sample(example_pool, min(3, len(example_pool)))
            prompt = build_prompt(examples, case["input"])
            response = call_llm(prompt)
            outputs.append(response)
        unique = len(set(outputs))
        consistency_scores.append(1.0 / unique)
    
    results["consistency"]["avg"] = sum(consistency_scores) / len(consistency_scores)
    
    # 3. 区分度评估
    for i, ex1 in enumerate(example_pool):
        for j, ex2 in enumerate(example_pool):
            if i >= j:
                continue
            sim = compute_similarity(ex1["input"], ex2["input"])
            if sim > 0.8 and ex1["output"] != ex2["output"]:
                results["discrimination"]["conflicts"].append({
                    "ex1": ex1, "ex2": ex2, "similarity": sim
                })
    
    return results

def test_few_shot_robustness(example_pool, test_set, call_llm, n_trials=5):
    """测试少样本Prompt的鲁棒性"""
    results = {}
    
    for case in test_set:
        outputs = []
        for trial in range(n_trials):
            examples = random.sample(example_pool, min(3, len(example_pool)))
            prompt = build_prompt(examples, case["input"])
            response = call_llm(prompt)
            outputs.append(response)
        
        unique_outputs = set(outputs)
        consistency = 1.0 if len(unique_outputs) == 1 else 1.0 / len(unique_outputs)
        
        results[case["input"][:30]] = {
            "consistency": consistency,
            "unique_count": len(unique_outputs),
            "outputs": list(unique_outputs)
        }
    
    avg_consistency = sum(r["consistency"] for r in results.values()) / len(results)
    print(f"平均一致性: {avg_consistency:.1%}")
    
    inconsistent = {k: v for k, v in results.items() if v["consistency"] < 1.0}
    if inconsistent:
        print(f"⚠️ 有 {len(inconsistent)} 个输入的输出不一致，需要检查示例质量")
        for k, v in inconsistent.items():
            print(f"  输入: {k}")
            print(f"  输出版本数: {v['unique_count']}")
    
    return results

import random

def test_few_shot_robustness_simple(prompt_template, example_pool, test_set, call_llm, n_trials=3):
    """测试不同示例组合是否产生一致结果"""
    results = {}
    for case in test_set:
        outputs = []
        for _ in range(n_trials):
            examples = random.sample(example_pool, min(3, len(example_pool)))
            prompt = build_prompt_with_examples(prompt_template, examples, case["input"])
            outputs.append(call_llm(prompt))
        unique = set(outputs)
        consistency = 1.0 if len(unique) == 1 else len(unique) / n_trials
        results[case["input"][:20]] = {"consistency": consistency, "outputs": list(unique)}
    avg = sum(r["consistency"] for r in results.values()) / len(results)
    print(f"平均一致性: {avg:.1%}")
    return results
