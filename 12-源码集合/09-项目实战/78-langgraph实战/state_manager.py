from typing import TypedDict, List, Dict, Any
import uuid
from datetime import datetime

class AgentState(TypedDict):
    """AI Agent状态定义"""
    session_id: str                    # 会话ID
    current_turn: int                  # 当前对话轮次
    user_input: str                   # 用户输入
    agent_response: str               # Agent回复
    context_history: List[Dict]       # 上下文历史
    test_results: Dict[str, Any]      # 测试结果
    execution_trace: List[str]        # 执行轨迹
    validation_errors: List[str]      # 验证错误

class StateManager:
    """状态管理器"""
    
    def __init__(self):
        self.states = {}
    
    def initialize_state(self, session_id: str = None) -> str:
        """初始化状态"""
        session_id = session_id or str(uuid.uuid4())
        initial_state = AgentState(
            session_id=session_id,
            current_turn=0,
            user_input="",
            agent_response="",
            context_history=[],
            test_results={},
            execution_trace=[f"State initialized at {datetime.now()}"],
            validation_errors=[]
        )
        self.states[session_id] = initial_state
        return session_id
    
    def update_state(self, session_id: str, **kwargs) -> AgentState:
        """更新状态"""
        if session_id not in self.states:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.states[session_id]
        for key, value in kwargs.items():
            if key in state:
                state[key] = value
        
        # 记录执行轨迹
        state['execution_trace'].append(
            f"Turn {state['current_turn']}: Updated {list(kwargs.keys())}"
        )
        
        return state
    
    def get_state(self, session_id: str) -> AgentState:
        """获取状态"""
        if session_id not in self.states:
            raise ValueError(f"Session {session_id} not found")
        return self.states[session_id]
    
    def reset_state(self, session_id: str):
        """重置状态"""
        if session_id in self.states:
            del self.states[session_id]