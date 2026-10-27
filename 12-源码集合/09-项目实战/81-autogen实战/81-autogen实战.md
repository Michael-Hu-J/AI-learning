# 81-autogen实战：多智能体对话测试框架

**作者**：测试员周周（14 年测试老兵）  
**难度**：实战  
**品牌**：测试员周周

> 延伸阅读：`78-langgraph` · AutoGen 文档

---

## 关键概念速览

**一句话**：AutoGen 测 **多 Agent 对话终止 + 人类在环 + 工具权限**。

**行动**：max_round → 人工审批节点 → 群聊日志审计

---

## 项目概述

作为拥有14年测试经验的工程师，我深知复杂AI系统的测试需要多角度、多层面的验证。本项目使用Microsoft AutoGen构建一个多智能体对话测试框架，通过多个具有不同专业能力的智能体协作，实现对AI系统更全面、更深入的测试验证。

### 项目目标
- 构建基于AutoGen的多智能体对话测试框架
- 实现智能体间的自然对话和协作
- 提供多样化的测试视角和策略
- 支持复杂测试场景的动态探索

### 技术栈
- autogen==0.2.0：多智能体对话框架
- openai==1.16.2：大模型服务
- docker==7.1.0：容器化支持
- flaml==2.1.2：自动化机器学习
- python-dotenv==1.0.1：环境配置

## 项目结构

```
81-autogen实战/
├── multi_agent_dialogue_framework.py    # 多智能体对话框架核心
├── agents/
│   ├── test_manager_agent.py            # 测试管理智能体
│   ├── functionality_tester_agent.py    # 功能测试智能体
│   ├── security_tester_agent.py         # 安全测试智能体
│   ├── performance_tester_agent.py      # 性能测试智能体
│   └── compatibility_tester_agent.py    # 兼容性测试智能体
├── group_chat_manager.py               # 群聊管理器
├── test_scenario_generator.py          # 测试场景生成器
├── conversation_analyzer.py            # 对话分析器
├── test_result_aggregator.py           # 测试结果聚合器
├── requirements.txt                    # 依赖包列表
├── run_autogen_tests.py               # autogen测试执行脚本
└── README.md                          # 项目说明文档
```

## 核心实现

### 1. 多智能体对话框架 (multi_agent_dialogue_framework.py)

```python
import autogen
from typing import List, Dict, Any, Optional
import json
import time
from agents.test_manager_agent import TestManagerAgent
from agents.functionality_tester_agent import FunctionalityTesterAgent
from agents.security_tester_agent import SecurityTesterAgent
from agents.performance_tester_agent import PerformanceTesterAgent
from agents.compatibility_tester_agent import CompatibilityTesterAgent
from group_chat_manager import GroupChatManager
from test_scenario_generator import TestScenarioGenerator
from conversation_analyzer import ConversationAnalyzer
from test_result_aggregator import TestResultAggregator

class MultiAgentDialogueFramework:
    """多智能体对话测试框架"""
    
    def __init__(self, 
                 llm_config: Optional[Dict] = None,
                 max_consecutive_auto_reply: int = 10,
                 human_input_mode: str = "NEVER"):
        self.llm_config = llm_config or {
            "model": "gpt-4-turbo",
            "temperature": 0.1,
        }
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
```

### 2. 智能体定义 (agents/test_manager_agent.py)

