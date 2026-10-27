"""营销文案生成系统 - 主流程"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .config import load_config, AppConfig
from .product import ProductInfo
from .audience import AudienceAnalyzer, AudienceProfile
from .style import StyleStrategy
from .generator import CopyGenerator, GeneratedCopy
from .compliance import ComplianceChecker, ComplianceIssue
from .evaluator import CopyEvaluator, EvaluationResult


logger = logging.getLogger(__name__)


@dataclass
class CopyGenerationResult:
    """文案生成结果"""
    product: ProductInfo = field(default_factory=ProductInfo)
    copies: List[GeneratedCopy] = field(default_factory=list)
    evaluation: Optional[EvaluationResult] = None
    best_copy: Optional[GeneratedCopy] = None
    compliance_report: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "product": {
                "name": self.product.name,
                "category": self.product.category,
                "industry": self.product.industry,
            },
            "copies": [c.to_dict() for c in self.copies],
            "best_copy": self.best_copy.to_dict() if self.best_copy else None,
            "compliance": self.compliance_report,
        }


class MarketingCopywriter:
    """营销文案生成器（主流程）"""
    
    def __init__(self, config: AppConfig = None):
        self.config = config or load_config()
        self.audience_analyzer = AudienceAnalyzer()
        self.style_strategy = StyleStrategy()
        self.generator = CopyGenerator()
        self.compliance_checker = ComplianceChecker(
            banned_words=self.config.compliance.banned_words,
            industry_rules=self.config.compliance.industry_rules,
        )
        self.evaluator = CopyEvaluator()
        
        logger.info("营销文案生成系统初始化完成")
        logger.info(f"  风格策略: {len(self.config.styles)} 种")
        logger.info(f"  禁用词: {len(self.config.compliance.banned_words)} 个")
    
    def generate(self, product: ProductInfo, num_versions: int = 3,
                 styles: List[str] = None) -> CopyGenerationResult:
        """完整生成流程"""
        result = CopyGenerationResult(product=product)
        
        # 1. 验证产品信息
        errors = product.validate()
        if errors:
            logger.warning(f"产品信息不完整: {errors}")
        
        # 2. 分析受众画像
        audience = self.audience_analyzer.analyze(
            product.name, product.category, product.target_audience
        )
        audience_hint = audience.to_prompt_hint()
        logger.info(f"受众画像: {audience_hint or '通用'}")
        
        # 3. 生成多个版本
        copies = self.generator.generate_multiple(
            product_name=product.name,
            selling_points=product.selling_points,
            styles=styles,
            num_versions=num_versions,
            max_length=self.config.generation.max_length,
        )
        
        # 4. 合规检查
        for copy in copies:
            is_ok, issues = self.compliance_checker.is_compliant(
                copy.text, product.industry
            )
            copy.is_compliant = is_ok
            copy.compliance_issues = [str(i) for i in issues]
        
        compliant_copies = [c for c in copies if c.is_compliant]
        non_compliant = [c for c in copies if not c.is_compliant]
        logger.info(f"合规检查: {len(compliant_copies)}/{len(copies)} 通过")
        
        # 5. 质量评估
        for copy in copies:
            comp_score = self.compliance_checker.get_compliance_score(
                copy.text, product.industry
            )
            eval_result = self.evaluator.evaluate(
                copy.text, product.name, product.industry, comp_score
            )
            copy.score = eval_result.score
        
        # 6. 选出最佳文案
        if copies:
            result.best_copy = max(copies, key=lambda c: c.score)
            result.evaluation = self.evaluator.evaluate(
                result.best_copy.text, product.name, product.industry
            )
        
        result.copies = copies
        result.compliance_report = {
            "total": len(copies),
            "compliant": len(compliant_copies),
            "non_compliant": len(non_compliant),
            "compliance_rate": len(compliant_copies) / len(copies) if copies else 0,
        }
        
        return result
    
    def compare(self, copies: List[GeneratedCopy], product_name: str,
                industry: str = "") -> List[EvaluationResult]:
        """比较多个文案"""
        return self.evaluator.compare_copies(
            [c.text for c in copies], product_name, industry
        )
    
    def print_result(self, result: CopyGenerationResult) -> str:
        """格式化输出结果"""
        lines = [
            "=" * 60,
            f"📝 营销文案生成报告",
            f"产品: {result.product.name} | 类别: {result.product.category}",
            "=" * 60,
        ]
        
        for i, copy in enumerate(result.copies, 1):
            lines.append(f"\n--- 版本 {i} [{copy.style}] (评分: {copy.score:.1f}) ---")
            lines.append(copy.text)
            if not copy.is_compliant:
                lines.append(f"⚠️ 合规问题: {', '.join(copy.compliance_issues)}")
        
        if result.best_copy:
            lines.append(f"\n{'=' * 60}")
            lines.append(f"🏆 最佳版本: {result.best_copy.style} (评分: {result.best_copy.score:.1f})")
        
        lines.append(f"\n合规率: {result.compliance_report.get('compliance_rate', 0):.0%}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
