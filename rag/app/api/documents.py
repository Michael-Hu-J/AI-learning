"""文档接口：上传导入、列表、删除。

路由层只做三件事：协议转换（multipart / JSON）、参数校验、调用 pipeline。
业务逻辑一律不写在这里，方便替换传输层（比如以后加 gRPC）。
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from ..deps import get_pipeline
from ..errors import DocumentParseError, UnsupportedFormatError
from ..schemas import DeleteResponse, DocumentInfo, DocumentList, IngestResponse
from ..services import loader
from ..services.pipeline import RAGPipeline

# prefix 在这里统一定义，main.py 再叠加 /api/v1：
# 最终路径 = /api/v1 + /documents + 子路径
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=IngestResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    # Depends 会先执行 get_pipeline：模型没加载完直接 503，不会进入后面的解析
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> IngestResponse:
    """上传一个文档，服务端完成解析、切片、向量化、入库。

    201 Created 表示"资源已创建"，比默认 200 更符合语义；
    重复上传同一文件会覆盖，返回体里的 replaced 标明这一点。
    """
    # 只取文件名本身（Path(...).name），防止 "../../etc/passwd" 这类路径穿越
    filename = Path(file.filename or "").name or "unnamed"

    # 前置校验扩展名：不合格直接 415，省掉读整个文件的开销
    if Path(filename).suffix.lower() not in loader.SUPPORTED_SUFFIXES:
        raise UnsupportedFormatError(
            f"不支持的文件类型：{Path(filename).suffix or '无扩展名'}，"
            f"可用：{', '.join(sorted(loader.SUPPORTED_SUFFIXES))}"
        )

    # UploadFile.read() 是异步的，不会阻塞事件循环；文件大小由 pipeline 再校验
    data = await file.read()
    if not data:
        raise DocumentParseError("上传文件为空")

    # 解析 + 向量化是同步 CPU 任务，放到线程池，避免阻塞事件循环
    # （run_in_threadpool 的默认线程数受 anyio 配置控制，足够应对单机并发）
    result = await run_in_threadpool(pipeline.ingest, filename, data)
    return IngestResponse(
        doc_id=result.doc_id,
        filename=result.filename,
        format=result.format,
        sections=result.sections,
        chunks=result.chunks,
        replaced=result.replaced,
        elapsed_ms=result.elapsed_ms,
    )


@router.get("", response_model=DocumentList)
async def list_documents(pipeline: RAGPipeline = Depends(get_pipeline)) -> DocumentList:
    """列出已入库文档。

    数据来自向量库 metadata 聚合（没有独立文档表），
    大库时是全量扫描，MVP 阶段可以接受。
    """
    # 同步访问 Chroma，同样走线程池
    documents = await run_in_threadpool(pipeline.store.list_documents)
    return DocumentList(
        total=len(documents),
        documents=[DocumentInfo(**item) for item in documents],
    )


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document(doc_id: str, pipeline: RAGPipeline = Depends(get_pipeline)) -> DeleteResponse:
    """按 doc_id 删除整个文档的所有切片。

    这里不返回 404：deleted_chunks=0 已足够表达"没有这个文档"，
    也方便调用方做幂等重试（重复删除不报错）。
    注意原始文件仍保留在 uploads 目录，只是不再被检索到。
    """
    deleted = await run_in_threadpool(pipeline.store.delete_by_doc, doc_id)
    return DeleteResponse(doc_id=doc_id, deleted_chunks=deleted)
