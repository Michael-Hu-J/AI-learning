#!/usr/bin/env python3
"""
LangGraph AI Agent测试框架执行脚本
作为14年测试工程师，确保测试的严谨性和可重复性
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agent_test_framework import AgentTestFramework
from test_scenarios import TestScenarioCollection, run_langgraph_tests
from visualization import visualize_test_execution
from state_manager import AgentState


def setup_environment():
    """设置环境变量"""
    env_file = project_root / ".env"
    if env_file.exists():
        import dotenv
        dotenv.load_dotenv(env_file)


def run_comprehensive_tests():
    """运行综合测试"""
    print("="*60)
    print("LangGraph AI Agent 测试框架 - 综合测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 初始化测试框架
    print("\n1. 初始化测试框架...")
    demo = not (os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY"))
    if demo:
        print("   ℹ️  未检测到 OPENAI_API_KEY，使用演示模式")
    framework = AgentTestFramework(demo_mode=demo)
    print("   ✅ 测试框架初始化完成")
    
    # 加载测试场景
    print("\n2. 加载测试场景...")
    scenarios = TestScenarioCollection()
    scenario_count = len(scenarios.get_all_scenarios())
    print(f"   ✅ 加载了 {scenario_count} 个测试场景")
    
    # 执行测试
    print("\n3. 执行测试用例...")
    results = []
    
    for i, scenario in enumerate(scenarios.get_all_scenarios()):
        print(f"\n   场景 {i+1}/{scenario_count}: {scenario.name}")
        print(f"   描述: {scenario.description}")
        
        for j, test_case in enumerate(scenario.test_cases):
            print(f"     用例 {j+1}: {test_case.get('input', 'N/A')[:50]}...")
            
            try:
                session_id = framework.state_manager.initialize_state()
                result = framework.run_test_scenario(session_id, test_case["input"])
                
                overall_result = result['test_results']['overall']
                status = "✅ PASS" if overall_result['passed'] else "❌ FAIL"
                score = overall_result['score']
                
                print(f"       结果: {status}, 分数: {score:.2f}")
                
                results.append({
                    'scenario': scenario.name,
                    'test_case': j+1,
                    'passed': overall_result['passed'],
                    'score': score,
                    'errors': result['validation_errors']
                })
                
            except Exception as e:
                print(f"       错误: {str(e)}")
                results.append({
                    'scenario': scenario.name,
                    'test_case': j+1,
                    'passed': False,
                    'score': 0.0,
                    'errors': [str(e)]
                })
    
    # 生成测试报告
    print("\n4. 生成测试报告...")
    passed_count = sum(1 for r in results if r['passed'])
    total_count = len(results)
    overall_score = sum(r['score'] for r in results) / total_count if total_count > 0 else 0
    
    print(f"\n{'='*60}")
    print("测试报告摘要")
    print(f"{'='*60}")
    print(f"总测试用例数: {total_count}")
    print(f"通过数量: {passed_count}")
    print(f"失败数量: {total_count - passed_count}")
    print(f"通过率: {(passed_count/total_count)*100:.1f}%" if total_count > 0 else "N/A")
    print(f"平均分数: {overall_score:.2f}")
    
    # 显示失败详情
    failed_results = [r for r in results if not r['passed']]
    if failed_results:
        print(f"\n失败详情:")
        for r in failed_results:
            print(f"  - 场景: {r['scenario']}, 用例: {r['test_case']}")
            for error in r['errors']:
                print(f"    错误: {error}")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    return results


def run_single_test(input_text: str):
    """运行单个测试"""
    print(f"执行单个测试: {input_text}")
    
    framework = AgentTestFramework(demo_mode=not os.getenv("OPENAI_API_KEY"))
    session_id = framework.state_manager.initialize_state()
    result = framework.run_test_scenario(session_id, input_text)
    
    print(f"测试结果: {result['test_results']['overall']}")
    print(f"Agent响应: {result['agent_response']}")
    
    # 可视化结果
    try:
        visualize_test_execution(result)
    except ImportError:
        print("注意: 无法生成可视化图表，缺少matplotlib或networkx依赖")
    
    return result


def main():
    parser = argparse.ArgumentParser(description='LangGraph AI Agent测试框架')
    parser.add_argument('--single', '-s', type=str, 
                       help='执行单个测试用例的输入文本')
    parser.add_argument('--demo', action='store_true',
                       help='运行演示测试')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 设置环境
    setup_environment()
    
    if args.single:
        # 执行单个测试
        run_single_test(args.single)
    elif args.demo:
        # 运行演示
        print("运行LangGraph测试演示...")
        run_langgraph_tests()
    else:
        # 运行综合测试
        run_comprehensive_tests()


if __name__ == "__main__":
    main()