"""
=============================================================================
 test_retrieval.py — 知识库检索模块单元测试
 作者: 测试员周周 (14年测试老兵)
 覆盖:
   - 精确匹配检索
   - 同义查询检索
   - 模糊查询
   - 跨类别检索
   - 无结果查询
   - 多关键词检索
   - 空查询
   - 文档管理 (添加/删除/清空)
   - 时效性得分
=============================================================================
"""

import unittest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.qa_retriever import KnowledgeBase, KnowledgeDocument


class TestKnowledgeBase(unittest.TestCase):
    """知识库基础功能测试"""

    def setUp(self):
        self.kb = KnowledgeBase()
        self.kb.add_document(KnowledgeDocument(
            doc_id="DOC001", title="如何报名课程",
            content="登录平台后点击课程中心，选择感兴趣的课程，点击立即报名，完成支付即可。",
            category="报名", tags=["报名", "课程", "支付"],
        ))
        self.kb.add_document(KnowledgeDocument(
            doc_id="DOC002", title="退款政策说明",
            content="课程开通后7天内可申请全额退款，超过7天按剩余课时比例退款。退款申请将在3-5个工作日内处理。",
            category="退款", tags=["退款", "政策"],
        ))
        self.kb.add_document(KnowledgeDocument(
            doc_id="DOC003", title="学习技巧与建议",
            content="建议每天学习1-2小时，按时完成作业，多参与讨论。",
            category="学习", tags=["学习", "技巧"],
        ))

    # ---------- 精确匹配检索 ----------

    def test_exact_match_enrollment(self):
        """TC-RET-001: 精确匹配 '报名' 类问题"""
        results = self.kb.hybrid_search("怎么报名课程", top_k=3)
        self.assertGreater(len(results), 0)
        # 最相关文档应该是 DOC001
        self.assertEqual(results[0][0].doc_id, "DOC001")
        # 得分应高于 0.3（精确匹配）
        self.assertGreater(results[0][1], 0.3)

    # ---------- 同义查询 ----------

    def test_synonym_search(self):
        """TC-RET-002: 同义查询 '如何选课' 应能匹配到报名文档"""
        results = self.kb.hybrid_search("如何选课", top_k=3)
        self.assertGreater(len(results), 0)
        # 由于同义词扩展，"选课"会扩展为"选课 报名 选择课程"
        # 所以 DOC001 应该出现在结果中
        doc_ids = [doc.doc_id for doc, _ in results]
        self.assertIn("DOC001", doc_ids)

    # ---------- 模糊查询 ----------

    def test_fuzzy_query(self):
        """TC-RET-003: 模糊查询 '那个报名的东西' 应能匹配"""
        results = self.kb.hybrid_search("那个报名的东西", top_k=3)
        self.assertGreater(len(results), 0)
        # "报名" 关键词应能命中 DOC001
        self.assertEqual(results[0][0].doc_id, "DOC001")

    # ---------- 跨类别检索 ----------

    def test_cross_category(self):
        """TC-RET-004: 跨类别查询 '退款后多久到账'"""
        results = self.kb.hybrid_search("退款后多久到账", top_k=3)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0][0].doc_id, "DOC002")

    # ---------- 无结果查询 ----------

    def test_no_result(self):
        """TC-RET-005: 无结果查询 '怎么修电脑'"""
        results = self.kb.hybrid_search("怎么修电脑", top_k=3)
        self.assertEqual(len(results), 0)

    # ---------- 多关键词检索 ----------

    def test_multi_keyword(self):
        """TC-RET-006: 多关键词 '课程报名退款政策' 应命中多篇文档"""
        results = self.kb.hybrid_search("课程报名退款政策", top_k=3)
        # 应至少有 2 篇文档命中
        self.assertGreaterEqual(len(results), 2)

    # ---------- 空查询 ----------

    def test_empty_query(self):
        """TC-RET-007: 空查询应返回空列表"""
        results = self.kb.hybrid_search("", top_k=5)
        self.assertEqual(len(results), 0)

    # ---------- 文档管理 ----------

    def test_add_document(self):
        """TC-RET-008: 添加新文档后应能检索到"""
        self.kb.add_document(KnowledgeDocument(
            doc_id="DOC004", title="账号注册",
            content="使用手机号注册账号。",
            category="账号",
        ))
        results = self.kb.hybrid_search("注册账号", top_k=1)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0][0].doc_id, "DOC004")

    def test_remove_document(self):
        """TC-RET-009: 删除文档后应检索不到"""
        self.kb.remove_document("DOC002")
        results = self.kb.hybrid_search("退款", top_k=3)
        # 删除后应没有退款相关文档
        for doc, _ in results:
            self.assertNotEqual(doc.doc_id, "DOC002")

    def test_remove_nonexistent(self):
        """TC-RET-010: 删除不存在的文档返回 False"""
        result = self.kb.remove_document("NOT_EXIST")
        self.assertFalse(result)

    def test_clear(self):
        """TC-RET-011: 清空知识库"""
        self.kb.clear()
        self.assertEqual(self.kb.document_count(), 0)
        results = self.kb.hybrid_search("报名", top_k=3)
        self.assertEqual(len(results), 0)

    def test_document_count(self):
        """TC-RET-012: 文档计数"""
        self.assertEqual(self.kb.document_count(), 3)

    def test_get_document(self):
        """TC-RET-013: 获取指定文档"""
        doc = self.kb.get_document("DOC001")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.title, "如何报名课程")

    def test_get_document_not_found(self):
        """TC-RET-014: 获取不存在的文档"""
        doc = self.kb.get_document("NOT_EXIST")
        self.assertIsNone(doc)

    # ---------- 检索参数调整 ----------

    def test_top_k_limit(self):
        """TC-RET-015: top_k 限制返回数量"""
        results = self.kb.hybrid_search("课程", top_k=1)
        self.assertLessEqual(len(results), 1)

    # ---------- 时效性得分 ----------

    def test_freshness_recent(self):
        """TC-RET-016: 新文档应有时效性得分"""
        doc = KnowledgeDocument(
            doc_id="NEW", title="新文档",
            content="新内容", category="新",
            updated_at=time.time(),  # 当前时间
        )
        score = KnowledgeBase._freshness_score(doc)
        self.assertEqual(score, 1.0)

    def test_freshness_old(self):
        """TC-RET-017: 旧文档时效性得分较低"""
        doc = KnowledgeDocument(
            doc_id="OLD", title="旧文档",
            content="旧内容", category="旧",
            updated_at=time.time() - 200 * 86400,  # 200天前
        )
        score = KnowledgeBase._freshness_score(doc)
        self.assertEqual(score, 0.4)

    def test_freshness_no_timestamp(self):
        """TC-RET-018: 无时间戳文档得默认分"""
        doc = KnowledgeDocument(
            doc_id="NO_TS", title="无时间",
            content="无时间内容", category="无",
            updated_at=0,
        )
        score = KnowledgeBase._freshness_score(doc)
        self.assertEqual(score, 0.5)

    # ---------- 同义词扩展 ----------

    def test_synonym_expansion(self):
        """TC-RET-019: 同义词扩展应提升检索效果"""
        # "注册" 不在任何文档标题或内容中直接出现
        # 但通过同义词扩展，"选择课程" 相关
        results_with_syn = self.kb.hybrid_search(
            "选课", top_k=3, config={"enable_synonym_expansion": True}
        )
        results_no_syn = self.kb.hybrid_search(
            "选课", top_k=3, config={"enable_synonym_expansion": False}
        )
        # 开启同义词扩展的结果数应不少于不开的
        self.assertGreaterEqual(len(results_with_syn), len(results_no_syn))


if __name__ == "__main__":
    unittest.main()
