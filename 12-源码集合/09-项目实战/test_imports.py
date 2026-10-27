#!/usr/bin/env python3
"""
测试所有项目文件的导入是否正常
此脚本用于验证代码的语法正确性和基本导入功能
"""

import sys
import os
from pathlib import Path

def test_project_imports():
    """测试各项目的导入"""
    base_path = Path(__file__).resolve().parent
    
    projects = {
        "78-langgraph实战": [
            "state_manager", "agent_test_framework", "test_scenarios", 
            "visualization", "run_tests"
        ],
        "79-langchain实战": [
            "document_loader", "embedding_validator", "retrieval_evaluator", 
            "answer_validator", "performance_tester", "rag_test_framework", 
            "run_rag_tests"
        ],
        "80-crewAI实战": [
            "agents.test_designer_agent", 
            "tasks.test_generation_task",
            "crew_manager", "test_orchestrator", 
            "multi_agent_test_framework", "run_crewai_tests"
        ],
        "81-autogen实战": [
            "agents.test_manager_agent",
            "group_chat_manager", "test_scenario_generator",
            "conversation_analyzer", "test_result_aggregator",
            "multi_agent_dialogue_framework", "run_autogen_tests"
        ]
    }
    
    results = {}
    
    for project, modules in projects.items():
        print(f"\n测试项目: {project}")
        proj_path = base_path / project
        results[project] = {"success": [], "failed": []}
        
        # 临时添加项目路径到sys.path
        original_path = sys.path[:]
        sys.path.insert(0, str(proj_path))
        
        for module in modules:
            try:
                # 处理子目录模块
                if '.' in module:
                    parts = module.split('.')
                    module_path = proj_path
                    for part in parts[:-1]:
                        module_path = module_path / part
                    module_file = module_path / f"{parts[-1]}.py"
                    if module_file.exists():
                        # 添加子目录到路径
                        sys.path.insert(0, str(module_path))
                        imported_module = __import__(parts[-1])
                        sys.path.pop(0)  # 移除临时路径
                        results[project]["success"].append(module)
                        print(f"  ✅ {module}")
                    else:
                        results[project]["failed"].append(module)
                        print(f"  ❌ {module} - 文件不存在")
                else:
                    imported_module = __import__(module)
                    results[project]["success"].append(module)
                    print(f"  ✅ {module}")
            except ImportError as e:
                results[project]["failed"].append(module)
                print(f"  ❌ {module} - 导入失败: {e}")
            except SyntaxError as e:
                results[project]["failed"].append(module)
                print(f"  ❌ {module} - 语法错误: {e}")
            except Exception as e:
                results[project]["failed"].append(module)
                print(f"  ❌ {module} - 其他错误: {e}")
        
        # 恢复原始路径
        sys.path[:] = original_path
    
    # 输出总结
    print(f"\n{'='*50}")
    print("导入测试总结:")
    print(f"{'='*50}")
    
    total_success = 0
    total_failed = 0
    
    for project, result in results.items():
        success_count = len(result["success"])
        failed_count = len(result["failed"])
        total_success += success_count
        total_failed += failed_count
        
        print(f"{project}: {success_count} 成功, {failed_count} 失败")
        if result["failed"]:
            print(f"  失败模块: {', '.join(result['failed'])}")
    
    print(f"\n总计: {total_success} 成功, {total_failed} 失败")
    
    if total_failed == 0:
        print("🎉 所有模块导入成功!")
        return True
    else:
        print("⚠️  存在导入失败的模块")
        return False

if __name__ == "__main__":
    success = test_project_imports()
    sys.exit(0 if success else 1)