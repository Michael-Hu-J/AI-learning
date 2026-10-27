"""RAG 知识库检索模块 - 混合检索（关键词 + 向量模拟）"""

import json
import hashlib
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDoc:
    """知识库文档"""
    doc_id: str
    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    updated_at: float = 0.0
    version: int = 1

    def to_dict(self) -> Dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeDoc":
        return cls(
            doc_id=data["doc_id"],
            title=data["title"],
            content=data["content"],
            category=data["category"],
            tags=data.get("tags", []),
            updated_at=data.get("updated_at", 0.0),
            version=data.get("version", 1),
        )


class VectorStore:
    """简易向量存储（生产环境用 Milvus / Pinecone / FAISS）"""

    def __init__(self):
        self.docs: Dict[str, KnowledgeDoc] = {}
        logger.info("向量存储初始化完成")

    def add_document(self, doc: KnowledgeDoc) -> None:
        """添加文档"""
        doc.updated_at = time.time()
        self.docs[doc.doc_id] = doc
        logger.debug(f"添加文档: {doc.doc_id} - {doc.title}")

    def load_from_json(self, filepath: str) -> int:
        """从 JSON 文件加载知识库"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            docs = data.get("documents", [])
            count = 0
            for doc_data in docs:
                doc = KnowledgeDoc.from_dict(doc_data)
                self.add_document(doc)
                count += 1
            logger.info(f"从 {filepath} 加载 {count} 条文档")
            return count
        except Exception as e:
            logger.error(f"加载知识库失败: {e}")
            return 0

    def search(self, query: str, top_k: int = 3, min_score: float = 0.25) -> List[KnowledgeDoc]:
        """
        混合检索：关键词匹配 + 简单向量相似度
        生产环境应使用专业向量数据库
        """
        query_lower = query.lower()
        scored_docs = []

        for doc_id, doc in self.docs.items():
            # 关键词匹配得分
            keyword_score = self._keyword_score(query_lower, doc)
            # 向量相似度得分（简化版：用内容重叠度模拟）
            vector_score = self._vector_score(query_lower, doc)
            # 时效性衰减
            freshness_score = self._freshness_score(doc)
            # 综合得分
            final_score = keyword_score * 0.5 + vector_score * 0.3 + freshness_score * 0.2

            scored_docs.append((doc, final_score))

        # 按得分排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 过滤低分结果
        filtered = [(doc, score) for doc, score in scored_docs if score >= min_score]
        results = [doc for doc, score in filtered[:top_k]]
        logger.info(f"检索 '{query}' -> 返回 {len(results)} 条结果")
        return results

    @staticmethod
    def _keyword_score(query: str, doc: KnowledgeDoc) -> float:
        """关键词匹配得分 - 支持中文逐字匹配"""
        # 中文按字符切分，英文按单词切分
        query_chars = set(query)
        doc_text = (doc.title + " " + doc.content).lower()
        doc_chars = set(doc_text)

        if not query_chars:
            return 0.0

        # 字符级 overlap
        overlap = len(query_chars & doc_chars) / len(query_chars)

        # 标题权重更高
        title_chars = set(doc.title.lower())
        title_overlap = len(query_chars & title_chars) / len(query_chars) if query_chars else 0

        # 完整词匹配加分（针对英文和数字）
        query_words = set(query.split())
        doc_words = set(doc_text.split())
        word_overlap = len(query_words & doc_words) / len(query_words) if query_words else 0

        return overlap * 0.5 + title_overlap * 0.3 + word_overlap * 0.2

    @staticmethod
    def _vector_score(query: str, doc: KnowledgeDoc) -> float:
        """向量相似度得分（简化模拟）"""
        if doc.embedding:
            # 实际应计算余弦相似度
            return 0.5  # 模拟值
        return 0.0

    @staticmethod
    def _freshness_score(doc: KnowledgeDoc) -> float:
        """时效性得分 - 文档越新得分越高"""
        if doc.updated_at == 0:
            return 1.0  # 无时间戳，默认最新
        days_old = (time.time() - doc.updated_at) / 86400
        if days_old < 90:
            return 1.0
        elif days_old < 180:
            return 0.7
        else:
            return 0.5

    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        categories = {}
        for doc in self.docs.values():
            categories[doc.category] = categories.get(doc.category, 0) + 1
        return {
            "total_docs": len(self.docs),
            "categories": categories,
        }


class RAGRetriever:
    """RAG 检索器"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        logger.info("RAG 检索器初始化完成")

    def retrieve(self, query: str, top_k: int = 3) -> List[KnowledgeDoc]:
        """检索相关知识文档"""
        docs = self.vector_store.search(query, top_k)
        return docs

    def retrieve_with_filter(self, query: str, category: str = "", top_k: int = 3) -> List[KnowledgeDoc]:
        """带分类过滤的检索"""
        all_docs = self.vector_store.search(query, top_k * 2)
        if category:
            filtered = [d for d in all_docs if d.category == category]
            return filtered[:top_k]
        return all_docs[:top_k]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = VectorStore()

    # 添加测试文档
    test_docs = [
        KnowledgeDoc(
            doc_id="FAQ001", title="如何重置密码",
            content="登录页面点击忘记密码，输入注册邮箱，系统会发送重置链接到您的邮箱。",
            category="account", tags=["密码", "重置", "登录"],
        ),
        KnowledgeDoc(
            doc_id="FAQ002", title="退款政策说明",
            content="商品签收后7天内可申请退款，退款将在3-5个工作日内原路返回。",
            category="refund", tags=["退款", "政策", "时间"],
        ),
        KnowledgeDoc(
            doc_id="FAQ003", title="物流查询方法",
            content="在订单详情页查看物流信息，或输入运单号在物流页面查询。",
            category="logistics", tags=["物流", "查询", "快递"],
        ),
        KnowledgeDoc(
            doc_id="FAQ004", title="如何修改收货地址",
            content="订单未发货前可在订单详情页修改收货地址，已发货订单需联系客服。",
            category="order", tags=["地址", "修改", "收货"],
        ),
    ]

    for doc in test_docs:
        store.add_document(doc)

    retriever = RAGRetriever(store)

    print("=" * 60)
    print("RAG 检索测试")
    print("=" * 60)
    test_queries = [
        "快递怎么还没到",
        "怎么重置密码",
        "退款要多久",
        "怎么修电脑",  # 无结果
    ]

    for query in test_queries:
        results = retriever.retrieve(query, top_k=2)
        print(f"\n查询: {query}")
        if results:
            for doc in results:
                print(f"  ✅ {doc.title} (分类: {doc.category})")
        else:
            print("  ❌ 无匹配结果")

    print(f"\n知识库统计: {store.get_stats()}")
