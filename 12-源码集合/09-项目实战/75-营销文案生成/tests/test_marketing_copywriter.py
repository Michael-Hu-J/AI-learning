"""营销文案生成系统测试"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.product import ProductInfo
from src.compliance import ComplianceChecker, ComplianceIssue
from src.evaluator import CopyEvaluator, EvaluationResult
from src.generator import CopyGenerator, GeneratedCopy
from src.audience import AudienceAnalyzer
from src.copywriter import MarketingCopywriter


class TestProduct:
    """测试产品信息模块"""
    
    def test_product_validation(self):
        p = ProductInfo()
        errors = p.validate()
        assert len(errors) > 0, "空产品应该验证失败"
        print("  ✅ 空产品验证正确拦截")
    
    def test_valid_product(self):
        p = ProductInfo(
            name="测试产品", category="数码", price=99.00,
            selling_points=["好用"], industry="food",
        )
        errors = p.validate()
        assert len(errors) == 0, "完整产品应该验证通过"
        print("  ✅ 完整产品验证通过")
    
    def test_to_prompt_context(self):
        p = ProductInfo(name="A", category="B", price=10, selling_points=["P1"], industry="C")
        ctx = p.to_prompt_context()
        assert "产品名称" in ctx
        assert "卖点" in ctx
        print("  ✅ Prompt上下文生成正确")


class TestCompliance:
    """测试合规检查模块"""
    
    def setup_method(self):
        self.checker = ComplianceChecker()
    
    def test_banned_words(self):
        text = "这是最优惠的产品"
        issues = self.checker.check(text)
        assert len(issues) > 0, "应该检测到禁用词"
        assert any("最" in i.word for i in issues)
        print("  ✅ 禁用词检测正常")
    
    def test_clean_text(self):
        text = "这是一段合规的文案"
        issues = self.checker.check(text)
        assert len(issues) == 0, "合规文案不应该有禁用词"
        print("  ✅ 合规文案检测正确")
    
    def test_industry_rules(self):
        text = "有效率98%"
        is_ok, issues = self.checker.is_compliant(text, "healthcare")
        assert not is_ok, "医疗行业有效率表述应该不合格"
        print("  ✅ 行业规则检测正常")
    
    def test_compliance_score(self):
        text = "最佳选择"
        score = self.checker.get_compliance_score(text)
        assert score < 100, "含禁用词应该扣分"
        print("  ✅ 合规评分正确")


class TestGenerator:
    """测试文案生成模块"""
    
    def setup_method(self):
        self.generator = CopyGenerator()
    
    def test_generate(self):
        copy = self.generator.generate("测试产品", ["好用", "便宜", "耐用"])
        assert copy.text, "应该生成文案"
        assert "测试产品" in copy.text, "文案应包含产品名"
        print(f"  ✅ 文案生成正常: {copy.text[:40]}...")
    
    def test_multiple_versions(self):
        copies = self.generator.generate_multiple("P", ["A", "B"])
        assert len(copies) >= 2, "应该生成多个版本"
        print(f"  ✅ 多版本生成: {len(copies)}个")
    
    def test_different_styles(self):
        for style in ["formal", "humorous", "emotional", "urgent"]:
            copy = self.generator.generate("P", ["A"], style)
            assert copy.style == style
        print("  ✅ 所有风格正常生成")


class TestEvaluator:
    """测试评估模块"""
    
    def setup_method(self):
        self.evaluator = CopyEvaluator()
    
    def test_evaluate(self):
        result = self.evaluator.evaluate("这款产品真好用", "产品")
        assert 0 <= result.score <= 100
        assert result.grade in "SABCD"
        print(f"  ✅ 评估正常: 评分{result.score:.1f} 等级{result.grade}")
    
    def test_compare_copies(self):
        results = self.evaluator.compare_copies(
            ["文案A", "文案B很好的产品"], "产品"
        )
        assert len(results) == 2
        assert results[0].score >= results[1].score  # 排序
        print("  ✅ 批量比较正常")


class TestAudience:
    """测试受众分析"""
    
    def setup_method(self):
        self.analyzer = AudienceAnalyzer()
    
    def test_analyze(self):
        profile = self.analyzer.analyze("智能手表", "数码")
        assert profile.age_group, "应该分析出年龄段"
        print(f"  ✅ 受众分析正常: {profile.age_group}")


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        self.writer = MarketingCopywriter()
    
    def test_full_pipeline(self):
        p = ProductInfo(
            name="测试集成", category="食品", price=10,
            selling_points=["卖点A", "卖点B"],
            industry="food",
        )
        result = self.writer.generate(p, num_versions=2)
        assert len(result.copies) == 2, "应该生成2个版本"
        assert result.best_copy is not None, "应该选出最佳版本"
        assert result.best_copy.score > 0, "最佳版本应该有评分"
        print(f"  ✅ 全流程集成: {len(result.copies)}版本, 最佳{result.best_copy.score:.1f}分")
    
    def test_compliance_check(self):
        p = ProductInfo(
            name="保健品测试", category="健康", price=199,
            selling_points=["最佳选择", "唯一方案"],
            industry="healthcare",
        )
        result = self.writer.generate(p)
        if result.copies:
            any_non_compliant = any(not c.is_compliant for c in result.copies)
            print(f"  ✅ 合规检查集成: {'发现违规' if any_non_compliant else '全部合规'}")


def run_all():
    """运行所有测试"""
    print("\n=== 产品模块测试 ===")
    t = TestProduct()
    t.test_product_validation()
    t.test_valid_product()
    t.test_to_prompt_context()
    
    print("\n=== 合规检查测试 ===")
    tc = TestCompliance()
    tc.setup_method()
    tc.test_banned_words()
    tc.test_clean_text()
    tc.test_industry_rules()
    tc.test_compliance_score()
    
    print("\n=== 文案生成测试 ===")
    tg = TestGenerator()
    tg.setup_method()
    tg.test_generate()
    tg.test_multiple_versions()
    tg.test_different_styles()
    
    print("\n=== 质量评估测试 ===")
    te = TestEvaluator()
    te.setup_method()
    te.test_evaluate()
    te.test_compare_copies()
    
    print("\n=== 受众分析测试 ===")
    ta = TestAudience()
    ta.setup_method()
    ta.test_analyze()
    
    print("\n=== 集成测试 ===")
    ti = TestIntegration()
    ti.setup_method()
    ti.test_full_pipeline()
    ti.test_compliance_check()
    
    print("\n✅ 所有测试通过！")


if __name__ == "__main__":
    run_all()
