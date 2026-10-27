from typing import List, Dict, Any
import numpy as np
from scipy.spatial.distance import cosine
from sentence_transformers import util

class EmbeddingValidator:
    """嵌入向量验证器"""
    
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的语义相似度"""
        embeddings = self.embedding_model.embed_documents([text1, text2])
        emb1, emb2 = embeddings[0], embeddings[1]
        
        # 使用余弦相似度
        similarity = 1 - cosine(emb1, emb2)
        return similarity
    
    def validate_embedding_quality(self, texts: List[str], threshold: float = 0.7) -> Dict[str, Any]:
        """验证嵌入质量"""
        if len(texts) < 2:
            return {'error': 'Need at least 2 texts for similarity comparison'}
        
        embeddings = self.embedding_model.embed_documents(texts)
        
        # 计算所有文本对之间的相似度
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = 1 - cosine(embeddings[i], embeddings[j])
                similarities.append(sim)
        
        avg_similarity = np.mean(similarities)
        max_similarity = np.max(similarities)
        min_similarity = np.min(similarities)
        
        # 检查是否有过于相似的文本（可能重复）
        highly_similar_pairs = [s for s in similarities if s > threshold]
        
        validation_result = {
            'avg_similarity': avg_similarity,
            'max_similarity': max_similarity,
            'min_similarity': min_similarity,
            'highly_similar_pairs': len(highly_similar_pairs),
            'total_pairs': len(similarities),
            'recommended_action': 'ok' if len(highly_similar_pairs) / len(similarities) < 0.1 else 'review_duplicates'
        }
        
        return validation_result
    
    def find_similar_texts(self, query_text: str, candidate_texts: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """查找最相似的文本"""
        query_embedding = self.embedding_model.embed_query(query_text)
        candidate_embeddings = self.embedding_model.embed_documents(candidate_texts)
        
        # 计算相似度
        similarities = []
        for i, cand_emb in enumerate(candidate_embeddings):
            sim = 1 - cosine(query_embedding, cand_emb)
            similarities.append({
                'index': i,
                'text': candidate_texts[i][:100] + '...' if len(candidate_texts[i]) > 100 else candidate_texts[i],
                'similarity': sim
            })
        
        # 按相似度排序
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

def test_embedding_validator():
    """测试嵌入验证器"""
    from langchain_openai import OpenAIEmbeddings
    
    # 初始化嵌入模型
    embedding_model = OpenAIEmbeddings()
    validator = EmbeddingValidator(embedding_model)
    
    # 测试文本
    texts = [
        "人工智能是计算机科学的分支",
        "机器学习属于人工智能领域", 
        "今天的天气很好",
        "人工智能和机器学习密切相关"
    ]
    
    # 验证嵌入质量
    quality_result = validator.validate_embedding_quality(texts)
    print("嵌入质量验证结果:", quality_result)
    
    # 查找相似文本
    similar_texts = validator.find_similar_texts(
        "AI技术的发展", 
        texts, 
        top_k=3
    )
    print("相似文本查找结果:", similar_texts)