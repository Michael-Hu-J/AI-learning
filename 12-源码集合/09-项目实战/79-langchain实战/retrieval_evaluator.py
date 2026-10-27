from typing import List, Dict, Any
from langchain.schema import Document
import numpy as np

class RetrievalEvaluator:
    """检索评估器"""
    
    def evaluate(self, query: str, retrieved_docs: List[Document], expected_docs: List[Document] = None) -> Dict[str, Any]:
        """评估检索结果"""
        if expected_docs is None:
            # 如果没有预期文档，只计算基本指标
            return {
                'precision': 1.0,  # 假设所有检索到的都是相关的
                'recall': 1.0,     # 假设所有相关文档都已检索到
                'f1_score': 1.0,
                'hit_rate': 1.0,
                'mrr': 1.0,  # Mean Reciprocal Rank
                'ndcg': 1.0, # Normalized Discounted Cumulative Gain
                'query': query,
                'retrieved_count': len(retrieved_docs)
            }
        
        # 将预期文档转换为文本集合以便比较
        expected_texts = {doc.page_content.strip() for doc in expected_docs}
        
        # 将检索到的文档转换为文本集合
        retrieved_texts = {doc.page_content.strip() for doc in retrieved_docs}
        
        # 计算基本指标
        true_positives = len(expected_texts.intersection(retrieved_texts))
        false_positives = len(retrieved_texts) - true_positives
        false_negatives = len(expected_texts) - true_positives
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Hit Rate (至少检索到一个相关文档的比例)
        hit_rate = 1.0 if true_positives > 0 else 0.0
        
        # Mean Reciprocal Rank (MRR)
        mrr = self._calculate_mrr(retrieved_docs, expected_docs)
        
        # Normalized Discounted Cumulative Gain (NDCG)
        ndcg = self._calculate_ndcg(retrieved_docs, expected_docs)
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'hit_rate': hit_rate,
            'mrr': mrr,
            'ndcg': ndcg,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'query': query,
            'retrieved_count': len(retrieved_docs),
            'expected_count': len(expected_docs)
        }
    
    def _calculate_mrr(self, retrieved_docs: List[Document], expected_docs: List[Document]) -> float:
        """计算平均倒数排名"""
        expected_texts = {doc.page_content.strip() for doc in expected_docs}
        
        for rank, doc in enumerate(retrieved_docs, 1):
            if doc.page_content.strip() in expected_texts:
                return 1.0 / rank
        
        return 0.0  # 没有找到相关文档
    
    def _calculate_ndcg(self, retrieved_docs: List[Document], expected_docs: List[Document]) -> float:
        """计算归一化折损累积增益"""
        # 简化版NDCG计算
        # 假设相关性为二元（相关或不相关）
        
        expected_texts = {doc.page_content.strip() for doc in expected_docs}
        relevance_scores = [1 if doc.page_content.strip() in expected_texts else 0 
                           for doc in retrieved_docs]
        
        if not relevance_scores or sum(relevance_scores) == 0:
            return 0.0
        
        # 计算DCG
        dcg = relevance_scores[0]  # 第一个元素不打折
        for i in range(1, len(relevance_scores)):
            dcg += relevance_scores[i] / np.log2(i + 1)
        
        # 计算理想DCG (IDCG)
        ideal_relevance = sorted(relevance_scores, reverse=True)
        idcg = ideal_relevance[0]  # 第一个元素不打折
        for i in range(1, len(ideal_relevance)):
            idcg += ideal_relevance[i] / np.log2(i + 1)
        
        # 避免除零错误
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def batch_evaluate(self, queries_with_ground_truth: List[Dict]) -> Dict[str, Any]:
        """批量评估多个查询"""
        all_results = []
        
        for query_item in queries_with_ground_truth:
            result = self.evaluate(
                query=query_item['query'],
                retrieved_docs=query_item.get('retrieved_docs', []),
                expected_docs=query_item.get('expected_docs', [])
            )
            all_results.append(result)
        
        # 计算平均指标
        avg_precision = np.mean([r['precision'] for r in all_results])
        avg_recall = np.mean([r['recall'] for r in all_results])
        avg_f1_score = np.mean([r['f1_score'] for r in all_results])
        avg_hit_rate = np.mean([r['hit_rate'] for r in all_results])
        avg_mrr = np.mean([r['mrr'] for r in all_results])
        avg_ndcg = np.mean([r['ndcg'] for r in all_results])
        
        return {
            'average_metrics': {
                'avg_precision': avg_precision,
                'avg_recall': avg_recall,
                'avg_f1_score': avg_f1_score,
                'avg_hit_rate': avg_hit_rate,
                'avg_mrr': avg_mrr,
                'avg_ndcg': avg_ndcg
            },
            'individual_results': all_results,
            'total_queries': len(queries_with_ground_truth)
        }

def test_retrieval_evaluator():
    """测试检索评估器"""
    from langchain.schema import Document
    
    evaluator = RetrievalEvaluator()
    
    # 创建测试数据
    query = "人工智能的发展历史"
    retrieved_docs = [
        Document(page_content="人工智能起源于20世纪50年代"),
        Document(page_content="机器学习是AI的重要分支"),
        Document(page_content="深度学习推动了AI的快速发展")
    ]
    expected_docs = [
        Document(page_content="人工智能起源于20世纪50年代"),
        Document(page_content="AI发展经历了多个阶段")
    ]
    
    result = evaluator.evaluate(query, retrieved_docs, expected_docs)
    print("检索评估结果:", result)