import time, statistics, threading
from dataclasses import dataclass
from typing import Dict, List, Callable
from collections import defaultdict
from enum import Enum

class RequestStatus(Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"

@dataclass
class RequestMetrics:
    request_id: str
    timestamp: float
    model: str
    endpoint: str
    status: RequestStatus
    latency_ms: float
    ttft_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    error_message: str = ""
    retry_count: int = 0

class PerformanceMonitor:
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics: List[RequestMetrics] = []
        self.lock = threading.Lock()
        self.alert_callbacks: List[Callable] = []

    def record(self, metric: RequestMetrics):
        with self.lock:
            self.metrics.append(metric)
            if len(self.metrics) > self.window_size:
                self.metrics = self.metrics[-self.window_size:]
        self._check_alerts(metric)

    def get_latency_stats(self) -> dict:
        with self.lock:
            latencies = sorted([m.latency_ms for m in self.metrics])
        if not latencies:
            return {"count": 0}
        n = len(latencies)
        return {
            "count": n, "min": latencies[0], "max": latencies[-1],
            "avg": round(statistics.mean(latencies), 1),
            "median": round(statistics.median(latencies), 1),
            "p90": latencies[int(n * 0.9)],
            "p95": latencies[int(n * 0.95)],
            "p99": latencies[int(n * 0.99)],
        }

    def get_throughput_stats(self, window_seconds: int = 60) -> dict:
        with self.lock:
            cutoff = time.time() - window_seconds
            recent = [m for m in self.metrics if m.timestamp >= cutoff]
        if not recent:
            return {"qps": 0}
        total = len(recent)
        errors = sum(1 for m in recent if m.status != RequestStatus.SUCCESS)
        return {
            "requests": total, "qps": round(total / window_seconds, 1),
            "error_rate": round(errors / total, 4),
        }

from prometheus_client import Counter, Histogram, Gauge, start_http_server

REQUEST_COUNT = Counter('ai_request_total', 'Total AI requests',
                        ['model', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('ai_request_latency_seconds', 'Request latency',
                            ['model', 'endpoint'],
                            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
ACTIVE_REQUESTS = Gauge('ai_requests_active', 'Currently active requests')
TOKEN_COST = Counter('ai_token_cost_total', 'Total token cost', ['model'])

start_http_server(8000)

import statistics
from datetime import datetime

class TrendAnalyzer:
    def __init__(self):
        self.data_points = defaultdict(list)

    def add_point(self, metric_name, value):
        self.data_points[metric_name].append({
            "time": datetime.now(), "value": value
        })

    def get_trend(self, metric_name, window=10):
        points = self.data_points.get(metric_name, [])[-window:]
        if len(points) < 2:
            return {"trend": "insufficient_data"}
        values = [p["value"] for p in points]
        mid = len(values) // 2
        first_avg = statistics.mean(values[:mid])
        second_avg = statistics.mean(values[mid:])
        change_pct = ((second_avg - first_avg) / max(0.001, first_avg)) * 100
        if change_pct > 10:
            trend = "increasing"
        elif change_pct < -10:
            trend = "decreasing"
        else:
            trend = "stable"
        return {"trend": trend, "change_pct": round(change_pct, 1)}

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

provider = TracerProvider()
jaeger_exporter = JaegerExporter(agent_host_name="localhost", agent_port=6831)
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("ai-search")

@tracer.start_as_current_span("vector_search")
def search_vectors(query, top_k=5):
    return vector_db.search(query, top_k)

@tracer.start_as_current_span("llm_inference")
def call_llm(prompt, model="gpt-4o"):
    return openai.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])

from locust import HttpUser, task, between

class AIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def search(self):
        with self.client.post("/api/search", json={
            "query": "AI性能监控最佳实践", "model": "gpt-4o", "top_k": 5
        }, catch_response=True) as resp:
            resp.success() if resp.status_code == 200 else resp.failure("fail")

    @task(1)
    def summarize(self):
        with self.client.post("/api/summarize", json={
            "text": "长文本内容" * 100, "model": "claude-3-5"
        }, catch_response=True) as resp:
            resp.success() if resp.status_code == 200 else resp.failure("fail")
