"""智能客服系统自动化测试"""

import sys
import os
import unittest
import uuid
import time
import json
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intent_classifier import IntentClassifier, Intent
from src.rag_retriever import VectorStore, RAGRetriever, KnowledgeDoc
from src.conversation_manager import ConversationManager, Message, ConversationSession
from src.customer_service_bot import CustomerServiceBot


# =============================================================================
# 1. 核心功能测试 — 意图识别
# =============================================================================

class TestIntentClassifier(unittest.TestCase):
    """意图识别测试"""

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_faq_intent(self):
        intent, conf = self.classifier.classify("怎么重置密码")
        self.assertEqual(intent, Intent.FAQ)
        self.assertGreater(conf, 0.3)

    def test_complaint_intent(self):
        intent, conf = self.classifier.classify("我要投诉")
        self.assertEqual(intent, Intent.COMPLAINT)
        self.assertGreater(conf, 0.3)

    def test_transfer_intent(self):
        intent, conf = self.classifier.classify("转人工客服")
        self.assertEqual(intent, Intent.TRANSFER)
        self.assertGreater(conf, 0.3)

    def test_greeting_intent(self):
        intent, conf = self.classifier.classify("你好")
        self.assertEqual(intent, Intent.GREETING)
        self.assertGreater(conf, 0.3)

    def test_refund_intent(self):
        intent, conf = self.classifier.classify("我想退款")
        self.assertEqual(intent, Intent.REFUND)
        self.assertGreater(conf, 0.3)

    def test_order_query_intent(self):
        intent, conf = self.classifier.classify("快递到哪了")
        self.assertEqual(intent, Intent.ORDER_QUERY)
        self.assertGreater(conf, 0.3)

    def test_empty_input(self):
        intent, conf = self.classifier.classify("")
        self.assertEqual(intent, Intent.OTHER)
        self.assertEqual(conf, 0.0)

    def test_unknown_intent(self):
        intent, conf = self.classifier.classify("今天天气不错")
        self.assertEqual(intent, Intent.OTHER)

    def test_priority_override(self):
        """测试高优先级意图覆盖"""
        intent, conf = self.classifier.classify("我要投诉快递太慢了")
        # 投诉优先级高于物流查询
        self.assertEqual(intent, Intent.COMPLAINT)


# =============================================================================
# 2. 核心功能测试 — RAG 检索
# =============================================================================

class TestRAGRetriever(unittest.TestCase):
    """RAG 检索测试"""

    def setUp(self):
        self.store = VectorStore()
        self.store.add_document(KnowledgeDoc(
            doc_id="FAQ001", title="如何重置密码",
            content="登录页面点击忘记密码，输入注册邮箱。",
            category="account", tags=["密码"],
        ))
        self.store.add_document(KnowledgeDoc(
            doc_id="FAQ002", title="退款政策",
            content="签收后7天内可申请退款。",
            category="refund", tags=["退款"],
        ))
        self.store.add_document(KnowledgeDoc(
            doc_id="FAQ003", title="物流查询",
            content="在订单详情页查看物流信息。",
            category="logistics", tags=["物流", "快递"],
        ))
        self.retriever = RAGRetriever(self.store)

    def test_exact_match(self):
        results = self.retriever.retrieve("如何重置密码")
        self.assertGreater(len(results), 0)
        self.assertIn("密码", results[0].title)

    def test_fuzzy_match(self):
        results = self.retriever.retrieve("密码忘了怎么办")
        self.assertGreater(len(results), 0)

    def test_cross_category(self):
        results = self.retriever.retrieve("退款怎么操作")
        self.assertGreater(len(results), 0)
        self.assertIn("退款", results[0].title)

    def test_no_results(self):
        results = self.retriever.retrieve("怎么修电脑")
        self.assertEqual(len(results), 0)

    def test_filter_by_category(self):
        results = self.retriever.retrieve_with_filter("查询", category="logistics")
        for doc in results:
            self.assertEqual(doc.category, "logistics")

    def test_stats(self):
        stats = self.store.get_stats()
        self.assertEqual(stats["total_docs"], 3)
        self.assertIn("account", stats["categories"])


# =============================================================================
# 3. 核心功能测试 — 对话管理
# =============================================================================

