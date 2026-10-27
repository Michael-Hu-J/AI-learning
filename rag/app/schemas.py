"""接口出入参模型（Pydantic）。

作用有三个：
1. 自动校验请求体/路径参数，非法输入由 FastAPI 直接返回 422，不进业务代码；
2. 通过 `response_model` 约束返回值，字段多了会被裁掉，避免泄漏内部数据；
3. 驱动 /docs 的 OpenAPI 文档，前端可以直接看到字段类型和示例。
"""

from typing import Literal

from pydantic import BaseModel, Field


class Reference(BaseModel):
    """回答引用的原文片段，用于前端展示"答案来自哪一段"。"""

    chunk_id: str  # 形如 "{doc_id}:{chunk_index}"，可唯一定位一个切片
    doc_id: str  # 文档级 ID = sha256(文件内容)[:12]
    chunk_index: int  # 该切片在文档内的序号，从 0 开始
    heading: str = ""  # 所属标题；纯文本类文档可能为空
    page: int | None = None  # PDF 页码，其他格式为 None
    score: float | None = None  # 相似度/重排分数，供调试参考
    snippet: str  # 片段前 120 字，避免响应体过大


class IngestResponse(BaseModel):
    """文档导入结果。"""

    doc_id: str
    filename: str
    format: str  # 解析时判定出的格式：md / txt / pdf / docx / doc / xmind
    sections: int  # 解析出的章节数（切片前的粗粒度单元）
    chunks: int  # 最终入库的切片数
    replaced: bool  # True 表示同内容文档之前已存在，本次是覆盖
    elapsed_ms: int  # 整个导入耗时（含向量化），毫秒


class DocumentInfo(BaseModel):
    """已入库文档的概要信息（由切片 metadata 聚合而来）。"""

    doc_id: str
    filename: str
    format: str
    chunks: int


class DocumentList(BaseModel):
    total: int
    documents: list[DocumentInfo]


class DeleteResponse(BaseModel):
    doc_id: str
    deleted_chunks: int  # 实际删除的切片数；为 0 说明该 doc_id 不存在


class QueryRequest(BaseModel):
    """问答请求。

    top_k / top_n / use_rerank 允许为空：为空时回落到 config.py 里的默认值，
    这样调用方不传参也能工作，调试时又可以按次覆盖。
    """

    # 问题不能为空，同时限制 2000 字，防止超长 prompt 拖垮生成
    question: str = Field(min_length=1, max_length=2000)
    # 向量召回条数：1~50
    top_k: int | None = Field(default=None, ge=1, le=50)
    # 最终送入大模型的片段数：1~10
    top_n: int | None = Field(default=None, ge=1, le=10)
    # 是否启用重排；None 表示跟随全局配置 ENABLE_RERANK
    use_rerank: bool | None = None


class QueryResponse(BaseModel):
    answer: str
    references: list[Reference]  # 与 prompt 中的片段一一对应，可按序溯源
    elapsed_ms: int  # 从向量化问题到生成答案的总耗时


class HealthResponse(BaseModel):
    """健康检查结果：status=degraded 表示模型未加载完或向量库异常。"""

    status: Literal["ok", "degraded"]
    chroma_chunks: int  # 向量库当前切片总数
    embedder_loaded: bool  # 向量模型是否已加载
    reranker_loaded: bool  # 重排模型是否已加载（默认关闭时为 False）
    reranker_enabled: bool  # 配置里是否开启重排
    doc_tool_available: bool  # 是否检测到 antiword/soffice，决定 .doc 能否解析
