from langgraph.graph import StateGraph
from typing import Dict, Any, Optional
from state_manager import StateManager, AgentState
import os
import sys
from pathlib import Path
from datetime import datetime

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import llm_env


class _DemoLLM:
    """演示模式模拟 LLM，无需 API Key"""

    def invoke(self, user_input):
        class _Response:
            content = (
                f"[演示模式] 已处理输入「{user_input[:80]}」。"
                "Agent 完成意图识别并返回模拟响应。"
            )

        return _Response()


def _use_demo_mode(demo_mode: Optional[bool]) -> bool:
    if demo_mode is not None:
        return demo_mode
    if os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes"):
        return True
    return not (os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY"))


class AgentTestFramework:
    """AI Agent测试框架"""
    
    def __init__(self, llm_model=None, demo_mode: Optional[bool] = None):
        self.demo_mode = _use_demo_mode(demo_mode)
        if self.demo_mode:
            self.llm = _DemoLLM()
        else:
            try:
                self.llm = llm_env.create_chat_openai(model=llm_model)
            except Exception as exc:
                print(f"[警告] LLM 初始化失败，切换演示模式: {exc}")
                self.demo_mode = True
                self.llm = _DemoLLM()
        self.state_manager = StateManager()
        self.graph = None
        self._build_graph()
    
    def _build_graph(self):
        """构建测试图"""
        builder = StateGraph(AgentState)
        
        # 添加节点
        builder.add_node("input_validator", self._validate_input)
        builder.add_node("agent_executor", self._execute_agent)
        builder.add_node("response_validator", self._validate_response)
        builder.add_node("state_updater", self._update_state)
        builder.add_node("test_evaluator", self._evaluate_test)
        
        # 添加边
        builder.add_edge("input_validator", "agent_executor")
        builder.add_edge("agent_executor", "response_validator")
        builder.add_edge("response_validator", "state_updater")
        builder.add_edge("state_updater", "test_evaluator")
        builder.add_edge("test_evaluator", "__end__")
        
        # 设置入口点
        builder.set_entry_point("input_validator")
        
        self.graph = builder.compile()
    
    def _validate_input(self, state: AgentState) -> Dict[str, Any]:
        """输入验证"""
        session_id = state['session_id']
        user_input = state['user_input']
        
        validation_result = {
            'input_valid': len(user_input.strip()) > 0,
            'input_length': len(user_input),
            'validation_time': datetime.now().isoformat()
        }
        
        test_results = state.get('test_results', {})
        test_results['input_validation'] = validation_result
        state['test_results'] = test_results
        
        state['execution_trace'].append(f"Input validation completed: {validation_result}")
        
        return {'test_results': test_results}
    
    def _execute_agent(self, state: AgentState) -> Dict[str, Any]:
        """执行Agent"""
        user_input = state['user_input']
        
        # 模拟Agent响应
        response = self.llm.invoke(user_input)
        agent_response = response.content
        
        # 更新上下文历史
        context_entry = {
            'turn': state['current_turn'],
            'user_input': user_input,
            'agent_response': agent_response,
            'timestamp': datetime.now().isoformat()
        }
        
        context_history = state['context_history']
        context_history.append(context_entry)
        
        state['agent_response'] = agent_response
        state['context_history'] = context_history
        state['current_turn'] += 1
        
        state['execution_trace'].append(f"Agent executed, response length: {len(agent_response)}")
        
        return {
            'agent_response': agent_response,
            'context_history': context_history,
            'current_turn': state['current_turn']
        }
    
    def _validate_response(self, state: AgentState) -> Dict[str, Any]:
        """响应验证"""
        agent_response = state['agent_response']
        
        # 基础验证规则
        validation_rules = {
            'non_empty': len(agent_response.strip()) > 0,
            'not_error_message': 'error' not in agent_response.lower(),
            'contains_expected_keywords': True,  # 可根据测试场景定制
            'response_quality_score': self._assess_response_quality(agent_response)
        }
        
        test_results = state.get('test_results', {})
        test_results['response_validation'] = validation_rules
        state['test_results'] = test_results
        
        # 如果验证失败，记录错误
        if not validation_rules['non_empty']:
            state['validation_errors'].append("Agent returned empty response")
        
        state['execution_trace'].append(f"Response validation completed: {validation_rules}")
        
        return {'test_results': test_results}
    
    def _update_state(self, state: AgentState) -> Dict[str, Any]:
        """状态更新"""
        # 在这里可以添加额外的状态更新逻辑
        state['execution_trace'].append("State updated after response validation")
        return {}
    
    def _evaluate_test(self, state: AgentState) -> Dict[str, Any]:
        """测试评估"""
        test_results = state['test_results']
        validation_errors = state['validation_errors']
        
        overall_result = {
            'passed': len(validation_errors) == 0,
            'error_count': len(validation_errors),
            'total_validations': len(test_results),
            'score': self._calculate_test_score(test_results),
            'completion_time': datetime.now().isoformat()
        }
        
        test_results['overall'] = overall_result
        state['test_results'] = test_results
        
        state['execution_trace'].append(f"Test evaluation completed: {overall_result}")
        
        return {'test_results': test_results}
    
    def _assess_response_quality(self, response: str) -> float:
        """评估响应质量"""
        # 简单的质量评估逻辑
        score = 0.5  # 基础分数
        
        if len(response) > 10:
            score += 0.2
        if '?' not in response[:20]:  # 响应不太像是反问
            score += 0.2
        if 'sorry' not in response.lower():
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_test_score(self, test_results: Dict[str, Any]) -> float:
        """计算测试分数"""
        if 'response_validation' not in test_results:
            return 0.0
        
        response_validation = test_results['response_validation']
        passed_checks = sum(1 for v in response_validation.values() if v is True)
        total_checks = len(response_validation)
        
        return passed_checks / total_checks if total_checks > 0 else 0.0
    
    def run_test_scenario(self, session_id: str, user_input: str) -> AgentState:
        """运行测试场景"""
        # 初始化状态
        if session_id not in self.state_manager.states:
            session_id = self.state_manager.initialize_state(session_id)
        
        # 更新初始输入
        initial_state = self.state_manager.update_state(
            session_id, 
            user_input=user_input
        )
        
        # 执行图
        final_state = self.graph.invoke(initial_state)
        
        return final_state