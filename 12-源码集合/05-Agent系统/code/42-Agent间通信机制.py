# 同步通信示例
def planner_send_to_executor(task):
    response = executor.execute(task)  # 阻塞等待
    return response

# 异步通信示例
async def planner_send_to_executor(task):
    await executor.execute_async(task)  # 不阻塞
    print("任务已提交，继续做其他事...")

async def executor_callback(result):
    print(f"任务完成，结果：{result}")

# 发布-订阅示例
class EventBus:
    def __init__(self):
        self.subscribers = {}
    
    def subscribe(self, event_type, handler):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def publish(self, event_type, data):
        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                handler(data)

# 使用示例
bus = EventBus()
bus.subscribe("test_completed", reporter.generate_report)
bus.subscribe("test_completed", monitor.update_dashboard)

bus.publish("test_completed", {"passed": 10, "failed": 2})

import asyncio
from datetime import datetime
import json

class MessageQueue:
    """简化的消息队列实现"""
    def __init__(self):
        self.queues = {}
    
    def create_queue(self, name):
        self.queues[name] = asyncio.Queue()
    
    async def send(self, to_queue, message):
        if to_queue not in self.queues:
            raise ValueError(f"队列 {to_queue} 不存在")
        
        msg = {
            "from": message.get("from"),
            "to": message.get("to"),
            "type": message.get("type"),
            "content": message.get("content"),
            "timestamp": datetime.now().isoformat(),
            "msg_id": str(hash(str(message)))
        }
        await self.queues[to_queue].put(msg)
    
    async def receive(self, queue_name, timeout=30):
        try:
            msg = await asyncio.wait_for(
                self.queues[queue_name].get(), 
                timeout=timeout
            )
            return msg
        except asyncio.TimeoutError:
            return {"type": "timeout", "content": "消息超时"}

# 使用示例
async def planner_agent(mq):
    plan = {"test_cases": ["login", "search", "checkout"]}
    await mq.send("executor_queue", {
        "from": "planner",
        "to": "executor",
        "type": "task_assignment",
        "content": plan
    })
    print(f"Planner: 发送测试计划")

async def executor_agent(mq):
    msg = await mq.receive("executor_queue")
    if msg["type"] == "task_assignment":
        print(f"Executor: 收到任务 {msg['content']}")
        results = {"passed": 3, "failed": 0, "total": 3}
        await mq.send("reporter_queue", {
            "from": "executor",
            "to": "reporter",
            "type": "test_results",
            "content": results
        })

async def reporter_agent(mq):
    msg = await mq.receive("reporter_queue")
    if msg["type"] == "test_results":
        print(f"Reporter: 生成报告...")
        print(f"测试结果：通过 {msg['content']['passed']}/{msg['content']['total']}")

from enum import Enum
from pydantic import BaseModel
from typing import Any, Optional

