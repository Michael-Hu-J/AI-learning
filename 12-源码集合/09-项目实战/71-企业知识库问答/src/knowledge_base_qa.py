"""知识库问答系统"""

import logging
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field

from .vector_store import HybridRetriever, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class QAResult:
    """问答结果"""
    question: str
    answer: str = ""
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    is_rejected: bool = False
    quality_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "sources": self.sources,
            "confidence": round(self.confidence, 3),
            "is_rejected": self.is_rejected,
            "quality_issues": self.quality_issues,
        }


class KnowledgeBaseQA:
    """知识库问答系统"""

    def __init__(self, retriever: HybridRetriever, llm_call_func: Optional[Callable] = None,
                 config: Optional[Dict] = None):
        self.retriever = retriever
        self.llm = llm_call_func
        self.config = config or {}
        self.min_score = self.config.get("min_retrieval_score", 0.3)
        logger.info("知识库问答系统初始化完成")

    def answer(self, question: str) -> QAResult:
        """回答用户问题"""
        result = QAResult(question=question)

        # 1. 检索相关知识
        search_results = self.retriever.retrieve(question, top_k=5)

        # 2. 判断检索质量
        if not search_results or search_results[0].score < self.min_score:
            result.is_rejected = True
            result.answer = "抱歉，知识库中未找到相关信息。"
            logger.info(f"问题 '{question}' 被拒绝 (最高分: {search_results[0].score if search_results else 0:.3f})")
            return result

        # 3. 拼接上下文
        context_parts = []
        for i, sr in enumerate(search_results[:3], 1):
            context_parts.append(
                f"[来源{i}] {sr.source_doc_title}：{sr.chunk.content}"
            )
        context = "\n".join(context_parts)
        result.sources = [sr.source_doc_title for sr in search_results[:3]]

        # 4. 生成回答
        if self.llm:
            result.answer = self._generate_answer(question, context)
        else:
            # 无 LLM 时直接返回首条结果
            result.answer = search_results[0].chunk.content

        # 5. 计算置信度
        result.confidence = search_results[0].score if search_results else 0.0

        # 6. 安全检查（数值一致性）
        self._check_safety_consistency(result, search_results)

        logger.info(f"回答问题 '{question}' -> 置信度: {result.confidence:.3f}")
        return result

    def _generate_answer(self, question: str, context: str) -> str:
        """基于检索结果生成回答"""
        prompt = (
            f"你是一个企业知识助手。请根据以下知识库内容回答用户问题。\n\n"
            f"知识库内容：\n{context}\n\n"
            f"用户问题：{question}\n\n"
            f"回答要求：\n"
            f"1. 只基于知识库内容回答，不要编造信息\n"
            f"2. 回答要准确、简洁\n"
            f"3. 如果知识库中没有相关信息，请回答'抱歉，知识库中未找到相关信息'\n"
            f"4. 涉及安全、合规的内容，务必严格按照知识库原文回答\n"
        )
        return self.llm(prompt)

    def _check_safety_consistency(self, result: QAResult, search_results: List[SearchResult]) -> None:
        """安全检查：确保安全相关回答的数值与原文一致"""
        # 简单检查：如果回答中包含数字，原文中也应有相同数字
        import re
        answer_numbers = re.findall(r'\d+\.?\d*', result.answer)
        for sr in search_results[:3]:
            doc_numbers = re.findall(r'\d+\.?\d*', sr.chunk.content)
            for num in answer_numbers:
                if num and num not in doc_numbers:
                    result.quality_issues.append(
                        f"回答中的数值 '{num}' 在源文档中未找到，可能存在不一致"
                    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from .document_parser import DocumentChunk
    from .vector_store import VectorStore

    def mock_llm(prompt):
        return "根据安全操作规程，压力容器操作的安全距离为3米。"

    store = VectorStore()
    store.add_chunks([DocumentChunk(
        chunk_id="qa001", source_doc_id="qa_doc",
        content="压力容器操作的安全距离为3米。操作人员必须佩戴防护装备，定期检查设备状态。",
        title="安全操作规程", metadata={"days_old": 30},
    )])

    retriever = HybridRetriever(store)
    retriever.build_keyword_index()

    qa = KnowledgeBaseQA(retriever, mock_llm)

    print("=" * 60)
    print("知识库问答测试")
    print("=" * 60)

    # 测试 1: 正常问答
    result = qa.answer("压力容器安全距离是多少")
    print(f"\n问题: {result.question}")
    print(f"回答: {result.answer}")
    print(f"来源: {result.sources}")
    print(f"置信度: {result.confidence:.3f}")

    # 测试 2: 拒答
    result = qa.answer("怎么修电脑")
    print(f"\n问题: {result.question}")
    print(f"回答: {result.answer}")
    print(f"是否拒答: {result.is_rejected}")
