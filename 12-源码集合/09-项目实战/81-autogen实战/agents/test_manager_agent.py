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