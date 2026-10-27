"""
=============================================================================
 test_generator.py — 答案生成模块单元测试
 作者: 测试员周周 (14年测试老兵)
 覆盖:
   - LLM 模式生成
   - 降级模板生成
   - 拒答消息
   - Prompt 构建
   - 无文档边界情况
=============================================================================
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.generator import (
    AnswerGenerator,
    build_prompt,
    mock_llm,
    DEFAULT_REJECTION_MESSAGE,
    DEFAULT_FALLBACK_MESSAGE,
)
from src.qa_retriever import KnowledgeDocument


class TestAnswerGenerator(unittest.TestCase):
    """答案生成器测试"""

    def setUp(self):
        self.docs = [
            KnowledgeDocument(
                doc_id="DOC001", title="如何报名课程",
                content="登录平台后点击课程中心，选择感兴趣的课程，点击立即报名，完成支付即可。",
                category="报名",
            ),
            KnowledgeDocument(
                doc_id="DOC002", title="退款政策",
                content="课程开通后7天内可申请全额退款。",
                category="退款",
            ),
        ]

    # ---------- LLM 模式 ----------

    def test_generate_with_llm(self):
        """TC-GEN-001: LLM 模式生成回答"""
        generator = AnswerGenerator(llm_call_func=mock_llm)
        answer = generator.generate("怎么报名课程", self.docs)
        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 0)

    # ---------- 降级模式 ----------

    def test_fallback_with_docs(self):
        """TC-GEN-002: 降级模式（有文档）"""
        generator = AnswerGenerator()  # 不传 llm
        answer = generator.generate("怎么报名课程", self.docs)
        self.assertIn("根据知识库", answer)
        self.assertIn("报名", answer)

    def test_fallback_no_docs(self):
        """TC-GEN-003: 降级模式（无文档）"""
        generator = AnswerGenerator()
        answer = generator.generate("怎么修电脑", [])
        self.assertEqual(answer, DEFAULT_REJECTION_MESSAGE)

    # ---------- Prompt 构建 ----------

    def test_build_prompt_contains_question(self):
        """TC-GEN-004: Prompt 应包含用户问题"""
        prompt = build_prompt("怎么报名", self.docs[:1])
        self.assertIn("怎么报名", prompt)

    def test_build_prompt_contains_context(self):
        """TC-GEN-005: Prompt 应包含知识库内容"""
        prompt = build_prompt("怎么报名", self.docs[:1])
        self.assertIn("来源1", prompt)
        self.assertIn("如何报名课程", prompt)

    def test_build_prompt_has_constraints(self):
        """TC-GEN-006: Prompt 应包含回答约束"""
        prompt = build_prompt("怎么报名", self.docs[:1])
        self.assertIn("不要编造信息", prompt)
        self.assertIn("不要提及任何第三方平台", prompt)

    # ---------- 拒答消息 ----------

    def test_rejection_message(self):
        """TC-GEN-007: 默认拒答消息"""
        msg = AnswerGenerator.get_rejection_message()
        self.assertEqual(msg, DEFAULT_REJECTION_MESSAGE)

    def test_rejection_message_custom(self):
        """TC-GEN-008: 自定义拒答消息"""
        custom = "自定义拒答"
        msg = AnswerGenerator.get_rejection_message(custom)
        self.assertEqual(msg, custom)

    # ---------- 后处理 ----------

    def test_post_process_truncation(self):
        """TC-GEN-009: 超长回答截断"""
        long_answer = "A" * 500
        result = AnswerGenerator._post_process(long_answer, max_length=200)
        self.assertLessEqual(len(result), 201)  # 200 + 省略号

    def test_post_process_trim(self):
        """TC-GEN-010: 回答去空白"""
        result = AnswerGenerator._post_process("  回答内容  ")
        self.assertEqual(result, "回答内容")

    # ---------- Mock LLM ----------

    def test_mock_llm_returns_string(self):
        """TC-GEN-011: Mock LLM 返回字符串"""
        prompt = build_prompt("怎么报名", self.docs[:1])
        result = mock_llm(prompt)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()
