#!/usr/bin/env python3
"""代码生成助手 CLI 入口"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.code_context import CodeContextManager
from src.code_generator import CodeGenerator, CodeGenerationResult
from src.code_quality import CodeQualityChecker
from src.test_generator import TestGenerator
from src.pipeline import CodeAssistantPipeline


def setup_logging(config):
    level = config.get("logging.level", "INFO")
    log_format = config.get("logging.format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
    )


def create_llm_func(config):
    """创建 LLM 调用函数"""
    if not config.get("llm.enabled", False):
        return None

    try:
        from openai import OpenAI
        api_key = config.get("llm.api_key", "")
        model = config.get("llm.model", "qwen-plus")
        max_tokens = config.get("llm.max_tokens", 4096)

        def llm_call(prompt: str) -> str:
            client = OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation")
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content

        return llm_call
    except ImportError:
        logging.warning("openai 库未安装，无法启用 LLM")
        return None


def demo_mode(pipeline: CodeAssistantPipeline):
    """演示模式"""
    print("=" * 60)
    print("代码生成助手 - 演示模式")
    print("=" * 60)

    # 内置模拟 LLM
    def mock_llm(prompt: str) -> str:
        if "数据迁移" in prompt:
            return '''import sqlite3
from typing import List, Dict

def migrate_data(source_db: str, target_db: str, table_name: str) -> int:
    """从源数据库迁移数据到目标数据库"""
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)

    try:
        cursor = source_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        target_cursor = target_conn.cursor()
        migrated = 0
        for row in rows:
            target_cursor.execute(
                f"INSERT OR IGNORE INTO {table_name} VALUES ({','.join(['?'] * len(row))})", row
            )
            migrated += 1

        target_conn.commit()
        return migrated
    finally:
        source_conn.close()
        target_conn.close()
'''
        elif "字符串处理" in prompt:
            return '''def count_words(text: str) -> Dict[str, int]:
    """统计字符串中每个单词的出现次数"""
    words = text.lower().split()
    result = {}
    for word in words:
        result[word] = result.get(word, 0) + 1
    return result

def find_longest_word(text: str) -> str:
    """找到字符串中最长的单词"""
    words = text.split()
    if not words:
        return ""
    return max(words, key=len)
'''
        else:
            return '''def hello():
    """返回问候语"""
    return "Hello, World!"
'''

    # 替换 pipeline 的 LLM
    pipeline.generator.llm = mock_llm
    pipeline.test_generator.llm = mock_llm

    test_cases = [
        "编写一个数据迁移脚本，从源 SQLite 数据库迁移数据到目标数据库",
        "编写一个字符串处理函数，统计单词出现次数并找到最长单词",
    ]

    for i, desc in enumerate(test_cases, 1):
        print(f"\\n{'='*40}")
        print(f"需求 {i}: {desc}")
        print(f"{'='*40}")

        result = pipeline.process(desc)

        print(f"\\n生成代码:")
        print(f"{'-'*40}")
        print(result.code[:500])
        if len(result.code) > 500:
            print(f"... (共 {len(result.code)} 字符)")
        print(f"{'-'*40}")

        print(f"语法检查: {'✅ 通过' if result.syntax_valid else '❌ 失败'}")
        print(f"安全问题: {len(result.security_issues)} 个")
        for issue in result.security_issues:
            print(f"  ⚠️ {issue}")
        print(f"质量评分: {result.quality_score:.0f}/100")
        if result.errors:
            print(f"错误信息: {len(result.errors)} 个")
            for err in result.errors:
                print(f"  ❌ {err}")


def interactive_mode(pipeline: CodeAssistantPipeline):
    """交互模式"""
    print("=" * 60)
    print("代码生成助手 - 交互模式")
    print("=" * 60)
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'help' 查看示例")
    print("-" * 60)

    while True:
        try:
            desc = input("\\n需求: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\\n再见！")
            break

        if not desc:
            continue

        if desc.lower() in ("quit", "exit"):
            print("再见！")
            break

        if desc.lower() == "help":
            print("\\n示例需求:")
            print("  - 编写一个数据迁移脚本")
            print("  - 编写一个字符串处理函数")
            print("  - 编写一个文件读取工具")
            continue

        result = pipeline.process(desc)

        print(f"\\n生成代码:")
        print(f"{'-'*40}")
        print(result.code[:800])
        if len(result.code) > 800:
            print(f"... (共 {len(result.code)} 字符)")
        print(f"{'-'*40}")

        print(f"语法检查: {'✅ 通过' if result.syntax_valid else '❌ 失败'}")
        print(f"安全问题: {len(result.security_issues)} 个")
        for issue in result.security_issues:
            print(f"  ⚠️ {issue}")
        print(f"质量评分: {result.quality_score:.0f}/100")
        if result.errors:
            print(f"错误: {len(result.errors)} 个")
            for err in result.errors:
                print(f"  ❌ {err}")

        # 输出 JSON 结果
        print(f"\\n[JSON 结果]")
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2)[:500])


def main():
    parser = argparse.ArgumentParser(description="代码生成助手")
    parser.add_argument("--mode", choices=["demo", "interactive"], default="demo",
                        help="运行模式")
    parser.add_argument("--project", type=str, default=None,
                        help="项目根目录（用于上下文检索）")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径")
    parser.add_argument("--debug", action="store_true",
                        help="启用调试模式")

    args = parser.parse_args()

    config = load_config(args.config)
    if args.debug:
        config._config["app"]["debug"] = True
        config._config["logging"]["level"] = "DEBUG"

    setup_logging(config)

    llm_func = create_llm_func(config)
    pipeline = CodeAssistantPipeline(llm_func, project_root=args.project)

    if args.mode == "demo":
        demo_mode(pipeline)
    elif args.mode == "interactive":
        interactive_mode(pipeline)


if __name__ == "__main__":
    main()