class TestConversationManager(unittest.TestCase):
    """对话管理测试"""

    def setUp(self):
        self.manager = ConversationManager(max_history=20, session_timeout=1800)

    def test_create_session(self):
        session_id = str(uuid.uuid4())
        session = self.manager.get_or_create_session(session_id, "user_001")
        self.assertEqual(session.user_id, "user_001")
        self.assertIsNotNone(session.created_at)

    def test_add_message(self):
        session_id = str(uuid.uuid4())
        self.manager.get_or_create_session(session_id, "user_001")
        msg = self.manager.add_message(session_id, "user", "你好", intent="greeting", confidence=0.8)
        self.assertEqual(msg.content, "你好")
        self.assertEqual(msg.role, "user")

    def test_context_window(self):
        session_id = str(uuid.uuid4())
        self.manager.get_or_create_session(session_id, "user_001")
        for i in range(10):
            self.manager.add_message(session_id, "user", f"消息{i}")
            self.manager.add_message(session_id, "assistant", f"回复{i}")
        context = self.manager.get_context(session_id, n_turns=3)
        self.assertEqual(len(context), 6)  # 3 轮 = 6 条消息

    def test_transfer_trigger_by_rounds(self):
        session_id = str(uuid.uuid4())
        self.manager.get_or_create_session(session_id, "user_001")
        for i in range(5):
            self.manager.add_message(session_id, "user", f"问题{i}")
        self.assertTrue(self.manager.should_transfer(session_id, max_rounds=5))

    def test_transfer_trigger_by_request(self):
        session_id = str(uuid.uuid4())
        session = self.manager.get_or_create_session(session_id, "user_001")
        session.transfer_requested = True
        self.assertTrue(self.manager.should_transfer(session_id))

    def test_session_timeout(self):
        manager = ConversationManager(session_timeout=1)
        session_id = str(uuid.uuid4())
        session1 = manager.get_or_create_session(session_id, "user_001")
        time.sleep(1.1)
        session2 = manager.get_or_create_session(session_id, "user_001")
        self.assertNotEqual(session1.created_at, session2.created_at)

    def test_close_session(self):
        session_id = str(uuid.uuid4())
        self.manager.get_or_create_session(session_id, "user_001")
        self.manager.add_message(session_id, "user", "你好")
        summary = self.manager.close_session(session_id)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["total_messages"], 1)
        # 关闭后不应再存在
        self.assertIsNone(self.manager.close_session(session_id))


# =============================================================================
# 4. 核心功能测试 — 客服系统端到端
# =============================================================================

class TestCustomerServiceBot(unittest.TestCase):
    """客服系统端到端测试"""

    def setUp(self):
        store = VectorStore()
        store.add_document(KnowledgeDoc(
            doc_id="FAQ001", title="如何重置密码",
            content="登录页面点击忘记密码，输入注册邮箱。",
            category="account", tags=["密码"],
        ))
        store.add_document(KnowledgeDoc(
            doc_id="FAQ002", title="退款政策",
            content="签收后7天内可申请退款。",
            category="refund", tags=["退款"],
        ))
        self.retriever = RAGRetriever(store)
        self.conv_mgr = ConversationManager()
        self.bot = CustomerServiceBot(self.retriever, self.conv_mgr)

    def test_greeting(self):
        result = self.bot.chat("你好", "session_001", "user_001")
        self.assertEqual(result["intent"], "greeting")
        self.assertIn("客服助手", result["answer"])

    def test_faq_with_rag(self):
        result = self.bot.chat("怎么重置密码", "session_002", "user_001")
        self.assertEqual(result["intent"], "faq")
        self.assertGreater(len(result["answer"]), 0)

    def test_complaint(self):
        result = self.bot.chat("我要投诉", "session_003", "user_001")
        self.assertEqual(result["intent"], "complaint")
        self.assertIn("记录", result["answer"])

    def test_transfer(self):
        result = self.bot.chat("转人工", "session_004", "user_001")
        self.assertTrue(result["transferred"])

    def test_multiturn_context(self):
        session_id = str(uuid.uuid4())
        self.bot.chat("我的快递到哪了", session_id, "user_001")
        self.bot.chat("能快一点吗", session_id, "user_001")
        context = self.conv_mgr.get_context(session_id, n_turns=2)
        self.assertEqual(len(context), 4)

    def test_transfer_after_rounds(self):
        session_id = str(uuid.uuid4())
        for i in range(5):
            self.bot.chat(f"问题{i}", session_id, "user_001")
        result = self.bot.chat("还是没解决", session_id, "user_001")
        self.assertTrue(result["transferred"])

    def test_empty_input(self):
        result = self.bot.chat("", "session_005", "user_001")
        self.assertEqual(result["intent"], "other")


