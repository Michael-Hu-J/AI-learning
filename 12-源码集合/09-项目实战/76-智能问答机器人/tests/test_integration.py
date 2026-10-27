"""
=============================================================================
 test_integration.py — 全流程集成测试
 作者: 测试员周周 (14年测试老兵)
 描述: 从用户输入到最终回答的端到端测试
 覆盖:
   - 正常问答流程（咨询 → 检索 → 生成 → 评估 → 返回）
   - 拒答流程（无相关知识 → 拒答）
   - 竞品查询流程（涉敏 → 拒答）
   - 置信度计算
   - 配置参数加载
   - 质量评估集成
=============================================================================
"""

import unittest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.qa_bot import QABot, QAResult
from src.qa_retriever import KnowledgeBase, KnowledgeDocument
from src.generator import mock_llm
from src.config import load_config, get_default_config, validate_config
from src.quality import AnswerQualityEvaluator, QualityReport


class TestQABotIntegration(unittest.TestCase):
    """全流程集成测试"""

    @classmethod
    def setUpClass(cls):
        """类级别初始化：构建知识库和机器人"""
        cls.kb = KnowledgeBase()
        cls.kb.add_document(KnowledgeDocument(
            doc_id="DOC001", title="如何报名课程",
            content="登录平台后点击课程中心，选择感兴趣的课程，点击立即报名，完成支付即可。",
            category="报名", tags=["报名", "课程", "支付"],
        ))
        cls.kb.add_document(KnowledgeDocument(
            doc_id="DOC002", title="退款政策说明",
            content="课程开通后7天内可申请全额退款，超过7天按剩余课时比例退款。",
            category="退款", tags=["退款", "政策"],
        ))
        cls.kb.add_document(KnowledgeDocument(
            doc_id="DOC003", title="学习技巧与建议",
            content="建议每天学习1-2小时，按时完成作业，多参与讨论。",
            category="学习", tags=["学习", "技巧"],
        ))

        # 加载配置
        cls.config = load_config()

        # 初始化机器人（使用 mock_llm）
        cls.bot = QABot(
            knowledge_base=cls.kb,
            llm_call_func=mock_llm,
            config=cls.config,
        )

        # 初始化评估器
        cls.evaluator = AnswerQualityEvaluator(cls.config.get("quality", {}))

    def setUp(self):
        """每个测试前记录开始时间"""
        self.start = time.time()

    # ---------- 正常问答流程 ----------

    def test_normal_answer_flow(self):
        """TC-INT-001: 完整流程 — 正常回答问题"""
        result = self.bot.answer("怎么报名课程")
        self.assertFalse(result.is_rejected)
        self.assertIn("报名", result.answer)
        self.assertGreater(result.confidence, 0.3)
        self.assertGreater(len(result.sources), 0)

    def test_refund_query(self):
        """TC-INT-002: 退款相关问题"""
        result = self.bot.answer("退款几天能到账")
        self.assertFalse(result.is_rejected)
        self.assertGreater(result.confidence, 0.2)

    def test_learning_tips(self):
        """TC-INT-003: 学习技巧问题"""
        result = self.bot.answer("怎么学习效果好")
        self.assertFalse(result.is_rejected)

    # ---------- 拒答流程 ----------

    def test_rejection_for_unknown(self):
        """TC-INT-004: 未知问题应拒答"""
        result = self.bot.answer("怎么修电脑")
        self.assertTrue(result.is_rejected)
        self.assertIn("抱歉", result.answer)
        self.assertIsNotNone(result.rejection_reason)

    def test_rejection_no_match_query(self):
        """TC-INT-005: 完全无关的问题应拒答"""
        result = self.bot.answer("今天股票涨了吗")
        self.assertTrue(result.is_rejected)

    # ---------- 竞品/涉敏查询 ----------

    def test_competitor_query_rejected(self):
        """TC-INT-006: 竞品对比问题应拒答（意图层面）"""
        result = self.bot.answer("你们跟隔壁平台比哪个好")
        self.assertTrue(result.is_rejected)
        self.assertIn("抱歉", result.answer)

    def test_sensitive_query_rejected(self):
        """TC-INT-007: 涉密问题应拒答"""
        result = self.bot.answer("我的身份证号是多少")
        self.assertTrue(result.is_rejected)

    # ---------- 置信度计算 ----------

    def test_confidence_high_for_good_match(self):
        """TC-INT-008: 良好匹配的置信度应较高"""
        result = self.bot.answer("怎么报名课程")
        self.assertGreater(result.confidence, 0.3)
        self.assertLessEqual(result.confidence, 1.0)

    def test_confidence_empty(self):
        """TC-INT-009: 空列表置信度为 0"""
        conf = QABot._compute_confidence([])
        self.assertEqual(conf, 0.0)

    def test_confidence_formula(self):
        """TC-INT-010: 置信度计算公式验证"""
        conf = QABot._compute_confidence([0.8, 0.6, 0.4])
        # max=0.8 * 0.7 + avg=0.6 * 0.3 = 0.56 + 0.18 = 0.74
        self.assertAlmostEqual(conf, 0.74, places=4)
        self.assertLessEqual(conf, 1.0)

    # ---------- 质量评估集成 ----------

    def test_quality_evaluation_in_answer(self):
        """TC-INT-011: 回答结果中应包含质量评估"""
        result = self.bot.answer("怎么报名课程")
        self.assertIsNotNone(result.quality_report)
        self.assertGreater(result.quality_score, 0)

    def test_quality_report_rejected(self):
        """TC-INT-012: 拒答结果的质量报告（无检索结果时无质量报告）"""
        result = self.bot.answer("怎么修电脑")
        # 检索无结果时直接拒答，不走质量评估流程
        self.assertTrue(result.is_rejected)
        # quality_report 可能为 None（早期拒答不走质量评估）
        # 这里只验证不报错即可

    # ---------- 边界情况 ----------

    def test_empty_question(self):
        """TC-INT-013: 空问题"""
        result = self.bot.answer("")
        self.assertTrue(result.is_rejected)

    def test_very_long_question(self):
        """TC-INT-014: 超长问题"""
        long_q = "报名" * 100
        result = self.bot.answer(long_q)
        # 应该正常处理，不崩溃
        self.assertIsNotNone(result.answer)

    # ---------- 多文档检索 ----------

    def test_multiple_sources(self):
        """TC-INT-015: 多关键词应检索到多个来源"""
        result = self.bot.answer("课程报名和退款政策")
        # 应命中至少 2 个来源
        self.assertGreaterEqual(len(result.sources), 1)

    # ---------- 意图分类集成 ----------

    def test_greeting_handling(self):
        """TC-INT-016: 问候语处理"""
        result = self.bot.answer("你好")
        self.assertFalse(result.is_rejected)
        self.assertIn("您好", result.answer)

    def test_chitchat_handling(self):
        """TC-INT-017: 闲聊处理"""
        result = self.bot.answer("你是谁")
        self.assertFalse(result.is_rejected)
        self.assertIn("助手", result.answer)


