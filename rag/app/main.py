"""应用入口：创建 FastAPI 实例、加载模型、注册路由与异常处理。

启动方式（在任意目录均可，配置里路径都是绝对路径）：
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .api import documents, query
from .config import settings
from .errors import RAGError
from .services.pipeline import RAGPipeline

logger = logging.getLogger("rag")
# 简单日志配置：MVP 阶段直接打到 stdout，容器里由 docker logs 收集
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动前加载模型，关闭时无需额外清理。

    模型加载是一次性重操作（数秒），必须放在这里而不是请求里，
    否则每次请求都要重新加载或承担懒加载的首次延迟。
    """
    pipeline = RAGPipeline(settings)
    # 挂到 app.state，路由通过 get_pipeline 依赖取用同一个实例
    app.state.pipeline = pipeline
    try:
        logger.info("开始加载本地模型...")
        # load_models 是同步阻塞的，放到线程池执行，避免卡住事件循环
        await run_in_threadpool(pipeline.load_models)
        logger.info("模型加载完成，向量库现有 %s 个片段", pipeline.store.count())
    except Exception:  # 加载失败不阻断启动，/health 会显示 degraded
        # 保留启动能力的意义：导入/列表接口的错误信息更友好，
        # 运维也能通过 /health 看到"进程活着但模型没起来"
        logger.exception("模型加载失败，接口将返回 503")
    yield  # 服务运行期
    # 这里没有需要释放的资源：Chroma 用持久化客户端，模型随进程退出回收


def create_app() -> FastAPI:
    """工厂函数：便于测试时创建独立实例（可注入不同配置）。"""
    app = FastAPI(
        title="RAG Service",
        version="1.0.0",
        description="文档导入 + 检索增强问答",
        lifespan=lifespan,
    )

    # 统一加 /api/v1 前缀：将来出 v2 时，两套路由可以并存，互不影响
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(query.router, prefix="/api/v1")

    @app.exception_handler(RAGError)
    async def handle_rag_error(request: Request, exc: RAGError) -> JSONResponse:
        """把所有业务异常转成 {"detail": "..."}。

        这样 services 层不用 import HTTPException，保持了与框架的解耦；
        状态码取自异常类，例如 DocumentParseError -> 400。
        """
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    return app


# uvicorn 通过 "app.main:app" 找到这个模块级实例
app = create_app()
