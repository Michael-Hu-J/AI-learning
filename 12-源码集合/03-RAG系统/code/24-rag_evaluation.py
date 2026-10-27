def calculate_recall_at_k(retrieved_docs: list, relevant_docs: list, k: int = 5) -> float:
    """计算Recall@K"""
    top_k = retrieved_docs[:k]
    relevant_in_top_k = len(set(top_k) & set(relevant_docs))
    recall = relevant_in_top_k / max(len(relevant_docs), 1)
    return recall

# 测试示例
retrieved = ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5", "doc_6"]
relevant = ["doc_3", "doc_7"]
recall_5 = calculate_recall_at_k(retrieved, relevant, k=5)
print(f"Recall@5: {recall_5}")  # 1/2 = 0.5

def calculate_precision_at_k(retrieved_docs: list, relevant_docs: list, k: int = 5) -> float:
    """计算Precision@K"""
    top_k = retrieved_docs[:k]
    relevant_in_top_k = len(set(top_k) & set(relevant_docs))
    precision = relevant_in_top_k / k
    return precision

def calculate_mrr(queries: list) -> float:
    """计算MRR"""
    rr_scores = []
    for query in queries:
        retrieved = query['retrieved']
        relevant = query['relevant']
        rank = None
        for i, doc in enumerate(retrieved):
            if doc in relevant:
                rank = i + 1
                break
        if rank is not None:
            rr_scores.append(1.0 / rank)
        else:
            rr_scores.append(0.0)
    return sum(rr_scores) / len(rr_scores)

import math

def calculate_ndcg(retrieved_docs: list, relevant_docs: list, k: int = 5) -> float:
    """计算NDCG@K"""
    dcg = 0.0
    for i, doc in enumerate(retrieved_docs[:k]):
        rel = 1 if doc in relevant_docs else 0
        dcg += (2**rel - 1) / math.log2(i + 2)
    
    ideal_relevant = min(len(relevant_docs), k)
    idcg = 0.0
    for i in range(ideal_relevant):
        idcg += (2**1 - 1) / math.log2(i + 2)
    
    return dcg / max(idcg, 1e-10)

from rouge_score import rouge_scorer

def calculate_rouge(generation: str, reference: str) -> dict:
    """计算ROUGE分数"""
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(reference, generation)
    return {
        'rouge1_f1': scores['rouge1'].fmeasure,
        'rouge2_f1': scores['rouge2'].fmeasure,
        'rougeL_f1': scores['rougeL'].fmeasure,
    }

# 测试示例
generation = "这款手机支持5G网络，搭载A17 Pro芯片，6.7英寸超视网膜XDR显示屏"
reference = "支持5G网络"
scores = calculate_rouge(generation, reference)
print(scores)

from bert_score import score

def calculate_bertscore(generation: str, reference: str) -> dict:
    """计算BERTScore"""
    P, R, F1 = score([generation], [reference], lang='zh')
    return {
        'precision': P.item(),
        'recall': R.item(),
        'f1': F1.item(),
    }

# 测试示例
generation = "这款手机支持5G网络"
reference = "支持第五代移动通信技术"
scores = calculate_bertscore(generation, reference)
print(scores)
# BERTScore能识别出"5G"和"第五代移动通信技术"语义相似

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall

dataset_v1 = [{
    "question": "订单超过 7 天还没发货怎么办？",
    "answer": "您可以联系客服申请退款或催促发货",
    "contexts": ["订单发货规则：付款后 48 小时内发货..."]
}]

dataset_v2 = [{
    "question": "订单超过 7 天还没发货怎么办？",
    "answer": "根据发货规则第 3 条，超过 7 天未发货您可以：\n1. 在订单页面点击催发货\n2. 联系客服申请退款\n3. 每超时一天可获得 10 元补偿",
    "contexts": [
        "订单发货规则：付款后 48 小时内发货...",
        "超时赔付标准：超过 7 天未发货，每超一天赔付 10 元"
    ]
}]

from ragas import evaluate
from ragas.metrics import (
    context_recall,        # 检索召回率
    context_precision,     # 检索精确率
    answer_relevance,      # 回答相关性
    faithfulness,          # 忠实度
    answer_accuracy        # 回答准确性
)
from datasets import Dataset

# 准备测试数据
data = {
    'question': [
        "这款手机支持5G吗？",
        "这个衣服有M码吗？",
        "退货怎么操作？",
    ],
    'answer': [
        "支持5G网络",
        "本店所有商品支持7天无理由退换货",  # 错误回答
        "在订单详情页面点击'申请退货'，按提示操作即可",
    ],
    'contexts': [
        ["这款手机支持5G双模网络，支持SA和NSA两种组网方式"],
        ["购物满199元免运费"],  # 不相关的上下文
        ["退货政策：7天内无理由退货，运费由买家承担"],
    ],
    'ground_truth': [
        "支持5G",
        "有M码",
        "7天内无理由退货，在订单页面申请",
    ]
}

dataset = Dataset.from_dict(data)

# 运行评测
results = evaluate(
    dataset,
    metrics=[context_recall, context_precision, answer_relevance, faithfulness]
)

print(results)

# RAG Triad的核心思想
# 三个独立的评估，而不是一个综合分数

# 1. Retrieval评分：检索文档和相关文档的重叠度
def retrieval_score(retrieved, relevant):
    return len(set(retrieved) & set(relevant)) / len(relevant)

# 2. Alignment评分：回答和检索文档的一致性
def alignment_score(answer, contexts):
    # 用LLM判断回答是否基于上下文
    pass

# 3. Answer评分：回答和标准答案的准确性
def answer_score(answer, ground_truth):
    # 用LLM判断回答是否准确
    pass

def end_to_end_accuracy(questions, answers, ground_truths):
    """端到端准确率：直接评估最终回答是否正确"""
    correct = 0
    for q, a, gt in zip(questions, answers, ground_truths):
        # 用LLM判断回答是否正确
        is_correct = llm_judge(question=q, answer=a, ground_truth=gt)
        if is_correct:
            correct += 1
    return correct / len(questions)

def hallucination_rate(answers, contexts):
    """幻觉率：回答中包含知识库中没有的信息的比例"""
    hallucinated = 0
    for answer, context in zip(answers, contexts):
        has_hallucination = detect_hallucination(answer, context)
        if has_hallucination:
            hallucinated += 1
    return hallucinated / len(answers)

def safety_violation_rate(answers):
    """安全违规率：回答中包含不安全内容的比例"""
    violations = 0
    for answer in answers:
        if check_safety(answer):
            violations += 1
    return violations / len(answers)
