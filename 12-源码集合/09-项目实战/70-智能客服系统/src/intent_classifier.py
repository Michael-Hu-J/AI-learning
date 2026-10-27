"""意图识别模块 - 基于规则 + 关键词匹配"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Intent(Enum):
    """意图类型枚举"""
    FAQ = "faq"
    COMPLAINT = "complaint"
    TRANSFER = "transfer"
    GREETING = "greeting"
    ORDER_QUERY = "order_query"
    REFUND = "refund"
    OTHER = "other"


@dataclass
class IntentRule:
    """意图识别规则"""
    intent: Intent
    keywords: List[str]
    patterns: List[str]  # 正则表达式
    priority: int = 0  # 优先级，数值越大优先级越高
    keyword_weights: Dict[str, float] = field(default_factory=dict)  # 关键词权重


class IntentClassifier:
    """意图分类器：基于规则 + 关键词匹配 + 优先级"""

    def __init__(self, config: Optional[Dict] = None):
        self.rules = self._build_rules()
        self.config = config or {}
        logger.info(f"意图分类器初始化完成，共 {len(self.rules)} 条规则")

    def _build_rules(self) -> List[IntentRule]:
        """构建意图识别规则库"""
        return [
            IntentRule(
                intent=Intent.TRANSFER,
                keywords=["转人工", "人工客服", "找人工", "转接", "真人"],
                patterns=[r".*转.*人工.*", r".*找.*人工.*", r".*人工.*客服.*"],
                priority=10,
                keyword_weights={"转人工": 1.0, "人工客服": 1.0, "找人工": 0.8},
            ),
            IntentRule(
                intent=Intent.COMPLAINT,
                keywords=["投诉", "举报", "不满意", "差评", "垃圾", "垃圾东西", "太差了", "垃圾服务"],
                patterns=[r".*投.*诉.*", r".*太.*差.*", r".*垃圾.*"],
                priority=9,
                keyword_weights={"投诉": 1.0, "举报": 0.9, "不满意": 0.7},
            ),
            IntentRule(
                intent=Intent.REFUND,
                keywords=["退款", "退货", "refund", "退钱", "不想要了", "取消订单"],
                patterns=[r".*退.*款.*", r".*退.*货.*", r".*取消.*订单.*"],
                priority=8,
                keyword_weights={"退款": 1.0, "退货": 0.9, "取消订单": 0.8},
            ),
            IntentRule(
                intent=Intent.ORDER_QUERY,
                keywords=["快递", "物流", "到哪了", "什么时候到", "运单号", "发货"],
                patterns=[r".*快递.*", r".*物流.*", r".*到哪.*", r".*发货.*"],
                priority=7,
                keyword_weights={"快递": 0.8, "物流": 0.8, "到哪了": 0.7},
            ),
            IntentRule(
                intent=Intent.FAQ,
                keywords=["怎么", "如何", "怎样", "怎么办", "为什么", "什么", "哪里", "哪个"],
                patterns=[r".*怎么.*", r".*如何.*", r".*怎样.*", r".*怎么办.*"],
                priority=6,
                keyword_weights={"怎么": 0.5, "如何": 0.5, "怎么办": 0.6},
            ),
            IntentRule(
                intent=Intent.GREETING,
                keywords=["你好", "嗨", "hello", "hi", "在吗", "有人吗"],
                patterns=[r"^你好$", r"^嗨$", r"^hello$", r"^hi$"],
                priority=5,
                keyword_weights={"你好": 1.0, "嗨": 0.8},
            ),
        ]

    def classify(self, text: str, min_confidence: float = 0.15) -> Tuple[Intent, float]:
        """
        分类用户输入，返回 (意图，置信度)
        置信度基于关键词匹配数量、权重和规则优先级计算
        """
        if not text or not text.strip():
            logger.debug("空输入，返回 other")
            return Intent.OTHER, 0.0

        text_lower = text.lower().strip()
        best_intent = Intent.OTHER
        best_score = 0.0

        for rule in self.rules:
            # 计算关键词匹配分数（带权重）
            keyword_score = 0.0
            for kw in rule.keywords:
                if kw.lower() in text_lower:
                    weight = rule.keyword_weights.get(kw, 0.3)
                    keyword_score += weight

            # 计算正则匹配
            pattern_matches = sum(1 for pat in rule.patterns if re.match(pat, text_lower))

            # 综合得分：关键词加权分数 + 正则匹配数 * 0.5 + 优先级 * 0.01
            score = keyword_score + pattern_matches * 0.5 + rule.priority * 0.01

            if score > best_score:
                best_score = score
                best_intent = rule.intent

        # 归一化置信度
        confidence = min(best_score / 2.0, 1.0)

        # 低于阈值返回 OTHER
        if confidence < min_confidence:
            logger.debug(f"置信度 {confidence:.2f} 低于阈值 {min_confidence}，返回 other")
            return Intent.OTHER, round(confidence, 2)

        logger.info(f"意图识别: '{text}' -> {best_intent.value} (置信度: {confidence:.2f})")
        return best_intent, confidence


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    classifier = IntentClassifier()
    test_cases = [
        "我的快递怎么还没到",
        "我要投诉你们",
        "转人工客服",
        "你好",
        "我想退款",
        "今天天气不错",
        "",
        "投诉快递太慢了",
    ]
    print("=" * 60)
    print("意图识别测试")
    print("=" * 60)
    for case in test_cases:
        intent, conf = classifier.classify(case)
        print(f"输入: {case!r:30s} | 意图: {intent.value:15s} | 置信度: {conf:.2f}")
