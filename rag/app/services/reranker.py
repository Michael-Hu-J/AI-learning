"""重排（Cross-Encoder）。

与向量召回的区别：
- 向量召回是"双塔"结构，问题和文档分别编码，快但精度一般，适合海量粗筛；
- 重排把 (问题, 文档) 拼在一起过模型，能看细粒度相关性，慢但准，适合对 top_k 精排。

默认关闭（ENABLE_RERANK=false）的原因：之前排查"无法回答"时，
Qwen3-Reranker 的打分被怀疑不可靠，先把主链路跑稳，再决定是否启用。
"""

from pathlib import Path
from typing import Any

from sentence_transformers import CrossEncoder

from ..errors import PipelineNotReadyError


class Reranker:
    def __init__(self, model_path: Path, enabled: bool = False) -> None:
        self.model_path = model_path
        self.enabled = enabled
        # 关闭时不加载，省内存；开启时在 lifespan 里加载
        self._model: CrossEncoder | None = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """只有开关打开才真正加载权重，避免白白占几百 MB 内存。"""
        if self.enabled and self._model is None:
            # Qwen3-Reranker 的 config 里带 default_prompt_name="query"，
            # 加载时会打印 "Default prompt name is set to 'query'..."，属正常提示
            self._model = CrossEncoder(str(self.model_path))

    def rerank(
        self,
        question: str,
        candidates: list[dict[str, Any]],
        top_n: int,
        enabled: bool | None = None,
    ) -> list[dict[str, Any]]:
        """对候选片段重新打分并取前 top_n。

        enabled 参数允许"单次请求覆盖全局开关"（对应 QueryRequest.use_rerank）：
        - None：跟随配置；
        - False：本次跳过重排，直接截断；
        - True：本次启用，即使全局关闭也会懒加载模型。
        """
        if enabled is None:
            enabled = self.enabled
        if not enabled or not candidates:
            # 不重排时保持召回顺序（Chroma 已按相似度降序），直接截取
            return candidates[:top_n]
        if self._model is None:
            self.load()  # 单次请求临时开启时按需加载
        if self._model is None:
            raise PipelineNotReadyError("重排模型尚未加载完成")

        # 复制一份再改，避免污染调用方传入的候选列表（其中 score 是向量相似度）
        scored = [dict(item) for item in candidates]
        # CrossEncoder 的输入是 (query, passage) 对，输出相关性分数
        scores = self._model.predict([(question, item["document"]) for item in scored])
        for item, score in zip(scored, scores):
            # 用重排分数覆盖向量相似度，后续 references 里展示的就是这个分数
            item["score"] = float(score)
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_n]