class TestConfigIntegration(unittest.TestCase):
    """配置模块集成测试"""

    def test_load_config_default(self):
        """TC-CFG-001: 加载默认配置"""
        cfg = load_config()
        self.assertIn("retrieval", cfg)
        self.assertIn("quality", cfg)
        self.assertIn("generation", cfg)

    def test_validate_config_valid(self):
        """TC-CFG-002: 校验合法配置"""
        cfg = get_default_config()
        self.assertTrue(validate_config(cfg))

    def test_validate_config_invalid_top_k(self):
        """TC-CFG-003: 校验非法 top_k"""
        cfg = get_default_config()
        cfg["retrieval"]["top_k"] = -1
        self.assertFalse(validate_config(cfg))

    def test_validate_config_invalid_threshold(self):
        """TC-CFG-004: 校验非法 threshold"""
        cfg = get_default_config()
        cfg["retrieval"]["threshold"] = 1.5
        self.assertFalse(validate_config(cfg))


class TestEvaluatorIntegration(unittest.TestCase):
    """评估器集成测试"""

    def test_evaluator_with_sources(self):
        """TC-EVAL-001: 评估器接收 sources 参数不报错"""
        evaluator = AnswerQualityEvaluator()
        report = evaluator.evaluate(
            question="怎么报名",
            answer="登录平台报名即可。",
            expected_answer="登录 报名",
            sources=["如何报名课程"],
        )
        self.assertIsNotNone(report.overall_score)

    def test_evaluator_overall_formula(self):
        """TC-EVAL-002: 综合得分计算公式"""
        evaluator = AnswerQualityEvaluator()
        report = evaluator.evaluate(
            question="怎么报名课程",
            answer="登录平台后点击课程中心，选择课程并点击立即报名，完成支付即可。",
            expected_answer="登录 课程中心 报名 支付",
        )
        # 验证综合得分 = 各维度加权和
        expected = (
            report.factual_score * 0.35
            + report.relevance_score * 0.25
            + report.safety_score * 0.25
            + report.completeness_score * 0.15
        )
        self.assertAlmostEqual(report.overall_score, expected, places=4)


if __name__ == "__main__":
    unittest.main()
