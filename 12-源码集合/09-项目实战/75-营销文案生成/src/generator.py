"""文案生成引擎"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random
import hashlib
import time


@dataclass
class GeneratedCopy:
    """生成的文案"""
    text: str = ""
    style: str = ""
    temperature: float = 0.7
    version_id: str = ""
    score: float = 0.0
    is_compliant: bool = True
    compliance_issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "style": self.style,
            "temperature": self.temperature,
            "version_id": self.version_id,
            "score": round(self.score, 1),
            "is_compliant": self.is_compliant,
            "compliance_issues": self.compliance_issues,
        }


class CopyGenerator:
    """文案生成器（模拟LLM生成）"""
    
    # 开场白模板
    OPENERS = {
        "formal": [
            "【{product}】—— 品质之选，信赖之选。",
            "专业打造，品质保障。{product}为您而来。",
            "{product}，以专业之心，铸品质之选。",
        ],
        "humorous": [
            "哈哈！{product}来了，这次真的不一样！",
            "别划走！{product}让你惊掉下巴！",
            "救命！{product}也太好用了吧！",
        ],
        "emotional": [
            "有些温暖，只有{product}懂你。",
            "用心对待每一个你，{product}一直在。",
            "生活需要一点感动，{product}给你。",
        ],
        "urgent": [
            "⏰ 限时！{product}最后X小时！",
            "🔥 抢购倒计时！{product}不容错过！",
            "⚡ 最后机会！{product}马上恢复原价！",
        ],
    }
    
    # 卖点表述模板
    SELLING_TEMPLATES = [
        "✅ {point}",
        "🌟 {point}",
        "💡 {point}",
        "✨ {point}",
    ]
    
    # 结尾模板
    CLOSERS = {
        "formal": "立即体验，品质生活从此开始。",
        "humorous": "赶紧下单吧，晚了就拍大腿！",
        "emotional": "给自己一个机会，让{product}陪伴你。",
        "urgent": "立即抢购，错过再等一年！",
    }
    
    def generate(self, product_name: str, selling_points: List[str], 
                 style: str = "formal", temperature: float = 0.7,
                 max_length: int = 500) -> GeneratedCopy:
        """生成文案（模拟LLM）"""
        # 生成版本ID
        version_id = hashlib.md5(
            f"{product_name}{style}{temperature}{time.time()}".encode()
        ).hexdigest()[:8]
        
        # 选择开场白
        openers = self.OPENERS.get(style, self.OPENERS["formal"])
        opener = random.choice(openers).format(product=product_name)
        
        # 构建卖点
        point_template = random.choice(self.SELLING_TEMPLATES)
        points_text = "\n".join(point_template.format(point=pt) for pt in selling_points[:3])
        
        # 选择结尾
        closer = self.CLOSERS.get(style, self.CLOSERS["formal"]).format(product=product_name)
        
        # 组合文案
        copy_text = f"{opener}\n\n{points_text}\n\n{closer}"
        
        # 根据temperature添加随机变化
        if temperature > 0.5:
            # 添加一些随机修饰词
            modifiers = ["真的", "超级", "绝对", "特别", "非常"]
            if random.random() < temperature:
                mod = random.choice(modifiers)
                # 在卖点前插入修饰词
                lines = copy_text.split("\n")
                if len(lines) > 2:
                    lines[2] = f"{mod}{lines[2]}"
                    copy_text = "\n".join(lines)
        
        # 截断到最大长度
        if len(copy_text) > max_length:
            copy_text = copy_text[:max_length - 3] + "..."
        
        return GeneratedCopy(
            text=copy_text,
            style=style,
            temperature=temperature,
            version_id=version_id,
        )
    
    def generate_multiple(self, product_name: str, selling_points: List[str],
                          styles: List[str] = None, num_versions: int = 3,
                          max_length: int = 500) -> List[GeneratedCopy]:
        """生成多个版本"""
        if styles is None:
            styles = ["formal", "humorous", "emotional", "urgent"]
        
        copies = []
        temps = [0.3, 0.7, 0.9]
        
        for i in range(min(num_versions, len(styles))):
            style = styles[i % len(styles)]
            temp = temps[i % len(temps)]
            copy = self.generate(product_name, selling_points, style, temp, max_length)
            copies.append(copy)
        
        return copies
    
    def regenerate_with_feedback(self, original: GeneratedCopy, feedback: str,
                                  product_name: str, selling_points: List[str]) -> GeneratedCopy:
        """根据反馈重新生成"""
        # 模拟：根据反馈调整temperature
        if "太正式" in feedback or "不够有趣" in feedback:
            new_temp = min(0.9, original.temperature + 0.3)
        elif "太随意" in feedback or "不够专业" in feedback:
            new_temp = max(0.3, original.temperature - 0.3)
        else:
            new_temp = original.temperature
        
        return self.generate(product_name, selling_points, original.style, new_temp)
