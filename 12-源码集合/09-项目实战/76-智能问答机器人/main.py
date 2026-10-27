#!/usr/bin/env python3
"""
=============================================================================
 main.py — 智能问答机器人入口
 作者: 测试员周周 (14年测试老兵)
 描述: 问答机器人 CLI 交互入口，支持单次查询和交互式对话
 用法:
   python main.py                           # 交互模式
   python main.py --query "怎么报名课程"     # 单次查询
   python main.py --config config.yaml      # 指定配置文件
=============================================================================
"""

import sys
import os
import argparse
import time
import logging

# 确保 src 在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config, validate_config
from src.qa_retriever import KnowledgeBase, KnowledgeDocument
from src.generator import mock_llm
from src.qa_bot import QABot, QAResult


def setup_logging(config: dict) -> None:
    """配置日志"""
    log_cfg = config.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    fmt = log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 确保日志目录存在
    log_file = log_cfg.get("file", "logs/qa_bot.log")
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8") if log_file else logging.StreamHandler(),
        ],
    )


def build_default_knowledge_base() -> KnowledgeBase:
    """
    构建默认知识库（演示用）

    生产环境中应从 data/knowledge/ 目录加载文档
    """
    kb = KnowledgeBase()
    kb.add_document(KnowledgeDocument(
        doc_id="DOC001", title="如何报名课程",
        content="登录平台后点击课程中心，选择感兴趣的课程，点击立即报名，完成支付即可。",
        category="报名", tags=["报名", "课程", "支付"],
    ))
    kb.add_document(KnowledgeDocument(
        doc_id="DOC002", title="退款政策说明",
        content="课程开通后7天内可申请全额退款，超过7天按剩余课时比例退款。退款申请将在3-5个工作日内处理。",
        category="退款", tags=["退款", "政策"],
    ))
    kb.add_document(KnowledgeDocument(
        doc_id="DOC003", title="学习技巧与建议",
        content="建议每天学习1-2小时，按时完成作业，多参与讨论。遇到问题可以随时向老师请教。",
        category="学习", tags=["学习", "技巧"],
    ))
    kb.add_document(KnowledgeDocument(
        doc_id="DOC004", title="课程分类介绍",
        content="我们平台提供编程、设计、营销、语言四大类课程。每类课程都有初级、中级、高级三个难度等级。",
        category="课程", tags=["课程", "分类", "难度"],
    ))
    kb.add_document(KnowledgeDocument(
        doc_id="DOC005", title="账号注册与登录",
        content="使用手机号或邮箱注册账号，设置密码后即可登录。支持微信和QQ第三方登录。",
        category="账号", tags=["注册", "登录", "账号"],
    ))
    return kb


def run_interactive(bot: QABot, config: dict) -> None:
    """交互式问答模式"""
    print("\n" + "=" * 50)
    print("  智能问答机器人 — 交互模式")
    print("  输入 'exit' 或 'quit' 退出")
    print("=" * 50)

    history = []
    while True:
        try:
            question = input("\n🙋 请输入问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n再见！")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            print("再见！")
            break

        print("\n🤖 思考中...", end="", flush=True)
        start = time.time()
        result = bot.answer(question)
        elapsed = time.time() - start

        print("\r" + " " * 20 + "\r", end="")  # 清除"思考中"
        print(f"\n🤖 回答: {result.answer}")

        if result.is_rejected:
            print(f"   [拒答] {result.rejection_reason}")

        print(f"   [置信度: {result.confidence:.2f} | "
              f"质量分: {result.quality_score:.2f} | "
              f"耗时: {result.elapsed_ms:.0f}ms]")

        if result.sources:
            print(f"   [来源: {', '.join(result.sources)}]")

        if result.quality_report and not result.quality_report.passed:
            print(f"   ⚠ 质量问题: {', '.join(result.quality_report.issues)}")

        history.append(result)



def run_demo(bot: QABot) -> None:
    """演示模式 — 预设问答，非交互"""
    print("\n" + "=" * 50)
    print("  智能问答机器人 — 演示模式")
    print("=" * 50)
    queries = ["怎么报名课程", "退款政策是什么", "有哪些课程分类"]
    for q in queries:
        result = bot.answer(q)
        print(f"\n问: {q}")
        print(f"答: {result.answer}")
        print(f"   confidence={result.confidence:.2f} quality={result.quality_score:.2f}")

def run_single_query(bot: QABot, query: str) -> None:
    """单次查询模式"""
    result = bot.answer(query)
    print(f"\n问题: {result.question}")
    print(f"回答: {result.answer}")
    if result.is_rejected:
        print(f"拒答原因: {result.rejection_reason}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"质量分: {result.quality_score:.2f}")
    print(f"来源: {', '.join(result.sources) if result.sources else '无'}")
    print(f"耗时: {result.elapsed_ms:.0f}ms")


def main():
    parser = argparse.ArgumentParser(description="智能问答机器人")
    parser.add_argument("--demo", action="store_true", help="演示模式（非交互）")
    parser.add_argument("--query", "-q", type=str, default="",
                        help="单次查询模式（不传则进入交互模式）")
    parser.add_argument("--config", "-c", type=str, default="",
                        help="配置文件路径")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config if args.config else None)
    if args.debug:
        config.setdefault("logging", {})["level"] = "DEBUG"
    if not validate_config(config):
        print("⚠ 配置校验有警告，继续使用...")

    setup_logging(config)
    logger = logging.getLogger("main")
    logger.info("智能问答机器人启动 (version=%s)", config.get("app", {}).get("version", "1.0.0"))

    # 构建知识库
    kb = build_default_knowledge_base()
    logger.info("知识库加载完成，共 %d 篇文档", kb.document_count())

    # 初始化机器人
    bot = QABot(
        knowledge_base=kb,
        llm_call_func=mock_llm,
        config=config,
    )

    # 运行模式选择
    if args.query:
        run_single_query(bot, args.query)
    elif args.demo:
        run_demo(bot)
    else:
        run_interactive(bot, config)


if __name__ == "__main__":
    main()
