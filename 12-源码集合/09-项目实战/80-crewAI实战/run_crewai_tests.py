#!/usr/bin/env python3
"""
CrewAI多智能体测试框架执行脚本
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

from multi_agent_test_framework import MultiAgentTestFramework, demonstrate_multi_agent_testing
from crew_manager import create_test_crew
from test_orchestrator import demonstrate_orchestration


def setup_environment():
    """设置环境变量"""
    env_file = project_root / ".env"
    if env_file.exists():
        import dotenv
        dotenv.load_dotenv(env_file)


def run_crewai_demo():
    """运行CrewAI演示测试"""
    print("="*70)
    print("CrewAI多智能体测试框架 - 演示测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        # 1. 创建测试框架
        print("\n1. 初始化多智能体测试框架...")
        framework = MultiAgentTestFramework(verbose=True)
        print("   ✅ 测试框架初始化完成")
        
        # 2. 定义测试目标系统
        print("\n2. 定义测试目标系统...")
        target_system = """
        一个基于大语言模型的客户服务机器人系统，具备以下功能：
        1. 理解客户问题
        2. 提供产品信息查询
        3. 处理订单状态查询
        4. 协助退换货流程
        5. 转接人工客服
        6. 情感分析和回应
        """
        
        # 3. 定义测试需求
        test_requirements = [
            "验证客户服务机器人的问题理解能力",
            "测试产品信息查询功能的准确性",
            "检查订单状态查询的响应速度",
            "验证退换货流程的引导准确性",
            "确认人工客服转接功能正常",
            "评估情感分析的准确性",
            "测试多轮对话的上下文保持能力"
        ]
        
        # 4. 定义测试场景
        test_scenarios = [
            {
                "name": "产品咨询场景",
                "description": "客户询问产品特性",
                "inputs": ["这款手机的电池续航怎么样？", "支持快充吗？", "有几种颜色可选？"],
                "expected_outcomes": ["提供准确的产品信息", "推荐相关配件", "引导购买决策"]
            },
            {
                "name": "订单查询场景", 
                "description": "客户查询订单状态",
                "inputs": ["我的订单Z123456789什么时候发货？", "可以修改收货地址吗？"],
                "expected_outcomes": ["显示准确的订单状态", "提供预计送达时间", "允许合法的地址修改"]
            },
            {
                "name": "投诉处理场景",
                "description": "客户表达不满情绪",
                "inputs": ["你们的服务太差了，我要投诉！", "这个问题已经出现好几次了"],
                "expected_outcomes": ["识别负面情绪", "表达歉意", "转接人工客服", "记录投诉信息"]
            }
        ]
        
        print(f"   ✅ 定义了 {len(test_requirements)} 个测试需求")
        print(f"   ✅ 定义了 {len(test_scenarios)} 个测试场景")
        
        # 5. 执行测试活动
        print("\n3. 执行多智能体测试活动...")
        results = framework.run_test_campaign(
            target_system_description=target_system,
            test_requirements=test_requirements,
            test_scenarios=test_scenarios
        )
        
        print("   ✅ 测试活动执行完成")
        
        # 6. 生成测试报告
        print("\n4. 生成测试报告...")
        report_path = framework.generate_test_report()
        print(f"   ✅ 测试报告已生成: {report_path}")
        
        # 7. 输出结果摘要
        print(f"\n{'='*70}")
        print("测试结果摘要")
        print(f"{'='*70}")
        
        summary = results.get('summary', {})
        print(f"总任务数: {summary.get('total_tasks', 0)}")
        print(f"完成任务: {summary.get('completed_tasks', 0)}")
        print(f"成功率: {summary.get('success_rate', 0):.1%}")
        print(f"严重问题: {summary.get('critical_issues', 0)}")
        print(f"警告数量: {summary.get('warnings', 0)}")
        
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
    print("运行CrewAI各组件演示...")
    
    print("\n演示智能体编队管理...")
    crew_info = create_test_crew()
    print(f"   编队信息: {crew_info}")
    
    print("\n演示测试编排...")
    orchestration_info = demonstrate_orchestration()
    print(f"   编排信息: {orchestration_info}")
    
    print("\n演示多智能体测试...")
    demo_results = demonstrate_multi_agent_testing()
    print(f"   演示结果: {'成功' if demo_results else '失败'}")


def run_simple_test():
    """运行简单测试以验证环境"""
    print("运行简单测试验证环境...")
    
    try:
        import sys
        from pathlib import Path
        _root = Path(__file__).resolve().parent.parent
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        import llm_env

        print("✅ LangChain OpenAI导入成功")
        
        from crewai import Agent, Task, Crew
        print("✅ CrewAI导入成功")
        
        llm = llm_env.create_chat_openai()
        print(f"✅ LLM 配置: {llm_env.get_llm_model()} @ DashScope")
        
        # 创建一个简单的测试代理
        test_agent = Agent(
            role='测试代理',
            goal='验证环境配置',
            backstory='我是用来验证CrewAI环境是否正确配置的测试代理',
            verbose=True,
            llm=llm
        )
        
        print("✅ 测试代理创建成功")
        
        # 创建一个简单的测试任务
        test_task = Task(
            description='验证CrewAI环境配置是否正确',
            expected_output='环境配置验证结果',
            agent=test_agent
        )
        
        print("✅ 测试任务创建成功")
        
        # 创建一个简单的编队
        test_crew = Crew(
            agents=[test_agent],
            tasks=[test_task],
            verbose=True
        )
        
        print("✅ 测试编队创建成功")
        
        # 执行测试
        result = test_crew.kickoff()
        print(f"✅ 环境验证结果: {result}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 环境验证失败 - 缺少依赖: {e}")
        return False
    except Exception as e:
        print(f"❌ 环境验证失败 - 错误: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='CrewAI多智能体测试框架')
    parser.add_argument('--demo', action='store_true',
                       help='运行演示测试')
    parser.add_argument('--components', action='store_true',
                       help='运行组件演示')
    parser.add_argument('--verify', action='store_true',
                       help='验证环境配置')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 设置环境
    setup_environment()
    
    if args.verify:
        success = run_simple_test()
        if success:
            print("\n✅ 环境验证通过！CrewAI可以正常使用。")
        else:
            print("\n❌ 环境验证失败！请检查依赖安装。")
    elif args.components:
        run_component_demonstrations()
    elif args.demo:
        run_crewai_demo()
    else:
        # 默认运行演示
        run_crewai_demo()


if __name__ == "__main__":
    main()