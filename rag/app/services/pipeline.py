"""编排层：把各模块串成两条完整链路，对外只暴露 ingest / ask。

依赖方向是单向的：
    路由层 -> pipeline -> (loader / chunker / embedder / store / reranker / generator)
services 层不 import FastAPI，所以它也能被 CLI、批处理脚本复用。

线程模型说明：
- ingest 是同步方法：解析 + 向量化是 CPU/IO 密集的同步调用，
  由路由层用 run_in_threadpool 包起来，避免阻塞事件循环；
- ask 是异步方法：内部把同步部分丢进线程池，只有调用 DeepSeek 才真正 await。
"""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from starlette.concurrency import run_in_threadpool

from ..config import Settings
from ..errors import DocumentParseError, PayloadTooLargeError, UnsupportedFormatError
from . import chunker, loader
from .embedder import Embedder
from .generator import Generator
from .reranker import Reranker
from .vector_store import VectorStore


@dataclass
class IngestResult:
    """导入结果，路由层再转成 IngestResponse。"""

    doc_id: str
    filename: str
    format: str
    sections: int
    chunks: int
    replaced: bool
    elapsed_ms: int


@dataclass
class AskResult:
    """问答结果，references 是 dict 列表（交给 schemas.Reference 校验）。"""

    answer: str
    references: list[dict[str, Any]]
    elapsed_ms: int


class RAGPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        settings.ensure_dirs()  # 首次启动时创建 uploads / chroma_db
        # 各组件在构造时都不加载模型权重，只有 embedder/rreranker 的 load() 才会，
        # 这样 RAGPipeline 的构造是"廉价"的，可以放心在 lifespan 里 new
        self.store = VectorStore(settings.chroma_dir, settings.collection_name)
        self.embedder = Embedder(settings.embedding_model_path, settings.embed_batch_size)
        self.reranker = Reranker(settings.reranker_model_path, settings.enable_rerank)
        self.generator = Generator(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            temperature=settings.deepseek_temperature,
            max_tokens=settings.deepseek_max_tokens,
            timeout=settings.deepseek_timeout,
        )

    @property
    def ready(self) -> bool:
        """能否提供检索能力（生成能力另由 generator.ready 决定）。"""
        return self.embedder.loaded

    def load_models(self) -> None:
        """在 lifespan 的线程池里调用，加载一次、全程复用。"""
        self.embedder.load()
        self.reranker.load()

    # ------------------------------------------------------------ 文档导入
    def ingest(self, filename: str, data: bytes) -> IngestResult:
        """文件字节 -> 切片 -> 向量 -> 入库。

        幂等设计：doc_id 由文件内容哈希得到，同一份内容重复上传会先删旧切片再写入，
        因此不会产生重复向量，也不会把旧版本残留的切片留在库里。
        """
        started = time.perf_counter()
        suffix = Path(filename).suffix.lower()

        # 三层校验：扩展名 -> 非空 -> 大小。路由层已校验过扩展名，
        # 这里再挡一次是为了让 pipeline 被直接调用时也安全
        if suffix not in loader.SUPPORTED_SUFFIXES:
            raise UnsupportedFormatError(f"不支持的文件类型：{suffix or '无扩展名'}")
        if not data:
            raise DocumentParseError("上传文件为空")
        if len(data) > self.settings.max_upload_mb * 1024 * 1024:
            raise PayloadTooLargeError(f"文件超过 {self.settings.max_upload_mb} MB 限制")

        # 内容哈希作 ID：相同内容 -> 相同 ID -> 覆盖；不同内容 -> 不同 ID -> 并存
        doc_id = hashlib.sha256(data).hexdigest()[:12]
        # 落盘文件名用 doc_id，避免用户上传的同名文件互相覆盖，也避免路径穿越
        target = self.settings.upload_dir / f"{doc_id}{suffix}"
        target.write_bytes(data)

        # 解析：得到 (格式名, 章节列表)；不支持的格式/空内容会抛 RAGError
        file_format, sections = loader.load(target)
        chunks = chunker.split(
            sections,
            max_chars=self.settings.chunk_max_chars,
            overlap=self.settings.chunk_overlap,
        )
        if not chunks:
            raise DocumentParseError("文档切片后为空")

        # 批量向量化（模型内部按 embed_batch_size 分批）
        vectors = self.embedder.embed_documents([chunk.text for chunk in chunks])
        # 先删旧数据再写新的：只有已存在时才会删，返回值用于告知调用方"是否覆盖"
        replaced = self.store.delete_by_doc(doc_id) > 0

        # Chroma 的 metadata 只接受 str/int/float/bool，None 会报错，
        # 所以 page 字段在不适用时直接不写入
        created_at = datetime.now(timezone.utc).isoformat()
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        for chunk, vector in zip(chunks, vectors):
            chunk_id = f"{doc_id}:{chunk.index}"
            meta: dict[str, Any] = {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_index": chunk.index,
                "filename": filename,  # 用原始文件名，落盘名是哈希不值展示
                "format": file_format,
                "heading": chunk.heading,
                "source": str(target),  # 回溯原始文件位置
                "created_at": created_at,
            }
            if chunk.page is not None:
                meta["page"] = chunk.page
            ids.append(chunk_id)
            documents.append(chunk.text)
            metadatas.append(meta)

        self.store.upsert(ids, documents, vectors, metadatas)

        return IngestResult(
            doc_id=doc_id,
            filename=filename,
            format=file_format,
            sections=len(sections),
            chunks=len(chunks),
            replaced=replaced,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    # ------------------------------------------------------------ 问答
    async def ask(
        self,
        question: str,
        top_k: int | None = None,
        top_n: int | None = None,
        use_rerank: bool | None = None,
    ) -> AskResult:
        """问题 -> 向量召回 -> 可选重排 -> 生成答案 + 引用。

        参数为 None 时回落到全局配置，路由层无需感知默认值。
        """
        started = time.perf_counter()

        # 召回：encode 是同步 CPU 计算，放到线程池，防止阻塞其他请求
        candidates = await run_in_threadpool(
            self._retrieve, question, top_k or self.settings.top_k
        )

        # 重排同样同步（CrossEncoder 推理），也走线程池；
        # use_rerank=False 时 rerank 内部只做截断，成本可忽略
        if use_rerank is None:
            use_rerank = self.settings.enable_rerank
        selected = await run_in_threadpool(
            self.reranker.rerank,
            question,
            candidates,
            top_n or self.settings.top_n,
            use_rerank,
        )

        # 生成：异步 HTTP 调用，直接 await
        answer = await self.generator.answer(question, [item["document"] for item in selected])

        # 引用信息从 metadata 还原，与送进 prompt 的片段顺序一致
        references = [
            {
                "chunk_id": item["metadata"].get("chunk_id", ""),
                "doc_id": item["metadata"].get("doc_id", ""),
                "chunk_index": int(item["metadata"].get("chunk_index", 0)),
                "heading": item["metadata"].get("heading", ""),
                "page": item["metadata"].get("page"),
                # 分数保留 4 位，避免响应里出现 0.8237198362 这种长尾
                "score": round(item["score"], 4),
                # 只截前 120 字，完整片段前端可以按 chunk_id 再查
                "snippet": item["document"][:120],
            }
            for item in selected
        ]

        return AskResult(
            answer=answer,
            references=references,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    def _retrieve(self, question: str, top_k: int) -> list[dict[str, Any]]:
        """同步检索：问题编码 + Chroma 查询，抽出来是为了方便丢进线程池。"""
        return self.store.query(self.embedder.embed_query(question), top_k)
