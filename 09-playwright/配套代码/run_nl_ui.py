#!/usr/bin/env python3
"""
一句话驱动秒杀系统 UI 自动化。

示例:
  python run_nl_ui.py "给我新增一个商品"
  python run_nl_ui.py "给我新增一个商品，商品名称：春节礼盒，价格：199，库存：50"
  python run_nl_ui.py --no-headless "查询商品"
"""
import argparse
import sys

from nl_executor import run_nl_command
from seckill_config import PRODUCTS_URL, SECKILL_BASE_URL


def main() -> int:
    parser = argparse.ArgumentParser(description="自然语言驱动秒杀系统 UI（真实浏览器 + 真实数据库）")
    parser.add_argument("text", nargs="?", default="给我新增一个商品", help="自然语言指令")
    parser.add_argument("--base-url", default=PRODUCTS_URL, help=f"业务系统地址，默认 {SECKILL_BASE_URL}")
    parser.add_argument("--no-headless", action="store_true", help="显示浏览器窗口")
    parser.add_argument(
        "--parser",
        choices=["auto", "llm", "regex"],
        default=None,
        help="拆分方式：auto=有 API Key 用 LLM；llm=强制 LLM；regex=仅规则",
    )
    args = parser.parse_args()

    if args.parser:
        import os

        os.environ["NL_PARSER"] = args.parser

    results = run_nl_command(
        args.text,
        base_url=args.base_url,
        headless=not args.no_headless,
        verbose=True,
    )
    failed = [r for r in results if r.get("status") != "passed"]
    if failed:
        print("\n 执行未全部通过，请检查业务系统是否在运行:", SECKILL_BASE_URL)
        return 1
    print("\n 全部步骤通过。请在浏览器打开商品管理页查看真实数据:", args.base_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