class MessageType(Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    QUERY = "query"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"
    COORDINATION = "coordination"

class Message(BaseModel):
    from_agent: str
    to_agent: str
    msg_type: MessageType
    content: Any
    timestamp: str
    msg_id: str
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None  # 用于关联请求和响应

class CommunicationProtocol:
    def __init__(self):
        self.rules = {
            MessageType.TASK_ASSIGNMENT: {
                "from": ["planner", "orchestrator"],
                "to": ["executor", "worker"],
                "required_fields": ["task_id", "description"]
            },
            MessageType.TASK_RESULT: {
                "from": ["executor", "worker"],
                "to": ["planner", "reporter"],
                "required_fields": ["task_id", "status", "result"]
            },
            MessageType.ERROR: {
                "from": ["executor", "worker", "reporter"],
                "to": ["planner", "monitor"],
                "required_fields": ["error_code", "message"]
            }
        }
    
    def validate(self, msg: Message) -> bool:
        """验证消息是否符合协议"""
        rule = self.rules.get(msg.msg_type)
        if not rule:
            return False
        
        if msg.from_agent not in rule["from"]:
            print(f"协议违规：{msg.from_agent} 不能发送 {msg.msg_type.value}")
            return False
        
        if msg.to_agent not in rule["to"]:
            print(f"协议违规：{msg.to_agent} 不能接收 {msg.msg_type.value}")
            return False
        
        return True

import asyncio
import json
from datetime import datetime

class MessageQueue:
    def __init__(self):
        self.queues = {}
        self.dead_letter_queue = asyncio.Queue()  # 死信队列
        self.message_log = []
    
    def create_queue(self, name):
        self.queues[name] = asyncio.Queue()
    
    async def send(self, to_queue, msg: Message):
        """发送消息"""
        if to_queue not in self.queues:
            raise ValueError(f"队列 {to_queue} 不存在")
        
        msg.timestamp = datetime.now().isoformat()
        await self.queues[to_queue].put(msg)
        
        # 记录日志
        self.message_log.append({
            "action": "send",
            "msg_id": msg.msg_id,
            "from": msg.from_agent,
            "to": msg.to_agent,
            "timestamp": msg.timestamp
        })
    
    async def receive(self, queue_name, timeout=30):
        """接收消息"""
        try:
            msg = await asyncio.wait_for(
                self.queues[queue_name].get(),
                timeout=timeout
            )
            
            self.message_log.append({
                "action": "receive",
                "msg_id": msg.msg_id,
                "from": msg.from_agent,
                "to": msg.to_agent,
                "timestamp": datetime.now().isoformat()
            })
            
            return msg
        except asyncio.TimeoutError:
            return None
    
    async def handle_dead_letter(self, msg: Message, error: str):
        """处理死信（无法处理的消息）"""
        self.dead_letter_queue.put({
            "msg": msg,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        print(f"消息 {msg.msg_id} 进入死信队列：{error}")

import time
from functools import wraps

def retry_on_timeout(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except asyncio.TimeoutError:
                    if i == max_retries - 1:
                        raise Exception(f"重试{max_retries}次后仍然超时")
                    print(f"第{i+1}次超时，{delay}秒后重试...")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator

class Agent:
    def __init__(self, name, mq: MessageQueue):
        self.name = name
        self.mq = mq
    
    @retry_on_timeout(max_retries=3, delay=1)
    async def send_with_timeout(self, to_agent, msg: Message, timeout=30):
        """带超时和重试的发送"""
        try:
            await self.mq.send(f"{to_agent}_queue", msg)
            
            if msg.reply_to:
                response = await self.mq.receive(f"{self.name}_queue", timeout=timeout)
                return response
            return None
        except Exception as e:
            print(f"发送失败：{e}")
            raise

class DeadlockDetector:
    def __init__(self):
        self.wait_graph = {}  # 等待图：agent -> waiting_for_agent
    
    def add_wait(self, agent, waiting_for):
        """记录等待关系"""
        self.wait_graph[agent] = waiting_for
        self._check_deadlock()
    
    def remove_wait(self, agent):
        """移除等待关系"""
        if agent in self.wait_graph:
            del self.wait_graph[agent]
    
    def _check_deadlock(self):
        """检测死锁（环状依赖）"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            neighbor = self.wait_graph.get(node)
            if neighbor:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for agent in list(self.wait_graph.keys()):
            if agent not in visited:
                if has_cycle(agent):
                    print(f"⚠️ 检测到死锁！涉及Agent: {list(self.wait_graph.keys())}")
                    self._resolve_deadlock()
                    return True
        return False
    
    def _resolve_deadlock(self):
        """解除死锁（简单策略：让等待时间最长的Agent放弃）"""
        print("正在解除死锁...")
        if self.wait_graph:
            victim = list(self.wait_graph.keys())[0]
            del self.wait_graph[victim]
            print(f"Agent {victim} 放弃等待，死锁解除")

async def test_agent_communication(agents, message_flow):
    """验证Agent通信流程的正确性"""
    results = []
    
    for step in message_flow:
        from_agent = step["from"]
        to_agent = step["to"]
        content = step.get("content", {})
        
        msg = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type=MessageType.TASK_ASSIGNMENT,
            content=content,
            timestamp=datetime.now().isoformat(),
            msg_id=f"msg_{from_agent}_{to_agent}"
        )
        
        try:
            await agents[from_agent].send_with_timeout(to_agent, msg, timeout=5)
            received = await agents[to_agent].mq.receive(f"{to_agent}_queue", timeout=5)
            
            if received and received.content == content:
                results.append({"step": f"{from_agent}→{to_agent}", "passed": True})
                print(f"✅ {from_agent} → {to_agent}: 通信正常")
            else:
                results.append({"step": f"{from_agent}→{to_agent}", "passed": False, "reason": "内容不一致"})
                print(f"❌ {from_agent} → {to_agent}: 内容不一致")
        
        except Exception as e:
            results.append({"step": f"{from_agent}→{to_agent}", "passed": False, "reason": str(e)})
            print(f"❌ {from_agent} → {to_agent}: {e}")
    
    pass_rate = sum(1 for r in results if r["passed"]) / len(results)
    
    return {
        "total_steps": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "pass_rate": pass_rate,
        "details": results
    }

def test_agent_communication(agents, message_flow, test_message):
    """验证 Agent 通信流程的正确性"""
    for step in message_flow:
        from_agent = step["from"]
        to_agent = step["to"]
        content = step.get("content", test_message)
        
        # 发送消息
        agents[from_agent].send_message(to_agent, content)
        
        # 验证接收
        received = agents[to_agent].receive_message(timeout=5)
        assert received is not None, f"{from_agent}→{to_agent} 消息未送达"
        assert received["content"] == content, f"{from_agent}→{to_agent} 内容不一致"
        
        print(f"{from_agent} → {to_agent}: 通信正常")
    
    print("所有 Agent 通信测试通过")

import redis
import json
import uuid
from datetime import datetime

class RedisMessageQueue:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.dead_letter_key = "dead_letter_queue"
    
    def send(self, queue_name, msg: dict):
        """发送消息到Redis队列"""
        msg["msg_id"] = msg.get("msg_id", str(uuid.uuid4()))
        msg["timestamp"] = datetime.now().isoformat()
        
        # 推入队列
        self.redis.lpush(queue_name, json.dumps(msg, ensure_ascii=False))
        
        # 记录日志
        self.redis.lpush("message_log", json.dumps({
            "action": "send",
            "msg_id": msg["msg_id"],
            "queue": queue_name,
            "timestamp": msg["timestamp"]
        }, ensure_ascii=False))
    
    def receive(self, queue_name, timeout=30):
        """从Redis队列接收消息（阻塞式）"""
        result = self.redis.brpop(queue_name, timeout=timeout)
        if result:
            msg = json.loads(result[1])
            self.redis.lpush("message_log", json.dumps({
                "action": "receive",
                "msg_id": msg["msg_id"],
                "queue": queue_name,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False))
            return msg
        return None
    
    def handle_dead_letter(self, msg, error):
        """消息进入死信队列"""
        dead_msg = {
            "msg": msg,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self.redis.lpush(self.dead_letter_key, json.dumps(dead_msg, ensure_ascii=False))

import pika
import json
import uuid

class RabbitMQBroker:
    def __init__(self, host="localhost"):
        credentials = pika.PlainCredentials('guest', 'guest')
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=host, credentials=credentials)
        )
        self.channel = self.connection.channel()
    
    def setup_queue(self, queue_name, durable=True):
        """声明队列"""
        self.channel.queue_declare(queue=queue_name, durable=durable)
    
    def send(self, queue_name, msg: dict):
        """发送消息"""
        msg["msg_id"] = msg.get("msg_id", str(uuid.uuid4()))
        
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(msg, ensure_ascii=False),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 持久化
                content_type='application/json',
                message_id=msg["msg_id"]
            )
        )
    
    def receive(self, queue_name, callback):
        """接收消息（回调式）"""
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False  # 手动确认
        )
        self.channel.start_consuming()
    
    def ack_message(self, channel, delivery_tag):
        """确认消息已处理"""
        channel.basic_ack(delivery_tag=delivery_tag)

# proto文件定义
# syntax = "proto3";
# service AgentService {
#     rpc SendTask (TaskRequest) returns (TaskResponse);
#     rpc StreamResults (stream ResultRequest) returns (stream ResultResponse);
# }

import grpc
import agent_pb2
import agent_pb2_grpc

class AgentClient:
    def __init__(self, host="localhost", port=50051):
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = agent_pb2_grpc.AgentServiceStub(self.channel)
    
    def send_task(self, task_id, description):
        """发送任务（同步）"""
        request = agent_pb2.TaskRequest(
            task_id=task_id,
            description=description
        )
        response = self.stub.SendTask(request)
        return response
    
    def stream_results(self):
        """流式接收结果"""
        request = agent_pb2.ResultRequest()
        for response in self.stub.StreamResults(iter(request)):
            print(f"收到结果: {response.result}")
