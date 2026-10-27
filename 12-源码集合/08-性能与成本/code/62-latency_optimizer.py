import time
import hashlib
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class TaskComplexity(Enum):
    SIMPLE = "simple"       # 分类、提取、翻译
    MEDIUM = "medium"       # 摘要、改写、问答
    COMPLEX = "complex"     # 推理、创作、分析

@dataclass
class ModelRoute:
    complexity: TaskComplexity
    model_name: str
    expected_latency_ms: int
    cost_per_1k_tokens: float

# 模型路由表
MODEL_ROUTES = {
    TaskComplexity.SIMPLE: ModelRoute(
        complexity=TaskComplexity.SIMPLE,
        model_name="gpt-3.5-turbo",
        expected_latency_ms=400,
        cost_per_1k_tokens=0.002,
    ),
    TaskComplexity.MEDIUM: ModelRoute(
        complexity=TaskComplexity.MEDIUM,
        model_name="gpt-4o-mini",
        expected_latency_ms=800,
        cost_per_1k_tokens=0.01,
    ),
    TaskComplexity.COMPLEX: ModelRoute(
        complexity=TaskComplexity.COMPLEX,
        model_name="gpt-4o",
        expected_latency_ms=1500,
        cost_per_1k_tokens=0.03,
    ),
}

def classify_task_complexity(prompt: str) -> TaskComplexity:
    """根据 prompt 特征判断任务复杂度"""
    complexity_keywords = {
        TaskComplexity.COMPLEX: ["分析", "推理", "设计", "评估", "比较"],
        TaskComplexity.MEDIUM: ["总结", "改写", "翻译", "问答"],
        TaskComplexity.SIMPLE: ["分类", "提取", "判断", "是否"],
    }

    for complexity, keywords in complexity_keywords.items():
        if any(kw in prompt for kw in keywords):
            return complexity

    # 默认走中等复杂度
    return TaskComplexity.MEDIUM

def get_optimal_model(prompt: str) -> ModelRoute:
    """根据任务复杂度选择最优模型"""
    complexity = classify_task_complexity(prompt)
    return MODEL_ROUTES[complexity]

import time
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class StreamingMetrics:
    """流式输出性能指标"""
    ttft_ms: float = 0.0          # Time To First Token
    total_tokens: int = 0
    total_time_ms: float = 0.0
    tokens_per_second: float = 0.0
    chunk_count: int = 0

def simulate_streaming_response(prompt: str, stream: bool = True) -> StreamingMetrics:
    """模拟流式 vs 非流式响应的延迟对比"""
    metrics = StreamingMetrics()
    ttft = 200 if stream else 3000
    metrics.ttft_ms = ttft
    total_tokens = 200
    metrics.total_tokens = total_tokens

    if stream:
        metrics.total_time_ms = ttft + (total_tokens - 1) * 15
        metrics.chunk_count = total_tokens
    else:
        metrics.total_time_ms = 3000 + total_tokens * 10
        metrics.chunk_count = 1

    metrics.tokens_per_second = (total_tokens / metrics.total_time_ms) * 1000
    return metrics

def compare_streaming_vs_blocking():
    """对比流式和非流式的用户体验差异"""
    print("=" * 60)
    print("流式输出 vs 非流式输出 — 延迟对比")
    print("=" * 60)

    for stream in [True, False]:
        mode = "流式输出" if stream else "非流式输出"
        metrics = simulate_streaming_response("写一篇长文", stream=stream)
        print(f"\n【{mode}】")
        print(f"  首字时间(TTFT): {metrics.ttft_ms:.0f}ms")
        print(f"  总耗时:         {metrics.total_time_ms:.0f}ms")
        print(f"  生成速度:       {metrics.tokens_per_second:.1f} tokens/s")
        print(f"  分块数量:       {metrics.chunk_count}")

    print("\n" + "=" * 60)
    print("结论：流式输出的首字时间通常只有非流式的 1/15")
    print("用户感知延迟大幅降低，即使总耗时相近")
    print("=" * 60)

import re
from typing import List

def count_tokens(text: str) -> int:
    """粗略估算 token 数量（中文约 1.5 字/token，英文约 4 字符/token）"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars / 4)

def estimate_inference_latency(prompt_tokens: int, model: str = "gpt-4o") -> float:
    """根据 prompt token 数估算推理延迟（毫秒）"""
    base_latency = {"gpt-4o": 150, "gpt-4o-mini": 80, "gpt-3.5-turbo": 50}
    per_token_time = {"gpt-4o": 2.5, "gpt-4o-mini": 1.2, "gpt-3.5-turbo": 0.8}
    return base_latency[model] + prompt_tokens * per_token_time[model]

def optimize_prompt(
    original_prompt: str,
    context_docs: List[str],
    max_context_tokens: int = 1000
) -> str:
    """精简 prompt：截断过长的上下文"""
    total_context_tokens = sum(count_tokens(doc) for doc in context_docs)
    if total_context_tokens <= max_context_tokens:
        return original_prompt

    truncated_docs = []
    current_tokens = 0
    for doc in context_docs:
        doc_tokens = count_tokens(doc)
        if current_tokens + doc_tokens <= max_context_tokens:
            truncated_docs.append(doc)
            current_tokens += doc_tokens
        else:
            break

    context = "\n---\n".join(truncated_docs)
    optimized = f"{original_prompt}\n\n【参考文档】\n{context}"
    return optimized

import hashlib
import time
import asyncio
from typing import Dict, Optional

class ResponseCache:
    """带防击穿保护的响应缓存"""
    
    def __init__(self, ttl: int = 3600):
        self.cache: Dict[str, dict] = {}
        self.ttl = ttl
        self.locks: Dict[str, asyncio.Lock] = {}
    
    def _hash(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()
    
    def get(self, prompt: str) -> Optional[str]:
        key = self._hash(prompt)
        if key in self.cache:
            entry = self.cache[key]
            # 提前 5 分钟预热：接近过期时返回旧值但触发后台刷新
            if time.time() - entry["timestamp"] < self.ttl - 300:
                return entry["response"]
            elif time.time() - entry["timestamp"] < self.ttl:
                return entry["response"]  # 接近过期，先返回旧值
            else:
                del self.cache[key]
        return None
    
    def set(self, prompt: str, response: str):
        key = self._hash(prompt)
        # TTL 加随机偏移，防止雪崩
        jitter = self.ttl * 0.1  # 10% 随机偏移
        actual_ttl = self.ttl + (hash(key) % int(jitter * 100)) / 100
        self.cache[key] = {
            "response": response,
            "timestamp": time.time(),
            "ttl": actual_ttl
        }
    
    def get_stats(self) -> dict:
        total = len(self.cache)
        expired = sum(
            1 for e in self.cache.values()
            if time.time() - e["timestamp"] > e["ttl"]
        )
        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired
        }

import asyncio
from typing import List

async def batch_inference(prompts: List[str], batch_size: int = 10) -> List[str]:
    """批量推理"""
    results = []
    for i in range(0, len(prompts), batch_size):
        batch = prompts[i:i+batch_size]
        batch_results = await call_batch_api(batch)
        results.extend(batch_results)
    return results

async def call_batch_api(prompts: List[str]) -> List[str]:
    """模拟批量 API 调用"""
    await asyncio.sleep(0.5)
    return [f"响应: {p[:20]}..." for p in prompts]