```python
import autogen
from typing import Optional, Dict, Any

class TestManagerAgent:
    """测试管理智能体"""
    
    def __init__(self, name: str, llm_config: Optional[Dict] = None, human_input_mode: str = "NEVER"):
        self.name = name
        self.llm_config = llm_config
        self.human_input_mode = human_input_mode
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """创建测试管理智能体"""
        return autogen.AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message="""
            你是测试管理智能体，负责协调和管理整个多智能体测试过程。
            
            你的职责包括：
            1. 制定测试计划和策略
            2. 分配测试任务给专业智能体
            3. 监控测试进度和质量
            4. 协调智能体间的沟通
            5. 汇总测试结果并生成报告
            6. 识别测试过程中的风险和问题
            7. 确保测试目标的达成
            
            你需要：
            - 保持对整体测试进度的掌控
            - 根据测试反馈调整测试策略
            - 确保各专业智能体有效协作
            - 在必要时介入解决冲突
            - 最终形成全面的测试评估
            """,
            human_input_mode=self.human_input_mode
        )
    
    def get_agent(self):
        """获取智能体实例"""
        return self.agent

class FunctionalityTesterAgent:
    """功能测试智能体"""
    
    def __init__(self, name: str, llm_config: Optional[Dict] = None, human_input_mode: str = "NEVER"):
        self.name = name
        self.llm_config = llm_config
        self.human_input_mode = human_input_mode
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """创建功能测试智能体"""
        return autogen.AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message="""
            你是功能测试智能体，专门负责验证系统功能的正确性和完整性。
            
            你的职责包括：
            1. 设计功能测试用例，覆盖正常流程和异常流程
            2. 验证系统是否按预期实现功能需求
            3. 检查边界条件和异常处理
            4. 评估用户交互体验
            5. 识别功能缺陷和改进建议
            6. 与其他测试智能体协作，提供功能层面的支持
            
            你需要：
            - 关注功能实现的准确性
            - 测试各种输入组合和边界情况
            - 评估功能的易用性和用户体验
            - 记录功能缺陷并分类优先级
            - 与安全和性能测试智能体协作
            """,
            human_input_mode=self.human_input_mode
        )
    
    def get_agent(self):
        """获取智能体实例"""
        return self.agent

class SecurityTesterAgent:
    """安全测试智能体"""
    
    def __init__(self, name: str, llm_config: Optional[Dict] = None, human_input_mode: str = "NEVER"):
        self.name = name
        self.llm_config = llm_config
        self.human_input_mode = human_input_mode
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """创建安全测试智能体"""
        return autogen.AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message="""
            你是安全测试智能体，专门负责识别和评估系统安全风险。
            
            你的职责包括：
            1. 识别潜在的安全漏洞和风险点
            2. 执行渗透测试和安全扫描
            3. 评估认证和授权机制
            4. 检查数据保护和隐私合规
            5. 测试Prompt注入等AI特有安全风险
            6. 评估安全控制措施的有效性
            7. 提供安全加固建议
            
            你需要：
            - 深入理解各种安全威胁模型
            - 运用专业的安全测试技术和工具
            - 关注AI系统特有的安全挑战
            - 提供具体的修复建议和最佳实践
            - 与功能和性能测试智能体协作
            """,
            human_input_mode=self.human_input_mode
        )
    
    def get_agent(self):
        """获取智能体实例"""
        return self.agent

class PerformanceTesterAgent:
    """性能测试智能体"""
    
    def __init__(self, name: str, llm_config: Optional[Dict] = None, human_input_mode: str = "NEVER"):
        self.name = name
        self.llm_config = llm_config
        self.human_input_mode = human_input_mode
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """创建性能测试智能体"""
        return autogen.AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message="""
            你是性能测试智能体，专门负责评估系统性能和可扩展性。
            
            你的职责包括：
            1. 设计性能测试场景和负载模型
            2. 评估系统响应时间、吞吐量和资源利用率
            3. 识别性能瓶颈和优化机会
            4. 测试系统在高负载下的稳定性
            5. 评估系统扩展能力和容量规划
            6. 提供性能优化建议
            
            你需要：
            - 理解性能测试方法论和指标
            - 能够设计有效的负载测试场景
            - 分析性能数据并识别趋势
            - 提供可操作的性能优化建议
            - 与其他测试智能体协作评估整体质量
            """,
            human_input_mode=self.human_input_mode
        )
    
    def get_agent(self):
        """获取智能体实例"""
        return self.agent

class CompatibilityTesterAgent:
    """兼容性测试智能体"""
    
    def __init__(self, name: str, llm_config: Optional[Dict] = None, human_input_mode: str = "NEVER"):
        self.name = name
        self.llm_config = llm_config
        self.human_input_mode = human_input_mode
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """创建兼容性测试智能体"""
        return autogen.AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message="""
            你是兼容性测试智能体，专门负责验证系统在不同环境和配置下的兼容性。
            
            你的职责包括：
            1. 测试系统在不同平台和设备上的表现
            2. 验证与第三方系统的集成兼容性
            3. 评估API和协议兼容性
            4. 检查数据格式和接口兼容性
            5. 评估向后兼容性和升级路径
            6. 识别兼容性问题和风险
            
            你需要：
            - 了解各种平台、系统和技术栈
            - 关注接口和数据格式的标准化
            - 评估系统的灵活性和适应性
            - 提供兼容性改进建议
            - 与其他测试智能体协作确保全面覆盖
            """,
            human_input_mode=self.human_input_mode
        )
    
    def get_agent(self):
        """获取智能体实例"""
        return self.agent
```

### 3. 群聊管理器 (group_chat_manager.py)

```python
import autogen
from typing import List, Dict, Any, Optional

class GroupChatManager:
    """群聊管理器"""
    
    def __init__(self, 
                 agents: List[autogen.Agent], 
                 max_round: int = 50,
                 speaker_selection_method: str = "round_robin",
                 allow_repeat_speaker: bool = True,
                 admin_name: str = "Admin"):
        self.agents = agents
        self.max_round = max_round
        self.speaker_selection_method = speaker_selection_method
        self.allow_repeat_speaker = allow_repeat_speaker
        self.admin_name = admin_name
        
        # 创建群聊
        self.groupchat = autogen.GroupChat(
            agents=agents,
            messages=[],
            max_round=self.max_round,
            speaker_selection_method=self.speaker_selection_method,
            allow_repeat_speaker=self.allow_repeat_speaker,
            admin_name=self.admin_name
        )
        
        # 创建群聊管理器
        self.manager = autogen.GroupChatManager(
            groupchat=self.groupchat,
            llm_config={
                "model": "gpt-4-turbo",
                "temperature": 0.1,
            },
            is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0
        )
    
    def get_participant_names(self) -> List[str]:
        """获取参与者名称列表"""
        return [agent.name for agent in self.agents]
    
    def get_groupchat_info(self) -> Dict[str, Any]:
        """获取群聊信息"""
        return {
            'participant_count': len(self.agents),
            'participants': self.get_participant_names(),
            'max_round': self.max_round,
            'selection_method': self.speaker_selection_method,
            'allow_repeat_speaker': self.allow_repeat_speaker,
            'admin_name': self.admin_name
        }
    
    def reset_groupchat(self):
        """重置群聊"""
        self.groupchat.messages.clear()
    
    def run_test_discussion(self, initial_message: str) -> autogen.ChatResult:
        """运行测试讨论"""
        # 使用其中一个智能体发起对话
        initiator = self.agents[0]  # 通常是测试管理智能体
        
        chat_result = initiator.initiate_chat(
            self.manager,
            message=initial_message,
            summary_method="reflection_with_llm",
            max_turns=self.max_round
        )
        
        return chat_result
    
    def run_directed_discussion(self, 
                               topic: str, 
                               assigned_agents: List[str], 
                               duration_rounds: int = 10) -> autogen.ChatResult:
        """运行定向讨论"""
        initial_message = f"""
        现在开始关于"{topic}"的专项讨论。
        
        参与讨论的智能体：{', '.join(assigned_agents)}
        
        请围绕主题展开深入讨论，分享各自的专业见解，
        并寻求协作解决方案。
        
        讨论将在{duration_rounds}轮后结束。
        """
        
        # 临时修改群聊配置以支持定向讨论
        original_max_round = self.max_round
        self.max_round = duration_rounds
        
        try:
            chat_result = self.run_test_discussion(initial_message)
            return chat_result
        finally:
            # 恢复原始配置
            self.max_round = original_max_round

def create_test_group_chat():
    """创建测试用的群聊"""
    print("创建AutoGen测试群聊...")
    
    # 这里需要实际的智能体实例，为简洁起见返回说明
    return {
        'group_chat': 'GroupChatManager',
        'features': [
            'Multi-Agent Conversation',
            'Speaker Selection',
            'Message History',
            'Termination Conditions'
        ]
    }
```

