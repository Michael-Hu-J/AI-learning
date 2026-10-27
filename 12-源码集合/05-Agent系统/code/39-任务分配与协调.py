from enum import Enum

class TaskType(Enum):
    FUNCTION = "功能测试"
    SECURITY = "安全测试"
    PERFORMANCE = "性能测试"
    REGRESSION = "回归测试"

class TaskRouter:
    def __init__(self):
        self.rules = {
            "登录": TaskType.FUNCTION,
            "注册": TaskType.FUNCTION,
            "SQL注入": TaskType.SECURITY,
            "XSS": TaskType.SECURITY,
            "并发": TaskType.PERFORMANCE,
            "压力": TaskType.PERFORMANCE,
        }
    
    def classify(self, task_description: str) -> TaskType:
        for keyword, task_type in self.rules.items():
            if keyword in task_description:
                return task_type
        return TaskType.FUNCTION

import redis

class DistributedLock:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def acquire(self, task_id, agent_id, timeout=300):
        lock_key = f"task_lock:{task_id}"
        acquired = self.redis.set(lock_key, agent_id, nx=True, ex=timeout)
        return acquired
    
    def release(self, task_id, agent_id):
        lock_key = f"task_lock:{task_id}"
        current_owner = self.redis.get(lock_key)
        if current_owner and current_owner.decode() == agent_id:
            self.redis.delete(lock_key)
            return True
        return False

class LoadBalancer:
    def __init__(self, agents):
        self.agents = agents
        self.current_index = 0
        self.weights = {a.id: a.capacity for a in agents}
    
    def get_next_agent(self):
        for _ in range(len(self.agents)):
            self.current_index = (self.current_index + 1) % len(self.agents)
            agent = self.agents[self.current_index]
            if agent.current_load < 0.8:
                return agent
        return min(self.agents, key=lambda a: a.current_load)

from enum import Enum
import time

class TaskStatus(Enum):
    PENDING = "待分配"
    ASSIGNED = "已领取"
    RUNNING = "执行中"
    COMPLETED = "已完成"
    FAILED = "失败"
    RETRYING = "重试中"
    ABANDONED = "已放弃"

class TaskStateMachine:
    def __init__(self):
        self.tasks = {}
        self.transitions = {
            TaskStatus.PENDING: [TaskStatus.ASSIGNED],
            TaskStatus.ASSIGNED: [TaskStatus.RUNNING],
            TaskStatus.RUNNING: [TaskStatus.COMPLETED, TaskStatus.FAILED],
            TaskStatus.FAILED: [TaskStatus.RETRYING, TaskStatus.ABANDONED],
            TaskStatus.RETRYING: [TaskStatus.RUNNING],
        }
    
    def create_task(self, task_id, task_data):
        self.tasks[task_id] = {
            "data": task_data,
            "status": TaskStatus.PENDING,
            "retry_count": 0,
            "max_retries": 3,
            "created_at": time.time(),
        }
    
    def transition(self, task_id, new_status):
        current_status = self.tasks[task_id]["status"]
        if new_status not in self.transitions[current_status]:
            raise ValueError(f"不允许从 {current_status.value} 转换到 {new_status.value}")
        self.tasks[task_id]["status"] = new_status
        if new_status == TaskStatus.RETRYING:
            self.tasks[task_id]["retry_count"] += 1

def test_task_distribution(assigner, test_tasks):
    assignment_counts = {agent_id: 0 for agent_id in assigner.agents}
    failures = []
    for task in test_tasks:
        try:
            agent = assigner.assign(task)
            assignment_counts[agent.id] += 1
        except Exception as e:
            failures.append((task, str(e)))
    assert len(failures) == 0, f"有 {len(failures)} 个任务分配失败"
    counts = list(assignment_counts.values())
    max_diff = max(counts) - min(counts)
    assert max_diff / sum(counts) * len(counts) < 0.3, "负载不均衡"
    return assignment_counts

