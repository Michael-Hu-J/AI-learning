#!/usr/bin/env python3
"""企业知识库问答系统 CLI 入口"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.document_parser import DocumentParser, TextSplitter, KnowledgeDocument, DocStatus
from src.vector_store import VectorStore, HybridRetriever
from src.knowledge_base_qa import KnowledgeBaseQA


def setup_logging(config):
    """配置日志"""
    level = config.get("logging.level", "INFO")
    log_format = config.get("logging.format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
    )


def create_system(config):
    """创建知识库问答系统"""
    project_dir = Path(__file__).parent
    docs_path = project_dir / config.get("retrieval.docs_path", "docs")

    # 初始化文档解析器和切片器
    parser = DocumentParser()
    splitter = TextSplitter()

    # 初始化向量存储
    store = VectorStore()

    # 加载文档
    if docs_path.exists():
        load_documents(docs_path, parser, splitter, store, config)
    else:
        logging.warning(f"文档目录不存在: {docs_path}，使用内置示例")
        load_builtin_knowledge(store)

    # 构建关键词索引
    retriever = HybridRetriever(store)
    retriever.build_keyword_index()

    stats = store.get_stats()
    logging.info(f"知识库统计: {stats}")

    # 创建问答系统
    qa = KnowledgeBaseQA(retriever)
    return qa


def load_documents(docs_path, parser, splitter, store, config):
    """加载文档目录中的所有文档"""
    chunk_size = config.get("parsing.chunk_size", 500)
    chunk_overlap = config.get("parsing.chunk_overlap", 50)

    total_chunks = 0
    for file_path in docs_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in [".md", ".txt", ".html", ".htm"]:
            try:
                # 解析文档
                text = parser.parse(str(file_path))
                if not text.strip():
                    logging.warning(f"空文档: {file_path}")
                    continue

                # 切片
                chunks = splitter.split(
                    text,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    source_title=file_path.stem,
                )

                # 设置 source_doc_id 和 metadata
                for chunk in chunks:
                    chunk.source_doc_id = file_path.stem
                    chunk.metadata["file_path"] = str(file_path)
                    chunk.metadata["days_old"] = 0  # 默认最新

                # 添加到存储
                store.add_chunks(chunks)
                total_chunks += len(chunks)
                logging.info(f"加载文档: {file_path.name} -> {len(chunks)} 个切片")

            except Exception as e:
                logging.error(f"加载文档失败 {file_path}: {e}")

    logging.info(f"共加载 {total_chunks} 个切片")


def load_builtin_knowledge(store):
    """加载内置示例知识库"""
    from src.document_parser import DocumentChunk

    docs = [
        DocumentChunk(
            chunk_id="safety001", source_doc_id="safety",
            content="压力容器操作的安全距离为 3 米。操作人员必须在安全距离外进行监控和操作。",
            title="安全操作规程", metadata={"days_old": 30},
        ),
        DocumentChunk(
            chunk_id="safety002", source_doc_id="safety",
            content="操作人员必须佩戴安全帽、防护眼镜、防护手套、安全鞋等防护装备。",
            title="安全操作规程", metadata={"days_old": 30},
        ),
        DocumentChunk(
            chunk_id="hr001", source_doc_id="employee",
            content="公司实行弹性工作制，核心工作时间为 10:00-16:00。",
            title="员工手册", metadata={"days_old": 60},
        ),
        DocumentChunk(
            chunk_id="hr002", source_doc_id="employee",
            content="每月允许 3 次迟到豁免，超过后每次扣减 50 元。",
            title="员工手册", metadata={"days_old": 60},
        ),
        DocumentChunk(
            chunk_id="hr003", source_doc_id="employee",
            content="报销流程：在系统中提交报销申请，上传发票，主管审批后财务打款。",
            title="员工手册", metadata={"days_old": 60},
        ),
    ]
    store.add_chunks(docs)


def run_interactive(qa):
    """交互式问答模式"""
    print("=" * 60)
    print("企业知识库问答系统 - 交互模式")
    print("=" * 60)
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'help' 查看示例问题")
    print("-" * 60)

    while True:
        try:
            question = input("\n问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not question:
            continue

        if question.lower() in ("quit", "exit"):
            print("再见！")
            break

        if question.lower() == "help":
            print("\n示例问题:")
            print("  - 压力容器安全距离是多少")
            print("  - 公司实行什么工作制")
            print("  - 报销流程是什么")
            print("  - 怎么修电脑")
            continue

        result = qa.answer(question)
        print(f"\n回答: {result.answer}")
        print(f"置信度: {result.confidence:.3f}")
        if result.sources:
            print(f"来源: {', '.join(result.sources)}")
        if result.is_rejected:
            print("⚠️ 知识库中未找到相关信息")
        if result.quality_issues:
            print(f"⚠️ 质量问题: {', '.join(result.quality_issues)}")


def run_demo(qa):
    """演示模式 - 自动运行预设问答"""
    test_questions = [
        "压力容器安全距离是多少",
        "操作人员需要佩戴什么防护装备",
        "公司实行什么工作制",
        "报销流程是什么",
        "怎么修电脑",  # 应该被拒绝
    ]

    print("=" * 60)
    print("企业知识库问答系统 - 演示模式")
    print("=" * 60)

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*40}")
        print(f"问题 {i}: {question}")
        print(f"{'='*40}")

        result = qa.answer(question)
        print(f"回答: {result.answer}")
        print(f"置信度: {result.confidence:.3f}")
        if result.sources:
            print(f"来源: {', '.join(result.sources)}")
        if result.is_rejected:
            print("⚠️ 知识库中未找到相关信息")


def run_test(qa):
    """运行自动化测试"""
    import unittest
    from tests.test_knowledge_base_qa import TestKnowledgeBaseQA

    print("=" * 60)
    print("运行自动化测试")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestKnowledgeBaseQA)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description="企业知识库问答系统")
    parser.add_argument("--mode", choices=["interactive", "demo", "test"], default="demo",
                        help="运行模式: interactive(交互), demo(演示), test(测试)")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径")
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

    # 创建系统
    qa = create_system(config)

    # 根据模式运行
    if args.mode == "interactive":
        run_interactive(qa)
    elif args.mode == "demo":
        run_demo(qa)
    elif args.mode == "test":
        success = run_test(qa)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