### 4. 测试场景生成器 (test_scenario_generator.py)

```python
import random
from typing import List, Dict, Any

class TestScenarioGenerator:
    """测试场景生成器"""
    
    def __init__(self):
        self.functional_scenarios = [
            {
                'name': '基本功能验证',
                'description': '验证系统核心功能是否正常工作',
                'category': 'functional',
                'complexity': 'low',
                'tags': ['smoke', 'core']
            },
            {
                'name': '边界值测试',
                'description': '测试输入参数的边界值情况',
                'category': 'functional',
                'complexity': 'medium',
                'tags': ['boundary', 'edge_case']
            },
            {
                'name': '异常流程测试',
                'description': '验证系统对异常情况的处理能力',
                'category': 'functional',
                'complexity': 'medium',
                'tags': ['error_handling', 'exception']
            },
            {
                'name': '多步骤业务流程',
                'description': '测试复杂的多步骤业务场景',
                'category': 'functional',
                'complexity': 'high',
                'tags': ['workflow', 'integration']
            }
        ]
        
        self.security_scenarios = [
            {
                'name': '输入验证测试',
                'description': '验证系统对恶意输入的过滤能力',
                'category': 'security',
                'complexity': 'medium',
                'tags': ['input_validation', 'injection']
            },
            {
                'name': '认证授权测试',
                'description': '验证访问控制和权限管理',
                'category': 'security',
                'complexity': 'high',
                'tags': ['auth', 'authorization']
            },
            {
                'name': '数据泄露防护',
                'description': '测试敏感数据的保护机制',
                'category': 'security',
                'complexity': 'high',
                'tags': ['privacy', 'data_protection']
            },
            {
                'name': 'Prompt注入测试',
                'description': '针对AI系统的特殊安全测试',
                'category': 'security',
                'complexity': 'high',
                'tags': ['prompt_injection', 'ai_specific']
            }
        ]
        
        self.performance_scenarios = [
            {
                'name': '负载压力测试',
                'description': '评估系统在高负载下的表现',
                'category': 'performance',
                'complexity': 'high',
                'tags': ['load', 'stress']
            },
            {
                'name': '并发性能测试',
                'description': '测试多用户同时访问的性能',
                'category': 'performance',
                'complexity': 'medium',
                'tags': ['concurrency', 'throughput']
            },
            {
                'name': '响应时间测试',
                'description': '测量系统响应时间指标',
                'category': 'performance',
                'complexity': 'low',
                'tags': ['latency', 'response_time']
            },
            {
                'name': '容量规划验证',
                'description': '评估系统容量和扩展性',
                'category': 'performance',
                'complexity': 'high',
                'tags': ['capacity', 'scalability']
            }
        ]
        
        self.compatibility_scenarios = [
            {
                'name': '跨平台兼容性',
                'description': '验证在不同平台上的兼容性',
                'category': 'compatibility',
                'complexity': 'medium',
                'tags': ['cross_platform', 'portability']
            },
            {
                'name': 'API兼容性',
                'description': '测试API接口的兼容性',
                'category': 'compatibility',
                'complexity': 'medium',
                'tags': ['api', 'interface']
            },
            {
                'name': '数据格式兼容性',
                'description': '验证数据格式的兼容性',
                'category': 'compatibility',
                'complexity': 'low',
                'tags': ['data_format', 'interoperability']
            },
            {
                'name': '版本升级兼容性',
                'description': '测试版本升级的兼容性',
                'category': 'compatibility',
                'complexity': 'high',
                'tags': ['upgrade', 'backward_compatibility']
            }
        ]
    
    def generate_scenarios(self, 
                          target_system: str, 
                          test_objectives: List[str],
                          count: int = 10) -> List[Dict[str, Any]]:
        """根据目标系统和测试目标生成测试场景"""
        all_scenarios = (
            self.functional_scenarios + 
            self.security_scenarios + 
            self.performance_scenarios + 
            self.compatibility_scenarios
        )
        
        # 根据测试目标筛选相关场景
        filtered_scenarios = []
        
        for obj in test_objectives:
            obj_lower = obj.lower()
            
            # 根据目标关键词匹配场景
            for scenario in all_scenarios:
                if (obj_lower in scenario['name'].lower() or 
                    obj_lower in scenario['description'].lower() or
                    any(tag in obj_lower for tag in scenario['tags'])):
                    if scenario not in filtered_scenarios:
                        filtered_scenarios.append(scenario)
        
        # 如果筛选后的场景不够，随机补充
        if len(filtered_scenarios) < count:
            remaining_count = count - len(filtered_scenarios)
            # 从所有场景中随机选择补充
            remaining_scenarios = [s for s in all_scenarios if s not in filtered_scenarios]
            selected_additional = random.sample(
                remaining_scenarios, 
                min(remaining_count, len(remaining_scenarios))
            )
            filtered_scenarios.extend(selected_additional)
        
        # 如果仍然不够，从所有场景中随机选择直到达到指定数量
        if len(filtered_scenarios) < count:
            remaining_count = count - len(filtered_scenarios)
            all_remaining = [s for s in all_scenarios if s not in filtered_scenarios]
            # 循环选择直到达到所需数量
            while len(filtered_scenarios) < count and all_remaining:
                filtered_scenarios.append(random.choice(all_remaining))
        
        # 返回前count个场景
        return filtered_scenarios[:count]
    
    def generate_custom_scenario(self, 
                                scenario_type: str, 
                                description: str, 
                                priority: str = 'medium') -> Dict[str, Any]:
        """生成自定义测试场景"""
        return {
            'name': f'Custom {scenario_type.title()} Test',
            'description': description,
            'category': scenario_type.lower(),
            'complexity': priority,
            'tags': ['custom', scenario_type.lower()],
            'custom': True
        }
    
    def get_scenario_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根据类别获取测试场景"""
        category_mapping = {
            'functional': self.functional_scenarios,
            'security': self.security_scenarios,
            'performance': self.performance_scenarios,
            'compatibility': self.compatibility_scenarios
        }
        
        return category_mapping.get(category, [])
    
    def create_regression_scenario(self, 
                                  previous_version_features: List[str],
                                  new_features: List[str]) -> Dict[str, Any]:
        """创建回归测试场景"""
        affected_features = list(set(previous_version_features) - set(new_features))
        
        return {
            'name': 'Regression Test Scenario',
            'description': f'Test previously working features: {", ".join(affected_features[:3])}',
            'category': 'regression',
            'complexity': 'medium',
            'tags': ['regression', 'existing_features'],
            'affected_features': affected_features
        }
    
    def create_exploratory_scenario(self, 
                                   target_system: str,
                                   exploration_depth: str = 'medium') -> Dict[str, Any]:
        """创建探索性测试场景"""
        depths = {
            'low': '表面功能验证',
            'medium': '深度功能交互测试', 
            'high': '极限边界和异常情况探索'
        }
        
        return {
            'name': 'Exploratory Test Scenario',
            'description': f'对{target_system[:50]}进行{depths.get(exploration_depth, "中等深度")}探索',
            'category': 'exploratory',
            'complexity': exploration_depth,
            'tags': ['exploratory', 'ad_hoc', 'discovery'],
            'depth': exploration_depth
        }

def demonstrate_scenario_generation():
    """演示场景生成"""
    generator = TestScenarioGenerator()
    
    # 示例目标系统和测试目标
    target_system = "智能客服AI系统"
    test_objectives = [
        "验证自然语言理解能力",
        "测试安全性",
        "评估响应性能"
    ]
    
    scenarios = generator.generate_scenarios(target_system, test_objectives, count=8)
    
    print(f"生成了 {len(scenarios)} 个测试场景:")
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i}. {scenario['name']} - {scenario['category']} ({scenario['complexity']})")
    
    return scenarios
```

