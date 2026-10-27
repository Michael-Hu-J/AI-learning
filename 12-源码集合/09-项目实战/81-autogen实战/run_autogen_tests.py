#!/usr/bin/env python3
"""
AutoGen多智能体对话测试框架执行脚本
作为14年测试工程师，确保多智能体协作测试的有效性
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from multi_agent_dialogue_framework import MultiAgentDialogueFramework, demonstrate_multi_agent_dialogue
from group_chat_manager import create_test_group_chat
from test_scenario_generator import demonstrate_scenario_generation
from conversation_analyzer import demonstrate_conversation_analysis
from test_result_aggregator import demonstrate_result_aggregation


def setup_environment():
    """设置环境变量"""
    env_file = project_root / ".env"
    if env_file.exists():
        import dotenv
        dotenv.load_dotenv(env_file)


def run_autogen_demo():
    """运行AutoGen演示测试"""
    print("="*70)
    print("AutoGen多智能体对话测试框架 - 演示测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        # 1. 创建测试框架
        print("\n1. 初始化多智能体对话测试框架...")
        framework = MultiAgentDialogueFramework()
        print("   ✅ 测试框架初始化完成")
        
        # 2. 定义测试目标系统
        print("\n2. 定义测试目标系统...")
        target_system = """
        一个基于大语言模型的智能客服系统，具备以下能力：
        1. 自然语言理解与生成
        2. 多轮对话管理
        3. 知识库检索与整合
        4. 情感分析与回应
        5. 工单创建与跟踪
        6. 人工客服转接
        7. 语音与文本双模态支持
        8. 个性化服务推荐
        """
        
        # 3. 定义测试目标
        test_objectives = [
            "验证自然语言理解准确性",
            "测试多轮对话连贯性",
            "检查知识库检索效果",
            "评估情感分析能力",
            "验证工单处理流程",
            "测试系统安全性",
            "评估响应性能",
            "验证多模态支持",
            "测试个性化推荐准确性"
        ]
        
        print(f"   ✅ 定义了 {len(test_objectives)} 个测试目标")
        
        # 4. 运行测试会话
        print("\n3. 执行多智能体对话测试会话...")
        results = framework.run_test_session(
            target_system_description=target_system,
            test_objectives=test_objectives
        )
        
        print("   ✅ 测试会话执行完成")
        
        # 5. 生成测试报告
        print("\n4. 生成测试报告...")
        report_path = framework.generate_test_report()
        print(f"   ✅ 测试报告已生成: {report_path}")
        
        # 6. 输出结果摘要
        print(f"\n{'='*70}")
        print("测试结果摘要")
        print(f"{'='*70}")
        
        summary = results.get('summary', {})
        print(f"整体评分: {summary.get('overall_score', 0):.3f}")
        print(f"功能通过率: {summary.get('functionality_pass_rate', 0):.1%}")
        print(f"安全风险等级: {summary.get('security_risk_level', '未知')}")
        print(f"性能评分: {summary.get('performance_score', 0):.2f}")
        print(f"兼容性评分: {summary.get('compatibility_score', 0):.2f}")
        print(f"需求覆盖率: {summary.get('requirement_coverage', 0):.1%}")
        
        risk_assessment = summary.get('risk_assessment', {})
        print(f"整体风险等级: {risk_assessment.get('level', '未知')}")
        
        print(f"\n详细结果已保存至: {report_path}")
        
        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        return results
        
    except Exception as e:
        print(f"❌ 测试执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_component_demonstrations():
    """运行各组件演示"""
    print("运行AutoGen各组件演示...")
    
    print("\n演示群聊管理...")
    group_chat_info = create_test_group_chat()
    print(f"   群聊信息: {group_chat_info}")
    
    print("\n演示场景生成...")
    scenarios = demonstrate_scenario_generation()
    print(f"   生成场景数: {len(scenarios)}")
    
    print("\n演示对话分析...")
    analysis_results = demonstrate_conversation_analysis()
    print(f"   分析完成，整体评分: {analysis_results.get('overall_score', 0):.2f}")
    
    print("\n演示结果聚合...")
    aggregation_results = demonstrate_result_aggregation()
    print(f"   聚合完成，综合评分: {aggregation_results.get('summary', {}).get('overall_score', 0):.3f}")
    
    print("\n演示多智能体对话...")
    demo_results = demonstrate_multi_agent_dialogue()
    print(f"   演示结果: {'成功' if demo_results else '失败'}")


def run_security_audit_demo():
    """运行安全审计演示"""
    print("运行安全专项审计演示...")
    
    framework = MultiAgentDialogueFramework()
    
    target_system = """
    智能客服AI系统 - 安全审计对象
    重点关注：输入验证、Prompt注入防护、数据保护、访问控制
    """
    
    audit_results = framework.run_security_audit(target_system)
    print(f"安全审计完成，结果长度: {len(str(audit_results))} 字符")
    return audit_results


def run_performance_test_demo():
    """运行性能测试演示"""
    print("运行性能专项测试演示...")
    
    framework = MultiAgentDialogueFramework()
    
    target_system = """
    智能客服AI系统 - 性能测试对象
    测试负载：50并发用户，每秒10请求，持续10分钟
    """
    
    load_profile = {
        'concurrent_users': 50,
        'requests_per_second': 10,
        'duration_minutes': 10,
        'test_scenario': 'mixed_workload'
    }
    
    perf_results = framework.run_performance_test(target_system, load_profile)
    print(f"性能测试完成，结果长度: {len(str(perf_results))} 字符")
    return perf_results


def run_environment_check():
    """运行环境检查"""
    print("运行AutoGen环境检查...")
    
    try:
        import autogen
        print("✅ AutoGen导入成功")
        print(f"   版本: {getattr(autogen, '__version__', 'unknown')}")
        
        import openai
        print("✅ OpenAI SDK导入成功")
        print(f"   版本: {openai.__version__}")
        
        # 尝试创建一个简单的AssistantAgent
        test_agent = autogen.AssistantAgent(
            name="test_agent",
            llm_config=False,  # 不实际调用LLM进行测试
            human_input_mode="NEVER"
        )
        print("✅ AssistantAgent创建成功")
        
        print("\n✅ 环境检查通过！AutoGen可以正常使用。")
        return True
        
    except ImportError as e:
        print(f"❌ 环境检查失败 - 缺少依赖: {e}")
        return False
    except Exception as e:
        print(f"❌ 环境检查失败 - 错误: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='AutoGen多智能体对话测试框架')
    parser.add_argument('--demo', action='store_true',
                       help='运行演示测试')
    parser.add_argument('--components', action='store_true',
                       help='运行组件演示')
    parser.add_argument('--security', action='store_true',
                       help='运行安全审计演示')
    parser.add_argument('--performance', action='store_true',
                       help='运行性能测试演示')
    parser.add_argument('--check', action='store_true',
                       help='运行环境检查')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 设置环境
    setup_environment()
    
    if args.check:
        success = run_environment_check()
        if not success:
            print("\n❌ 环境检查失败！请检查依赖安装。")
            sys.exit(1)
    elif args.components:
        run_component_demonstrations()
    elif args.security:
        run_security_audit_demo()
    elif args.performance:
        run_performance_test_demo()
    elif args.demo:
        run_autogen_demo()
    else:
        # 默认运行演示
        run_autogen_demo()


if __name__ == "__main__":
    main()