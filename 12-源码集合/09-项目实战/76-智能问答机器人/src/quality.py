"""
=============================================================================
 quality.py — 质量评估模块
 作者: 测试员周周 (14年测试老兵)
 描述: 对问答机器人的回答进行多维度质量评估，决定是否通过
 评估维度:
   1. 事实性 (factual): 回答是否包含关键信息
   2. 相关性 (relevance): 回答是否与问题相关
   3. 安全性 (safety): 是否包含竞品/敏感/编造内容
   4. 完整性 (completeness): 回答是否完整、有行动指引
 综合得分 = factual*0.35 + relevance*0.25 + safety*0.25 + completeness*0.15
 通过标准: 综合得分 >= pass_threshold (默认 0.7)
=============================================================================
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("qa_bot.quality")


# ======================== 中文关键词提取 ========================


def _extract_chinese_keywords(text: str) -> set:
    """
    提取中文关键词：将连续中文块拆分为 2-gram 后去重

    示例:
      "登录平台后点击课程中心" → {"登录", "录平", "平台", "台后", "后点", "点击", ...}
      "登录 课程中心 报名"    → {"登录", "课程", "程中", "中心", "报名"}
    """
    result = set()
    blocks = re.findall(r"[\u4e00-\u9fff]+", text)
    for block in blocks:
        if len(block) <= 2:
            result.add(block)
        else:
            for i in range(len(block) - 1):
                result.add(block[i:i+2])
    return result


# ======================== 数据结构 ========================


@dataclass
class QualityReport:
    """质量评估报告"""
    question: str
    answer: str
    factual_score: float = 0.0        # 事实性得分
    relevance_score: float = 0.0      # 相关性得分
    safety_score: float = 0.0         # 安全性得分
    completeness_score: float = 0.0   # 完整性得分
    overall_score: float = 0.0        # 综合得分
    issues: List[str] = field(default_factory=list)
    passed: bool = False


# ======================== 核心评估器 ========================


class AnswerQualityEvaluator:
    """
    答案质量评估器

    综合评估回答的四个维度，给出是否通过的决定。
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.pass_threshold = self.config.get("pass_threshold", 0.7)
        self.factual_weight = self.config.get("factual_weight", 0.35)
        self.relevance_weight = self.config.get("relevance_weight", 0.25)
        self.safety_weight = self.config.get("safety_weight", 0.25)
        self.completeness_weight = self.config.get("completeness_weight", 0.15)

    def evaluate(self, question: str, answer: str,
                 expected_answer: str = "",
                 sources: Optional[List[str]] = None) -> QualityReport:
        """
        综合质量评估

        参数:
            question: 用户问题
            answer: 机器人回答
            expected_answer: 期望的标准答案（用于事实性检查，可选）
            sources: 知识来源文档标题列表（用于追溯，可选）

        返回:
            QualityReport 包含各维度得分和最终判定
        """
        report = QualityReport(question=question, answer=answer)

        # 1. 事实性检查
        report.factual_score = self._check_factual(answer, expected_answer)
        if report.factual_score < 0.3:
            report.issues.append("事实性不足：回答缺少关键信息")

        # 2. 相关性检查
        report.relevance_score = self._check_relevance(question, answer)
        if report.relevance_score < 0.3:
            report.issues.append("相关性不足：回答与问题关联度低")

        # 3. 安全性检查
        report.safety_score = self._check_safety(answer)
        if report.safety_score < 0.5:
            report.issues.append("安全性风险：包含竞品或敏感信息")

        # 4. 完整性检查
        report.completeness_score = self._check_completeness(answer)
        if report.completeness_score < 0.5:
            report.issues.append("完整性不足：回答过短或缺少行动指引")

        # 5. 综合得分
        report.overall_score = (
            report.factual_score * self.factual_weight
            + report.relevance_score * self.relevance_weight
            + report.safety_score * self.safety_weight
            + report.completeness_score * self.completeness_weight
        )

        report.passed = report.overall_score >= self.pass_threshold

        logger.info(
            "质量评估完成: question=%s, factual=%.2f, relevance=%.2f, "
            "safety=%.2f, completeness=%.2f, overall=%.2f, passed=%s",
            question[:20], report.factual_score, report.relevance_score,
            report.safety_score, report.completeness_score,
            report.overall_score, report.passed,
        )

        if not report.passed:
            logger.warning("质量评估未通过: issues=%s", report.issues)

        return report

    # ======================== 各维度检查 ========================

    @staticmethod
    def _check_factual(answer: str, expected: str) -> float:
        """
        事实性检查：回答是否包含关键信息

        当有标准答案时，通过 2-gram 关键词覆盖率评估；
        无标准答案时，给出 0.7 默认值。
        """
        if not answer or answer.strip() == "":
            return 0.0

        if not expected:
            # 无标准答案时，检查回答是否合理（有实际内容即可）
            return 0.7

        expected_keywords = _extract_chinese_keywords(expected)
        answer_keywords = _extract_chinese_keywords(answer)

        if not expected_keywords:
            return 0.5

        overlap = expected_keywords & answer_keywords
        coverage = len(overlap) / len(expected_keywords)

        # 信息密度检查
        if len(answer_keywords) > 0:
            info_density = len(overlap) / len(answer_keywords)
        else:
            info_density = 0

        # 综合得分：覆盖率占 70%，信息密度占 30%
        score = coverage * 0.7 + min(info_density, 1.0) * 0.3
        return min(score, 1.0)

    @staticmethod
    def _check_relevance(question: str, answer: str) -> float:
        """
        相关性检查：回答是否与问题相关

        通过 2-gram 问题关键词在回答中的覆盖率来评估。
        如果回答中包含问题的任一关键语义词（原词匹配），给予保底分。
        """
        if not question or not answer:
            return 0.0

        question_keywords = _extract_chinese_keywords(question)
        answer_keywords = _extract_chinese_keywords(answer)

        if not question_keywords:
            return 0.5

        overlap = question_keywords & answer_keywords
        keyword_coverage = len(overlap) / len(question_keywords)

        # 主题词直接命中：问题中的 2 字及以上中文词出现在回答中
        question_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}", question))
        direct_hits = sum(1 for term in question_terms if term in answer)
        if question_terms and direct_hits:
            direct_coverage = direct_hits / len(question_terms)
            keyword_coverage = max(keyword_coverage, direct_coverage)

        # 有语义交集时不应因 2-gram 稀疏被判为完全不相关
        if overlap:
            keyword_coverage = max(keyword_coverage, 0.45)

        # 判断是否为通用回复
        generic_phrases = [
            "抱歉", "暂时没有", "联系人工", "不知道",
            "无法回答", "请稍后",
        ]
        is_generic = any(phrase in answer for phrase in generic_phrases)

        # 通用回复但问题有具体关键词，说明答非所问
        if is_generic and keyword_coverage < 0.2:
            return 0.2

        # 保底：只要回答包含了问题的关键实义词，相关性就不应为 0
        # 检查原词级别（非 2-gram）的关键词是否出现在回答中
        raw_question_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", question))
        raw_answer_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", answer))
        raw_overlap = raw_question_words & raw_answer_words
        if raw_overlap and keyword_coverage < 0.15:
            return 0.3

        return keyword_coverage

    @staticmethod
    def _check_safety(answer: str) -> float:
        """
        安全性检查：是否包含不当内容

        检查项:
          1. 竞品信息
          2. 敏感信息（身份证、银行卡等）
          3. 编造内容信号（模糊表述）
        """
        if not answer:
            return 0.0

        # 1. 竞品关键词检查
        competitor_keywords = [
            "隔壁", "竞品", "另一家", "其他平台", "相比",
            "比.*好", "比.*差", "更便宜", "更贵",
        ]
        for kw in competitor_keywords:
            if re.search(kw, answer):
                return 0.0  # 一票否决

        # 2. 敏感信息检查
        sensitive_patterns = [
            (r"密码", "密码泄露"),
            (r"身份证", "身份证信息"),
            (r"银行卡号", "银行卡信息"),
            (r"手机号", "手机号泄露"),
        ]
        for pattern, desc in sensitive_patterns:
            if re.search(pattern, answer):
                return 0.0  # 一票否决

        # 3. 编造内容检测（模糊表述）
        hedge_words = [
            "根据我的了解", "一般来说", "通常情况下",
            "可能", "大概", "也许", "估计",
        ]
        hedge_count = sum(1 for hw in hedge_words if hw in answer)
        if hedge_count >= 2:
            return 0.3

        if hedge_count >= 1:
            return 0.7

        return 1.0

    @staticmethod
    def _check_completeness(answer: str) -> float:
        """
        完整性检查：回答是否完整

        评估标准:
          - 回答太短 (< 10 字) → 不完整
          - 包含行动指引（点击、登录等）→ 完整
          - 拒答类回答 → 合理性检查
        """
        if not answer:
            return 0.0

        # 回答太短
        if len(answer) < 10:
            return 0.3

        # 拒答类回答
        rejection_indicators = ["抱歉", "暂时没有", "联系人工"]
        is_rejection = any(ind in answer for ind in rejection_indicators)
        if is_rejection:
            if len(answer) >= 10 and len(answer) <= 100:
                return 0.8
            return 0.6

        # 检查是否包含行动指引（操作类回答）
        action_words = ["点击", "登录", "联系", "前往", "打开", "输入", "选择"]
        has_action = any(aw in answer for aw in action_words)

        # 检查是否提供了具体步骤
        has_steps = any(step in answer for step in ["第一步", "首先", "然后", "最后", "步骤"])

        if has_action and has_steps:
            return 1.0
        elif has_action:
            return 0.9
        elif len(answer) >= 50:
            return 0.85
        elif len(answer) >= 20:
            return 0.75
        else:
            return 0.6


# ======================== 快捷导出 ========================

__all__ = [
    "AnswerQualityEvaluator",
    "QualityReport",
]
