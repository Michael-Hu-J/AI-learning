"""问答接口与健康检查。"""

from fastapi import APIRouter, Depends, Request

from ..deps import get_pipeline
from ..schemas import HealthResponse, QueryRequest, QueryResponse, Reference
from ..services import loader
from ..services.pipeline import RAGPipeline

# 不设 prefix：本组接口分别是 /query 和 /health，路径本身已经足够表意
router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> QueryResponse:
    """检索增强问答。

    请求体示例：{"question": "哆啦A梦的3个秘密道具是什么？", "top_n": 3}
    响应同时给出答案和引用，调用方可据此判断答案是否有据可依。
    """
    # strip 去掉用户误输入的首尾空白；空字符串已被 pydantic 的 min_length 拦下
    question = payload.question.strip()
    # pipeline.ask 内部已经把同步部分丢进线程池，这里直接 await 即可
    result = await pipeline.ask(
        question,
        top_k=payload.top_k,
        top_n=payload.top_n,
        use_rerank=payload.use_rerank,
    )
    return QueryResponse(
        answer=result.answer,
        references=[Reference(**item) for item in result.references],
        elapsed_ms=result.elapsed_ms,
    )


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """健康检查：容器编排、负载均衡的探活入口。

    刻意不用 Depends(get_pipeline)——那个依赖在未就绪时会抛 503，
    而探活接口需要"总能返回 200 + 状态描述"，让调用方自己判断。
    """
    pipeline: RAGPipeline | None = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        # lifespan 还没执行完（或初始化失败），只能报降级
        return HealthResponse(
            status="degraded",
            chroma_chunks=0,
            embedder_loaded=False,
            reranker_loaded=False,
            reranker_enabled=False,
            doc_tool_available=loader.doc_tool_available(),
        )

    try:
        chunks = pipeline.store.count()
        ready = pipeline.ready
    except Exception:
        # 向量库损坏（目录权限、文件损坏）时不要让探活接口 500，
        # 否则编排系统会认为进程死了，而实际上它还能返回明确错误
        chunks, ready = 0, False

    return HealthResponse(
        # ok 只代表可以检索；DeepSeek 的可用性由调用 /query 时才知道
        status="ok" if ready else "degraded",
        chroma_chunks=chunks,
        embedder_loaded=pipeline.embedder.loaded,
        reranker_loaded=pipeline.reranker.loaded,
        reranker_enabled=pipeline.reranker.enabled,
        doc_tool_available=loader.doc_tool_available(),
    )
