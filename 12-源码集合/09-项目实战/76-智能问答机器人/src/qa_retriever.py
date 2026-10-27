"""
=============================================================================
 qa_retriever.py — 知识库检索模块
 作者: 测试员周周 (14年测试老兵)
 描述: 知识库管理 + 混合检索（关键词 + 语义 + 时效）
 架构:
   - KnowledgeDocument: 文档数据类
   - KnowledgeBase: 知识库容器，支持添加/检索/索引构建
   - 检索流程: 分词 → 关键词倒排索引命中 → 多维度打分 → 排序截断
 注意: 生产环境替换 _tokenize 为 jieba，替换 _semantic_score 为 Embedding 模型
=============================================================================
"""

import hashlib
import math
import re
import time
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("qa_bot.retriever")


# ======================== 数据结构 ========================


@dataclass
class KnowledgeDocument:
    """知识文档"""
    doc_id: str
    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    source: str = ""          # 来源文档
    updated_at: float = 0.0
    version: int = 1

    def to_dict(self) -> Dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "source": self.source,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeDocument":
        return cls(**data)


@dataclass
class RetrievalResult:
    """检索结果"""
    query: str
    documents: List[Tuple[KnowledgeDocument, float]] = field(default_factory=list)
    total_candidates: int = 0
    elapsed_ms: float = 0.0
    top_score: float = 0.0


# ======================== 知识库核心类 ========================


