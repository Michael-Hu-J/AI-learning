import logging
import json
import time
import re
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """结构化日志格式化器"""
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "agent_id": getattr(record, "agent_id", "unknown"),
            "task_id": getattr(record, "task_id", "unknown"),
            "step": getattr(record, "step", None),
            "tool": getattr(record, "tool", None),
            "duration_ms": getattr(record, "duration_ms", None),
        }
        return json.dumps(log_record, ensure_ascii=False)

def sanitize(text):
    """脱敏处理：替换手机号、身份证等敏感信息"""
    text = re.sub(r'1[3-9]\d{9}', '***PHONE***', text)
    text = re.sub(r'\d{15}|\d{18}', '***ID***', text)
    return text

class SanitizingJsonFormatter(JsonFormatter):
    """带脱敏的结构化日志格式化器"""
    def format(self, record):
        # 先脱敏再格式化
        if hasattr(record, 'args') and isinstance(record.args, dict):
            for key, value in record.args.items():
                if isinstance(value, str):
                    record.args[key] = sanitize(value)
        return super().format(record)

# 配置日志
handler = logging.StreamHandler()
handler.setFormatter(SanitizingJsonFormatter())
logger = logging.getLogger("Agent")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

import os
from langsmith import Client

# 配置 LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = "agent-debugging"

# 采样配置
TRACE_SAMPLE_RATE = 0.1  # 10%的成功请求被记录
FAILED_ALWAYS_TRACE = True  # 所有失败请求都记录

class TracingAgent:
    """带追踪的Agent包装器"""
    def __init__(self, agent):
        self.agent = agent
        self.client = Client()
    
    def execute(self, task, task_id=None):
        import random
        should_trace = False
        
        try:
            result = self.agent.execute(task)
            # 失败请求 always trace，成功请求按采样率
            should_trace = random.random() < TRACE_SAMPLE_RATE
            return result
        except Exception as e:
            should_trace = FAILED_ALWAYS_TRACE
            raise
        finally:
            if should_trace:
                # LangSmith 自动记录，这里只需确保 trace_id 正确关联
                pass

class CircuitBreaker:
    def __init__(self, failure_threshold=5):
        self.failure_threshold = failure_threshold
        self.failures = 0
        self.open = False

    def is_open(self):
        return self.open

    def is_half_open(self):
        return self.open and self.failures >= self.failure_threshold

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.open = True

class ResilientTool:
    def __init__(self, primary_api, fallback_api, max_retries=3):
        self.primary = primary_api
        self.fallback = fallback_api
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker(failure_threshold=5)

    def _run(self, params):
        if self.circuit_breaker.is_open():
            return "服务暂时不可用，请稍后再试"

        for attempt in range(self.max_retries):
            try:
                if self.circuit_breaker.is_half_open():
                    return self.fallback.call(params)
                return self.primary.call(params)
            except TimeoutError:
                logger.warning(f"第 {attempt+1} 次重试超时")
                continue

        self.circuit_breaker.record_failure()
        return "服务异常，已通知运维"

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# 定义指标
tasks_total = Counter(
    'agent_tasks_total', 
    '总任务数', 
    ['status', 'agent_type']
)
task_duration = Histogram(
    'agent_task_duration_seconds', 
    '任务耗时',
    buckets=[1, 5, 10, 30, 60, 120]
)
tool_calls_total = Counter(
    'agent_tool_calls_total', 
    '工具调用总数', 
    ['tool_name', 'status']
)
token_usage = Counter(
    'agent_token_usage_total', 
    'Token消耗量', 
    ['model']
)
active_agents = Gauge('agent_active_agents', '当前活跃Agent数')
step_count = Histogram(
    'agent_step_count', 
    '任务执行步数',
    buckets=[1, 3, 5, 10, 15, 20, 30]
)

class MonitoredAgent:
    """带监控的Agent包装器"""
    def __init__(self, agent, agent_type="default"):
        self.agent = agent
        self.agent_type = agent_type
    
    def execute(self, task):
        start = time.time()
        active_agents.inc()
        
        try:
            result = self.agent.execute(task)
            tasks_total.labels(status="success", agent_type=self.agent_type).inc()
            return result
        except Exception as e:
            tasks_total.labels(status="failed", agent_type=self.agent_type).inc()
            raise
        finally:
            duration = time.time() - start
            task_duration.observe(duration)
            active_agents.dec()

# 启动 Prometheus 指标服务
start_http_server(8000)

import json
from typing import List, Dict

def evaluate_accuracy(expected: str, actual: str) -> Dict:
    """评估准确性"""
    # 简单规则匹配
    expected_keywords = set(expected.lower().split())
    actual_keywords = set(actual.lower().split())
    overlap = expected_keywords & actual_keywords
    score = len(overlap) / len(expected_keywords) if expected_keywords else 0
    return {"score": round(score, 2), "metric": "accuracy"}

def evaluate_completeness(expected: str, actual: str) -> Dict:
    """评估完整性"""
    expected_sentences = expected.split('.')
    covered = sum(1 for s in expected_sentences if s.strip() in actual)
    score = covered / len(expected_sentences) if expected_sentences else 0
    return {"score": round(score, 2), "metric": "completeness"}

def run_evaluation(agent, test_set_path: str) -> Dict:
    """运行完整评估"""
    test_set = json.load(open(test_set_path))
    results = {"accuracy": [], "completeness": [], "total": len(test_set)}
    
    for case in test_set:
        actual = agent.execute(case["question"])
        acc = evaluate_accuracy(case["answer"], actual)
        comp = evaluate_completeness(case["answer"], actual)
        results["accuracy"].append(acc["score"])
        results["completeness"].append(comp["score"])
    
    results["avg_accuracy"] = sum(results["accuracy"]) / len(results["accuracy"])
    results["avg_completeness"] = sum(results["completeness"]) / len(results["completeness"])
    
    return results

# 使用示例
# results = run_evaluation(agent, "test_set.json")
# print(f"平均准确率: {results['avg_accuracy']:.2f}")
# print(f"平均完整性: {results['avg_completeness']:.2f}")
