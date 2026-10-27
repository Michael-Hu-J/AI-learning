from typing import List, Dict, Any
from langchain.schema import Document
import numpy as np
from embedding_validator import EmbeddingValidator

class AnswerValidator:
    """答案验证器"""
    
    def __init__(self, embedding_model=None):
        self._embedding_model = embedding_model
        self.embedding_validator = None  # 延迟初始化
    
    def validate(self, 
                 question: str, 
                 generated_answer: str, 
                 expected_answer: str = "",
                 expected_sources: List[str] = None,
                 source_documents: List[Document] = None) -> Dict[str, Any]:
        """验证生成的答案"""
        if self.embedding_validator is None:
            if self._embedding_model is not None:
                embedding_model = self._embedding_model
            else:
                from langchain_openai import OpenAIEmbeddings
                embedding_model = OpenAIEmbeddings()
            self.embedding_validator = EmbeddingValidator(embedding_model)
        
        # 1. 相关性评分 (与问题的相关性)
        relevance_score = self._calculate_relevance_score(question, generated_answer)
        
        # 2. 准确性评分 (与期望答案的相似度，如果有提供)
        accuracy_score = self._calculate_accuracy_score(generated_answer, expected_answer)
        
        # 3. 忠实度评分 (答案是否基于提供的文档)
        faithfulness_score = self._calculate_faithfulness_score(
            generated_answer, source_documents or []
        )
        
        # 4. 来源验证 (答案是否引用了正确的文档)
        source_coverage_score = self._calculate_source_coverage_score(
            generated_answer, expected_sources or [], source_documents or []
        )
        
        # 5. 语法和流畅性评分
        fluency_score = self._calculate_fluency_score(generated_answer)
        
        return {
            'relevance_score': relevance_score,
            'accuracy_score': accuracy_score,
            'faithfulness_score': faithfulness_score,
            'source_coverage_score': source_coverage_score,
            'fluency_score': fluency_score,
            'overall_score': self._calculate_overall_answer_score(
                relevance_score, accuracy_score, faithfulness_score, 
                source_coverage_score, fluency_score
            )
        }
    
    def _calculate_relevance_score(self, question: str, answer: str) -> float:
        """计算答案与问题的相关性"""
        return self.embedding_validator.calculate_similarity(question, answer)
    
    def _calculate_accuracy_score(self, generated: str, expected: str) -> float:
        """计算答案准确性"""
        if not expected:
            return 0.5  # 没有期望答案时返回中等分数
        
        return self.embedding_validator.calculate_similarity(generated, expected)
    
    def _calculate_faithfulness_score(self, answer: str, source_docs: List[Document]) -> float:
        """计算答案忠实度（基于源文档）"""
        if not source_docs:
            return 0.3  # 没有源文档时返回较低分数
        
        # 检查答案中的关键信息是否在源文档中
        answer_sentences = self._split_into_sentences(answer)
        source_text = " ".join([doc.page_content for doc in source_docs])
        
        faithful_sentences = 0
        total_sentences = len(answer_sentences)
        
        for sent in answer_sentences:
            if len(sent.strip()) > 10:  # 只考虑有意义的句子
                # 检查句子是否在源文档中能找到相关信息
                similarity = self.embedding_validator.calculate_similarity(sent, source_text)
                if similarity > 0.3:  # 阈值可调整
                    faithful_sentences += 1
        
        return faithful_sentences / total_sentences if total_sentences > 0 else 0.0
    
    def _calculate_source_coverage_score(self, answer: str, expected_sources: List[str], source_docs: List[Document]) -> float:
        """计算来源覆盖评分"""
        if not expected_sources or not source_docs:
            return 0.5  # 没有预期来源时返回中等分数
        
        # 检查答案是否提到了预期的来源信息
        answer_lower = answer.lower()
        expected_found = 0
        
        for expected in expected_sources:
            if expected.lower() in answer_lower:
                expected_found += 1
        
        return expected_found / len(expected_sources) if len(expected_sources) > 0 else 0.0
    
    def _calculate_fluency_score(self, answer: str) -> float:
        """计算语法和流畅性评分"""
        # 简单的启发式评分
        score = 0.5  # 基础分数
        
        # 长度合理性
        words = answer.split()
        if 10 <= len(words) <= 200:  # 合理的回答长度
            score += 0.2
        
        # 是否包含完整的句子
        sentences = self._split_into_sentences(answer)
        if len(sentences) >= 1:
            score += 0.2
        
        # 是否包含适当的标点符号
        if '.' in answer or '?' in answer or '!' in answer:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_overall_answer_score(self, *scores) -> float:
        """计算总体答案评分"""
        return np.mean(scores)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """简单的句子分割"""
        import re
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[.!?]+', text)
        # 过滤空字符串并去除首尾空格
        return [s.strip() for s in sentences if s.strip()]

def test_answer_validator():
    """测试答案验证器"""
    validator = AnswerValidator()
    
    # 测试数据
    question = "人工智能的发展历史是什么？"
    generated_answer = "人工智能起源于20世纪50年代，经过了多个发展阶段，现在已经成为重要的技术领域。"
    expected_answer = "人工智能始于1956年的达特茅斯会议，至今经历了多次起伏。"
    source_docs = [
        Document(page_content="人工智能起源于20世纪50年代"),
        Document(page_content="AI发展经历了多个阶段")
    ]
    
    result = validator.validate(
        question=question,
        generated_answer=generated_answer,
        expected_answer=expected_answer,
        source_documents=source_docs
    )
    
    print("答案验证结果:", result)