### 5. 对话分析器 (conversation_analyzer.py)

```python
from typing import List, Dict, Any
import re
from collections import Counter, defaultdict

class ConversationAnalyzer:
    """对话分析器"""
    
    def __init__(self):
        self.patterns = {
            'issue_indicators': [
                r'bug', r'error', r'fail', r'problem', r'issue', 
                r'not working', r'doesn\'t work', r'broken', r'incorrect'
            ],
            'positive_indicators': [
                r'success', r'works', r'correct', r'good', r'great',
                r'effective', r'efficient', r'properly', r'validated'
            ],
            'security_terms': [
                r'security', r'vulnerability', r'exploit', r'hack', 
                r'attack', r'breach', r'leak', r'auth', r'permission'
            ],
            'performance_terms': [
                r'performance', r'speed', r'fast', r'slow', r'latency',
                r'response time', r'throughput', r'load', r'concurrent'
            ],
            'functionality_terms': [
                r'feature', r'function', r'capability', r'behavior',
                r'input', r'output', r'process', r'workflow'
            ]
        }
    
    def analyze_conversation(self, 
                           conversation_history: Dict[str, List[Dict]], 
                           test_objectives: List[str]) -> Dict[str, Any]:
        """分析对话历史"""
        # 合并所有消息
        all_messages = []
        for msg_list in conversation_history.values():
            all_messages.extend(msg_list)
        
        # 按时间排序
        all_messages.sort(key=lambda x: x.get('timestamp', 0))
        
        # 执行各种分析
        sentiment_analysis = self._analyze_sentiment(all_messages)
        topic_analysis = self._analyze_topics(all_messages)
        participation_analysis = self._analyze_participation(all_messages)
        issue_detection = self._detect_issues(all_messages)
        objective_alignment = self._analyze_objective_alignment(all_messages, test_objectives)
        
        # 计算整体评分
        overall_score = self._calculate_overall_score(
            sentiment_analysis, issue_detection, objective_alignment
        )
        
        return {
            'sentiment': sentiment_analysis,
            'topics': topic_analysis,
            'participation': participation_analysis,
            'issues': issue_detection,
            'objective_alignment': objective_alignment,
            'overall_score': overall_score,
            'summary': self._generate_summary(
                sentiment_analysis, issue_detection, topic_analysis
            )
        }
    
    def _analyze_sentiment(self, messages: List[Dict]) -> Dict[str, Any]:
        """分析情感倾向"""
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for msg in messages:
            content = msg.get('content', '').lower()
            
            # 检查积极词汇
            for pattern in self.patterns['positive_indicators']:
                if re.search(r'\b' + pattern + r'\b', content):
                    positive_count += 1
                    break
            
            # 检查消极词汇
            for pattern in self.patterns['issue_indicators']:
                if re.search(r'\b' + pattern + r'\b', content):
                    negative_count += 1
                    break
            else:
                # 如果没有检测到积极或消极词汇，则为中性
                if not re.search(r'\b(' + '|'.join(self.patterns['positive_indicators'] + self.patterns['issue_indicators']) + r')\b', content):
                    neutral_count += 1
        
        total = len(messages)
        if total == 0:
            total = 1  # 避免除零错误
            
        return {
            'positive_ratio': positive_count / total,
            'negative_ratio': negative_count / total,
            'neutral_ratio': neutral_count / total,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count
        }
    
    def _analyze_topics(self, messages: List[Dict]) -> Dict[str, Any]:
        """分析话题分布"""
        topic_counts = defaultdict(int)
        
        for msg in messages:
            content = msg.get('content', '').lower()
            
            # 检测各类话题
            for topic, patterns in self.patterns.items():
                for pattern in patterns:
                    if re.search(r'\b' + pattern + r'\b', content):
                        topic_counts[topic] += 1
                        break  # 每个消息只计入一个话题
        
        return {
            'distribution': dict(topic_counts),
            'dominant_topic': max(topic_counts, key=topic_counts.get) if topic_counts else 'none',
            'topic_diversity': len(topic_counts) / len(self.patterns) if self.patterns else 0
        }
    
    def _analyze_participation(self, messages: List[Dict]) -> Dict[str, Any]:
        """分析参与度"""
        participant_stats = defaultdict(lambda: {'messages': 0, 'words': 0})
        
        for msg in messages:
            sender = msg.get('name', 'unknown')
            content = msg.get('content', '')
            
            participant_stats[sender]['messages'] += 1
            participant_stats[sender]['words'] += len(content.split())
        
        # 计算参与均衡度
        message_counts = [stats['messages'] for stats in participant_stats.values()]
        if len(message_counts) > 1:
            avg_messages = sum(message_counts) / len(message_counts)
            participation_balance = 1 - (max(message_counts) - min(message_counts)) / avg_messages if avg_messages > 0 else 1
        else:
            participation_balance = 1.0
        
        return {
            'participants': dict(participant_stats),
            'total_participants': len(participant_stats),
            'total_messages': len(messages),
            'participation_balance': participation_balance
        }
    
    def _detect_issues(self, messages: List[Dict]) -> Dict[str, Any]:
        """检测问题"""
        issues = []
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for i, msg in enumerate(messages):
            content = msg.get('content', '').lower()
            sender = msg.get('name', 'unknown')
            
            # 检测问题关键词
            for pattern in self.patterns['issue_indicators']:
                if re.search(r'\b' + pattern + r'\b', content):
                    # 简单的严重程度判断（基于上下文关键词）
                    severity = 'medium'
                    if any(word in content for word in ['critical', 'urgent', 'major', 'severe']):
                        severity = 'high'
                    elif any(word in content for word in ['minor', 'small', 'trivial']):
                        severity = 'low'
                    
                    severity_counts[severity] += 1
                    
                    issues.append({
                        'message_idx': i,
                        'sender': sender,
                        'content': content[:100] + '...' if len(content) > 100 else content,
                        'severity': severity,
                        'detected_pattern': pattern
                    })
                    break  # 每条消息只记录一个问题
        
        return {
            'total_issues': len(issues),
            'issues': issues,
            'severity_distribution': severity_counts,
            'issue_density': len(issues) / len(messages) if messages else 0
        }
    
    def _analyze_objective_alignment(self, messages: List[Dict], objectives: List[str]) -> Dict[str, Any]:
        """分析目标对齐度"""
        aligned_messages = 0
        objective_coverage = {}
        
        for obj in objectives:
            obj_lower = obj.lower()
            obj_matches = 0
            
            for msg in messages:
                content = msg.get('content', '').lower()
                if obj_lower in content:
                    obj_matches += 1
                    aligned_messages += 1
            
            objective_coverage[obj] = {
                'matched_messages': obj_matches,
                'coverage_ratio': obj_matches / len(messages) if messages else 0
            }
        
        return {
            'aligned_message_count': aligned_messages,
            'alignment_ratio': aligned_messages / len(messages) if messages else 0,
            'objective_coverage': objective_coverage,
            'coverage_score': sum(obj['coverage_ratio'] for obj in objective_coverage.values()) / len(objectives) if objectives else 0
        }
    
    def _calculate_overall_score(self, sentiment: Dict, issues: Dict, alignment: Dict) -> float:
        """计算整体评分"""
        # 基于多个因素计算综合评分
        sentiment_factor = sentiment['positive_ratio'] * 0.3
        issue_factor = max(0, 1 - issues['issue_density']) * 0.4  # 问题越少分越高
        alignment_factor = alignment['alignment_ratio'] * 0.3
        
        return sentiment_factor + issue_factor + alignment_factor
    
    def _generate_summary(self, sentiment: Dict, issues: Dict, topics: Dict) -> str:
        """生成摘要"""
        summary_parts = []
        
        # 情感摘要
        if sentiment['positive_ratio'] > 0.6:
            summary_parts.append("对话整体呈积极态势")
        elif sentiment['negative_ratio'] > 0.3:
            summary_parts.append("检测到较多负面反馈")
        else:
            summary_parts.append("对话情感较为中性")
        
        # 问题摘要
        if issues['total_issues'] > 0:
            summary_parts.append(f"发现了{issues['total_issues']}个问题")
            high_severity = issues['severity_distribution']['high']
            if high_severity > 0:
                summary_parts.append(f"包含{high_severity}个高严重性问题")
        else:
            summary_parts.append("未发现明显问题")
        
        # 话题摘要
        dominant_topic = topics['dominant_topic']
        if dominant_topic != 'none':
            summary_parts.append(f"主要讨论集中在{dominant_topic.replace('_', ' ')}方面")
        
        return "；".join(summary_parts)

def demonstrate_conversation_analysis():
    """演示对话分析"""
    analyzer = ConversationAnalyzer()
    
    # 模拟对话历史
    mock_conversation = {
        'messages': [
            {'name': 'test_manager', 'content': '开始功能测试', 'timestamp': 1},
            {'name': 'functionality_tester', 'content': '功能测试正常通过', 'timestamp': 2},
            {'name': 'security_tester', 'content': '发现一个安全问题需要修复', 'timestamp': 3},
            {'name': 'performance_tester', 'content': '性能测试结果良好', 'timestamp': 4}
        ]
    }
    
    objectives = ["功能验证", "安全测试", "性能评估"]
    results = analyzer.analyze_conversation(mock_conversation, objectives)
    
    print("对话分析结果:")
    print(f"  整体评分: {results['overall_score']:.2f}")
    print(f"  情感倾向: {results['sentiment']['positive_ratio']:.1%} 积极")
    print(f"  发现问题: {results['issues']['total_issues']} 个")
    print(f"  目标对齐: {results['objective_alignment']['alignment_ratio']:.1%}")
    
    return results
```

