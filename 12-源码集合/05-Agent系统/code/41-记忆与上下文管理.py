def sliding_window(history, window_size=5):
    """只保留最近 N 轮对话"""
    if len(history) > window_size:
        return history[-window_size:]
    return history

def summarize_history(history, llm):
    summary_prompt = f"请用 100 字以内总结以下对话的关键信息：\n{history}"
    summary = llm.invoke(summary_prompt)
    return summary

from langchain.memory import ConversationBufferMemory

class AgentWithMemory:
    def __init__(self, llm, max_history=10):
        self.llm = llm
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=2000  # 防止上下文溢出
        )
        self.max_history = max_history
    
    def execute(self, user_input):
        # 加载历史
        history = self.memory.load_memory_variables({})
        
        # 构建带上下文的 Prompt
        prompt = f"""
        历史对话：
        {history.get('chat_history', '无')}
        
        当前问题：{user_input}
        
        请基于历史对话回答当前问题。
        """
        
        response = self.llm.invoke(prompt)
        
        # 保存到记忆
        self.memory.save_context(
            {"input": user_input},
            {"output": response}
        )
        
        return response

# 短期记忆：会话级，用完即丢
session_memory = []

def add_to_memory(message):
    session_memory.append(message)
    if len(session_memory) > 10:  # 限制长度
        session_memory.pop(0)

# 长期记忆：跨会话，持久化到文件
import json
import os

class LongTermMemory:
    def __init__(self, file_path="memory.json"):
        self.file_path = file_path
        self.memory = self._load()
    
    def _load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                return json.load(f)
        return {}
    
    def save(self, key, value):
        self.memory[key] = value
        with open(self.file_path, "w") as f:
            json.dump(self.memory, f, ensure_ascii=False)
    
    def recall(self, key):
        return self.memory.get(key, None)

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document

class VectorMemory:
    def __init__(self, persist_dir='./vector_memory'):
        self.embeddings = OpenAIEmbeddings()
        self.store = Chroma(persist_directory=persist_dir, embedding_function=self.embeddings)
    
    def add(self, text, metadata=None):
        self.store.add_documents([Document(page_content=text, metadata=metadata or {})])
    
    def search(self, query, k=5):
        return [d.page_content for d in self.store.similarity_search(query, k=k)]
    
    def persist(self):
        self.store.persist()

def test_agent_memory(agent, conversation_turns):
    """验证 Agent 的记忆能力"""
    for i, turn in enumerate(conversation_turns):
        response = agent.execute(turn["input"])
        
        if turn.get("expect_recall"):
            # 检查是否能引用之前的对话
            if turn["expect_recall"] in response:
                print(f"第 {i+1} 轮：正确回忆")
            else:
                print(f"第 {i+1} 轮：忘记 '{turn['expect_recall']}'")

import sqlite3, json, time

class LightweightMemory:
    def __init__(self, db_path='memory.db'):
        self.conn = sqlite3.connect(db_path)
        self._init_db()
        self._cache = {}
    
    def _init_db(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        ''')
        self.conn.commit()
    
    def store(self, user_id, memory_type, key, value):
        now = time.time()
        self.conn.execute(
            'INSERT INTO memories VALUES (NULL, ?, ?, ?, ?, ?, ?)',
            (user_id, memory_type, key, json.dumps(value), now, now)
        )
        self.conn.commit()
        self._cache[f'{user_id}:{memory_type}:{key}'] = value
    
    def retrieve(self, user_id, memory_type, key):
        cache_key = f'{user_id}:{memory_type}:{key}'
        if cache_key in self._cache:
            return self._cache[cache_key]
        cursor = self.conn.execute(
            'SELECT value FROM memories WHERE user_id=? AND memory_type=? AND key=? ORDER BY updated_at DESC LIMIT 1',
            (user_id, memory_type, key)
        )
        row = cursor.fetchone()
        if row:
            val = json.loads(row[0])
            self._cache[cache_key] = val
            return val
        return None

from langchain.memory import ConversationBufferWindowMemory
from langchain.memory import ConversationSummaryMemory

window_memory = ConversationBufferWindowMemory(k=10)
summary_memory = ConversationSummaryMemory(llm=OpenAI())
