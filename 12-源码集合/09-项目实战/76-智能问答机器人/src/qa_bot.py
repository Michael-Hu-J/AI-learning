"""
=============================================================================
 qa_bot.py — 问答机器人主流程
 作者: 测试员周周 (14年测试老兵)
 描述: 智能问答机器人的核心流程编排
 流程: 意图分类 → 知识库检索 → 答案生成 → 质量评估 → 返回结果
 架构:
   用户问题
      ↓
   [意图分类] ---- 拒答/闲聊/问候 → 直接回复
      ↓
   [知识库检索] -- 未找到 → 拒答
      ↓
   [答案生成]   -- LLM/降级模板
      ↓
   [质量评估]   -- 不通过 → 降级处理
      ↓
   返回用户
=============================================================================
"""

import logging
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field

from src.qa_retriever import KnowledgeBase, KnowledgeDocument
from src.intent import IntentClassifier, IntentResult, INTENT_CONSULT, INTENT_REJECT
from src.generator import AnswerGenerator
from src.quality import AnswerQualityEvaluator, QualityReport

logger = logging.getLogger("qa_bot.qa_bot")


# ======================== 数据结构 ========================


@dataclass
class QAResult:
    """问答结果"""
    question: str
    answer: str = ""
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    quality_score: float = 0.0
    quality_report: Optional[QualityReport] = None
    is_rejected: bool = False
    rejection_reason: str = ""
    intent: str = ""
    elapsed_ms: float = 0.0


# ======================== 主流程类 ========================