class StaticTaskAssigner:
    def __init__(self):
        self.agents = {
            "function_test": FunctionTestAgent(),
            "security_test": SecurityTestAgent(),
            "performance_test": PerformanceTestAgent(),
        }
    
    def assign(self, task):
        # 按类型静态分配
        if task["type"] == "功能":
            return self.agents["function_test"]
        elif task["type"] == "安全":
            return self.agents["security_test"]
        elif task["type"] == "性能":
            return self.agents["performance_test"]
        else:
            raise ValueError(f"未知任务类型: {task['type']}")

class DynamicTaskAssigner:
    def __init__(self):
        self.agents = [
            FunctionTestAgent(capability=["功能测试", "接口测试"]),
            SecurityTestAgent(capability=["安全测试", "渗透测试"]),
            PerformanceTestAgent(capability=["性能测试", "负载测试"]),
            FullStackAgent(capability=["功能测试", "接口测试", "性能测试"]),
        ]
    
    def assign(self, task):
        # 找能力最匹配且负载最低的 Agent
        best_agent = None
        best_score = -1
        
        for agent in self.agents:
            if task["type"] in agent.capability:
                score = agent.capability_match(task) * (1 - agent.current_load)
                if score > best_score:
                    best_score = score
                    best_agent = agent
        
        return best_agent

class Coordinator:
    def __init__(self):
        self.task_queue = []
        self.agents = {}
        self.task_status = {}
    
    def submit_task(self, task):
        task_id = generate_id()
        self.task_queue.append({"id": task_id, "task": task})
        self.task_status[task_id] = "pending"
        return task_id
    
    def assign_task(self, agent_id):
        if self.task_queue:
            task = self.task_queue.pop(0)
            self.agents[agent_id].execute(task)
            self.task_status[task["id"]] = "running"

from celery import Celery

app = Celery('agent_tasks', broker='redis://localhost:6379/0')

@app.task(bind=True, max_retries=3)
def run_function_test(self, task_data):
    try:
        result = execute_function_test(task_data)
        return result
    except Exception as exc:
        self.retry(exc=exc, countdown=60)

import ray

@ray.remote
class TestAgent:
    def __init__(self, agent_id, capabilities):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.current_load = 0.0
    
    def can_handle(self, task_type):
        return task_type in self.capabilities
    
    def execute_task(self, task):
        self.current_load += 1
        try:
            result = run_test(task)
            return {"status": "success", "result": result}
        finally:
            self.current_load -= 1

from langgraph.graph import Graph, State

workflow = Graph()

def classify_task(state):
    task = state.tasks.pop(0)
    task_type = classify(task.description)
    return {"task": task, "task_type": task_type}

def assign_task(state):
    agent = find_best_agent(state.task_type, state)
    return {"current_agent": agent, "task": state.task}

workflow.add_node("classify", classify_task)
workflow.add_node("assign", assign_task)
workflow.add_edge("classify", "assign")

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class TaskStatus(Enum):
    PENDING = "待分配"
    RUNNING = "执行中"
    COMPLETED = "已完成"
    FAILED = "失败"

@dataclass
class Task:
    id: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class Agent:
    id: str
    capabilities: List[str]
    current_tasks: List[str] = field(default_factory=list)
    
    @property
    def load(self) -> float:
        return len(self.current_tasks) / 10.0
    
    def can_handle(self, task_type: str) -> bool:
        return task_type in self.capabilities

class TaskDispatcher:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.agents: Dict[str, Agent] = {}
        self._lock = threading.Lock()
    
    def dispatch(self) -> Optional[tuple]:
        with self._lock:
            for task_id, task in self.tasks.items():
                if task.status != TaskStatus.PENDING:
                    continue
                for agent_id, agent in self.agents.items():
                    if agent.can_handle(task.task_type) and agent.load < 0.8:
                        task.status = TaskStatus.RUNNING
                        task.assigned_agent = agent_id
                        agent.current_tasks.append(task_id)
                        return (task, agent)
            return None
