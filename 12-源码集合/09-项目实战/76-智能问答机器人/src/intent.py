"""
=============================================================================
 intent.py — 意图分类模块
 作者: 测试员周周 (14年测试老兵)
 描述: 对用户问题进行意图识别，支持：咨询、投诉、闲聊、拒答等类别
 核心逻辑:
   1. 基于关键词规则 + 简单的统计匹配
   2. 判断查询是否需要进入知识库检索，还是直接走拒答/闲聊流程
 注意: 生产环境建议用文本分类模型替换这里的规则逻辑
=============================================================================
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("qa_bot.intent")


# ======================== 常量定义 ========================

# 意图类别
INTENT_CONSULT = "consult"        # 咨询（知识库可回答）
INTENT_COMPLAINT = "complaint"    # 投诉
INTENT_CHITCHAT = "chitchat"      # 闲聊
INTENT_GREETING = "greeting"      # 问候
INTENT_REJECT = "reject"          # 应拒答（涉敏/越权）
INTENT_AMBIGUOUS = "ambiguous"    # 模糊问题，需澄清

# ---------- 各类别关键词库 ----------

GREETING_KEYWORDS = [
    "你好", "您好", "嗨", "hello", "hi", "hey",
    "早上好", "下午好", "晚上好", "在吗", "在不在",
]

CHITCHAT_KEYWORDS = [
    "你是谁", "你叫什么", "你多大了", "你吃饭了吗",
    "今天天气", "心情", "聊天", "无聊",
]

COMPLAINT_KEYWORDS = [
    "投诉", "差评", "退货", "赔偿",
    "太差了", "不好用", "垃圾", "骗子", "欺诈",
]

REJECT_KEYWORDS = [
    "竞品", "隔壁", "另一家", "对比", "哪个好",
    "密码", "身份证号", "银行卡", "信用卡",
    "黑客", "攻击", "漏洞", "入侵",
]

AMBIGUOUS_PATTERNS = [
    r"^那个$",
    r"^这个$",
    r"^那个东西.*$",
    r"^这个什么.*$",
]

# ======================== 数据结构 ========================


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: str = INTENT_CONSULT
    confidence: float = 0.0
    sub_type: str = ""
    keywords_matched: List[str] = field(default_factory=list)
    details: str = ""


# ======================== 核心类 ========================


class IntentClassifier:
    """
    意图分类器

    按优先级依次检查：
      1. 拒答关键词（安全性/敏感词）
      2. 问候语
      3. 闲聊
      4. 投诉
      5. 模糊问题（长度过短）
      6. 默认走咨询流程
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def classify(self, question: str) -> IntentResult:
        """
        对用户问题进行意图分类

        参数:
            question: 用户输入的问题文本

        返回:
            IntentResult 包含意图类别和置信度
        """
        if not question or not question.strip():
            return IntentResult(
                intent=INTENT_REJECT,
                confidence=1.0,
                details="空查询",
            )

        question = question.strip()
        result = IntentResult()

        # 1. 拒答检查（最高优先级）
        reject_matches = self._match_keywords(question, REJECT_KEYWORDS)
        if reject_matches:
            result.intent = INTENT_REJECT
            result.confidence = 0.95
            result.keywords_matched = reject_matches
            result.details = f"命中拒答关键词: {reject_matches}"
            logger.info("意图分类=拒答, question=%s, keywords=%s", question[:30], reject_matches)
            return result

        # 2. 问候检查
        greeting_matches = self._match_keywords(question, GREETING_KEYWORDS)
        if greeting_matches:
            result.intent = INTENT_GREETING
            result.confidence = 0.9
            result.keywords_matched = greeting_matches
            result.details = "问候意图"
            logger.info("意图分类=问候, question=%s", question[:30])
            return result

        # 3. 闲聊检查
        chitchat_matches = self._match_keywords(question, CHITCHAT_KEYWORDS)
        if chitchat_matches:
            result.intent = INTENT_CHITCHAT
            result.confidence = 0.85
            result.keywords_matched = chitchat_matches
            result.details = "闲聊意图"
            logger.info("意图分类=闲聊, question=%s", question[:30])
            return result

        # 4. 投诉检查
        complaint_matches = self._match_keywords(question, COMPLAINT_KEYWORDS)
        if complaint_matches:
            result.intent = INTENT_COMPLAINT
            result.confidence = 0.8
            result.keywords_matched = complaint_matches
            result.details = f"投诉关键词: {complaint_matches}"
            logger.info("意图分类=投诉, question=%s", question[:30])
            return result

        # 5. 模糊检查（问题太短或全是代词）
        if len(question) < 5:
            result.intent = INTENT_AMBIGUOUS
            result.confidence = 0.6
            result.details = "问题过短，可能需澄清"
            logger.info("意图分类=模糊, question=%s", question[:30])
            return result

        for pattern in AMBIGUOUS_PATTERNS:
            if re.match(pattern, question):
                result.intent = INTENT_AMBIGUOUS
                result.confidence = 0.5
                result.details = f"匹配模糊模式: {pattern}"
                logger.info("意图分类=模糊(模式), question=%s", question[:30])
                return result

        # 6. 默认：咨询
        result.intent = INTENT_CONSULT
        result.confidence = 0.7
        result.details = "默认走咨询流程"
        logger.info("意图分类=咨询, question=%s", question[:30])
        return result

    # ======================== 辅助方法 ========================

    @staticmethod
    def _match_keywords(text: str, keywords: List[str]) -> List[str]:
        """返回 text 中匹配到的关键词列表"""
        matched = []
        for kw in keywords:
            if kw in text:
                matched.append(kw)
        return matched

    def is_retrieval_needed(self, intent: str) -> bool:
        """判断该意图是否需要走知识库检索流程"""
        return intent in (INTENT_CONSULT, INTENT_COMPLAINT)

    def is_reject(self, intent: str) -> bool:
        """判断该意图是否应该拒答"""
        return intent == INTENT_REJECT


# ======================== 快捷导出 ========================

__all__ = [
    "IntentClassifier",
    "IntentResult",
    "INTENT_CONSULT",
    "INTENT_COMPLAINT",
    "INTENT_CHITCHAT",
    "INTENT_GREETING",
    "INTENT_REJECT",
    "INTENT_AMBIGUOUS",
]