class QABot:
    """
    智能问答机器人主流程

    将 intent / retrieval / generation / quality 四个模块串联起来。

    使用示例:
        kb = KnowledgeBase()
        kb.add_document(KnowledgeDocument(doc_id="DOC001", title="...", content="...", category="..."))

        bot = QABot(knowledge_base=kb, llm_call_func=mock_llm)
        result = bot.answer("怎么报名课程")
        print(result.answer)
    """

    def __init__(self, knowledge_base: KnowledgeBase,
                 llm_call_func: Optional[Callable] = None,
                 config: Optional[Dict] = None):
        """
        参数:
            knowledge_base: 知识库实例（必填）
            llm_call_func: LLM 调用函数（可选，无则使用降级模板）
            config: 全局配置字典
        """
        self.knowledge_base = knowledge_base
        self.config = config or {}

        # 子模块初始化
        self.intent_classifier = IntentClassifier(self.config)
        self.generator = AnswerGenerator(
            llm_call_func=llm_call_func,
            config=self.config.get("generation", {}),
        )
        self.evaluator = AnswerQualityEvaluator(self.config.get("quality", {}))

        # 检索配置
        self.retrieval_config = self.config.get("retrieval", {})
        self.top_k = self.retrieval_config.get("top_k", 5)
        self.retrieval_threshold = self.retrieval_config.get("threshold", 0.15)

        # 拒答消息
        rejection_cfg = self.config.get("rejection", {})
        self.rejection_message = rejection_cfg.get(
            "message", "抱歉，我暂时没有找到相关信息。建议您联系人工客服。"
        )
        self.fallback_message = rejection_cfg.get(
            "fallback_message", "抱歉，我暂时没有找到相关信息。"
        )

        logger.info("QABot 初始化完成: top_k=%d, threshold=%.2f",
                     self.top_k, self.retrieval_threshold)

    def answer(self, question: str) -> QAResult:
        """
        回答用户问题 — 全流程编排

        参数:
            question: 用户输入的文本

        返回:
            QAResult 包含回答、来源、置信度、质量评分等信息
        """
        import time
        start_time = time.time()

        result = QAResult(question=question)
        logger.info("===== 开始处理问题: %s =====", question[:50])

        # ==================== Step 1: 意图分类 ====================
        intent_result = self.intent_classifier.classify(question)
        result.intent = intent_result.intent
        logger.info("Step1-意图分类: %s (confidence=%.2f)",
                     intent_result.intent, intent_result.confidence)

        # 拒答意图直接返回
        if intent_result.intent == INTENT_REJECT:
            result.is_rejected = True
            result.rejection_reason = f"意图分类为拒答: {intent_result.details}"
            result.answer = self.rejection_message
            result.elapsed_ms = (time.time() - start_time) * 1000
            logger.info("结果: 拒答 (reason=%s)", result.rejection_reason)
            return result

        # 非咨询/投诉类意图（问候、闲聊等）直接返回通用消息
        if not self.intent_classifier.is_retrieval_needed(intent_result.intent):
            result.answer = self._handle_non_consult(intent_result)
            result.elapsed_ms = (time.time() - start_time) * 1000
            logger.info("结果: 非咨询类回复 (intent=%s)", intent_result.intent)
            return result

        # ==================== Step 2: 知识库检索 ====================
        if self.knowledge_base.document_count() == 0:
            logger.warning("知识库为空")
            result.is_rejected = True
            result.rejection_reason = "知识库为空"
            result.answer = self.rejection_message
            result.elapsed_ms = (time.time() - start_time) * 1000
            return result

        search_results = self.knowledge_base.hybrid_search(
            question,
            top_k=self.top_k,
            config=self.retrieval_config,
        )
        logger.info("Step2-知识库检索: 结果数=%d", len(search_results))

        # ==================== Step 3: 判断检索质量 ====================
        if not search_results:
            result.is_rejected = True
            result.rejection_reason = "知识库中未命中任何文档"
            result.answer = self.rejection_message
            result.elapsed_ms = (time.time() - start_time) * 1000
            logger.info("结果: 拒答 (未命中文档)")
            return result

        top_score = search_results[0][1]
        if top_score < self.retrieval_threshold:
            result.is_rejected = True
            result.rejection_reason = (
                f"检索得分低于阈值: top_score={top_score:.4f} < threshold={self.retrieval_threshold}"
            )
            result.answer = self.rejection_message
            result.elapsed_ms = (time.time() - start_time) * 1000
            logger.info("结果: 拒答 (得分不足: %.4f)", top_score)
            return result

        # ==================== Step 4: 答案生成 ====================
        docs = [doc for doc, score in search_results]
        scores = [score for doc, score in search_results]
        result.sources = [doc.title for doc in docs]

        answer = self.generator.generate(question, docs, scores)
        result.answer = answer
        logger.info("Step4-答案生成完成: length=%d", len(answer))

        # ==================== Step 5: 置信度计算 ====================
        result.confidence = self._compute_confidence(scores)
        logger.info("Step5-置信度: %.4f", result.confidence)

        # ==================== Step 6: 质量评估 ====================
        quality_report = self.evaluator.evaluate(
            question=question,
            answer=answer,
            expected_answer="",  # 无标准答案时不传
            sources=result.sources,
        )
        result.quality_report = quality_report
        result.quality_score = quality_report.overall_score
        logger.info("Step6-质量评估: overall=%.4f, passed=%s",
                     quality_report.overall_score, quality_report.passed)

        # ==================== Step 7: 质量不达标的降级处理 ====================
        if not quality_report.passed:
            logger.warning("质量评估未通过，执行降级处理: issues=%s",
                            quality_report.issues)
            # 如果安全性有问题，使用拒答消息
            if quality_report.safety_score < 0.5:
                result.answer = self.rejection_message
                result.is_rejected = True
                result.rejection_reason = "安全性检查未通过"
            else:
                # 否则降级为拒答
                result.answer = self.rejection_message
                result.is_rejected = True
                result.rejection_reason = "质量评估未通过"

        result.elapsed_ms = (time.time() - start_time) * 1000
        logger.info("===== 处理完成: elapsed=%.1fms, rejected=%s =====",
                     result.elapsed_ms, result.is_rejected)
        return result

    # ======================== 辅助方法 ========================

    def _handle_non_consult(self, intent_result: IntentResult) -> str:
        """处理非咨询类意图"""
        intent = intent_result.intent
        if intent == "greeting":
            return "您好！我是智能问答机器人，请问有什么可以帮您的？"
        elif intent == "chitchat":
            return "我是您的智能问答助手，专注于回答课程相关问题。如果有课程报名、退款等问题，随时问我！"
        elif intent == "complaint":
            return "非常抱歉给您带来不好的体验，我已记录您的问题，会转交给人工客服优先处理。"
        elif intent == "ambiguous":
            return "抱歉，我没有完全理解您的问题。请提供更多细节，例如课程名称或具体操作，我会尽力帮您解答。"
        return self.rejection_message

    @staticmethod
    def _compute_confidence(scores: List[float]) -> float:
        """
        基于检索得分计算回答置信度

        计算公式:
          confidence = max_score * 0.7 + avg_score * 0.3
          上限 1.0
        """
        if not scores:
            return 0.0

        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        return min(max_score * 0.7 + avg_score * 0.3, 1.0)


# ======================== 快捷导出 ========================

__all__ = [
    "QABot",
    "QAResult",
]
