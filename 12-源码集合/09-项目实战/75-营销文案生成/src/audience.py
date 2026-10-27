"""受众画像分析"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re


@dataclass
class AudienceProfile:
    """受众画像"""
    age_group: str = ""          # 年龄段
    gender: str = "all"          # 性别
    preferences: List[str] = field(default_factory=list)  # 偏好
    pain_points: List[str] = field(default_factory=list)  # 痛点
    interests: List[str] = field(default_factory=list)    # 兴趣
    language_style: str = ""     # 语言风格偏好
    
    def to_prompt_hint(self) -> str:
        """生成受众提示"""
        hints = []
        if self.age_group:
            hints.append(f"目标受众年龄段：{self.age_group}")
        if self.gender != "all":
            hints.append(f"性别：{self.gender}")
        if self.preferences:
            hints.append(f"偏好：{', '.join(self.preferences)}")
        if self.pain_points:
            hints.append(f"痛点：{', '.join(self.pain_points)}")
        if self.language_style:
            hints.append(f"语言风格：{self.language_style}")
        return "；".join(hints) if hints else ""


class AudienceAnalyzer:
    """受众画像分析器"""
    
    # 年龄段特征
    AGE_FEATURES = {
        "18-25": {"language": "年轻化、网络用语", "focus": "潮流、个性、社交"},
        "26-35": {"language": "成熟稳重", "focus": "品质、效率、家庭"},
        "36-45": {"language": "正式专业", "focus": "健康、教育、投资"},
        "46-60": {"language": "传统朴实", "focus": "安全、实用、性价比"},
    }
    
    # 偏好关键词映射
    PREFERENCE_KEYWORDS = {
        "price_sensitive": ["优惠", "特价", "省钱", "性价比", "划算"],
        "quality_focused": ["品质", "精选", "高端", "专业", "保障"],
        "brand_loyal": ["品牌", "信赖", "经典", "传承", "口碑"],
        "trend_follower": ["新款", "潮流", "时尚", "热门", "爆款"],
    }
    
    def analyze(self, product_name: str, category: str, target: str = "") -> AudienceProfile:
        """根据产品信息分析受众画像"""
        profile = AudienceProfile()
        
        # 根据品类推断年龄段
        category_age_map = {
            "玩具": "18-25",
            "教育": "26-35",
            "健康": "36-45",
            "食品": "26-35",
            "数码": "18-25",
            "家居": "26-35",
            "美妆": "18-25",
            "服饰": "18-25",
        }
        for cat, age in category_age_map.items():
            if cat in category or cat in product_name:
                profile.age_group = age
                break
        
        if not profile.age_group:
            profile.age_group = target or "26-35"
        
        # 设置语言风格
        features = self.AGE_FEATURES.get(profile.age_group, {})
        profile.language_style = features.get("language", "通用")
        
        # 设置偏好
        if "价格" in target or "优惠" in target:
            profile.preferences.append("price_sensitive")
        if "品质" in target or "高端" in target:
            profile.preferences.append("quality_focused")
        
        return profile
    
    def get_keywords_for_preference(self, preference: str) -> List[str]:
        """获取偏好对应的关键词"""
        return self.PREFERENCE_KEYWORDS.get(preference, [])
