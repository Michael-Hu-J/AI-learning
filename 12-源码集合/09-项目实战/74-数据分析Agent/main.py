#!/usr/bin/env python3
"""数据分析Agent CLI 入口"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.schema_manager import SchemaManager, TableSchema, Column
from src.sql_generator import SQLGenerator
from src.sql_validator import SQLValidator
from src.sql_executor import SQLExecutor
from src.data_analyzer import DataAnalyzer
from src.pipeline import DataAnalysisAgent


def setup_logging(config):
    level = config.get("logging.level", "INFO")
    log_format = config.get("logging.format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
    )


def create_schema_manager(config) -> SchemaManager:
    """创建 Schema 管理器"""
    mgr = SchemaManager()

    # 加载内置示例 Schema
    mgr.add_table(TableSchema(
        table_name="users",
        description="用户表",
        aliases=["用户", "用户信息"],
        columns=[
            Column("id", "INT", "用户ID", is_primary_key=True),
            Column("name", "VARCHAR(100)", "用户姓名"),
            Column("age", "INT", "年龄"),
            Column("city", "VARCHAR(50)", "所在城市"),
            Column("created_at", "DATETIME", "注册时间"),
        ],
    ))
    mgr.add_table(TableSchema(
        table_name="orders",
        description="订单表",
        aliases=["订单", "订单信息"],
        columns=[
            Column("id", "INT", "订单ID", is_primary_key=True),
            Column("user_id", "INT", "用户ID", is_foreign_key=True, references="users.id"),
            Column("product_id", "INT", "商品ID"),
            Column("price", "DECIMAL(10,2)", "单价"),
            Column("quantity", "INT", "数量"),
            Column("amount", "DECIMAL(10,2)", "总金额"),
            Column("created_at", "DATETIME", "下单时间"),
        ],
    ))

    # 尝试从文件加载
    schema_path = config.get("schema.path", "samples/schema.json")
    if Path(schema_path).exists():
        mgr.load_from_json(schema_path)

    return mgr


def create_agent(config) -> DataAnalysisAgent:
    """创建 Agent"""
    schema_mgr = create_schema_manager(config)

    # 创建 LLM 函数
    llm_func = None
    if config.get("llm.enabled", False):
        try:
            from openai import OpenAI
            api_key = config.get("llm.api_key", "")
            model = config.get("llm.model", "qwen-plus")

            def llm_call(prompt: str) -> str:
                client = OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation")
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=config.get("llm.max_tokens", 2048),
                )
                return resp.choices[0].message.content

            llm_func = llm_call
        except ImportError:
            logging.warning("openai 库未安装")

    return DataAnalysisAgent(schema_mgr, llm_func)


def demo_mode(agent: DataAnalysisAgent):
    """演示模式"""
    print("=" * 60)
    print("数据分析Agent - 演示模式")
    print("=" * 60)

    # 使用内置 mock LLM
    def mock_llm(prompt: str) -> str:
        # 从 prompt 中提取用户问题
        question = ""
        if "用户问题：" in prompt:
            question = prompt.split("用户问题：")[1].split("\n")[0]

        if "用户数" in question or "统计用户" in question:
            return "SELECT COUNT(*) AS user_count FROM users;"
        elif "最高" in question and ("销售额" in question or "top" in question.lower()):
            return "SELECT name, SUM(amount) AS total FROM orders JOIN users ON orders.user_id = users.id GROUP BY name ORDER BY total DESC LIMIT 10;"
        elif "销售额" in question or "总销售额" in question:
            return "SELECT SUM(price * quantity) AS total_sales FROM orders;"
        elif "城市" in question:
            return "SELECT city, COUNT(*) AS user_count FROM users GROUP BY city;"
        elif "所有用户" in question:
            return "SELECT * FROM users;"
        elif "DROP" in question:
            return "DROP TABLE users;"
        else:
            return "SELECT 1;"

    # 更新 agent 的 generator
    agent.generator.llm = mock_llm

    test_questions = [
        "统计用户数",
        "上个月总销售额是多少",
        "销售额最高的十个用户",
        "各城市的用户数",
        "查询所有用户",
        "DROP TABLE users",  # 危险操作
        "SELECT *; ",  # 语法错误
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\\n{'='*40}")
        print(f"问题 {i}: {question}")
        print(f"{'='*40}")

        result = agent.query(question)

        print(f"生成 SQL: {result.sql}")
        print(f"校验结果: {'✅ 通过' if result.validation.is_valid else '❌ 失败'}")
        print(f"风险等级: {result.validation.risk_level}")
        if result.validation.errors:
            print(f"错误: {', '.join(result.validation.errors)}")
        if result.validation.warnings:
            print(f"警告: {', '.join(result.validation.warnings)}")

        if result.execution:
            print(f"执行结果: {result.execution['row_count']} 行")
            for row in result.execution['rows'][:3]:
                print(f"  {row}")

        if result.analysis:
            print(f"数据摘要: {result.analysis.summary}")
            print(f"图表类型: {result.analysis.chart_type}")
            if result.analysis.anomalies:
                print(f"异常检测: {', '.join(result.analysis.anomalies)}")

        if result.error:
            print(f"错误: {result.error}")


def interactive_mode(agent: DataAnalysisAgent):
    """交互模式"""
    print("=" * 60)
    print("数据分析Agent - 交互模式")
    print("=" * 60)
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'help' 查看示例")
    print("-" * 60)

    while True:
        try:
            question = input("\\n问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\\n再见！")
            break

        if not question:
            continue

        if question.lower() in ("quit", "exit"):
            print("再见！")
            break

        if question.lower() == "help":
            print("\\n示例问题:")
            print("  - 统计用户数")
            print("  - 销售额最高的十个用户")
            print("  - 各城市的用户数")
            continue

        result = agent.query(question)

        print(f"\\n生成 SQL: {result.sql}")
        print(f"校验: {'✅' if result.validation.is_valid else '❌'} 风险: {result.validation.risk_level}")
        if result.validation.errors:
            print(f"错误: {', '.join(result.validation.errors)}")

        if result.execution:
            print(f"结果: {result.execution['row_count']} 行")
            for row in result.execution['rows'][:5]:
                print(f"  {row}")

        if result.analysis:
            print(f"摘要: {result.analysis.summary}")
            print(f"图表: {result.analysis.chart_type}")
            if result.analysis.anomalies:
                print(f"异常: {', '.join(result.analysis.anomalies)}")

        # JSON 输出
        print(f"\\n[JSON]")
        print(json.dumps({
            "question": result.question,
            "sql": result.sql,
            "valid": result.validation.is_valid,
            "risk": result.validation.risk_level,
            "errors": result.validation.errors,
            "warnings": result.validation.warnings,
            "row_count": result.execution.get("row_count", 0) if result.execution else 0,
            "summary": result.analysis.summary if result.analysis else "",
            "chart_type": result.analysis.chart_type if result.analysis else "",
        }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="数据分析Agent")
    parser.add_argument("--mode", choices=["demo", "interactive"], default="demo",
                        help="运行模式")
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

    agent = create_agent(config)

    if args.mode == "demo":
        demo_mode(agent)
    elif args.mode == "interactive":
        interactive_mode(agent)


if __name__ == "__main__":
    main()
