"""智能客服系统主流程 - 意图识别 + RAG 检索 + 对话管理"""

import logging
from typing import Dict, List, Optional, Callable

from .intent_classifier import IntentClassifier, Intent
from .rag_retriever import RAGRetriever, KnowledgeDoc
from .conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class CustomerServiceBot:
    """智能客服系统主类"""

    def __init__(self, retriever: RAGRetriever, conversation_mgr: ConversationManager,
                 llm_call_func: Optional[Callable] = None, config: Optional[Dict] = None):
        self.classifier = IntentClassifier()
        self.retriever = retriever
        self.conversation_mgr = conversation_mgr
        self.llm = llm_call_func
        self.config = config or {}
        logger.info("智能客服系统初始化完成")

    def chat(self, user_input: str, session_id: str, user_id: str = "anonymous") -> Dict:
        """
        处理用户输入，返回回复结果
        返回格式: {"answer": str, "intent": str, "confidence": float, "transferred": bool, "sources": list}
        """
        # 1. 获取或创建会话
        session = self.conversation_mgr.get_or_create_session(session_id, user_id)

        # 2. 意图识别
        intent, confidence = self.classifier.classify(user_input)

        # 3. 检查是否需要转人工
        if intent == Intent.TRANSFER:
            session.transfer_requested = True

        # 4. 根据意图路由处理
        answer = ""
        sources = []

        if intent == Intent.TRANSFER or self.conversation_mgr.should_transfer(session_id):
            answer = self._handle_transfer(session_id)
        elif intent == Intent.COMPLAINT:
            answer = self._handle_complaint(user_input, session_id)
        elif intent == Intent.GREETING:
            answer = "您好，我是客服助手，请问有什么可以帮您？"
        elif intent in (Intent.FAQ, Intent.ORDER_QUERY, Intent.REFUND, Intent.OTHER):
            # RAG 检索 + 生成回答
            docs = self.retriever.retrieve(user_input, top_k=3)
            sources = [d.title for d in docs]
            answer = self._generate_answer(user_input, docs, intent)

        # 5. 记录对话
        self.conversation_mgr.add_message(
            session_id, "user", user_input,
            intent=intent.value, confidence=confidence
        )
        self.conversation_mgr.add_message(session_id, "assistant", answer)

        result = {
            "answer": answer,
            "intent": intent.value,
            "confidence": round(confidence, 2),
            "transferred": self.conversation_mgr.should_transfer(session_id),
            "sources": sources,
        }
        logger.info(f"对话处理完成: intent={intent.value}, transferred={result['transferred']}")
        return result

    def _handle_transfer(self, session_id: str) -> str:
        """转人工处理"""
        return "正在为您转接人工客服，请稍候。当前排队人数：3人。"

    def _handle_complaint(self, user_input: str, session_id: str) -> str:
        """投诉处理"""
        session = self.conversation_mgr.sessions.get(session_id)
        if session:
            session.complaint_logged = True
        return "已记录您的反馈，我们会将问题转交相关部门处理，并在24小时内给您回复。"

    def _generate_answer(self, question: str, docs: List[KnowledgeDoc], intent: Intent) -> str:
        """基于检索结果生成回答"""
        if not docs:
            return "抱歉，我暂时没有找到相关信息。建议您转接人工客服。"

        # 拼接检索到的文档作为上下文
        context = "\n".join([f"- {d.title}: {d.content}" for d in docs])
        prompt = (
            f"你是一个电商客服助手。请根据以下知识库内容回答用户问题。\n"
            f"如果知识库中没有相关信息，请说'抱歉，我暂时没有找到相关信息'。\n\n"
            f"知识库内容：\n{context}\n\n"
            f"用户问题：{question}\n\n"
            f"请给出简洁、准确的回答：\n"
        )

        if self.llm:
            return self.llm(prompt)
        # 无 LLM 时返回首条检索结果
        return f"根据知识库：{docs[0].content}"

    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """获取会话摘要"""
        return self.conversation_mgr.close_session(session_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from .rag_retriever import VectorStore

    # 初始化知识库
    store = VectorStore()
    store.add_document(KnowledgeDoc(
        doc_id="FAQ001", title="如何重置密码",
        content="登录页面点击忘记密码，输入注册邮箱，系统会发送重置链接。",
        category="account", tags=["密码", "重置"],
    ))
    store.add_document(KnowledgeDoc(
        doc_id="FAQ002", title="退款政策",
        content="签收后7天内可申请退款，退款3-5个工作日原路返回。",
        category="refund", tags=["退款"],
    ))
    store.add_document(KnowledgeDoc(
        doc_id="FAQ003", title="物流查询",
        content="在订单详情页查看物流信息，或输入运单号查询。",
        category="logistics", tags=["物流", "快递"],
    ))

    retriever = RAGRetriever(store)
    conv_mgr = ConversationManager()
    bot = CustomerServiceBot(retriever, conv_mgr)

    session_id = "test_session_001"

    print("=" * 60)
    print("智能客服系统测试")
    print("=" * 60)

    # 模拟对话
    responses = [
        "我的快递怎么还没到",
        "都三天了",
        "转人工",
    ]
    for i, query in enumerate(responses):
        result = bot.chat(query, session_id, f"user_{i}")
        print(f"\n用户: {query}")
        print(f"客服: {result['answer']}")
        print(f"意图: {result['intent']} | 置信度: {result['confidence']} | 转人工: {result['transferred']}")
        if result['sources']:
            print(f"参考来源: {', '.join(result['sources'])}")
        print("-" * 40)
