"""多轮对话管理模块 - 维护会话状态、上下文、轮次计数"""

import time
import uuid
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """单条对话消息"""
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: float = 0.0
    intent: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "intent": self.intent,
            "confidence": self.confidence,
        }


@dataclass
class ConversationSession:
    """对话会话"""
    session_id: str
    user_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: float = 0.0
    last_active: float = 0.0
    intent_history: List[str] = field(default_factory=list)
    transfer_requested: bool = False
    complaint_logged: bool = False
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "total_messages": len(self.messages),
            "created_at": self.created_at,
            "last_active": self.last_active,
            "transfer_requested": self.transfer_requested,
            "complaint_logged": self.complaint_logged,
        }


class ConversationManager:
    """多轮对话管理器"""

    def __init__(self, max_history: int = 20, session_timeout: int = 1800):
        self.sessions: Dict[str, ConversationSession] = {}
        self.max_history = max_history  # 最大历史消息数
        self.session_timeout = session_timeout  # 会话超时时间（秒）
        logger.info(f"对话管理器初始化: max_history={max_history}, timeout={session_timeout}s")

    def get_or_create_session(self, session_id: str, user_id: str) -> ConversationSession:
        """获取或创建会话"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # 检查是否超时
            if time.time() - session.last_active > self.session_timeout:
                # 超时，创建新会话
                logger.info(f"会话 {session_id} 超时，创建新会话")
                del self.sessions[session_id]
            else:
                return session

        new_session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            created_at=time.time(),
            last_active=time.time(),
        )
        self.sessions[session_id] = new_session
        logger.debug(f"创建新会话: {session_id} (用户: {user_id})")
        return new_session

    def add_message(self, session_id: str, role: str, content: str,
                    intent: str = "", confidence: float = 0.0) -> Message:
        """添加消息到会话"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")

        msg = Message(role=role, content=content, timestamp=time.time(),
                      intent=intent, confidence=confidence)
        session.messages.append(msg)
        session.last_active = time.time()

        # 维护历史窗口
        if len(session.messages) > self.max_history:
            session.messages = session.messages[-self.max_history:]

        if intent:
            session.intent_history.append(intent)

        return msg

    def get_context(self, session_id: str, n_turns: int = 3) -> List[Dict]:
        """获取最近 N 轮对话上下文"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        recent = session.messages[-n_turns * 2:]
        return [{"role": m.role, "content": m.content} for m in recent]

    def should_transfer(self, session_id: str, max_rounds: int = 5) -> bool:
        """判断是否需要转人工"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        # 用户明确要求转人工
        if session.transfer_requested:
            logger.info(f"会话 {session_id}: 用户要求转人工")
            return True

        # 对话轮次超过上限
        user_messages = [m for m in session.messages if m.role == "user"]
        if len(user_messages) >= max_rounds:
            logger.info(f"会话 {session_id}: 对话轮次超限 ({len(user_messages)} >= {max_rounds})")
            return True

        # 连续低置信度识别
        low_conf_count = sum(
            1 for m in session.messages
            if m.role == "user" and m.confidence < 0.3
        )
        if low_conf_count >= 3:
            logger.info(f"会话 {session_id}: 连续低置信度 ({low_conf_count} >= 3)")
            return True

        return False

    def close_session(self, session_id: str) -> Optional[Dict]:
        """关闭会话，返回会话摘要"""
        session = self.sessions.pop(session_id, None)
        if not session:
            return None

        summary = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "total_messages": len(session.messages),
            "duration": round(time.time() - session.created_at, 2),
            "transferred": session.transfer_requested,
            "intents": session.intent_history,
            "complaint_logged": session.complaint_logged,
        }
        logger.info(f"会话关闭: {session_id} - {summary}")
        return summary

    def get_active_sessions_count(self) -> int:
        """获取活跃会话数"""
        return len(self.sessions)

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        expired = []
        now = time.time()
        for sid, session in self.sessions.items():
            if now - session.last_active > self.session_timeout:
                expired.append(sid)
        for sid in expired:
            del self.sessions[sid]
        if expired:
            logger.info(f"清理 {len(expired)} 个过期会话")
        return len(expired)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = ConversationManager()
    session_id = str(uuid.uuid4())

    print("=" * 60)
    print("多轮对话管理测试")
    print("=" * 60)

    # 模拟多轮对话
    manager.get_or_create_session(session_id, "user_001")
    manager.add_message(session_id, "user", "我的快递怎么还没到", intent="order_query", confidence=0.8)
    manager.add_message(session_id, "assistant", "正在为您查询物流信息...")
    manager.add_message(session_id, "user", "都三天了还没到", intent="complaint", confidence=0.6)
    manager.add_message(session_id, "assistant", "理解您的焦急，我帮您加急处理...")

    context = manager.get_context(session_id)
    print(f"当前上下文轮数: {len(context)}")
    print(f"需要转人工: {manager.should_transfer(session_id)}")

    # 测试转人工
    manager.add_message(session_id, "user", "转人工")
    print(f"要求转人工后: {manager.should_transfer(session_id)}")

    # 关闭会话
    summary = manager.close_session(session_id)
    print(f"\n会话摘要: {summary}")
