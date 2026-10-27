"""业务异常体系。

为什么不直接在路由里抛 HTTPException：
- services 层不应该依赖 FastAPI（这样它也能被 CLI、定时任务复用）；
- 用自定义异常携带 `status_code`，在 main.py 里注册一个处理器统一转成 JSON，
  业务代码只关心"发生了什么错误"，不关心"该返回什么状态码"。

状态码约定：
- 400 请求内容无法解析（空文件、空文本、扫描版 PDF 等）
- 413 上传文件超过大小限制
- 415 扩展名不在白名单内
- 500 未预期的服务端错误（兜底）
- 502 下游大模型调用失败（超时、限流、鉴权）
- 503 模型尚未加载完成，服务暂不可用
"""


class RAGError(Exception):
    """所有业务异常的基类，默认映射为 500。"""

    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        # 单独保存一份：处理器里要用它拼响应体，不必再 str(exc)
        self.message = message


class UnsupportedFormatError(RAGError):
    """文件类型不在支持列表内。"""

    status_code = 415


class DocumentParseError(RAGError):
    """文件能识别类型，但内容解析失败或为空。"""

    status_code = 400


class PayloadTooLargeError(RAGError):
    """上传体积超限。"""

    status_code = 413


class PipelineNotReadyError(RAGError):
    """模型还在加载，或加载失败，此时不能提供检索/问答能力。"""

    status_code = 503


class GenerationError(RAGError):
    """调用 DeepSeek 失败（网络、鉴权、限流、超时）。"""

    status_code = 502
