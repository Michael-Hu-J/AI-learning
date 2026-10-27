"""向量存储与混合检索模块"""

import re
import math
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .document_parser import DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    chunk: DocumentChunk
    score: float
    source_doc_title: str = ""


class VectorStore:
    """向量存储（简化版，生产环境用 Milvus / FAISS / Chroma）"""

    def __init__(self):
        self.chunks: Dict[str, DocumentChunk] = {}
        logger.info("向量存储初始化完成")

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """批量添加切片"""
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk
        logger.info(f"添加 {len(chunks)} 个切片到向量存储")

    def remove_chunks(self, chunk_ids: List[str]) -> int:
        """批量删除切片"""
        removed = 0
        for chunk_id in chunk_ids:
            if chunk_id in self.chunks:
                del self.chunks[chunk_id]
                removed += 1
        logger.info(f"删除 {removed} 个切片")
        return removed

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """向量相似度检索（简化版）"""
        if not query_embedding:
            return []

        scored = []
        for chunk_id, chunk in self.chunks.items():
            if chunk.embedding:
                similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                scored.append((chunk, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def get_stats(self) -> Dict:
        """获取存储统计信息"""
        return {
            "total_chunks": len(self.chunks),
            "with_embedding": sum(1 for c in self.chunks.values() if c.embedding),
        }


class HybridRetriever:
    """混合检索器：向量检索 + 关键词检索 + 重排序"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.keyword_index: Dict[str, List[str]] = {}  # 关键词倒排索引
        logger.info("混合检索器初始化完成")

    def build_keyword_index(self) -> None:
        """构建关键词倒排索引"""
        self.keyword_index.clear()
        for chunk_id, chunk in self.vector_store.chunks.items():
            words = self._tokenize(chunk.content + " " + chunk.title)
            for word in words:
                if word not in self.keyword_index:
                    self.keyword_index[word] = []
                if chunk_id not in self.keyword_index[word]:
                    self.keyword_index[word].append(chunk_id)
        logger.info(f"关键词索引构建完成: {len(self.keyword_index)} 个词项")

    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        混合检索流程：
        1. 向量检索召回
        2. 关键词检索召回
        3. 合并去重
        4. 重排序
        """
        # 1. 向量检索（简化：用关键词匹配模拟向量得分）
        vector_results = self._keyword_vector_fallback(query, top_k * 2)

        # 2. 关键词检索
        keyword_results = self._keyword_search(query, top_k * 2)

        # 3. 合并去重
        merged = self._merge_results(vector_results, keyword_results)

        # 4. 重排序
        reranked = self._rerank(query, merged, top_k)

        logger.info(f"检索 '{query}' -> 返回 {len(reranked)} 条结果")
        return reranked

    def _keyword_vector_fallback(self, query: str, top_k: int) -> List[Tuple[DocumentChunk, float]]:
        """向量检索降级（用字符级匹配模拟）"""
        query_chars = set(query)
        scored = []

        for chunk_id, chunk in self.vector_store.chunks.items():
            chunk_chars = set(chunk.content + chunk.title)
            if not query_chars:
                continue
            overlap = len(query_chars & chunk_chars) / len(query_chars)
            scored.append((chunk, overlap))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _keyword_search(self, query: str, top_k: int) -> List[Tuple[DocumentChunk, float]]:
        """关键词检索"""
        query_words = self._tokenize(query)
        doc_scores: Dict[str, float] = {}

        for word in query_words:
            if word in self.keyword_index:
                for chunk_id in self.keyword_index[word]:
                    doc_scores[chunk_id] = doc_scores.get(chunk_id, 0) + 1

        results = []
        for chunk_id, score in doc_scores.items():
            chunk = self.vector_store.chunks.get(chunk_id)
            if chunk:
                normalized_score = score / len(query_words) if query_words else 0
                results.append((chunk, normalized_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    @staticmethod
    def _merge_results(vector_results: List, keyword_results: List) -> List[Tuple[DocumentChunk, float]]:
        """合并两种检索结果（加权平均 + RRF 微调）"""
        rrf_k = 60
        chunk_scores: Dict[str, List[float]] = {}
        chunk_map: Dict[str, DocumentChunk] = {}
        chunk_ranks: Dict[str, List[int]] = {}

        # 收集原始得分和排名
        for rank, (chunk, raw_score) in enumerate(vector_results, 1):
            if chunk.chunk_id not in chunk_scores:
                chunk_scores[chunk.chunk_id] = []
                chunk_ranks[chunk.chunk_id] = []
            chunk_scores[chunk.chunk_id].append(raw_score)
            chunk_ranks[chunk.chunk_id].append(rank)
            chunk_map[chunk.chunk_id] = chunk

        for rank, (chunk, raw_score) in enumerate(keyword_results, 1):
            if chunk.chunk_id not in chunk_scores:
                chunk_scores[chunk.chunk_id] = []
                chunk_ranks[chunk.chunk_id] = []
            chunk_scores[chunk.chunk_id].append(raw_score)
            chunk_ranks[chunk.chunk_id].append(rank)
            chunk_map[chunk.chunk_id] = chunk

        # 综合得分：平均原始得分 + RRF 排名奖励
        results = []
        for chunk_id, scores in chunk_scores.items():
            chunk = chunk_map[chunk_id]
            avg_score = sum(scores) / len(scores)
            # RRF 排名奖励（最高 0.1）
            rrf_bonus = sum(1 / (rrf_k + rank) for rank in chunk_ranks[chunk_id])
            rrf_bonus = min(rrf_bonus * 60, 0.1)  # 归一化到 0-0.1
            final_score = avg_score + rrf_bonus
            results.append((chunk, final_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    @staticmethod
    def _rerank(query: str, results: List, top_k: int) -> List[SearchResult]:
        """重排序：考虑文档时效性、标题匹配等因素"""
        query_lower = query.lower()
        search_results = []

        for chunk, base_score in results[:top_k * 2]:
            score = base_score

            # 标题匹配加分（最高 1.3 倍）
            if query_lower in chunk.title.lower():
                score *= 1.3

            # 时效性衰减（基于 metadata 中的时间信息）
            days_old = chunk.metadata.get("days_old", 0)
            if days_old > 365:
                score *= 0.6
            elif days_old > 180:
                score *= 0.8
            elif days_old > 90:
                score *= 0.9

            # 确保得分不超过 1.0
            score = min(score, 1.0)

            # 最低分过滤
            if score < 0.01:
                continue

            search_results.append(SearchResult(
                chunk=chunk,
                score=score,
                source_doc_title=chunk.title,
            ))

        return search_results[:top_k]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """简单分词 - 支持中英文，中文按字符切分"""
        # 先提取中文单字和英文单词
        tokens = []
        # 提取英文单词和数字（>=2 字符）
        english_tokens = re.findall(r"[a-zA-Z0-9]{2,}", text)
        tokens.extend(english_tokens)
        # 提取中文字符（单字）
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
        tokens.extend(chinese_chars)
        return [t.lower() for t in tokens]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = VectorStore()
    retriever = HybridRetriever(store)

    chunk = DocumentChunk(
        chunk_id="test001",
        source_doc_id="doc001",
        content="压力容器操作的安全距离为3米。操作人员必须佩戴防护装备。",
        title="安全操作规程",
        metadata={"days_old": 30},
    )
    store.add_chunks([chunk])
    retriever.build_keyword_index()

    print("=" * 60)
    print("混合检索测试")
    print("=" * 60)

    results = retriever.retrieve("压力容器安全距离")
    for r in results:
        print(f"得分: {r.score:.3f} | {r.chunk.content[:30]}...")
