import json
from dataclasses import dataclass
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, util

@dataclass
class RAGTestResult:
    question: str
    retrieved_docs: List[str]
    answer: str
    expected_answer: str
    similarity: float
    passed: bool

def test_rag_end_to_end(rag_system, test_cases: List[Dict]) -> Dict:
    """
    RAG端到端测试
    
    从用户问题到最终回答的完整链路测试。
    """
    eval_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    results = []
    
    for tc in test_cases:
        question = tc['question']
        expected = tc['expected_answer']
        
        # 完整流程：用户问题 → 检索 → 生成 → 回答
        retrieved_docs = rag_system.retrieve(question, top_k=5)
        answer = rag_system.generate(question, retrieved_docs)
        
        # 评估回答与期望答案的语义相似度
        emb1 = eval_model.encode([answer])
        emb2 = eval_model.encode([expected])
        similarity = util.cos_sim(emb1, emb2)[0][0].item()
        
        passed = similarity >= 0.80
        
        results.append(RAGTestResult(
            question=question,
            retrieved_docs=[d[:100] for d in retrieved_docs],
            answer=answer,
            expected_answer=expected,
            similarity=round(similarity, 4),
            passed=passed
        ))
    
    pass_rate = sum(1 for r in results if r.passed) / len(results) if results else 0
    avg_similarity = sum(r.similarity for r in results) / len(results)
    
    return {
        'test': 'end_to_end',
        'total': len(results),
        'passed': sum(1 for r in results if r.passed),
        'failed': sum(1 for r in results if not r.passed),
        'pass_rate': round(pass_rate, 4),
        'avg_similarity': round(avg_similarity, 4),
        'details': [vars(r) for r in results]
    }

import re
from typing import List, Tuple

def extract_claims(text: str) -> List[str]:
    """从文本中提取事实声明——按句号、分号、逗号拆分"""
    sentences = re.split(r'[。；！,，]', text)
    claims = [s.strip() for s in sentences if len(s.strip()) > 10]
    return claims

def verify_claim_against_docs(claim: str, docs: List[str], 
                               threshold: float = 0.75) -> Tuple[bool, str]:
    """验证声明是否能在文档中找到依据"""
    eval_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    claim_emb = eval_model.encode([claim])
    
    best_similarity = 0
    best_doc = ""
    
    for doc in docs:
        doc_sentences = re.split(r'[。；！,，]', doc)
        for sentence in doc_sentences:
            sentence = sentence.strip()
            if len(sentence) < 5:
                continue
            doc_emb = eval_model.encode([sentence])
            similarity = util.cos_sim(claim_emb, doc_emb)[0][0].item()
            if similarity > best_similarity:
                best_similarity = similarity
                best_doc = sentence
    
    return best_similarity >= threshold, best_doc

def test_hallucination(rag_system, test_cases: List[Dict]) -> Dict:
    """幻觉检测——检测RAG系统的回答是否存在幻觉"""
    results = []
    
    for tc in test_cases:
        question = tc['question']
        retrieved_docs = rag_system.retrieve(question, top_k=5)
        answer = rag_system.generate(question, retrieved_docs)
        
        claims = extract_claims(answer)
        
        supported_claims = []
        for claim in claims:
            supported, source_doc = verify_claim_against_docs(claim, retrieved_docs)
            supported_claims.append({
                'claim': claim,
                'supported': supported,
                'source': source_doc[:100] if source_doc else "无依据"
            })
        
        support_rate = (sum(1 for c in supported_claims if c['supported']) / 
                       len(supported_claims)) if supported_claims else 1.0
        
        hallucination_claims = [c for c in supported_claims if not c['supported']]
        
        results.append({
            'question': question,
            'answer': answer,
            'total_claims': len(supported_claims),
            'supported_claims': sum(1 for c in supported_claims if c['supported']),
            'hallucination_claims': hallucination_claims,
            'support_rate': round(support_rate, 4),
            'has_hallucination': support_rate < 0.80,
            'passed': support_rate >= 0.80
        })
    
    hallucination_rate = (sum(1 for r in results if r['has_hallucination']) / 
                         len(results)) if results else 0
    
    return {
        'test': 'hallucination_detection',
        'total': len(results),
        'hallucination_count': sum(1 for r in results if r['has_hallucination']),
        'hallucination_rate': round(hallucination_rate, 4),
        'passed': hallucination_rate < 0.15,
        'details': results
    }

def test_retrieval_quality(rag_system, test_cases: List[Dict]) -> Dict:
    """检索质量测试——只测试检索环节的质量"""
    results = []
    
    for tc in test_cases:
        question = tc['question']
        relevant_ids = set(tc['relevant_doc_ids'])
        
        retrieved = rag_system.retrieve(question, top_k=5)
        retrieved_ids = set(r['doc_id'] for r in retrieved)
        
        # Recall@5
        recall = len(retrieved_ids & relevant_ids) / max(len(relevant_ids), 1)
        # Precision@5
        precision = len(retrieved_ids & relevant_ids) / 5
        # MRR
        rank = None
        for i, r in enumerate(retrieved):
            if r['doc_id'] in relevant_ids:
                rank = i + 1
                break
        rr = 1.0 / rank if rank else 0.0
        # NDCG@5
        dcg = sum(1.0 / (i + 1) for i, r in enumerate(retrieved) if r['doc_id'] in relevant_ids)
        idcg = sum(1.0 / (i + 1) for i in range(min(len(relevant_ids), 5)))
        ndcg = dcg / idcg if idcg > 0 else 0
        
        results.append({
            'question': question,
            'recall_at_5': round(recall, 4),
            'precision_at_5': round(precision, 4),
            'mrr': round(rr, 4),
            'ndcg_at_5': round(ndcg, 4),
            'passed': recall >= 0.90
        })
    
    return {
        'test': 'retrieval_quality',
        'total': len(results),
        'avg_recall_at_5': round(sum(r['recall_at_5'] for r in results) / len(results), 4),
        'avg_precision_at_5': round(sum(r['precision_at_5'] for r in results) / len(results), 4),
        'avg_mrr': round(sum(r['mrr'] for r in results) / len(results), 4),
        'avg_ndcg_at_5': round(sum(r['ndcg_at_5'] for r in results) / len(results), 4),
        'passed': sum(r['recall_at_5'] for r in results) / len(results) >= 0.90,
        'details': results
    }

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

# 准备测试数据
data = {
    'question': ['理财产品的收益率是多少？', '保险理赔流程是什么？'],
    'answer': ['年化收益率6%-10%...', '理赔流程：1.提交申请 2.审核 3.赔付'],
    'contexts': [['文档1内容...', '文档2内容...'], ['文档3内容...', '文档4内容...']],
    'ground_truth': ['年化收益率6%-10%，具体根据产品不同有所差异', 
                     '理赔流程：1.提交理赔申请 2.保险公司审核 3.审核通过后赔付']
}

dataset = Dataset.from_dict(data)

# 评估
result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)

print(result)
# 输出各指标的得分
