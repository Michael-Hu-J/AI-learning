"""
=============================================================================
 generator.py — 答案生成模块
 作者: 测试员周周 (14年测试老兵)
 描述: 基于检索结果生成回答，支持 LLM 生成和降级模板生成两种模式
 核心约束:
   1. 只基于知识库内容回答，不编造信息
   2. 不提及第三方平台或竞品信息
   3. 回答简洁明了，不超过 max_length 字
   4. 知识库中无答案时走拒答流程
 注意: 生产环境将 mock_llm 替换为真实 API 调用
=============================================================================
"""

import logging
from typing import List, Dict, Optional, Callable

from src.qa_retriever import KnowledgeDocument

logger = logging.getLogger("qa_bot.generator")


# ======================== 常量 ========================

DEFAULT_REJECTION_MESSAGE = "抱歉，我暂时没有找到相关信息。建议您联系人工客服。"
DEFAULT_FALLBACK_MESSAGE = "抱歉，我暂时没有找到相关信息。"


# ======================== Prompt 模板 ========================

def build_prompt(question: str, docs: List[KnowledgeDocument],
                 max_length: int = 200) -> str:
    """
    构建 LLM 调用的 Prompt

    包含严格的回答约束：
      1. 只基于知识库内容
      2. 不提及竞品
      3. 简洁回答
      4. 无信息时拒答
    """
    context_parts = []
    for i, doc in enumerate(docs, 1):
        context_parts.append(f"[来源{i}] {doc.title}：{doc.content}")

    context = "\n".join(context_parts)

    prompt = (
        f"你是一个在线教育平台的客服助手。请根据以下知识库内容回答用户问题。\n\n"
        f"知识库内容：\n{context}\n\n"
        f"用户问题：{question}\n\n"
        f"回答要求：\n"
        f"1. 只基于知识库内容回答，不要编造信息\n"
        f"2. 不要提及任何第三方平台或竞品信息\n"
        f"3. 回答要简洁明了，不超过 {max_length} 字\n"
        f"4. 如果知识库中没有相关信息，请回答'抱歉，我暂时没有找到相关信息'\n"
        f"重要：如果你的回答中包含以下类型的内容，请立即停止并回复'抱歉，知识库中没有相关信息'：\n"
        f"  - 具体数字（如课程数量、价格）\n"
        f"  - 竞品名称\n"
        f"  - 未在上述知识库中提及的功能或服务\n"
    )
    return prompt


# ======================== 核心类 ========================


class AnswerGenerator:
    """
    答案生成器

    两种模式：
      - LLM 模式：调用外部大模型生成（需传入 llm_call_func）
      - 降级模式：直接返回知识库原文（无 LLM 时使用）
    """

    def __init__(self, llm_call_func: Optional[Callable] = None,
                 config: Optional[Dict] = None):
        """
        参数:
            llm_call_func: LLM 调用函数，接受 prompt 字符串，返回回答字符串
            config: 生成配置，可包含 max_length, temperature 等
        """
        self.llm = llm_call_func
        self.config = config or {}

    def generate(self, question: str, docs: List[KnowledgeDocument],
                 retrieval_scores: Optional[List[float]] = None) -> str:
        """
        基于检索结果生成回答

        参数:
            question: 用户问题
            docs: 检索到的知识文档列表
            retrieval_scores: 检索得分列表（用于日志和置信度计算）

        返回:
            生成的回答字符串
        """
        if not docs:
            logger.info("无可用的知识文档，返回拒答消息")
            return DEFAULT_REJECTION_MESSAGE

        max_length = self.config.get("max_length", 200)

        if self.llm:
            # LLM 模式
            prompt = build_prompt(question, docs, max_length)
            try:
                answer = self.llm(prompt)
                logger.info("LLM 生成回答完成, length=%d", len(answer))
                return self._post_process(answer, max_length)
            except Exception as e:
                logger.error("LLM 调用失败: %s，降级到模板模式", e)
                return self._fallback_answer(docs)
        else:
            # 降级模式
            logger.info("无 LLM 可用，使用降级模板生成回答")
            return self._fallback_answer(docs)

    # ======================== 降级回答 ========================

    @staticmethod
    def _fallback_answer(docs: List[KnowledgeDocument]) -> str:
        """无 LLM 时的降级回答：直接返回最相关文档的内容"""
        if not docs:
            return DEFAULT_FALLBACK_MESSAGE
        return f"根据知识库：{docs[0].content}"

    # ======================== 后处理 ========================

    @staticmethod
    def _post_process(answer: str, max_length: int = 200) -> str:
        """对生成的回答做后处理（截断、去空白等）"""
        answer = answer.strip()

        # 截断超长回答
        if len(answer) > max_length:
            answer = answer[:max_length] + "…"

        return answer

    # ======================== 拒答消息 ========================

    @staticmethod
    def get_rejection_message(custom_message: Optional[str] = None) -> str:
        """返回拒答时使用的消息"""
        return custom_message or DEFAULT_REJECTION_MESSAGE

    @staticmethod
    def get_fallback_message(custom_message: Optional[str] = None) -> str:
        """返回降级时使用的消息"""
        return custom_message or DEFAULT_FALLBACK_MESSAGE


# ======================== Mock LLM（测试用） ========================


def mock_llm(prompt: str) -> str:
    """
    模拟 LLM 调用（测试/演示用）

    真实场景请替换为:
      openai.ChatCompletion.create(...)
      或  requests.post(api_url, json={...})
    """
    logger.debug("Mock LLM 收到 prompt，长度=%d", len(prompt))

    # 简单的规则：提取第一个知识库来源的内容作为回答
    import re
    match = re.search(r"\[来源1\] [^：]+：(.+)", prompt)
    if match:
        return match.group(1).strip()
    return "登录平台后点击课程中心，选择课程并点击立即报名，完成支付即可。"


# ======================== 快捷导出 ========================

__all__ = [
    "AnswerGenerator",
    "build_prompt",
    "mock_llm",
    "DEFAULT_REJECTION_MESSAGE",
    "DEFAULT_FALLBACK_MESSAGE",
]
