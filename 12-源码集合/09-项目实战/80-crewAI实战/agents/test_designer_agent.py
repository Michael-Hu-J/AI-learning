from crewai import Agent
from langchain_openai import ChatOpenAI
from typing import Optional, Dict, Any

class TestDesignerAgent:
    """测试设计智能体"""
    
    def __init__(self, llm: ChatOpenAI, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """创建测试设计智能体"""
        return Agent(
            role='资深测试设计师',
            goal='根据系统需求和规格，设计全面、有效的测试用例和测试场景',
            backstory="""
            你是一位拥有15年软件测试经验的资深测试设计师，专精于AI系统和复杂业务流程的测试设计。
            你擅长从需求文档中识别测试点，设计边界条件测试，以及创建高覆盖率的测试场景。
            你知道如何平衡测试的全面性与执行效率，并且总是关注风险最高的区域。
            """,
            verbose=self.verbose,
            llm=self.llm,
            max_iter=15,
            max_rpm=100,
            cache=True
        )
    
    def get_agent(self) -> Agent:
        """获取智能体实例"""
        return self.agent

class TestExecutorAgent:
    """测试执行智能体"""
    
    def __init__(self, llm: ChatOpenAI, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """创建测试执行智能体"""
        return Agent(
            role='自动化测试执行专家',
            goal='高效执行测试用例，准确记录测试结果，并识别执行过程中的异常情况',
            backstory="""
            你是一位专业的自动化测试工程师，精通各种测试执行框架和工具。
            你能够快速搭建测试环境，执行测试用例，并准确捕获和分类测试结果。
            你对测试执行中的常见问题有敏锐的洞察力，能够区分功能性问题和环境问题。
            """,
            verbose=self.verbose,
            llm=self.llm,
            max_iter=20,
            max_rpm=100,
            cache=True
        )
    
    def get_agent(self) -> Agent:
        """获取智能体实例"""
        return self.agent

class TestAnalyzerAgent:
    """测试分析智能体"""
    
    def __init__(self, llm: ChatOpenAI, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """创建测试分析智能体"""
        return Agent(
            role='测试数据分析专家',
            goal='深入分析测试结果数据，识别模式和趋势，提供有价值的洞察和改进建议',
            backstory="""
            你是数据分析和质量保证领域的专家，擅长从大量测试数据中提取有意义的信息。
            你能够识别测试结果中的异常模式，分析失败的根本原因，并提供可操作的改进建议。
            你了解统计学原理，能够进行回归分析和趋势预测。
            """,
            verbose=self.verbose,
            llm=self.llm,
            max_iter=15,
            max_rpm=100,
            cache=True
        )
    
    def get_agent(self) -> Agent:
        """获取智能体实例"""
        return self.agent

class QualityAssuranceAgent:
    """质量保证智能体"""
    
    def __init__(self, llm: ChatOpenAI, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """创建质量保证智能体"""
        return Agent(
            role='质量保证经理',
            goal='综合评估产品质量，制定质量标准，确保交付符合质量要求的软件产品',
            backstory="""
            你是质量管理领域的资深专家，拥有丰富的质量保证和质量控制经验。
            你熟悉各种质量模型和评估标准，能够从战略层面评估产品质量。
            你善于平衡质量、时间和成本的关系，能够为项目提供高质量的决策支持。
            """,
            verbose=self.verbose,
            llm=self.llm,
            max_iter=10,
            max_rpm=100,
            cache=True
        )
    
    def get_agent(self) -> Agent:
        """获取智能体实例"""
        return self.agent