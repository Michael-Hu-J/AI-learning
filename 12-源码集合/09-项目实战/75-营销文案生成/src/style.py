"""风格策略管理"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import random


@dataclass
class StyleConfig:
    """风格配置"""
    name: str = ""
    description: str = ""
    temperature: float = 0.7
    tone: str = ""
    keywords: List[str] = field(default_factory=list)
    sentence_pattern: str = ""  # 句式特征
    
    def to_prompt_instruction(self) -> str:
        """生成风格指令"""
        parts = [f"风格：{self.description}"]
        if self.tone:
            parts.append(f"语气：{self.tone}")
        if self.keywords:
            parts.append(f"关键词：{', '.join(self.keywords)}")
        if self.sentence_pattern:
            parts.append(f"句式：{self.sentence_pattern}")
        return "；".join(parts)


class StyleStrategy:
    """风格策略管理器"""
    
    STYLES = {
        "formal": StyleConfig(
            name="formal",
            description="正式/专业风格",
            temperature=0.3,
            tone="专业、权威、可信",
            keywords=["专业", "品质", "保障", "信赖", "严谨"],
            sentence_pattern="完整句式，逻辑清晰，数据支撑",
        ),
        "humorous": StyleConfig(
            name="humorous",
            description="幽默/轻松风格",
            temperature=0.8,
            tone="轻松、幽默、有趣",
            keywords=["有趣", "好玩", "惊喜", "哈哈", "绝了"],
            sentence_pattern="短句为主，穿插网络用语，适当夸张",
        ),
        "emotional": StyleConfig(
            name="emotional",
            description="情感/共鸣风格",
            temperature=0.7,
            tone="温暖、感性、有共鸣",
            keywords=["温暖", "陪伴", "感动", "用心", "懂得"],
            sentence_pattern="故事化叙述，情感渲染，代入感强",
        ),
        "urgent": StyleConfig(
            name="urgent",
            description="紧迫感/促销风格",
            temperature=0.6,
            tone="紧迫、直接、有号召力",
            keywords=["限时", "抢购", "最后", "错过", "立即"],
            sentence_pattern="短句+感叹号，行动号召，紧迫感强",
        ),
    }
    
    def get_style(self, name: str) -> Optional[StyleConfig]:
        """获取指定风格"""
        return self.STYLES.get(name)
    
    def get_all_styles(self) -> List[StyleConfig]:
        """获取所有风格"""
        return list(self.STYLES.values())
    
    def get_random_style(self, exclude: List[str] = None) -> StyleConfig:
        """随机获取一个风格"""
        exclude = exclude or []
        available = [s for s in self.STYLES.values() if s.name not in exclude]
        return random.choice(available) if available else self.STYLES["formal"]
    
    def build_prompt(self, product_context: str, audience_hint: str, style: StyleConfig, 
                     max_length: int = 500) -> str:
        """构建文案生成Prompt"""
        prompt = f"""你是一个专业的营销文案写手。请根据以下信息生成一段营销文案。

【产品信息】
{product_context}

【受众画像】
{audience_hint}

【写作要求】
{style.to_prompt_instruction()}

【格式要求】
- 字数：{max_length}字以内
- 结构：开头吸引注意力 → 中间突出卖点 → 结尾行动号召
- 不要使用任何广告法禁用词
- 不要做出无法验证的承诺

请直接输出文案内容，不要加任何解释或前言。"""
        return prompt