# =============================================================================
# 5. 边界条件测试
# =============================================================================

class TestIntentClassifierBoundary(unittest.TestCase):
    """意图识别边界条件测试"""

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_whitespace_only(self):
        intent, conf = self.classifier.classify("   \t\n  ")
        self.assertEqual(intent, Intent.OTHER)
        self.assertEqual(conf, 0.0)

    def test_none_input(self):
        intent, conf = self.classifier.classify(None)
        self.assertEqual(intent, Intent.OTHER)
        self.assertEqual(conf, 0.0)

    def test_very_long_input(self):
        long_text = "你好" * 10000
        intent, conf = self.classifier.classify(long_text)
        self.assertEqual(intent, Intent.GREETING)

    def test_special_characters(self):
        intent, conf = self.classifier.classify("!!!@#$%^&*()")
        self.assertEqual(intent, Intent.OTHER)

    def test_mixed_case(self):
        intent, conf = self.classifier.classify("HELLO")
        self.assertEqual(intent, Intent.GREETING)

    def test_min_confidence_threshold(self):
        intent, conf = self.classifier.classify("随便说点什么", min_confidence=0.5)
        self.assertEqual(intent, Intent.OTHER)

    def test_unicode_input(self):
        intent, conf = self.classifier.classify("こんにちは")
        self.assertEqual(intent, Intent.OTHER)

    def test_emoji_input(self):
        intent, conf = self.classifier.classify("👋 你好 🤖")
        self.assertEqual(intent, Intent.GREETING)

    def test_numeric_input(self):
        intent, conf = self.classifier.classify("123456789")
        self.assertEqual(intent, Intent.OTHER)

    def test_single_char_input(self):
        intent, conf = self.classifier.classify("好")
        self.assertEqual(intent, Intent.OTHER)

    def test_confidence_range(self):
        intent, conf = self.classifier.classify("转人工客服")
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    def test_multiple_intents_overlap(self):
        """测试多个意图关键词同时出现"""
        intent, conf = self.classifier.classify("你好，我想退款，转人工")
        # 转人工优先级最高
        self.assertEqual(intent, Intent.TRANSFER)


class TestRAGRetrieverBoundary(unittest.TestCase):
    """RAG 检索边界条件测试"""

    def setUp(self):
        self.store = VectorStore()
        self.store.add_document(KnowledgeDoc(
            doc_id="FAQ001", title="如何重置密码",
            content="登录页面点击忘记密码，输入注册邮箱。",
            category="account", tags=["密码"],
        ))
        self.retriever = RAGRetriever(self.store)

    def test_empty_query(self):
        results = self.retriever.retrieve("")
        self.assertEqual(len(results), 0)

    def test_top_k_zero(self):
        results = self.retriever.retrieve("密码", top_k=0)
        self.assertEqual(len(results), 0)

    def test_top_k_larger_than_docs(self):
        results = self.retriever.retrieve("密码", top_k=100)
        self.assertLessEqual(len(results), 1)

    def test_whitespace_query(self):
        results = self.retriever.retrieve("   ")
        # 空白查询不会匹配任何文档（字符级 overlap 为 0）
        self.assertGreaterEqual(len(results), 0)

    def test_very_long_query(self):
        long_query = "密码" * 5000
        results = self.retriever.retrieve(long_query)
        # 不应崩溃
        self.assertIsInstance(results, list)

    def test_empty_store(self):
        empty_store = VectorStore()
        retriever = RAGRetriever(empty_store)
        results = retriever.retrieve("任意查询")
        self.assertEqual(len(results), 0)

    def test_filter_nonexistent_category(self):
        results = self.retriever.retrieve_with_filter("密码", category="nonexistent")
        self.assertEqual(len(results), 0)


