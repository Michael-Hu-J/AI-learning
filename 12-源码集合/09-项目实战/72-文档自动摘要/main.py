#!/usr/bin/env python3
"""文档自动摘要系统 CLI 入口"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.document_parser import DocumentParser
from src.extractive_summarizer import ExtractiveSummarizer
from src.generative_summarizer import GenerativeSummarizer
from src.summary_evaluator import SummaryEvaluator


def setup_logging(config):
    level = config.get("logging.level", "INFO")
    log_format = config.get("logging.format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
    )


def read_document(filepath: str) -> str:
    """读取文档文件"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    ext = path.suffix.lower()
    if ext in (".md", ".txt", ".html", ".htm"):
        for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                with open(path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法解码文件: {filepath}")
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def create_system(config):
    parser = DocumentParser()
    extractor = ExtractiveSummarizer(
        damping=config.get("extractive.damping", 0.85),
        iterations=config.get("extractive.iterations", 50),
    )

    # 生成式摘要（如果配置了 LLM）
    generator = None
    if config.get("generative.enabled", False):
        from openai import OpenAI

        api_key = config.get("generative.api_key", "")
        model = config.get("generative.model", "qwen-plus")
        base_url = config.get("generative.base_url",
                              "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation")

        def llm_call(prompt: str) -> str:
            client = OpenAI(api_key=api_key, base_url=base_url)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content

        generator = GenerativeSummarizer(
            llm_call_func=llm_call,
            max_chunk_size=config.get("generative.max_chunk_size", 2000),
            max_summary_length=config.get("generative.max_summary_length", 500),
        )

    evaluator = SummaryEvaluator()
    return parser, extractor, generator, evaluator


def sample_demo(extractor, generator, evaluator):
    """演示模式 - 使用内置示例文本"""
    text = """人工智能（Artificial Intelligence，简称 AI）是计算机科学的一个分支，
用于开发能够模拟人类智能行为的系统。自 1956 年达特茅斯会议首次提出"人工智能"概念以来，
该领域经历了多次发展浪潮。

机器学习是人工智能的核心技术之一。2012 年，深度学习在图像识别领域取得突破性进展，
AlexNet 在 ImageNet 竞赛中将错误率从 26% 降低到 15%。此后，深度学习在语音识别、
自然语言处理、机器翻译等领域相继取得重大突破。

2017 年，Google 提出了 Transformer 架构，彻底改变了自然语言处理领域。
基于 Transformer 的 BERT、GPT 等模型在多项 NLP 任务上刷新了记录。
2022 年，ChatGPT 的发布引发了全球对大语言模型的关注。

大语言模型的核心能力包括：文本生成、问答、摘要、翻译、代码生成等。
这些模型通过在海量文本数据上进行预训练，学习语言的统计规律和语义表示。
GPT-4 在多项基准测试中达到或超过了人类水平的表现。"""

    print("=" * 60)
    print("原始文本")
    print("=" * 60)
    print(text[:200] + "...\n")

    # 抽取式摘要
    print("=" * 60)
    print("抽取式摘要 (TextRank)")
    print("=" * 60)
    extractive_result = extractor.summarize(text, summary_ratio=0.3)
    print(extractive_result)
    print(f"\n原文字数: {len(text)} | 摘要字数: {len(extractive_result)} | 压缩比: {len(extractive_result)/len(text):.1%}")

    # 质量评估
    print("\n" + "=" * 60)
    print("摘要质量评估")
    print("=" * 60)
    results = evaluator.evaluate(text, extractive_result)
    for metric, value in results.items():
        print(f"{metric}: {value}")

    # 生成式摘要（如果可用）
    if generator and generator.llm:
        print("\n" + "=" * 60)
        print("生成式摘要 (LLM)")
        print("=" * 60)
        generative_result = generator.summarize(text)
        print(generative_result)
        print(f"\n摘要字数: {len(generative_result)} | 压缩比: {len(generative_result)/len(text):.1%}")


def file_mode(parser, extractor, evaluator, filepath: str, ratio: float):
    """文件模式 - 对指定文件生成摘要"""
    text = read_document(filepath)

    print(f"=== 文档: {filepath} ===")
    print(f"原文长度: {len(text)} 字")
    print()

    # 解析
    chunks = parser.split_into_chunks(text)

    # 抽取式摘要
    summary = extractor.summarize(text, summary_ratio=ratio)
    print("=== 抽取式摘要 ===")
    print(summary)
    print(f"\n摘要长度: {len(summary)} 字 | 压缩比: {len(summary)/len(text):.1%}")

    # 质量评估
    print("\n=== 质量评估 ===")
    results = evaluator.evaluate(text, summary)
    for metric, value in results.items():
        print(f"  {metric}: {value}")


def main():
    parser_cli = argparse.ArgumentParser(description="文档自动摘要系统")
    parser_cli.add_argument("--mode", choices=["demo", "file"], default="demo",
                            help="运行模式")
    parser_cli.add_argument("--file", type=str, default=None,
                            help="待摘要的文档路径")
    parser_cli.add_argument("--ratio", type=float, default=0.2,
                            help="摘要压缩比 (默认: 0.2)")
    parser_cli.add_argument("--config", type=str, default=None,
                            help="配置文件路径")
    parser_cli.add_argument("--debug", action="store_true",
                            help="启用调试模式")
    parser_cli.add_argument("--output", type=str, default=None,
                            help="输出结果到 JSON 文件")

    args = parser_cli.parse_args()

    config = load_config(args.config)
    if args.debug:
        config._config["app"]["debug"] = True
        config._config["logging"]["level"] = "DEBUG"

    setup_logging(config)

    parser, extractor, generator, evaluator = create_system(config)

    if args.mode == "demo":
        sample_demo(extractor, generator, evaluator)
    elif args.mode == "file":
        if not args.file:
            print("错误: --file 参数必须提供")
            sys.exit(1)
        file_mode(parser, extractor, evaluator, args.file, args.ratio)


if __name__ == "__main__":
    main()
