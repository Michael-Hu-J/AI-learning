import autogen
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import llm_env

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
            llm_config=llm_env.get_autogen_llm_config(),
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