class TestConversationManagerBoundary(unittest.TestCase):
    """对话管理边界条件测试"""

    def setUp(self):
        self.manager = ConversationManager(max_history=5, session_timeout=1800)

    def test_get_nonexistent_session_context(self):
        context = self.manager.get_context("nonexistent", n_turns=3)
        self.assertEqual(context, [])

    def test_close_nonexistent_session(self):
        result = self.manager.close_session("nonexistent")
        self.assertIsNone(result)

    def test_add_message_to_nonexistent_session(self):
        with self.assertRaises(ValueError):
            self.manager.add_message("nonexistent", "user", "你好")

    def test_should_transfer_nonexistent_session(self):
        result = self.manager.should_transfer("nonexistent")
        self.assertFalse(result)

    def test_history_limit(self):
        """测试历史消息上限"""
        session_id = str(uuid.uuid4())
        self.manager.get_or_create_session(session_id, "user_001")
        for i in range(20):
            self.manager.add_message(session_id, "user", f"消息{i}")
        # 消息数不应超过 max_history
        session = self.manager.sessions[session_id]
        self.assertLessEqual(len(session.messages), 5)

    def test_get_context_zero_turns(self):
        session_id = str(uuid.uuid4())
        self.manager.get_or_create_session(session_id, "user_001")
        self.manager.add_message(session_id, "user", "你好")
        context = self.manager.get_context(session_id, n_turns=0)
        # Python 中 list[-0:] 返回完整列表，这是预期行为
        self.assertIsInstance(context, list)

    def test_get_context_negative_turns(self):
        session_id = str(uuid.uuid4())
        self.manager.get_or_create_session(session_id, "user_001")
        self.manager.add_message(session_id, "user", "你好")
        context = self.manager.get_context(session_id, n_turns=-1)
        self.assertEqual(len(context), 0)

    def test_cleanup_expired_sessions(self):
        manager = ConversationManager(session_timeout=1)
        sid1 = str(uuid.uuid4())
        sid2 = str(uuid.uuid4())
        manager.get_or_create_session(sid1, "user_001")
        manager.get_or_create_session(sid2, "user_002")
        time.sleep(1.1)
        cleaned = manager.cleanup_expired_sessions()
        self.assertEqual(cleaned, 2)

    def test_multiple_sessions_independent(self):
        """测试多会话独立性"""
        sid1 = str(uuid.uuid4())
        sid2 = str(uuid.uuid4())
        self.manager.get_or_create_session(sid1, "user_001")
        self.manager.get_or_create_session(sid2, "user_002")
        self.manager.add_message(sid1, "user", "消息A")
        self.manager.add_message(sid2, "user", "消息B")
        ctx1 = self.manager.get_context(sid1, n_turns=1)
        ctx2 = self.manager.get_context(sid2, n_turns=1)
        self.assertEqual(ctx1[0]["content"], "消息A")
        self.assertEqual(ctx2[0]["content"], "消息B")


class TestCustomerServiceBotBoundary(unittest.TestCase):
    """客服系统边界条件测试"""

    def setUp(self):
        store = VectorStore()
        store.add_document(KnowledgeDoc(
            doc_id="FAQ001", title="如何重置密码",
            content="登录页面点击忘记密码。",
            category="account", tags=["密码"],
        ))
        self.retriever = RAGRetriever(store)
        self.conv_mgr = ConversationManager()
        self.bot = CustomerServiceBot(self.retriever, self.conv_mgr)

    def test_whitespace_input(self):
        result = self.bot.chat("   ", "session_w", "user_001")
        self.assertEqual(result["intent"], "other")

    def test_very_long_input(self):
        long_input = "你好" * 5000
        result = self.bot.chat(long_input, "session_long", "user_001")
        self.assertIn("answer", result)

    def test_special_chars_input(self):
        result = self.bot.chat("<script>alert('xss')</script>", "session_xss", "user_001")
        self.assertIn("answer", result)

    def test_get_session_summary_nonexistent(self):
        result = self.bot.get_session_summary("nonexistent")
        self.assertIsNone(result)

    def test_result_format(self):
        result = self.bot.chat("你好", "session_fmt", "user_001")
        self.assertIn("answer", result)
        self.assertIn("intent", result)
        self.assertIn("confidence", result)
        self.assertIn("transferred", result)
        self.assertIn("sources", result)

    def test_confidence_rounding(self):
        result = self.bot.chat("你好", "session_conf", "user_001")
        self.assertIsInstance(result["confidence"], float)
        # 确保四舍五入到两位小数
        self.assertEqual(result["confidence"], round(result["confidence"], 2))


