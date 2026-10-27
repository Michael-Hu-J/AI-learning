#!/usr/bin/env python3
"""智能客服系统 CLI 入口"""

import sys
import os
import uuid
import argparse
import logging
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.intent_classifier import IntentClassifier
from src.rag_retriever import VectorStore, RAGRetriever, KnowledgeDoc
from src.conversation_manager import ConversationManager
from src.customer_service_bot import CustomerServiceBot


def setup_logging(config):
    """配置日志"""
    level = config.get("logging.level", "INFO")
    log_format = config.get("logging.format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
    )


def create_bot(config, knowledge_base_path=None):
    """创建客服机器人实例"""
    # 初始化向量存储
    store = VectorStore()

    # 加载知识库 - 优先使用项目目录下的 data/ 路径
    project_dir = Path(__file__).parent
    kb_path = knowledge_base_path or config.get("retrieval.knowledge_base_path", "data/knowledge_base.json")

    # 尝试多个路径
    possible_paths = [
        Path(kb_path),  # 绝对路径或当前工作目录
        project_dir / kb_path,  # 项目目录下
        project_dir / "data" / "knowledge_base.json",  # 默认路径
    ]

    loaded = False
    for path in possible_paths:
        if path.exists():
            store.load_from_json(str(path))
            loaded = True
            break

    if not loaded:
        # 使用内置示例知识库
        logging.warning("知识库文件不存在，使用内置示例")
        _load_builtin_knowledge(store)

    stats = store.get_stats()
    logging.info(f"知识库统计: {stats}")

    # 初始化检索器和对话管理器
    retriever = RAGRetriever(store)
    conv_mgr = ConversationManager(
        max_history=config.get("conversation.max_history", 20),
        session_timeout=config.get("conversation.session_timeout", 1800),
    )

    # 初始化客服机器人
    bot = CustomerServiceBot(retriever, conv_mgr)
    return bot


def _load_builtin_knowledge(store):
    """加载内置示例知识库"""
    docs = [
        KnowledgeDoc(doc_id="FAQ001", title="如何重置密码",
                     content="登录页面点击忘记密码，输入注册邮箱，系统会发送重置链接。",
                     category="account", tags=["密码", "重置"]),
        KnowledgeDoc(doc_id="FAQ002", title="退款政策",
                     content="签收后7天内可申请退款，退款3-5个工作日原路返回。",
                     category="refund", tags=["退款"]),
        KnowledgeDoc(doc_id="FAQ003", title="物流查询",
                     content="在订单详情页查看物流信息，或输入运单号查询。",
                     category="logistics", tags=["物流", "快递"]),
        KnowledgeDoc(doc_id="FAQ004", title="如何修改收货地址",
                     content="订单未发货前可在订单详情页修改收货地址。",
                     category="order", tags=["地址", "修改"]),
        KnowledgeDoc(doc_id="FAQ005", title="优惠券使用方法",
                     content="下单时在结算页面选择可用优惠券。",
                     category="promotion", tags=["优惠券"]),
    ]
    for doc in docs:
        store.add_document(doc)


def run_interactive(bot, config):
    """交互式对话模式"""
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    user_id = "interactive_user"

    print("=" * 60)
    print("智能客服系统 - 交互模式")
    print("=" * 60)
    print("输入 'quit' 或 'exit' 退出对话")
    print("输入 'session' 查看当前会话信息")
    print("输入 'clear' 清空对话历史")
    print("-" * 60)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            summary = bot.get_session_summary(session_id)
            if summary:
                print(f"\n会话摘要: {json.dumps(summary, ensure_ascii=False, indent=2)}")
            print("再见！")
            break

        if user_input.lower() == "session":
            print(f"会话 ID: {session_id}")
            print(f"用户 ID: {user_id}")
            continue

        if user_input.lower() == "clear":
            summary = bot.get_session_summary(session_id)
            if summary:
                print(f"已关闭会话: {summary['total_messages']} 条消息")
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            print("已创建新会话")
            continue

        result = bot.chat(user_input, session_id, user_id)
        print(f"\n客服: {result['answer']}")
        print(f"意图: {result['intent']} | 置信度: {result['confidence']}")
        if result.get('sources'):
            print(f"参考: {', '.join(result['sources'])}")
        if result['transferred']:
            print("⚠️ 已触发转人工")


def run_demo(bot):
    """演示模式 - 自动运行预设对话"""
    session_id = "demo_session"
    user_id = "demo_user"

    test_conversations = [
        ["你好", "我想查快递", "我的快递到哪了", "都三天了还没到", "转人工"],
        ["你好", "怎么重置密码", "好的谢谢"],
        ["我要投诉", "退款怎么操作"],
    ]

    print("=" * 60)
    print("智能客服系统 - 演示模式")
    print("=" * 60)

    for i, conversation in enumerate(test_conversations, 1):
        print(f"\n{'='*40}")
        print(f"对话场景 {i}")
        print(f"{'='*40}")

        for user_input in conversation:
            result = bot.chat(user_input, session_id, user_id)
            print(f"\n用户: {user_input}")
            print(f"客服: {result['answer']}")
            print(f"  意图: {result['intent']} | 置信度: {result['confidence']} | 转人工: {result['transferred']}")

        # 关闭当前会话
        summary = bot.get_session_summary(session_id)
        if summary:
            print(f"\n会话结束: {summary['total_messages']} 条消息, 时长: {summary['duration']}s")

        # 重置会话
        session_id = f"demo_session_{i+1}"


def run_test(bot):
    """运行自动化测试"""
    import unittest
    from tests.test_customer_service_bot import TestCustomerServiceBot

    print("=" * 60)
    print("运行自动化测试")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCustomerServiceBot)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description="智能客服系统")
    parser.add_argument("--mode", choices=["interactive", "demo", "test"], default="demo",
                        help="运行模式: interactive(交互), demo(演示), test(测试)")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径")
    parser.add_argument("--knowledge-base", type=str, default=None,
                        help="知识库文件路径")
    parser.add_argument("--debug", action="store_true",
                        help="启用调试模式")

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)
    if args.debug:
        config._config["app"]["debug"] = True
        config._config["logging"]["level"] = "DEBUG"

    # 设置日志
    setup_logging(config)

    # 创建机器人
    bot = create_bot(config, args.knowledge_base)

    # 根据模式运行
    if args.mode == "interactive":
        run_interactive(bot, config)
    elif args.mode == "demo":
        run_demo(bot)
    elif args.mode == "test":
        success = run_test(bot)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