class KnowledgeBase:
    """
    知识库：支持向量检索 + 关键词检索的混合检索

    核心能力:
      - add_document: 添加文档并构建倒排索引
      - hybrid_search: 混合检索（关键词 + 语义相似度 + 时效）
      - remove_document / clear: 文档管理
      - load / save: 持久化
    """

    def __init__(self):
        self.documents: Dict[str, KnowledgeDocument] = {}
        self.word_index: Dict[str, List[str]] = {}   # 关键词 → doc_id 列表
        self._initialized = True
        logger.info("知识库初始化完成")

    # ---------- 文档管理 ----------

    def add_document(self, doc: KnowledgeDocument) -> None:
        """添加文档到知识库"""
        doc.updated_at = time.time()
        self.documents[doc.doc_id] = doc
        self._build_index(doc)
        logger.info("添加文档: doc_id=%s, title=%s, category=%s",
                     doc.doc_id, doc.title, doc.category)

    def remove_document(self, doc_id: str) -> bool:
        """从知识库移除文档"""
        doc = self.documents.pop(doc_id, None)
        if doc is None:
            logger.warning("移除文档失败，不存在: %s", doc_id)
            return False
        # 重建索引（简单实现：全量重建）
        self._rebuild_index()
        logger.info("移除文档: doc_id=%s", doc_id)
        return True

    def clear(self) -> None:
        """清空知识库"""
        self.documents.clear()
        self.word_index.clear()
        logger.info("知识库已清空")

    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """获取指定文档"""
        return self.documents.get(doc_id)

    def document_count(self) -> int:
        """文档总数"""
        return len(self.documents)

    # ---------- 索引构建 ----------

    def _build_index(self, doc: KnowledgeDocument) -> None:
        """为单个文档构建倒排索引"""
        words = self._tokenize(doc.title + " " + doc.content)
        for word in words:
            if word not in self.word_index:
                self.word_index[word] = []
            if doc.doc_id not in self.word_index[word]:
                self.word_index[word].append(doc.doc_id)

    def _rebuild_index(self) -> None:
        """全量重建倒排索引"""
        self.word_index.clear()
        for doc in self.documents.values():
            self._build_index(doc)
        logger.info("倒排索引重建完成，共 %d 个词条", len(self.word_index))

    # ---------- 分词 ----------

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        简单分词（生产环境用 jieba 或专业分词器）

        策略:
          1. 提取连续中文块，按 2-gram 滑动窗口拆分（模拟词级粒度）
          2. 提取英文单词
          3. 过滤长度 < 2 的词

        示例:
          "怎么报名课程" → ["怎么", "么报", "报名", "名课", "课程"]
          "hello world"  → ["hello", "world"]
        """
        result = []

        # 1. 提取英文单词
        english_tokens = re.findall(r"[a-zA-Z]+", text)
        for token in english_tokens:
            t = token.lower()
            if len(t) >= 2:
                result.append(t)

        # 2. 提取中文并做 2-gram 拆分
        chinese_blocks = re.findall(r"[\u4e00-\u9fff]+", text)
        for block in chinese_blocks:
            if len(block) <= 2:
                if block not in result:
                    result.append(block)
            else:
                for i in range(len(block) - 1):
                    gram = block[i:i+2]
                    if gram not in result:
                        result.append(gram)

        return result

    # ---------- 同义词扩展 ----------

    @staticmethod
    def _expand_synonyms(query: str) -> str:
        """
        简单的同义词扩展
        生产环境应使用同义词词库或 Embedding 语义匹配
        """
        synonym_map = {
            "报名": "报名 注册 选课 购买",
            "选课": "选课 报名 选择课程",
            "退款": "退款 退费 退钱 取消",
            "登录": "登录 登陆 进入 访问",
            "密码": "密码 口令 验证码",
            "课程": "课程 课 教程 学习内容",
            "支付": "支付 付款 缴费 交钱",
            "学习": "学习 学 上课 听课",
        }
        expanded = query
        for word, synonyms in synonym_map.items():
            if word in query:
                expanded += " " + synonyms
        return expanded if expanded != query else query

    # ---------- 混合检索 ----------

    def hybrid_search(self, query: str, top_k: int = 5,
                      config: Optional[Dict] = None) -> List[Tuple[KnowledgeDocument, float]]:
        """
        混合检索：关键词匹配 + 语义相似度 + 时效性
        返回按综合得分排序的文档列表

        参数:
            query: 用户查询
            top_k: 返回结果数
            config: 检索配置（权重等），None 则使用默认值

        返回:
            List[(KnowledgeDocument, score)]
        """
        start_time = time.time()

        if config is None:
            config = {}

        kw_weight = config.get("keyword_weight", 0.4)
        sem_weight = config.get("semantic_weight", 0.4)
        fresh_weight = config.get("freshness_weight", 0.2)
        enable_synonym = config.get("enable_synonym_expansion", True)

        # 分词
        query_tokens = self._tokenize(query)
        if not query_tokens:
            logger.info("空查询，返回空结果")
            return []

        # 同义词扩展
        if enable_synonym:
            expanded_query = self._expand_synonyms(query)
            expanded_tokens = self._tokenize(expanded_query)
            logger.debug("同义词扩展: %s -> %s", query, expanded_query)
        else:
            expanded_tokens = query_tokens

        # 收集候选文档
        candidate_ids = set()
        for token in expanded_tokens:
            if token in self.word_index:
                candidate_ids.update(self.word_index[token])

        if not candidate_ids:
            logger.info("未命中任何文档，查询=%s", query[:30])
            return []

        # 评分
        scored_docs = []
        for doc_id in candidate_ids:
            doc = self.documents.get(doc_id)
            if not doc:
                continue

            keyword_score = self._keyword_match_score(query_tokens, doc)
            semantic_score = self._semantic_score(expanded_tokens, doc)
            freshness_score = self._freshness_score(doc)

            final_score = (
                keyword_score * kw_weight
                + semantic_score * sem_weight
                + freshness_score * fresh_weight
            )

            scored_docs.append((doc, final_score))

        # 排序截断
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        top_results = scored_docs[:top_k]

        elapsed = (time.time() - start_time) * 1000
        logger.info("混合检索完成: query=%s, candidates=%d, top_score=%.4f, elapsed=%.1fms",
                     query[:30], len(candidate_ids),
                     top_results[0][1] if top_results else 0,
                     elapsed)

        return top_results

    # ======================== 评分方法 ========================

    @staticmethod
    def _keyword_match_score(query_tokens: List[str],
                              doc: KnowledgeDocument) -> float:
        """
        关键词匹配得分

        计算查询词在文档标题和内容中的命中率
        标题匹配权重 (0.6) > 正文匹配 (0.4)
        """
        if not query_tokens:
            return 0.0

        doc_title_lower = doc.title.lower()
        doc_text_lower = (doc.title + " " + doc.content).lower()

        # 标题匹配
        title_matched = sum(1 for t in query_tokens if t in doc_title_lower)
        # 全文匹配
        body_matched = sum(1 for t in query_tokens if t in doc_text_lower)

        n = len(query_tokens)
        title_score = title_matched / n
        body_score = body_matched / n

        return title_score * 0.6 + body_score * 0.4

    @staticmethod
    def _semantic_score(query_tokens: List[str],
                         doc: KnowledgeDocument) -> float:
        """
        语义相似度得分（简化版）

        基于 Jaccard 相似度计算查询词与文档词集合的重叠度
        生产环境应替换为 Embedding 向量余弦相似度
        """
        if not query_tokens:
            return 0.0

        doc_tokens = set(
            KnowledgeBase._tokenize(doc.title + " " + doc.content)
        )
        query_set = set(query_tokens)

        if not query_set:
            return 0.0

        intersection = query_set & doc_tokens
        union = query_set | doc_tokens

        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def _freshness_score(doc: KnowledgeDocument) -> float:
        """
        文档时效性得分

        规则:
          - 30 天内更新: 1.0
          - 30-90 天: 0.8
          - 90-180 天: 0.6
          - 180 天以上: 0.4
          - 未记录时间: 0.5
        """
        if doc.updated_at == 0:
            return 0.5

        days_old = (time.time() - doc.updated_at) / 86400
        if days_old < 30:
            return 1.0
        elif days_old < 90:
            return 0.8
        elif days_old < 180:
            return 0.6
        else:
            return 0.4

    # ---------- 持久化 ----------

    def save(self, filepath: str) -> bool:
        """将知识库保存到 JSON 文件"""
        try:
            data = {
                "documents": {
                    doc_id: doc.to_dict()
                    for doc_id, doc in self.documents.items()
                },
                "saved_at": time.time(),
            }
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("知识库已保存: %s, 文档数=%d", filepath, len(self.documents))
            return True
        except Exception as e:
            logger.error("保存知识库失败: %s", e)
            return False

    def load(self, filepath: str) -> bool:
        """从 JSON 文件加载知识库"""
        try:
            if not Path(filepath).exists():
                logger.warning("知识库文件不存在: %s", filepath)
                return False
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.documents = {}
            for doc_id, doc_data in data.get("documents", {}).items():
                self.documents[doc_id] = KnowledgeDocument.from_dict(doc_data)
            self._rebuild_index()
            logger.info("知识库已加载: %s, 文档数=%d", filepath, len(self.documents))
            return True
        except Exception as e:
            logger.error("加载知识库失败: %s", e)
            return False


# ======================== 快捷导出 ========================

__all__ = [
    "KnowledgeBase",
    "KnowledgeDocument",
    "RetrievalResult",
]