### 6. 测试结果聚合器 (test_result_aggregator.py)

```python
from typing import Dict, Any, List
import statistics
from datetime import datetime

class TestResultAggregator:
    """测试结果聚合器"""
    
    def __init__(self):
        self.aggregated_results = {}
    
    def aggregate_results(self, 
                         chat_result: Any, 
                         analysis_result: Dict[str, Any],
                         test_objectives: List[str]) -> Dict[str, Any]:
        """聚合测试结果"""
        # 提取聊天结果的关键信息
        chat_summary = self._extract_chat_summary(chat_result)
        
        # 合并分析结果
        combined_results = {
            'timestamp': datetime.now().isoformat(),
            'chat_summary': chat_summary,
            'conversation_analysis': analysis_result,
            'test_objectives': test_objectives,
            'summary': self._create_comprehensive_summary(chat_summary, analysis_result, test_objectives)
        }
        
        # 计算综合评分
        combined_results['summary']['overall_score'] = self._calculate_comprehensive_score(combined_results)
        
        self.aggregated_results = combined_results
        return combined_results
    
    def _extract_chat_summary(self, chat_result: Any) -> Dict[str, Any]:
        """从聊天结果中提取摘要"""
        # 由于chat_result的结构可能因AutoGen版本而异，这里提供通用处理
        summary = {
            'total_turns': getattr(chat_result, 'turns', 0) if hasattr(chat_result, 'turns') else 0,
            'final_summary': getattr(chat_result, 'summary', 'No summary available'),
            'cost': getattr(chat_result, 'cost', 0) if hasattr(chat_result, 'cost') else 0,
            'start_time': getattr(chat_result, 'start_time', None),
            'end_time': getattr(chat_result, 'end_time', None)
        }
        
        # 如果chat_result有消息历史，也包含进来
        if hasattr(chat_result, 'chat_history'):
            summary['has_history'] = True
            summary['history_length'] = len(chat_result.chat_history) if chat_result.chat_history else 0
        else:
            summary['has_history'] = False
            summary['history_length'] = 0
        
        return summary
    
    def _create_comprehensive_summary(self, 
                                    chat_summary: Dict[str, Any], 
                                    analysis_result: Dict[str, Any],
                                    test_objectives: List[str]) -> Dict[str, Any]:
        """创建综合摘要"""
        # 从分析结果中提取关键指标
        sentiment = analysis_result.get('sentiment', {})
        issues = analysis_result.get('issues', {})
        topics = analysis_result.get('topics', {})
        participation = analysis_result.get('participation', {})
        alignment = analysis_result.get('objective_alignment', {})
        
        # 计算各项评分
        functionality_score = self._calculate_functionality_score(issues, topics)
        security_score = self._calculate_security_score(issues, topics)
        performance_score = self._calculate_performance_score(issues, topics)
        compatibility_score = self._calculate_compatibility_score(issues, topics)
        
        return {
            'functionality_pass_rate': functionality_score,
            'security_risk_level': self._determine_security_level(issues),
            'performance_score': performance_score,
            'compatibility_score': compatibility_score,
            'communication_effectiveness': participation.get('participation_balance', 0.5),
            'requirement_coverage': alignment.get('coverage_score', 0),
            'defect_density': issues.get('issue_density', 0),
            'test_completion_rate': min(1.0, len(issues.get('issues', [])) / max(1, len(test_objectives))),
            'risk_assessment': self._assess_overall_risk(issues, sentiment)
        }
    
    def _calculate_functionality_score(self, issues: Dict, topics: Dict) -> float:
        """计算功能测试评分"""
        # 基于问题数量和功能话题覆盖计算
        high_severity_issues = issues.get('severity_distribution', {}).get('high', 0)
        medium_severity_issues = issues.get('severity_distribution', {}).get('medium', 0)
        
        # 严重问题大幅降低分数
        deduction = high_severity_issues * 0.3 + medium_severity_issues * 0.1
        base_score = max(0, 1 - deduction)
        
        # 如果功能话题被充分讨论，略有加分
        functional_topic_ratio = topics.get('distribution', {}).get('functionality_terms', 0) / max(1, sum(topics.get('distribution', {}).values()))
        if functional_topic_ratio > 0.3:  # 如果功能话题占比超过30%
            base_score = min(1.0, base_score + 0.1)
        
        return round(base_score, 3)
    
    def _calculate_security_score(self, issues: Dict, topics: Dict) -> float:
        """计算安全测试评分"""
        # 安全问题严重影响评分
        security_issues = sum(issues.get('severity_distribution', {}).values())
        high_security_issues = issues.get('severity_distribution', {}).get('high', 0)
        
        if high_security_issues > 0:
            return 0.1  # 有高危安全问题直接评为低分
        elif security_issues > 0:
            return 0.4  # 有一般安全问题评为中等偏下
        else:
            # 没有安全问题，但要看是否充分讨论了安全话题
            security_topic_ratio = topics.get('distribution', {}).get('security_terms', 0) / max(1, sum(topics.get('distribution', {}).values()))
            if security_topic_ratio > 0.1:  # 安全话题占比超过10%
                return 0.9  # 充分讨论安全问题且无实际安全问题
            else:
                return 0.7  # 无安全问题但安全讨论较少
    
    def _calculate_performance_score(self, issues: Dict, topics: Dict) -> float:
        """计算性能测试评分"""
        # 性能相关问题影响评分
        performance_issues = issues.get('severity_distribution', {}).get('high', 0) + issues.get('severity_distribution', {}).get('medium', 0)
        
        if performance_issues > 0:
            return max(0.2, 0.8 - performance_issues * 0.1)  # 性能问题扣分
        else:
            # 没有性能问题，看性能话题讨论情况
            performance_topic_ratio = topics.get('distribution', {}).get('performance_terms', 0) / max(1, sum(topics.get('distribution', {}).values()))
            if performance_topic_ratio > 0.1:  # 性能话题占比超过10%
                return 0.9
            else:
                return 0.7
    
    def _calculate_compatibility_score(self, issues: Dict, topics: Dict) -> float:
        """计算兼容性测试评分"""
        # 兼容性问题影响评分
        compatibility_issues = issues.get('severity_distribution', {}).get('high', 0) + issues.get('severity_distribution', {}).get('medium', 0)
        
        if compatibility_issues > 0:
            return max(0.2, 0.8 - compatibility_issues * 0.15)  # 兼容性问题扣分较重
        else:
            # 没有兼容性问题，看兼容性话题讨论情况
            comp_topic_ratio = topics.get('distribution', {}).get('compatibility_terms', 0) / max(1, sum(topics.get('distribution', {}).values()))
            if comp_topic_ratio > 0.05:  # 兼容性话题占比超过5%
                return 0.85
            else:
                return 0.65
    
    def _determine_security_level(self, issues: Dict) -> str:
        """确定安全风险等级"""
        high_issues = issues.get('severity_distribution', {}).get('high', 0)
        medium_issues = issues.get('severity_distribution', {}).get('medium', 0)
        low_issues = issues.get('severity_distribution', {}).get('low', 0)
        
        if high_issues > 0:
            return "高危"
        elif medium_issues > 2:  # 中等风险超过2个
            return "中危"
        elif medium_issues > 0 or low_issues > 3:  # 有中等风险或低风险超过3个
            return "低危"
        else:
            return "安全"
    
    def _assess_overall_risk(self, issues: Dict, sentiment: Dict) -> Dict[str, Any]:
        """评估整体风险"""
        total_issues = issues.get('total_issues', 0)
        high_severity = issues.get('severity_distribution', {}).get('high', 0)
        negative_ratio = sentiment.get('negative_ratio', 0)
        
        if high_severity > 0:
            risk_level = "高"
            confidence = "中等" if total_issues > 5 else "低"
        elif total_issues > 5 or negative_ratio > 0.4:
            risk_level = "中"
            confidence = "高" if total_issues > 10 else "中等"
        else:
            risk_level = "低"
            confidence = "高" if total_issues == 0 else "中等"
        
        return {
            'level': risk_level,
            'confidence': confidence,
            'details': {
                'total_issues': total_issues,
                'high_severity_count': high_severity,
                'negative_sentiment_ratio': negative_ratio
            }
        }
    
    def _calculate_comprehensive_score(self, results: Dict[str, Any]) -> float:
        """计算综合评分"""
        summary = results.get('summary', {})
        
        # 各项指标权重
        weights = {
            'functionality_pass_rate': 0.3,
            'security_score': 0.25,
            'performance_score': 0.2,
            'compatibility_score': 0.15,
            'communication_effectiveness': 0.05,
            'requirement_coverage': 0.05
        }
        
        # 计算加权分数
        weighted_score = 0
        for metric, weight in weights.items():
            value = summary.get(metric, 0)
            if isinstance(value, (int, float)):
                weighted_score += value * weight
        
        return round(weighted_score, 3)
    
    def generate_metrics_dashboard(self) -> Dict[str, Any]:
        """生成指标仪表板"""
        if not self.aggregated_results:
            return {'error': 'No aggregated results available'}
        
        summary = self.aggregated_results.get('summary', {})
        
        return {
            'overall_score': summary.get('overall_score', 0),
            'key_metrics': {
                'Functionality': summary.get('functionality_pass_rate', 0),
                'Security': summary.get('security_score', 0) if 'security_score' in summary else 0,
                'Performance': summary.get('performance_score', 0),
                'Compatibility': summary.get('compatibility_score', 0)
            },
            'risk_level': summary.get('risk_assessment', {}).get('level', 'unknown'),
            'defect_density': summary.get('defect_density', 0),
            'requirement_coverage': summary.get('requirement_coverage', 0)
        }

def demonstrate_result_aggregation():
    """演示结果聚合"""
    aggregator = TestResultAggregator()
    
    # 模拟输入数据
    mock_chat_result = type('MockChatResult', (), {
        'turns': 25,
        'summary': 'Test session completed successfully',
        'cost': 0.45
    })()
    
    mock_analysis_result = {
        'sentiment': {'positive_ratio': 0.7, 'negative_ratio': 0.1},
        'issues': {'total_issues': 2, 'severity_distribution': {'high': 0, 'medium': 1, 'low': 1}},
        'topics': {'distribution': {'functionality_terms': 8, 'security_terms': 3}, 'dominant_topic': 'functionality'},
        'participation': {'participation_balance': 0.85},
        'objective_alignment': {'alignment_ratio': 0.92, 'coverage_score': 0.88},
        'overall_score': 0.78
    }
    
    test_objectives = ["功能验证", "安全测试", "性能评估"]
    
    results = aggregator.aggregate_results(mock_chat_result, mock_analysis_result, test_objectives)
    
    print("结果聚合演示:")
    print(f"  综合评分: {results['summary']['overall_score']:.3f}")
    print(f"  功能通过率: {results['summary']['functionality_pass_rate']:.1%}")
    print(f"  安全风险等级: {results['summary']['security_risk_level']}")
    print(f"  性能评分: {results['summary']['performance_score']:.2f}")
    
    return results
```

