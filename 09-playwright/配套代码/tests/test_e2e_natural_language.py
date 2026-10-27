"""
端到端演示：自然语言 → 解析 → 适配 → 执行
完整展示从自然语言需求到浏览器操作的流程

对应文章：第2篇-执行引擎、第3篇-三层定位降级
"""
import sys
import os
import json

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from step_parser_service import step_parser_service
from nl_executor import run_nl_steps
from seckill_config import PRODUCTS_URL, SECKILL_BASE_URL


def run_e2e(natural_language: str, base_url: str = None, headless: bool = True):
    """
    端到端执行：自然语言描述 → 浏览器操作（秒杀系统）
    """
    target = base_url or PRODUCTS_URL
    print("=" * 60)
    print("  端到端演示：自然语言 → 浏览器操作")
    print("=" * 60)
    print(f"\n  输入: {natural_language}")
    print(f"  目标: {target}\n")

    print(" 第一步：解析自然语言")
    print("-" * 40)
    parsed_steps = step_parser_service.parse_description(natural_language, target)
    for i, step in enumerate(parsed_steps, 1):
        print(f"  [{i}] {step.get('skill')}: {step.get('params')} → {step.get('description')}")
    print(f"\n   解析完成：{len(parsed_steps)} 个步骤\n")

    if not parsed_steps:
        print("   没有解析到任何步骤")
        return []

    print("🌐 第二步：启动浏览器并执行")
    print("-" * 40)
    return run_nl_steps(parsed_steps, target, headless=headless, verbose=True)


def demo_login():
    """演示：登录系统"""
    print("\n" + "="*60)
    print(" 演示 1：登录系统")
    print("="*60)
    
    natural_language = "用户名：admin，密码：admin123，点击登录"
    results = run_e2e(natural_language, f"{SECKILL_BASE_URL}/login")
    return results


def demo_add_product():
    """演示：添加商品"""
    print("\n" + "="*60)
    print(" 演示 2：添加商品")
    print("="*60)
    
    natural_language = f"导航到：{PRODUCTS_URL}，点击新增商品按钮，商品名称：测试商品，价格：199.9，库存：50，点击确认添加"
    results = run_e2e(natural_language, PRODUCTS_URL)
    return results


def demo_full_flow():
    """演示：完整流程"""
    print("\n" + "="*60)
    print(" 演示 3：完整流程（登录 + 添加商品）")
    print("="*60)
    
    natural_language = (
        f"用户名：admin，密码：admin123，点击登录，导航到：{PRODUCTS_URL}，"
        "点击新增商品，商品名称：Playwright测试商品，价格：299.9，库存：100，点击确认添加"
    )
    results = run_e2e(natural_language, PRODUCTS_URL)
    return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="自然语言驱动浏览器操作演示")
    parser.add_argument('--demo', choices=['login', 'add_product', 'full_flow', 'all'],
                       default='all', help='选择演示场景')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--base-url', default=PRODUCTS_URL, help='基础URL')
    parser.add_argument('--one-liner', action='store_true', help='演示一句话：给我新增一个商品')
    parser.add_argument('--custom', type=str, help='自定义自然语言描述')
    
    args = parser.parse_args()
    
    if args.one_liner:
        run_e2e("给我新增一个商品", args.base_url, args.headless)
    elif args.custom:
        run_e2e(args.custom, args.base_url, args.headless)
    elif args.demo == 'login':
        demo_login()
    elif args.demo == 'add_product':
        demo_add_product()
    elif args.demo == 'full_flow':
        demo_full_flow()
    elif args.demo == 'all':
        demo_login()
        demo_add_product()
        demo_full_flow()


if __name__ == "__main__":
    main()
