import autogen
from typing import List, Dict, Any, Optional
import json
import os
import sys
import time
from pathlib import Path
from agents.test_manager_agent import TestManagerAgent
from agents.functionality_tester_agent import FunctionalityTesterAgent
from agents.security_tester_agent import SecurityTesterAgent
from agents.performance_tester_agent import PerformanceTesterAgent
from agents.compatibility_tester_agent import CompatibilityTesterAgent
from group_chat_manager import GroupChatManager
from test_scenario_generator import TestScenarioGenerator
from conversation_analyzer import ConversationAnalyzer
from test_result_aggregator import TestResultAggregator

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import llm_env

class MultiAgentDialogueFramework:
    """多智能体对话测试框架"""
    
    def __init__(self, 
                 llm_config: Optional[Dict] = None,
                 max_consecutive_auto_reply: int = 10,
                 human_input_mode: str = "NEVER"):
        self.llm_config = llm_config or llm_env.get_autogen_llm_config()
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        self.human_input_mode = human_input_mode
        
        # 初始化智能体
        self.test_manager = None
        self.functionality_tester = None
        self.security_tester = None
        self.performance_tester = None
        self.compatibility_tester = None
        
        # 初始化其他组件
        self.group_chat_manager = None
        self.scenario_generator = TestScenarioGenerator()
        self.conversation_analyzer = ConversationAnalyzer()
        self.result_aggregator = TestResultAggregator()
        
        self._initialize_agents()
        self._initialize_group_chat()
        
        # 测试结果存储
        self.test_results = {}
        self.conversation_history = []
    
    def _initialize_agents(self):
        """初始化各个测试智能体"""
        self.test_manager = TestManagerAgent(
            name="test_manager",
            llm_config=self.llm_config,
            human_input_mode=self.human_input_mode
        ).get_agent()
        
        self.functionality_tester = FunctionalityTesterAgent(
            name="functionality_tester",
            llm_config=self.llm_config,
            human_input_mode=self.human_input_mode
        ).get_agent()
        
        self.security_tester = SecurityTesterAgent(
            name="security_tester",
            llm_config=self.llm_config,
            human_input_mode=self.human_input_mode
        ).get_agent()
        
        self.performance_tester = PerformanceTesterAgent(
            name="performance_tester",
            llm_config=self.llm_config,
            human_input_mode=self.human_input_mode
        ).get_agent()
        
        self.compatibility_tester = CompatibilityTesterAgent(
            name="compatibility_tester",
            llm_config=self.llm_config,
            human_input_mode=self.human_input_mode
        ).get_agent()
    
    def _initialize_group_chat(self):
        """初始化群聊管理器"""
        self.group_chat_manager = GroupChatManager(
            agents=[
                self.test_manager,
                self.functionality_tester,
                self.security_tester,
                self.performance_tester,
                self.compatibility_tester
            ],
            max_round=50,
            speaker_selection_method="round_robin",  # 或 "auto" 用于动态选择
            allow_repeat_speaker=True
        )
    
    def run_test_session(self, 
                        target_system_description: str,
                        test_objectives: List[str],
                        custom_scenarios: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """运行测试会话"""
        print(f"开始多智能体对话测试会话...")
        print(f"目标系统: {target_system_description[:50]}...")
        print(f"测试目标: {len(test_objectives)} 项目标")
        
        # 生成测试场景
        if custom_scenarios:
            test_scenarios = custom_scenarios
        else:
            test_scenarios = self.scenario_generator.generate_scenarios(
                target_system_description, test_objectives
            )
        
        print(f"生成测试场景: {len(test_scenarios)} 个")
        
        # 开始群聊测试
        chat_result = self._conduct_group_testing(
            target_system_description, test_scenarios
        )
        
        # 分析对话
        analysis_result = self.conversation_analyzer.analyze_conversation(
            chat_result.chat_history,
            test_objectives
        )
        
        # 聚合结果
        aggregated_results = self.result_aggregator.aggregate_results(
            chat_result,
            analysis_result,
            test_objectives
        )
        
        self.test_results = aggregated_results
        self.conversation_history = chat_result.chat_history
        
        return aggregated_results
    
    def _conduct_group_testing(self, target_system: str, test_scenarios: List[Dict]) -> Any:
        """执行群聊测试"""
        # 构建初始消息
        initial_message = f"""
        开始对目标系统进行测试：
        {target_system}
        
        测试场景：
        {chr(10).join([f"- {scenario['name']}: {scenario['description']}" for scenario in test_scenarios[:3]])}
        
        请各位测试专家开始协作测试，重点关注各自专业领域的验证。
        测试管理智能体负责协调和监督整个测试过程。
        """
        
        # 启动群聊
        chat_result = self.test_manager.initiate_chat(
            self.group_chat_manager.groupchat,
            message=initial_message,
            summary_method="reflection_with_llm",
            max_turns=30
        )
        
        return chat_result
    
    def run_security_audit(self, target_system: str) -> Dict[str, Any]:
        """运行安全审计"""
        print("启动安全专项审计...")
        
        # 构建安全测试消息
        security_message = f"""
        对系统进行安全专项审计：
        {target_system}
        
        安全测试智能体请重点关注：
        1. 输入验证和过滤
        2. 认证和授权机制
        3. 数据保护和隐私
        4. 常见安全漏洞（SQL注入、XSS等）
        5. Prompt注入防护
        
        请提供详细的安全测试结果和建议。
        """
        
        # 启动安全审计对话
        audit_result = self.security_tester.initiate_chat(
            self.group_chat_manager.groupchat,
            message=security_message,
            max_turns=20
        )
        
        return {
            'audit_result': audit_result.summary if hasattr(audit_result, 'summary') else str(audit_result),
            'timestamp': time.time(),
            'target_system': target_system
        }
    
    def run_performance_test(self, target_system: str, load_profile: Dict[str, Any]) -> Dict[str, Any]:
        """运行性能测试"""
        print("启动性能专项测试...")
        
        # 构建性能测试消息
        performance_message = f"""
        对系统进行性能专项测试：
        {target_system}
        
        负载配置：
        - 并发用户数: {load_profile.get('concurrent_users', 10)}
        - 请求频率: {load_profile.get('requests_per_second', 1)}
        - 测试持续时间: {load_profile.get('duration_minutes', 5)} 分钟
        - 测试场景: {load_profile.get('test_scenario', 'standard')}
        
        性能测试智能体请执行性能基准测试，并评估系统在不同负载下的表现。
        重点关注响应时间、吞吐量、资源利用率等指标。
        """
        
        # 启动性能测试对话
        perf_result = self.performance_tester.initiate_chat(
            self.group_chat_manager.groupchat,
            message=performance_message,
            max_turns=25
        )
        
        return {
            'performance_result': perf_result.summary if hasattr(perf_result, 'summary') else str(perf_result),
            'timestamp': time.time(),
            'target_system': target_system,
            'load_profile': load_profile
        }
    
    def generate_test_report(self, filename: str = "autogen_test_report.html") -> str:
        """生成测试报告"""
        import datetime
        
        # 准备报告数据
        report_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'framework': 'Multi-Agent Dialogue Test Framework (AutoGen)',
            'results': self.test_results,
            'conversation_summary': self._summarize_conversation(),
            'participants': [
                'Test Manager', 'Functionality Tester', 
                'Security Tester', 'Performance Tester', 
                'Compatibility Tester'
            ]
        }
        
        # 生成HTML报告
        html_content = f"""
        <html>
        <head>
            <title>AutoGen多智能体对话测试报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }}
                .agent-talk {{ background-color: #f8f9fa; margin: 10px 0; padding: 10px; border-radius: 5px; }}
                .test-manager {{ border-left: 3px solid #007acc; }}
                .tester {{ border-left: 3px solid #28a745; }}
                .security {{ border-left: 3px solid #dc3545; }}
                .performance {{ border-left: 3px solid #ffc107; }}
                .compatibility {{ border-left: 3px solid #17a2b8; }}
                .metric {{ display: inline-block; margin: 5px; padding: 8px; background-color: #e9ecef; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AutoGen多智能体对话测试报告</h1>
                <p>生成时间: {report_data['timestamp']}</p>
            </div>
            
            <div class="section">
                <h2>参与智能体</h2>
                <ul>
                    {"".join([f'<li>{agent}</li>' for agent in report_data['participants']])}
                </ul>
            </div>
            
            <div class="section">
                <h2>测试摘要</h2>
                {self._format_test_summary_html()}
            </div>
            
            <div class="section">
                <h2>对话历史摘要</h2>
                <div>{self._format_conversation_html()}</div>
            </div>
            
            <div class="section">
                <h2>详细结果</h2>
                <pre>{json.dumps(report_data['results'], indent=2, ensure_ascii=False)}</pre>
            </div>
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"测试报告已生成: {filename}")
        return filename
    
    def _summarize_conversation(self) -> Dict[str, Any]:
        """总结对话"""
        if not self.conversation_history:
            return {'total_messages': 0, 'participants': [], 'summary': '无对话历史'}
        
        # 简单统计
        participants = set()
        total_messages = 0
        for msg_list in self.conversation_history.values():
            for msg in msg_list:
                if 'name' in msg:
                    participants.add(msg['name'])
                total_messages += 1
        
        return {
            'total_messages': total_messages,
            'participants': list(participants),
            'summary': f"共{total_messages}条消息，参与智能体：{', '.join(list(participants)[:3])}"
        }
    
    def _format_test_summary_html(self) -> str:
        """格式化测试摘要为HTML"""
        if not self.test_results:
            return '<p>暂无测试结果</p>'
        
        summary = self.test_results.get('summary', {})
        
        # 确定整体状态
        overall_score = summary.get('overall_score', 0)
        if overall_score >= 0.8:
            status_class = 'good'
            status_text = '✅ 优秀'
        elif overall_score >= 0.6:
            status_class = 'warning'
            status_text = '⚠️ 良好'
        else:
            status_class = 'critical'
            status_text = '❌ 需要改进'
        
        html_parts = [
            f'<p><strong>整体评估: </strong><span class="{status_class}">{status_text}</span></p>',
            '<div>'
        ]
        
        # 添加关键指标
        metrics = [
            ('功能测试通过率', summary.get('functionality_pass_rate', 0)),
            ('安全风险等级', summary.get('security_risk_level', '未知')),
            ('性能评分', summary.get('performance_score', 0)),
            ('兼容性评分', summary.get('compatibility_score', 0))
        ]
        
        for name, value in metrics:
            if isinstance(value, float):
                value = f"{value:.1%}" if name.endswith('率') else f"{value:.2f}"
            html_parts.append(f'<span class="metric">{name}: {value}</span>')
        
        html_parts.append('</div>')
        return "".join(html_parts)
    
    def _format_conversation_html(self) -> str:
        """格式化对话历史为HTML"""
        if not self.conversation_history:
            return '<p>无对话历史</p>'
        
        html_parts = []
        
        # 取最近的对话进行展示
        recent_msgs = []
        for msg_list in self.conversation_history.values():
            recent_msgs.extend(msg_list[-5:])  # 取每个智能体最近5条消息
        
        # 按时间排序并取最新的20条
        recent_msgs = sorted(recent_msgs, key=lambda x: x.get('timestamp', 0))[-20:]
        
        for msg in recent_msgs:
            sender = msg.get('name', 'Unknown')
            content = msg.get('content', '')[:200] + '...' if len(msg.get('content', '')) > 200 else msg.get('content', '')
            
            # 根据发送者添加不同样式
            css_class = 'agent-talk'
            if 'manager' in sender.lower():
                css_class += ' test-manager'
            elif 'function' in sender.lower():
                css_class += ' tester'
            elif 'security' in sender.lower():
                css_class += ' security'
            elif 'performance' in sender.lower():
                css_class += ' performance'
            elif 'compatibility' in sender.lower():
                css_class += ' compatibility'
            
            html_parts.append(f'''
            <div class="{css_class}">
                <strong>{sender}:</strong> {content}
            </div>
            ''')
        
        return "".join(html_parts) if html_parts else '<p>暂无对话内容</p>'

def demonstrate_multi_agent_dialogue():
    """演示多智能体对话测试"""
    print("开始演示AutoGen多智能体对话测试框架...")
    
    # 创建测试框架实例
    framework = MultiAgentDialogueFramework()
    
    # 定义目标系统
    target_system = """
    一个基于大语言模型的智能客服系统，具备以下能力：
    1. 自然语言理解与生成
    2. 多轮对话管理
    3. 知识库检索与整合
    4. 情感分析与回应
    5. 工单创建与跟踪
    6. 人工客服转接
    """
    
    # 定义测试目标
    test_objectives = [
        "验证自然语言理解准确性",
        "测试多轮对话连贯性",
        "检查知识库检索效果",
        "评估情感分析能力",
        "验证工单处理流程",
        "测试系统安全性",
        "评估响应性能"
    ]
    
    # 运行测试会话
    results = framework.run_test_session(
        target_system_description=target_system,
        test_objectives=test_objectives
    )
    
    print(f"测试会话完成！结果: {results}")
    
    # 生成报告
    framework.generate_test_report()
    
    return results