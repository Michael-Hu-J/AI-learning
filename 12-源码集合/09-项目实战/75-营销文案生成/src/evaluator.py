"""质量评估模块"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re
import math


@dataclass
class EvaluationResult:
    """评估结果"""
    score: float = 0.0          # 综合评分 (0-100)
    relevance: float = 0.0      # 相关性 (0-100)
    creativity: float = 0.0     # 创意度 (0-100)
    compliance: float = 0.0     # 合规性 (0-100)
    persuasiveness: float = 0.0 # 说服力 (0-100)
    grade: str = ""             # 等级 (S/A/B/C/D)
    
    def to_dict(self) -> Dict:
        return {
            "score": round(self.score, 1),
            "relevance": round(self.relevance, 1),
            "creativity": round(self.creativity, 1),
            "compliance": round(self.compliance, 1),
            "persuasiveness": round(self.persuasiveness, 1),
            "grade": self.grade,
        }


class CopyEvaluator:
    """文案评估器"""
    
    # 权重配置
    WEIGHTS = {
        "relevance": 0.30,
        "compliance": 0.30,
        "creativity": 0.20,
        "persuasiveness": 0.20,
    }
    
    # 等级阈值
    GRADES = {
        "S": 95,
        "A": 85,
        "B": 70,
        "C": 60,
        "D": 0,
    }
    
    # 评估关键词
    PERSUASIVE_WORDS = [
        "立即", "马上", "现在", "限时", "抢购", "不容错过",
        " guaranteed", "放心", "安心", "省心", "超值",
        "点击", "领取", "享受", "体验", "拥有",
    ]
    
    CREATIVE_PATTERNS = [
        r"比喻", r"排比", r"反问", r"感叹", r"对比",
        r"数字", r"故事", r"场景",
    ]
    
    def evaluate(self, copy: str, product_name: str, industry: str = "",
                 compliance_score: float = 100.0) -> EvaluationResult:
        """综合评估文案质量"""
        result = EvaluationResult()
        
        # 1. 相关性评估
        result.relevance = self._evaluate_relevance(copy, product_name)
        
        # 2. 合规性评估（传入或计算）
        result.compliance = compliance_score
        
        # 3. 创意度评估
        result.creativity = self._evaluate_creativity(copy)
        
        # 4. 说服力评估
        result.persuasiveness = self._evaluate_persuasiveness(copy)
        
        # 5. 综合评分
        result.score = (
            result.relevance * self.WEIGHTS["relevance"] +
            result.compliance * self.WEIGHTS["compliance"] +
            result.creativity * self.WEIGHTS["creativity"] +
            result.persuasiveness * self.WEIGHTS["persuasiveness"]
        )
        
        # 6. 评级
        result.grade = self._get_grade(result.score)
        
        return result
    
    def _evaluate_relevance(self, copy: str, product_name: str) -> float:
        """评估文案与产品的相关性"""
        if not product_name or not copy:
            return 0.0
        
        score = 0.0
        
        # 产品名称出现
        if product_name in copy:
            score += 40
        
        # 产品相关词出现
        keywords = list(set(product_name))
        if len(keywords) > 1:
            matched = sum(1 for k in keywords if k in copy)
            score += min(30, matched * 10)
        
        # 文案长度合理
        length = len(copy)
        if 50 <= length <= 500:
            score += 20
        elif length > 500:
            score += 10
        
        # 有行动号召
        cta_words = ["购买", "下单", "点击", "领取", "立即", "现在"]
        if any(w in copy for w in cta_words):
            score += 10
        
        return min(100, score)
    
    def _evaluate_creativity(self, copy: str) -> float:
        """评估文案创意度"""
        if not copy:
            return 0.0
        
        score = 50.0  # 基础分
        
        # 使用修辞手法
        rhetorical_count = 0
        if re.search(r"[，。！？]", copy):
            sentences = copy.replace("，", "。").replace("！", "。").replace("？", "。").split("。")
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) >= 3:
                rhetorical_count += 1
        
        # 句式变化
        if "?" in copy or "!" in copy:
            score += 15
        
        # 有具体数据/数字
        if re.search(r"\d+", copy):
            score += 10
        
        # 有比喻/对比
        if any(w in copy for w in ["像", "如同", "仿佛", "相比", "对比"]):
            score += 10
        
        # 有情感词
        emotion_words = ["温暖", "感动", "惊喜", "快乐", "幸福", "安心", "放心"]
        if any(w in copy for w in emotion_words):
            score += 5
        
        # 长度适中（不太短也不太长）
        length = len(copy)
        if 100 <= length <= 300:
            score += 10
        elif length > 300:
            score += 5
        
        return min(100, score)
    
    def _evaluate_persuasiveness(self, copy: str) -> float:
        """评估文案说服力"""
        if not copy:
            return 0.0
        
        score = 40.0  # 基础分
        
        # 有行动号召词
        cta_count = sum(1 for w in self.PERSUASIVE_WORDS if w in copy)
        score += min(25, cta_count * 5)
        
        # 有紧迫感
        urgent_words = ["限时", "最后", "即将", "马上", "错过"]
        if any(w in copy for w in urgent_words):
            score += 10
        
        # 有信任背书
        trust_words = ["保障", "放心", "安心", "专业", "认证", "权威"]
        if any(w in copy for w in trust_words):
            score += 10
        
        # 有具体利益点
        benefit_words = ["省钱", "免费", "赠送", "优惠", "折扣", "立减"]
        if any(w in copy for w in benefit_words):
            score += 10
        
        # 有社交证明
        social_words = ["万人", "热销", "爆款", "好评", "推荐", "口碑"]
        if any(w in copy for w in social_words):
            score += 5
        
        return min(100, score)
    
    def _get_grade(self, score: float) -> str:
        """根据分数评级"""
        for grade, threshold in sorted(self.GRADES.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return grade
        return "D"
    
    def compare_copies(self, copies: List[str], product_name: str, 
                       industry: str = "") -> List[EvaluationResult]:
        """批量比较多个文案"""
        results = []
        for copy in copies:
            result = self.evaluate(copy, product_name, industry)
            results.append(result)
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results