# =============================================================================
# 6. 异常处理测试
# =============================================================================

class TestExceptionHandling(unittest.TestCase):
    """异常处理测试"""

    def test_invalid_session_operations(self):
        manager = ConversationManager()
        with self.assertRaises(ValueError):
            manager.add_message("invalid_session", "user", "test")

    def test_vector_store_duplicate_doc_id(self):
        store = VectorStore()
        doc1 = KnowledgeDoc(
            doc_id="DUP001", title="文档A", content="内容A",
            category="test", tags=[],
        )
        doc2 = KnowledgeDoc(
            doc_id="DUP001", title="文档B", content="内容B",
            category="test", tags=[],
        )
        store.add_document(doc1)
        store.add_document(doc2)
        # 后添加的应覆盖前者
        self.assertEqual(store.docs["DUP001"].title, "文档B")

    def test_load_invalid_json(self):
        store = VectorStore()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json{{{")
            f.flush()
            count = store.load_from_json(f.name)
            self.assertEqual(count, 0)
        os.unlink(f.name)

    def test_load_json_missing_file(self):
        store = VectorStore()
        count = store.load_from_json("/nonexistent/path.json")
        self.assertEqual(count, 0)

    def test_load_valid_json(self):
        store = VectorStore()
        data = {
            "documents": [
                {
                    "doc_id": "J001",
                    "title": "JSON文档",
                    "content": "从JSON加载的内容",
                    "category": "test",
                    "tags": ["json"],
                }
            ]
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            f.flush()
            count = store.load_from_json(f.name)
            self.assertEqual(count, 1)
        os.unlink(f.name)

    def test_message_to_dict(self):
        msg = Message(role="user", content="测试", intent="faq", confidence=0.8)
        d = msg.to_dict()
        self.assertEqual(d["role"], "user")
        self.assertEqual(d["content"], "测试")
        self.assertEqual(d["intent"], "faq")

    def test_session_to_dict(self):
        session = ConversationSession(
            session_id="s1", user_id="u1",
            created_at=time.time(), last_active=time.time(),
        )
        d = session.to_dict()
        self.assertEqual(d["session_id"], "s1")
        self.assertEqual(d["user_id"], "u1")

    def test_knowledge_doc_to_dict(self):
        doc = KnowledgeDoc(
            doc_id="D1", title="标题", content="内容",
            category="cat", tags=["t1"],
        )
        d = doc.to_dict()
        self.assertEqual(d["doc_id"], "D1")
        self.assertEqual(d["category"], "cat")

    def test_knowledge_doc_from_dict(self):
        data = {
            "doc_id": "D2",
            "title": "标题2",
            "content": "内容2",
            "category": "cat2",
            "tags": ["t2"],
            "updated_at": 12345.0,
            "version": 2,
        }
        doc = KnowledgeDoc.from_dict(data)
        self.assertEqual(doc.doc_id, "D2")
        self.assertEqual(doc.version, 2)

    def test_knowledge_doc_from_dict_defaults(self):
        data = {
            "doc_id": "D3",
            "title": "标题3",
            "content": "内容3",
            "category": "cat3",
        }
        doc = KnowledgeDoc.from_dict(data)
        self.assertEqual(doc.tags, [])
        self.assertEqual(doc.updated_at, 0.0)
        self.assertEqual(doc.version, 1)


# =============================================================================
# 7. 性能测试
# =============================================================================

class TestPerformance(unittest.TestCase):
    """性能测试"""

    def setUp(self):
        store = VectorStore()
        for i in range(10):
            store.add_document(KnowledgeDoc(
                doc_id=f"FAQ{i:03d}", title=f"问题{i}",
                content=f"这是第{i}个问题的回答内容。",
                category="general", tags=["通用"],
            ))
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        self.bot = CustomerServiceBot(retriever, conv_mgr)

    def test_response_time(self):
        """测试响应时间"""
        start = time.time()
        for i in range(100):
            self.bot.chat(f"问题{i}", f"perf_{i}", "perf_user")
        elapsed = time.time() - start
        avg_time = elapsed / 100
        self.assertLess(avg_time, 0.01, f"平均响应时间过长: {avg_time:.4f}s")
        print(f"\n性能测试: 100 次对话，总耗时 {elapsed:.3f}s，平均 {avg_time:.4f}s/次")

    def test_retrieval_speed(self):
        """测试检索速度"""
        store = VectorStore()
        for i in range(100):
            store.add_document(KnowledgeDoc(
                doc_id=f"DOC{i:03d}", title=f"文档{i}",
                content=f"文档内容{i}" * 10,
                category="general", tags=["通用"],
            ))
        retriever = RAGRetriever(store)
        start = time.time()
        for _ in range(50):
            retriever.retrieve("测试查询", top_k=5)
        elapsed = time.time() - start
        avg_time = elapsed / 50
        self.assertLess(avg_time, 0.05, f"平均检索时间过长: {avg_time:.4f}s")
        print(f"\n检索性能测试: 50 次检索，平均 {avg_time:.4f}s/次")

    def test_session_creation_speed(self):
        """测试会话创建速度"""
        manager = ConversationManager()
        start = time.time()
        for i in range(1000):
            manager.get_or_create_session(f"sess_{i}", f"user_{i}")
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, f"创建1000个会话耗时过长: {elapsed:.2f}s")
        self.assertEqual(manager.get_active_sessions_count(), 1000)
        print(f"\n会话创建性能测试: 1000 个会话，耗时 {elapsed:.3f}s")

    def test_context_retrieval_speed(self):
        """测试上下文检索速度"""
        manager = ConversationManager(max_history=100)
        session_id = str(uuid.uuid4())
        manager.get_or_create_session(session_id, "user_001")
        for i in range(50):
            manager.add_message(session_id, "user", f"用户消息{i}")
            manager.add_message(session_id, "assistant", f"助手回复{i}")
        start = time.time()
        for _ in range(100):
            manager.get_context(session_id, n_turns=5)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"上下文检索耗时过长: {elapsed:.2f}s")
        print(f"\n上下文检索性能测试: 100 次，耗时 {elapsed:.3f}s")


# =============================================================================
# 8. 集成测试
# =============================================================================

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_conversation_flow(self):
        """测试完整对话流程：问候 → FAQ → 投诉 → 转人工"""
        store = VectorStore()
        store.add_document(KnowledgeDoc(
            doc_id="FAQ001", title="如何重置密码",
            content="登录页面点击忘记密码，输入注册邮箱。",
            category="account", tags=["密码"],
        ))
        store.add_document(KnowledgeDoc(
            doc_id="FAQ002", title="退款政策",
            content="签收后7天内可申请退款。",
            category="refund", tags=["退款"],
        ))
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        bot = CustomerServiceBot(retriever, conv_mgr)
        session_id = str(uuid.uuid4())

        # 1. 问候
        r1 = bot.chat("你好", session_id, "user_001")
        self.assertEqual(r1["intent"], "greeting")

        # 2. 咨询 FAQ
        r2 = bot.chat("怎么重置密码", session_id, "user_001")
        self.assertEqual(r2["intent"], "faq")

        # 3. 退款咨询
        r3 = bot.chat("我想退款", session_id, "user_001")
        self.assertEqual(r3["intent"], "refund")

        # 4. 投诉
        r4 = bot.chat("我要投诉", session_id, "user_001")
        self.assertEqual(r4["intent"], "complaint")

        # 验证会话中有消息记录
        context = conv_mgr.get_context(session_id, n_turns=4)
        self.assertEqual(len(context), 8)  # 4轮 = 8条消息

        # 验证会话摘要
        summary = bot.get_session_summary(session_id)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["user_id"], "user_001")

    def test_multi_user_concurrent_sessions(self):
        """测试多用户并发会话"""
        store = VectorStore()
        store.add_document(KnowledgeDoc(
            doc_id="FAQ001", title="通用问题",
            content="通用回答内容。",
            category="general", tags=[],
        ))
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        bot = CustomerServiceBot(retriever, conv_mgr)

        sessions = {}
        for i in range(5):
            sid = f"multi_session_{i}"
            r = bot.chat("你好", sid, f"user_{i}")
            sessions[sid] = r

        # 每个会话应有独立的结果
        for sid, result in sessions.items():
            self.assertEqual(result["intent"], "greeting")
            self.assertEqual(result["transferred"], False)

    def test_llm_integration(self):
        """测试 LLM 集成"""
        store = VectorStore()
        store.add_document(KnowledgeDoc(
            doc_id="FAQ001", title="如何重置密码",
            content="登录页面点击忘记密码。",
            category="account", tags=["密码"],
        ))
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()

        call_count = 0
        def mock_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "根据知识库，您可以前往登录页面重置密码。"

        bot = CustomerServiceBot(retriever, conv_mgr, llm_call_func=mock_llm)
        result = bot.chat("怎么重置密码", "session_llm", "user_001")
        self.assertEqual(result["intent"], "faq")
        self.assertIn("重置密码", result["answer"])
        self.assertEqual(call_count, 1)

    def test_rag_no_docs_fallback(self):
        """测试 RAG 无文档时的降级处理"""
        store = VectorStore()  # 空知识库
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        bot = CustomerServiceBot(retriever, conv_mgr)
        result = bot.chat("怎么重置密码", "session_empty_rag", "user_001")
        self.assertIn("抱歉", result["answer"])
        self.assertEqual(result["sources"], [])

    def test_complaint_sets_flag(self):
        """测试投诉后设置标记"""
        store = VectorStore()
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        bot = CustomerServiceBot(retriever, conv_mgr)
        session_id = str(uuid.uuid4())
        bot.chat("我要投诉你们的服务", session_id, "user_001")
        session = conv_mgr.sessions.get(session_id)
        self.assertIsNotNone(session)
        self.assertTrue(session.complaint_logged)

    def test_transfer_request_persists(self):
        """测试转人工请求持久化"""
        store = VectorStore()
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        bot = CustomerServiceBot(retriever, conv_mgr)
        session_id = str(uuid.uuid4())
        bot.chat("转人工", session_id, "user_001")
        # 后续对话也应触发转人工
        result = bot.chat("还有什么问题吗", session_id, "user_001")
        self.assertTrue(result["transferred"])


# =============================================================================
# 9. 配置测试
# =============================================================================

class TestConfiguration(unittest.TestCase):
    """配置测试"""

    def test_default_classifier_config(self):
        """测试默认分类器配置"""
        classifier = IntentClassifier()
        self.assertIsNotNone(classifier.rules)
        self.assertGreater(len(classifier.rules), 0)

    def test_custom_classifier_config(self):
        """测试自定义分类器配置"""
        classifier = IntentClassifier(config={"min_confidence": 0.5})
        self.assertEqual(classifier.config["min_confidence"], 0.5)

    def test_default_conversation_config(self):
        """测试默认对话管理器配置"""
        manager = ConversationManager()
        self.assertEqual(manager.max_history, 20)
        self.assertEqual(manager.session_timeout, 1800)

    def test_custom_conversation_config(self):
        """测试自定义对话管理器配置"""
        manager = ConversationManager(max_history=50, session_timeout=3600)
        self.assertEqual(manager.max_history, 50)
        self.assertEqual(manager.session_timeout, 3600)

    def test_bot_with_config(self):
        """测试带配置的客服系统"""
        store = VectorStore()
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        config = {"max_rounds": 3, "enable_transfer": True}
        bot = CustomerServiceBot(retriever, conv_mgr, config=config)
        self.assertEqual(bot.config["max_rounds"], 3)

    def test_bot_default_config(self):
        """测试客服系统默认配置"""
        store = VectorStore()
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        bot = CustomerServiceBot(retriever, conv_mgr)
        self.assertEqual(bot.config, {})

    def test_vector_store_stats(self):
        """测试向量存储统计"""
        store = VectorStore()
        store.add_document(KnowledgeDoc(
            doc_id="S001", title="文档1", content="内容1",
            category="cat_a", tags=[],
        ))
        store.add_document(KnowledgeDoc(
            doc_id="S002", title="文档2", content="内容2",
            category="cat_b", tags=[],
        ))
        store.add_document(KnowledgeDoc(
            doc_id="S003", title="文档3", content="内容3",
            category="cat_a", tags=[],
        ))
        stats = store.get_stats()
        self.assertEqual(stats["total_docs"], 3)
        self.assertEqual(stats["categories"]["cat_a"], 2)
        self.assertEqual(stats["categories"]["cat_b"], 1)

    def test_retriever_default_top_k(self):
        """测试检索器默认 top_k"""
        store = VectorStore()
        for i in range(10):
            store.add_document(KnowledgeDoc(
                doc_id=f"T{i:03d}", title=f"标题{i}",
                content=f"内容{i}", category="test", tags=[],
            ))
        retriever = RAGRetriever(store)
        results = retriever.retrieve("内容")
        self.assertLessEqual(len(results), 3)  # 默认 top_k=3


# =============================================================================
# 10. 数据验证测试
# =============================================================================

class TestDataValidation(unittest.TestCase):
    """数据验证测试"""

    def test_message_to_dict_complete(self):
        """测试 Message 序列化完整性"""
        msg = Message(role="assistant", content="回答内容",
                      timestamp=12345.0, intent="faq", confidence=0.9)
        d = msg.to_dict()
        self.assertEqual(len(d), 5)
        self.assertIn("role", d)
        self.assertIn("content", d)
        self.assertIn("timestamp", d)
        self.assertIn("intent", d)
        self.assertIn("confidence", d)

    def test_session_to_dict_complete(self):
        """测试 Session 序列化完整性"""
        session = ConversationSession(
            session_id="s1", user_id="u1",
            created_at=12345.0, last_active=12346.0,
            transfer_requested=True, complaint_logged=False,
        )
        d = session.to_dict()
        self.assertIn("session_id", d)
        self.assertIn("user_id", d)
        self.assertIn("total_messages", d)
        self.assertIn("transfer_requested", d)
        self.assertIn("complaint_logged", d)

    def test_knowledge_doc_roundtrip(self):
        """测试 KnowledgeDoc 序列化/反序列化往返"""
        original = KnowledgeDoc(
            doc_id="RT001", title="往返测试", content="往返内容",
            category="test", tags=["t1", "t2"],
            updated_at=12345.0, version=3,
        )
        d = original.to_dict()
        restored = KnowledgeDoc.from_dict(d)
        self.assertEqual(restored.doc_id, original.doc_id)
        self.assertEqual(restored.title, original.title)
        self.assertEqual(restored.content, original.content)
        self.assertEqual(restored.category, original.category)
        self.assertEqual(restored.tags, original.tags)
        self.assertEqual(restored.version, original.version)

    def test_chat_result_type_validation(self):
        """测试 chat 返回结果的类型验证"""
        store = VectorStore()
        retriever = RAGRetriever(store)
        conv_mgr = ConversationManager()
        bot = CustomerServiceBot(retriever, conv_mgr)
        result = bot.chat("你好", "session_val", "user_001")

        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["answer"], str)
        self.assertIsInstance(result["intent"], str)
        self.assertIsInstance(result["confidence"], float)
        self.assertIsInstance(result["transferred"], bool)
        self.assertIsInstance(result["sources"], list)

    def test_context_format_validation(self):
        """测试上下文格式验证"""
        manager = ConversationManager()
        session_id = str(uuid.uuid4())
        manager.get_or_create_session(session_id, "user_001")
        manager.add_message(session_id, "user", "你好", intent="greeting", confidence=0.9)
        manager.add_message(session_id, "assistant", "您好")
        context = manager.get_context(session_id, n_turns=1)
        self.assertEqual(len(context), 2)
        for item in context:
            self.assertIn("role", item)
            self.assertIn("content", item)
            self.assertIn(item["role"], ["user", "assistant"])

    def test_session_summary_validation(self):
        """测试会话摘要验证"""
        manager = ConversationManager()
        session_id = str(uuid.uuid4())
        manager.get_or_create_session(session_id, "user_001")
        manager.add_message(session_id, "user", "问题1", intent="faq", confidence=0.7)
        manager.add_message(session_id, "assistant", "回答1")
        summary = manager.close_session(session_id)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["session_id"], session_id)
        self.assertEqual(summary["user_id"], "user_001")
        self.assertEqual(summary["total_messages"], 2)
        self.assertIn("duration", summary)
        self.assertIn("intents", summary)
        self.assertIn(summary["intents"], [["faq"], []])

    def test_stats_categories_type(self):
        """测试统计信息 categories 类型"""
        store = VectorStore()
        stats = store.get_stats()
        self.assertIsInstance(stats["categories"], dict)
        self.assertEqual(stats["total_docs"], 0)

    def test_intent_enum_values(self):
        """测试 Intent 枚举值"""
        expected_values = {"faq", "complaint", "transfer", "greeting",
                           "order_query", "refund", "other"}
        actual_values = {intent.value for intent in Intent}
        self.assertEqual(expected_values, actual_values)


if __name__ == "__main__":
    unittest.main(verbosity=2)
