"""产品信息模型"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProductInfo:
    """产品信息"""
    name: str = ""
    category: str = ""           # 产品类别
    price: float = 0.0
    original_price: float = 0.0
    selling_points: List[str] = field(default_factory=list)  # 卖点列表
    target_audience: str = ""    # 目标受众
    usage_scenarios: List[str] = field(default_factory=list)  # 使用场景
    industry: str = ""           # 行业（用于合规检查）
    brand_name: str = ""
    description: str = ""
    
    def validate(self) -> List[str]:
        """验证产品信息完整性"""
        errors = []
        if not self.name:
            errors.append("产品名称不能为空")
        if not self.selling_points:
            errors.append("至少需要一个卖点")
        if self.price <= 0:
            errors.append("价格必须大于0")
        if not self.industry:
            errors.append("必须指定行业类别")
        return errors
    
    def to_prompt_context(self) -> str:
        """转换为Prompt上下文"""
        lines = [
            f"产品名称：{self.name}",
            f"产品类别：{self.category}",
            f"价格：{self.price}元",
            f"品牌：{self.brand_name}",
            f"行业：{self.industry}",
            f"卖点：{', '.join(self.selling_points)}",
            f"目标受众：{self.target_audience}",
            f"使用场景：{', '.join(self.usage_scenarios)}",
        ]
        if self.description:
            lines.append(f"产品描述：{self.description}")
        return "\n".join(lines)