### 7. 依赖文件 (requirements.txt)

```txt
pyautogen==0.2.0
openai==1.16.2
docker==7.1.0
flaml==2.1.2
python-dotenv==1.0.1
tiktoken==0.6.0
termcolor==2.4.0
colorama==0.4.6
diskcache==5.6.3
environ==1.0
regex==2023.12.25
requests==2.31.0
sse-starlette==1.6.5
starlette==0.37.2
uvicorn==0.29.0
fastapi==0.110.2
pydantic==2.6.4
numpy==1.24.3
pandas==2.2.2
matplotlib==3.8.3
seaborn==0.13.2
pytest==8.1.1
```

### 8. autogen测试执行脚本 (run_autogen_tests.py)

```python
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
```

### 9. 项目说明文档 (README.md)

```markdown
# 81-autogen实战：多智能体对话测试框架

## 项目简介

本项目构建了一个基于Microsoft AutoGen的多智能体对话测试框架，通过多个具有不同专业能力的智能体协作，实现对AI系统更全面、更深入的测试验证。作为14年测试经验的工程师，我们注重测试的协作性、智能性和深度探索能力。

## 项目特点

- **多智能体协作**：测试管理、功能、安全、性能、兼容性专业智能体协作
- **自然对话流程**：智能体间通过自然对话进行协作测试
- **动态探索能力**：支持基于对话的动态测试场景探索
- **全面评估视角**：从多个维度对系统进行全面评估

## 环境准备

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 配置API密钥：
   ```bash
   # 创建.env文件
   cp .env.example .env
   # 编辑.env文件填入你的OpenAI API密钥
   ```

## 快速开始

1. **检查环境配置**：
   ```bash
   python run_autogen_tests.py --check
   ```

2. **运行演示测试**：
   ```bash
   python run_autogen_tests.py --demo
   ```

3. **运行组件演示**：
   ```bash
   python run_autogen_tests.py --components
   ```

4. **运行专项测试**：
   ```bash
   # 安全审计
   python run_autogen_tests.py --security
   
   # 性能测试
   python run_autogen_tests.py --performance
   ```

## 核心组件

### 1. 多智能体对话框架 (multi_agent_dialogue_framework.py)
- 统一的对话测试入口
- 智能体管理和群聊协调
- 测试结果聚合和报告生成

### 2. 智能体定义 (agents/)
- **测试管理智能体**：协调和管理测试过程
- **功能测试智能体**：验证功能正确性
- **安全测试智能体**：识别安全风险
- **性能测试智能体**：评估系统性能
- **兼容性测试智能体**：验证兼容性

### 3. 群聊管理器 (group_chat_manager.py)
- 管理多智能体对话流程
- 控制发言顺序和轮次
- 维护对话历史

### 4. 测试场景生成器 (test_scenario_generator.py)
- 根据测试目标生成场景
- 支持多种测试类型
- 提供定制化场景

### 5. 对话分析器 (conversation_analyzer.py)
- 分析对话内容和情感
- 识别问题和风险
- 评估目标对齐度

### 6. 测试结果聚合器 (test_result_aggregator.py)
- 汇总多方测试结果
- 计算综合评分
- 生成评估报告

## 智能体角色

### 测试管理智能体
- **职责**：协调测试过程，分配任务，汇总结果
- **能力**：项目管理，进度跟踪，资源协调

### 功能测试智能体
- **职责**：验证系统功能的正确性和完整性
- **能力**：用例设计，边界测试，用户体验评估

### 安全测试智能体
- **职责**：识别和评估系统安全风险
- **能力**：漏洞检测，渗透测试，AI特有安全评估

### 性能测试智能体
- **职责**：评估系统性能和可扩展性
- **能力**：负载测试，瓶颈识别，优化建议

### 兼容性测试智能体
- **职责**：验证系统在不同环境下的兼容性
- **能力**：跨平台测试，接口验证，升级兼容性

## 测试流程

1. **初始化阶段**：创建多智能体团队和群聊环境
2. **规划阶段**：测试管理智能体制定测试计划
3. **执行阶段**：各专业智能体协作执行测试
4. **分析阶段**：对话分析器评估测试过程
5. **聚合阶段**：结果聚合器生成综合报告

## 使用场景

1. **AI系统测试**：对复杂AI系统进行全面评估
2. **安全审计**：识别安全漏洞和风险
3. **性能基准**：评估系统性能指标
4. **兼容性验证**：验证多环境兼容性
5. **探索性测试**：动态发现潜在问题

## 最佳实践

1. **明确智能体角色**：为每个智能体定义清晰的职责边界
2. **控制对话长度**：设置合理的对话轮次限制
3. **监控资源消耗**：关注API调用成本和时间消耗
4. **验证输出质量**：检查智能体对话的准确性和有用性
5. **迭代优化**：根据测试结果优化智能体配置
```

现在让我更新主目录下的README.md文件，将新增的4个项目添加进去：
---

### 误区速查表

| # | 误区 | 正确做法 |
|---|------|---------|
| 1 | 只测 Demo  happy path | 真实日志 + 边界/安全 |
| 2 | 无 `./run.sh` 可复现 | 交付物必须一键跑通 |
| 3 | 测试与工程文档分离 | 用例对照代码目录 |
| 4 | 忽略成本/延迟 | 报告含 Token、P95 |
| 5 | 上线无回归集 | Golden Set 版本化 |

### 测试工程师行动清单

1. 读 **关键概念速览**，定 3 个验收 KPI  
2. `cd` 项目目录 → `./run.sh demo` → `pytest -v`  
3. 从生产/工单抽 20 条加入 `tests/`  
4. 对照本篇检查清单与 `config.yaml`  
5. 发版前同一 Golden Set 回归  

**作者**：测试员周周（14 年测试老兵）  
**品牌 / 公众号**：测试员周周  
**版权声明**：原创内容，转载请注明出处
