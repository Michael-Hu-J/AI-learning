"""Chroma 读写封装。

全项目只有这一个文件直接操作 chromadb，好处是以后换 Milvus/Qdrant 只改这里，
pipeline 和路由层完全不用动。

索引约定：
- 建库时指定 hnsw:space=cosine，配合向量归一化，distance 才是"1 - 余弦相似度"；
- 注意 Chroma 的距离空间在 collection 创建时固定，已有库改不了，
  所以 config 里用了新名字 rag_chunks_v1，与旧脚本的库隔离。
"""

from pathlib import Path
from typing import Any

import chromadb


class VectorStore:
    def __init__(self, path: Path, collection_name: str) -> None:
        # PersistentClient：数据落盘到本地目录，进程重启后仍在
        self._client = chromadb.PersistentClient(path=str(path))
        # get_or_create：首次启动自动建库，后续启动复用已有数据
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """向量库中的切片总数，/health 用它判断是否为空库。"""
        return self._collection.count()

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """批量写入，返回写入条数。

        用 upsert 而非 add：同一 id 重复写入会覆盖，天然幂等。
        分批是为了控制单次请求的内存与事务大小（大文档可能上千条）。
        """
        total = 0
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            self._collection.upsert(
                ids=ids[start:end],
                documents=documents[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
            )
            total += len(ids[start:end])
        return total

    def query(self, embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        """向量检索，返回按距离升序（即相似度降序）的候选列表。

        Chroma 的返回是"二维"结构（每个 query 一组结果），
        这里只查一个向量，所以统一取下标 [0]。
        """
        result = self._collection.query(query_embeddings=[embedding], n_results=top_k)
        # 空库时这些键可能是 None 或空列表，用 or [[]] 统一成可迭代结构
        documents = result.get("documents") or [[]]
        metadatas = result.get("metadatas") or [[]]
        distances = result.get("distances") or [[]]

        hits: list[dict[str, Any]] = []
        for doc, meta, distance in zip(documents[0], metadatas[0], distances[0]):
            hits.append(
                {
                    "document": doc,
                    "metadata": meta or {},
                    # cosine 距离 ∈ [0,2]，转成相似度后越大越相关；
                    # 负数说明向量方向几乎相反，属于正常现象
                    "score": 1.0 - float(distance),
                }
            )
        return hits

    def delete_by_doc(self, doc_id: str) -> int:
        """删除某个文档的全部切片，返回删除条数。

        用 where 过滤 doc_id，而不是按 chunk_id 前缀删：
        Chroma 的 where 只支持等值/范围，不支持前缀匹配。
        """
        existing = self._collection.get(where={"doc_id": doc_id})
        ids = existing.get("ids") or []
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def list_documents(self) -> list[dict[str, Any]]:
        """扫描所有 metadata 并按 doc_id 聚合，得到"已入库文档列表"。

        没有单独的文档表，文档的元信息（文件名、格式）冗余存在每个切片上，
        属于典型的文档数据库反范式设计：查一次就够，不需要 join。
        """
        data = self._collection.get(include=["metadatas"])
        summary: dict[str, dict[str, Any]] = {}
        for meta in data.get("metadatas") or []:
            doc_id = (meta or {}).get("doc_id")
            if not doc_id:
                continue  # 历史遗留数据可能缺字段，跳过而不是报错
            item = summary.setdefault(
                doc_id,
                {
                    "doc_id": doc_id,
                    "filename": meta.get("filename", ""),
                    "format": meta.get("format", ""),
                    "chunks": 0,
                },
            )
            item["chunks"] += 1  # 每扫到一条切片就计数一次
        return sorted(summary.values(), key=lambda item: item["filename"])
