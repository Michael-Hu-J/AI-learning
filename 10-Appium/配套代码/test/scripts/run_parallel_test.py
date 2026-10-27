#!/usr/bin/env python3
# run_parallel_test.py - 并行执行测试脚本（同时支持Android和iOS）
"""
并行执行测试脚本
功能：
1. 同时连接Android和iOS设备
2. 并行执行全量用例
3. 分别生成报告
"""
import sys
import os
import argparse
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import Logger

logger = Logger().get_logger()


def generate_report_name(platform: str, test_type: str) -> str:
    """生成报告名称"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{platform}_{test_type}_{timestamp}"


def check_device_connection(platform: str) -> bool:
    """检查设备连接"""
    try:
        if platform == "android":
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                devices = [line for line in lines if line.strip() and 'device' in line]
                authorized = [d for d in devices if 'device' in d and 'unauthorized' not in d]
                return len(authorized) > 0
        elif platform == "ios":
            result = subprocess.run(["tidevice", "list"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return len(result.stdout.strip().split('\n')) > 1  # 至少有一个设备
        return False
    except Exception as e:
        logger.warning(f"检查{platform}设备连接失败: {e}")
        return False


def run_test_on_platform(platform: str, test_type: str, yaml_file: str, output_dir: str, no_open: bool = True):
    """在指定平台执行测试"""
    report_name = generate_report_name(platform, test_type)
    report_dir = os.path.join(output_dir, report_name)
    
    # 设置环境变量
    env = os.environ.copy()
    env["PLATFORM"] = platform
    env["ALLURE_RESULTS_DIR"] = os.path.join(report_dir, "allure-results")
    
    # 构建命令
    cmd = [
        sys.executable,
        "scripts/run_test.py",
        "--type", test_type,
        "--platform", platform,
        "--output-dir", output_dir,
        yaml_file
    ]
    
    if no_open:
        cmd.append("--no-open")
    
    logger.info(f"开始执行 {platform.upper()} 测试: {report_name}")
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f" {platform.upper()} 测试执行成功: {report_name}")
            return True, report_dir
        else:
            logger.error(f" {platform.upper()} 测试执行失败: {report_name}")
            return False, report_dir
            
    except Exception as e:
        logger.error(f"执行 {platform.upper()} 测试时出错: {e}")
        return False, report_dir


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="并行执行测试脚本 - 同时支持Android和iOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 同时执行Android和iOS的UI测试
  python scripts/run_parallel_test.py --platforms android,ios --type ui testcases/yaml/ui_test.yaml
  
  # 同时执行所有测试类型
  python scripts/run_parallel_test.py --platforms android,ios --type hybrid testcases/yaml/test_suite.yaml
        """
    )
    
    parser.add_argument("yaml_file", nargs='?', default="testcases/yaml/test_suite_example.yaml",
                       help="YAML测试用例文件路径")
    parser.add_argument("--platforms", "-p", default="android,ios",
                       help="平台列表，用逗号分隔，如: android,ios 或 android 或 ios")
    parser.add_argument("--type", "-t", choices=["api", "ui", "visual", "hybrid"],
                       default="hybrid", help="测试类型: api(接口), ui(UI), visual(视觉对比), hybrid(混合)")
    parser.add_argument("--output-dir", default="reports", help="报告输出根目录")
    parser.add_argument("--no-open", action="store_true", help="不自动打开报告")
    
    args = parser.parse_args()
    
    # 解析平台列表
    platforms = [p.strip().lower() for p in args.platforms.split(",")]
    valid_platforms = []
    
    for platform in platforms:
        if platform not in ["android", "ios"]:
            logger.warning(f"忽略无效平台: {platform}")
            continue
        
        # 检查设备连接
        if check_device_connection(platform):
            valid_platforms.append(platform)
            logger.info(f" {platform.upper()} 设备已连接")
        else:
            logger.warning(f"  {platform.upper()} 设备未连接，跳过")
    
    if not valid_platforms:
        logger.error(" 没有可用的设备连接")
        print("\n 提示:")
        print("   1. Android: 确认设备已连接并授权USB调试 (adb devices)")
        print("   2. iOS: 确认设备已连接 (tidevice list)")
        sys.exit(1)
    
    print("=" * 70)
    print(" 并行执行测试脚本")
    print("=" * 70)
    print(f"测试类型: {args.type.upper()}")
    print(f"测试用例文件: {args.yaml_file}")
    print(f"执行平台: {', '.join([p.upper() for p in valid_platforms])}")
    print(f"报告目录: {args.output_dir}")
    print("=" * 70)
    print()
    
    # 并行执行测试
    threads = []
    results = {}
    
    for platform in valid_platforms:
        thread = threading.Thread(
            target=lambda p=platform: results.update({
                p: run_test_on_platform(p, args.type, args.yaml_file, args.output_dir, args.no_open)
            }),
            daemon=False
        )
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 打印结果
    print()
    print("=" * 70)
    print(" 并行执行结果")
    print("=" * 70)
    
    all_success = True
    for platform in valid_platforms:
        success, report_dir = results.get(platform, (False, ""))
        status = " 成功" if success else " 失败"
        print(f"{platform.upper()}: {status}")
        if report_dir:
            print(f"   报告目录: {report_dir}")
        if not success:
            all_success = False
    
    print()
    print("=" * 70)
    
    if all_success:
        print(" 所有平台测试执行完成！")
    else:
        print("  部分平台测试执行失败，请查看上述报告目录")
        sys.exit(1)


if __name__ == "__main__":
    main()

