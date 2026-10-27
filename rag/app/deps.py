"""依赖注入。

pipeline 的生命周期与 FastAPI 应用一致（在 lifespan 里创建），这里不 new 对象，
而是从 `app.state` 取出同一个实例，避免每个请求重复加载模型。
"""

from fastapi import Request

from .errors import PipelineNotReadyError
from .services.pipeline import RAGPipeline


def get_pipeline(request: Request) -> RAGPipeline:
    """作为 `Depends(get_pipeline)` 使用。

    - request.app.state 是应用级共享存储，可跨请求复用；
    - ready=False（模型仍在加载或加载失败）时抛 503，而不是让请求跑到
      embedder 内部再报一个含义模糊的异常。
    """
    pipeline: RAGPipeline | None = getattr(request.app.state, "pipeline", None)
    if pipeline is None or not pipeline.ready:
        raise PipelineNotReadyError("模型仍在加载中，请稍后重试")
    return pipeline
