from crewai import Crew
from typing import Dict, Any

class CrewManager:
    """智能体编队管理器"""
    
    def __init__(self, 
                 test_designer_agent,
                 test_executor_agent, 
                 test_analyzer_agent,
                 quality_assurance_agent,
                 max_rpm: int = 100,
                 verbose: bool = False):
        self.test_designer_agent = test_designer_agent
        self.test_executor_agent = test_executor_agent
        self.test_analyzer_agent = test_analyzer_agent
        self.quality_assurance_agent = quality_assurance_agent
        self.max_rpm = max_rpm
        self.verbose = verbose
        self.crew = None
    
    def create_crew(self, tasks: list):
        """创建智能体编队"""
        self.crew = Crew(
            agents=[
                self.test_designer_agent,
                self.test_executor_agent,
                self.test_analyzer_agent,
                self.quality_assurance_agent
            ],
            tasks=tasks,
            verbose=self.verbose,
            max_rpm=self.max_rpm,
            share_crew=True  # 允许智能体共享上下文
        )
        return self.crew
    
    def execute_crew(self, tasks: list, inputs: Dict[str, Any] = None):
        """执行智能体编队"""
        if not self.crew:
            self.create_crew(tasks)
        
        # 如果没有提供输入，使用默认值
        if inputs is None:
            inputs = {}
        
        result = self.crew.kickoff(inputs=inputs)
        return result
    
    def execute_sequential_crew(self, tasks: list, inputs: Dict[str, Any] = None):
        """执行顺序智能体编队（任务按顺序执行）"""
        if not self.crew:
            self.crew = Crew(
                agents=[
                    self.test_designer_agent,
                    self.test_executor_agent,
                    self.test_analyzer_agent,
                    self.quality_assurance_agent
                ],
                tasks=tasks,
                verbose=self.verbose,
                max_rpm=self.max_rpm,
                share_crew=True,
                process='sequential'  # 确保任务按顺序执行
            )
        
        if inputs is None:
            inputs = {}
        
        result = self.crew.kickoff(inputs=inputs)
        return result
    
    def execute_hierarchical_crew(self, tasks: list, manager_agent=None, inputs: Dict[str, Any] = None):
        """执行层级智能体编队（有管理者协调）"""
        # 如果没有提供管理者，默认使用QA经理
        if manager_agent is None:
            manager_agent = self.quality_assurance_agent
        
        self.crew = Crew(
            agents=[
                self.test_designer_agent,
                self.test_executor_agent,
                self.test_analyzer_agent,
                self.quality_assurance_agent
            ],
            tasks=tasks,
            manager_agent=manager_agent,
            verbose=self.verbose,
            max_rpm=self.max_rpm,
            share_crew=True,
            process='hierarchical'  # 使用层级处理流程
        )
        
        if inputs is None:
            inputs = {}
        
        result = self.crew.kickoff(inputs=inputs)
        return result
    
    def get_crew_status(self):
        """获取编队状态"""
        if not self.crew:
            return {'status': 'NOT_INITIALIZED', 'message': 'Crew not created yet'}
        
        return {
            'status': 'READY',
            'agents_count': len(self.crew.agents),
            'tasks_count': len(self.crew.tasks),
            'max_rpm': self.max_rpm,
            'verbose': self.verbose
        }

def create_test_crew():
    """创建测试用的智能体编队"""
    print("创建CrewAI测试编队...")
    
    # 这里需要先创建智能体实例，但为了简洁，我们返回创建说明
    return {
        'agents': ['Test Designer', 'Test Executor', 'Test Analyzer', 'QA Manager'],
        'process_types': ['sequential', 'hierarchical', 'collaborative'],
        'capabilities': [
            'Test Case Design',
            'Test Execution', 
            'Result Analysis',
            'Quality Assurance'
        ]
    }