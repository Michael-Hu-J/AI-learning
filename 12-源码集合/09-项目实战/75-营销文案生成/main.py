#!/usr/bin/env python3
"""营销文案生成系统 CLI 入口"""

import sys
import os
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.product import ProductInfo
from src.copywriter import MarketingCopywriter


def setup_logging(config):
    """配置日志"""
    level = getattr(logging, config.log_level, logging.INFO)
    logging.basicConfig(level=level, format=config.log_format)


def run_demo():
    """演示模式"""
    config = load_config()
    setup_logging(config)
    writer = MarketingCopywriter(config)
    
    # 演示产品
    product = ProductInfo(
        name="智能保温杯",
        category="家居用品",
        price=199.00,
        original_price=299.00,
        selling_points=["24小时保温", "316不锈钢内胆", "智能温控显示", "真空隔热层"],
        target_audience="注重健康的上班族",
        usage_scenarios=["办公室", "户外", "旅行"],
        industry="food",
        brand_name="温小暖",
        description="一款采用316不锈钢的智能保温杯，内置温控芯片，可实时显示水温。",
    )
    
    print("=" * 60)
    print("📝 营销文案生成系统 - 演示模式")
    print("=" * 60)
    print(f"\n📦 产品: {product.name}")
    print(f"💰 价格: {product.price}元")
    print(f"🎯 受众: {product.target_audience}")
    print(f"💡 卖点: {', '.join(product.selling_points)}")
    
    input("\n按 Enter 生成文案...")
    result = writer.generate(product, num_versions=4)
    print(writer.print_result(result))


def run_interactive():
    """交互模式"""
    config = load_config()
    setup_logging(config)
    writer = MarketingCopywriter(config)
    
    print("=" * 60)
    print("📝 营销文案生成系统 - 交互模式")
    print("输入产品信息，按 Enter 确认，输入 q 退出")
    print("=" * 60)
    
    while True:
        print("\n--- 新产品 ---")
        name = input("产品名称: ").strip()
        if name.lower() in ("q", "quit", "exit"):
            break
        
        category = input("产品类别: ").strip()
        industry = input("行业 (healthcare/finance/food/education/other): ").strip()
        
        try:
            price = float(input("价格: ").strip() or "0")
        except ValueError:
            price = 0.0
        
        points_input = input("卖点 (逗号分隔): ").strip()
        selling_points = [p.strip() for p in points_input.split("，") if p.strip()]
        if not selling_points:
            selling_points = [points_input.replace("，", ",").split(",")[0].strip()]
        
        target = input("目标受众: ").strip()
        
        product = ProductInfo(
            name=name, category=category, price=price,
            selling_points=selling_points, target_audience=target,
            industry=industry,
        )
        
        result = writer.generate(product, num_versions=3)
        print("\n" + writer.print_result(result))
        
        input("\n按 Enter 继续...")


def run_test():
    """测试模式"""
    config = load_config()
    setup_logging(config)
    writer = MarketingCopywriter(config)
    
    print("=" * 60)
    print("📝 营销文案生成系统 - 测试模式")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # 测试用例1：正常产品
    test1 = ProductInfo(
        name="测试商品A", category="数码", price=99.00,
        selling_points=["测试卖点1", "测试卖点2"],
        industry="food",
    )
    result = writer.generate(test1, num_versions=2)
    if result.copies and any(c.text for c in result.copies):
        print(f"✅ 测试1(正常生成): 通过 ({len(result.copies)}个版本)")
        passed += 1
    else:
        print("❌ 测试1(正常生成): 失败")
        failed += 1
    
    # 测试用例2：合规检查
    test2 = ProductInfo(
        name="保健品B", category="健康", price=199.00,
        selling_points=["顶级品质", "100%纯天然"],
        industry="healthcare",
    )
    result = writer.generate(test2, num_versions=2)
    if result.compliance_report.get("compliance_rate", 0) <= 1:
        print(f"✅ 测试2(合规检查): 通过 (合规率{result.compliance_report.get('compliance_rate', 0):.0%})")
        passed += 1
    else:
        print("❌ 测试2(合规检查): 失败")
        failed += 1
    
    # 测试用例3：多版本对比
    test3 = ProductInfo(
        name="测试商品C", category="食品", price=50.00,
        selling_points=["美味", "健康"],
        industry="food",
    )
    result = writer.generate(test3, num_versions=4)
    if result.best_copy and result.best_copy.score > 0:
        print(f"✅ 测试3(多版本对比): 通过 (最佳评分{result.best_copy.score:.1f})")
        passed += 1
    else:
        print("❌ 测试3(多版本对比): 失败")
        failed += 1
    
    # 报告
    print(f"\n{'=' * 40}")
    print(f"测试完成: {passed}通过 / {failed}失败 / {passed+failed}总计")
    return 0 if failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="营销文案生成系统")
    parser.add_argument("--mode", choices=["demo", "interactive", "test"], 
                        default="demo", help="运行模式")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    args = parser.parse_args()
    
    modes = {
        "demo": run_demo,
        "interactive": run_interactive,
        "test": run_test,
    }
    
    func = modes.get(args.mode, run_demo)
    sys.exit(func())


if __name__ == "__main__":
    main()
