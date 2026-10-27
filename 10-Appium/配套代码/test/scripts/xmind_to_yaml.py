#!/usr/bin/env python3
# xmind_to_yaml.py - XMind转YAML脚本
"""
XMind转YAML转换脚本
用法: python scripts/xmind_to_yaml.py <xmind_file> [output_yaml]
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.xmind_parser import XMindParser
from utils.logger import Logger

logger = Logger().get_logger()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python scripts/xmind_to_yaml.py <xmind_file> [output_yaml]")
        print("示例: python scripts/xmind_to_yaml.py testcases/xmind/test.xmind testcases/yaml/test.yaml")
        sys.exit(1)
    
    xmind_file = sys.argv[1]
    
    # 如果没有指定输出文件，自动生成
    if len(sys.argv) >= 3:
        output_yaml = sys.argv[2]
    else:
        # 自动生成输出文件名
        base_name = os.path.splitext(os.path.basename(xmind_file))[0]
        output_dir = os.path.join(os.path.dirname(os.path.dirname(xmind_file)), "yaml")
        os.makedirs(output_dir, exist_ok=True)
        output_yaml = os.path.join(output_dir, f"{base_name}.yaml")
    
    try:
        parser = XMindParser()
        parser.parse_to_yaml(xmind_file, output_yaml)
        print(f" 转换成功！")
        print(f"   XMind: {xmind_file}")
        print(f"   YAML:  {output_yaml}")
    except Exception as e:
        logger.error(f"转换失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

