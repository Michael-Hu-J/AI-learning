#!/usr/bin/env python3
"""
语法验证器 - 验证所有Python文件的语法正确性
"""

import ast
import os
import sys
from pathlib import Path

def validate_syntax(file_path):
    """验证单个文件的语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def find_python_files(root_dir):
    """查找所有Python文件"""
    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # 跳过__pycache__目录
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files

def main():
    print("🔍 Python 语法验证器")
    print("="*60)
    
    base_path = Path(__file__).resolve().parent
    
    # 定义要检查的项目
    projects = [
        "78-langgraph实战",
        "79-langchain实战", 
        "80-crewAI实战",
        "81-autogen实战"
    ]
    
    total_files = 0
    valid_files = 0
    invalid_files = []
    
    for project in projects:
        print(f"\n📋 检查项目: {project}")
        project_path = base_path / project
        
        if not project_path.exists():
            print(f"  ⚠️  项目不存在: {project_path}")
            continue
        
        # 查找该项目的所有Python文件
        py_files = []
        for root, dirs, files in os.walk(project_path):
            # 跳过__pycache__目录
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    py_files.append(Path(root) / file)
        
        project_valid = 0
        project_invalid = []
        
        for py_file in py_files:
            is_valid, error = validate_syntax(py_file)
            total_files += 1
            
            if is_valid:
                project_valid += 1
                valid_files += 1
                print(f"  ✅ {py_file.relative_to(base_path)}")
            else:
                project_invalid.append((py_file, error))
                invalid_files.append((py_file, error))
                print(f"  ❌ {py_file.relative_to(base_path)} - {error}")
        
        print(f"  总计: {len(py_files)} 个文件, {project_valid} 个有效, {len(project_invalid)} 个无效")
    
    print("\n" + "="*60)
    print("📊 验证结果摘要:")
    print(f"总文件数: {total_files}")
    print(f"有效文件: {valid_files}")
    print(f"无效文件: {len(invalid_files)}")
    
    if invalid_files:
        print("\n❌ 无效文件详情:")
        for file_path, error in invalid_files:
            print(f"  {file_path.relative_to(base_path)}: {error}")
    else:
        print("\n🎉 所有文件语法验证通过!")
    
    # 检查文档文件
    print(f"\n📄 检查文档文件...")
    md_files = list(base_path.glob("**/*.md"))
    txt_files = list(base_path.glob("**/*.txt"))
    print(f"  Markdown文档: {len(md_files)} 个")
    print(f"  配置文件: {len(txt_files)} 个")
    
    # 项目完整性检查
    print(f"\n📦 项目完整性检查:")
    for project in projects:
        proj_path = base_path / project
        if proj_path.exists():
            # 检查主文档
            main_md = list(proj_path.glob(f"{project}.md"))
            main_py = list(proj_path.glob("run_*.py"))  # 运行脚本
            
            print(f"  {project}:")
            print(f"    主文档: {'✅' if main_md else '❌'} ({len(main_md)} 个)")
            print(f"    运行脚本: {'✅' if main_py else '❌'} ({len(main_py)} 个)")
            
            # 检查依赖文件
            req_files = list(proj_path.glob("requirements.txt"))
            print(f"    依赖文件: {'✅' if req_files else '❌'} ({len(req_files)} 个)")

if __name__ == "__main__":
    main()