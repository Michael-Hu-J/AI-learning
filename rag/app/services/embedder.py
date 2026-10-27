"""向量化：本地 Qwen3-Embedding 模型。

两个关键点（旧脚本出问题正是这里）：
1. normalize_embeddings=True：向量归一化后，余弦距离与点积等价，
   排序不再受向量模长影响；
2. 文档与查询使用不同的编码方式：Qwen3-Embedding 自带 query 指令，
   查询侧必须传 prompt_name="query"，文档侧不能传，否则两侧分布对不齐。

模型只加载一次（单例），加载动作放在 lifespan 里，不要在请求里 new。
"""

from pathlib import Path

from sentence_transformers import SentenceTransformer

from ..errors import PipelineNotReadyError


class Embedder:
    def __init__(self, model_path: Path, batch_size: int = 16) -> None:
        self.model_path = model_path
        self.batch_size = batch_size
        # 惰性加载：构造对象很快，真正占内存的是模型权重
        self._model: SentenceTransformer | None = None

    @property
    def loaded(self) -> bool:
        """供 /health 和 get_pipeline 判断服务是否可用。"""
        return self._model is not None

    def load(self) -> None:
        """加载模型权重（秒级到十秒级，只应在 lifespan 中调用一次）。"""
        if self._model is None:
            self._model = SentenceTransformer(str(self.model_path))

    @property
    def model(self) -> SentenceTransformer:
        """取模型时统一做就绪校验，避免在 encode 处抛难懂的 AttributeError。"""
        if self._model is None:
            raise PipelineNotReadyError("向量模型尚未加载完成")
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量编码文档切片。

        - batch_size 控制单次前向的样本数，受内存限制；
        - show_progress_bar=False：服务端日志不需要进度条；
        - 返回 Python list 而不是 numpy 数组，Chroma 直接可序列化。
        """
        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        """编码用户问题，必须带 query 指令。

        有些模型/版本没有内置 "query" prompt，encode 会抛 ValueError 或 KeyError，
        此时降级为普通编码——虽然略损效果，但比整个接口 500 好。
        """
        try:
            vector = self.model.encode(text, prompt_name="query", normalize_embeddings=True)
        except (ValueError, KeyError):
            # 模型未内置 query 指令时降级为普通编码
            vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()
