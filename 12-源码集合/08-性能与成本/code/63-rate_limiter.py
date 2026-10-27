import time
import threading
from dataclasses import dataclass
from typing import Optional

@dataclass
class TokenBucketConfig:
    capacity: int = 100          # 桶容量（最大突发）
    refill_rate: float = 10.0    # 每秒补充令牌数
    initial_tokens: float = 100.0

class TokenBucketRateLimiter:
    def __init__(self, config: TokenBucketConfig):
        self.capacity = config.capacity
        self.refill_rate = config.refill_rate
        self.tokens = config.initial_tokens
        self.last_refill_time = time.monotonic()
        self.lock = threading.Lock()
        self.wait_count = 0
        self.pass_count = 0

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill_time
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill_time = now

    def try_acquire(self, tokens: int = 1) -> bool:
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.pass_count += 1
                return True
            self.wait_count += 1
            return False

import time
import random
from dataclasses import dataclass
from enum import Enum

class RetryStrategy(Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_WITH_JITTER = "exponential_with_jitter"

@dataclass
class RetryConfig:
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_WITH_JITTER
    retryable_status_codes: list = None

    def __post_init__(self):
        if self.retryable_status_codes is None:
            self.retryable_status_codes = [429, 503, 500]

def calculate_delay(config: RetryConfig, attempt: int) -> float:
    if config.strategy == RetryStrategy.FIXED:
        delay = config.base_delay
    elif config.strategy == RetryStrategy.EXPONENTIAL:
        delay = config.base_delay * (2 ** attempt)
    else:  # EXPONENTIAL_WITH_JITTER
        delay = config.base_delay * (2 ** attempt)
        jitter = random.uniform(0.5, 1.5)
        delay = delay * jitter
    return min(delay, config.max_delay)

import redis
import time

class DistributedRateLimiter:
    def __init__(self, redis_client: redis.Redis, max_rpm: int = 100):
        self.redis = redis_client
        self.max_rpm = max_rpm

    def is_allowed(self, key: str = "default") -> bool:
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        current, _ = pipe.execute()
        return current <= self.max_rpm

LUA_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], 60)
end
return current
"""

class DistributedRateLimiter:
    def __init__(self, redis_client: redis.Redis, max_rpm: int = 100):
        self.redis = redis_client
        self.max_rpm = max_rpm
        self.script = self.redis.register_script(LUA_SCRIPT)

    def is_allowed(self, key: str = "default") -> bool:
        current = self.script(keys=[key])
        return current <= self.max_rpm

import time
import threading
import statistics
from dataclasses import dataclass, field
from typing import List, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class LoadTestResult:
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_time_seconds: float = 0.0
    qps: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successful / max(1, self.total_requests)

    @property
    def p50_latency(self) -> float:
        if not self.latencies: return 0
        return statistics.median(self.latencies)

    @property
    def p95_latency(self) -> float:
        if not self.latencies: return 0
        sorted_l = sorted(self.latencies)
        idx = int(len(sorted_l) * 0.95)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    @property
    def p99_latency(self) -> float:
        if not self.latencies: return 0
        sorted_l = sorted(self.latencies)
        idx = int(len(sorted_l) * 0.99)
        return sorted_l[min(idx, len(sorted_l) - 1)]

import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: float = 30.0,
                 half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        else:  # HALF_OPEN
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

    def on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
        self.failure_count = 0

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

class TenantRateLimiter:
    def __init__(self, redis_client, tenant_id: str, 
                 rpm_limit: int, tpm_limit: int):
        self.redis = redis_client
        self.tenant_id = tenant_id
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit

    def check_rpm(self) -> bool:
        key = f"ratelimit:{self.tenant_id}:rpm"
        lua = """
        local current = redis.call('INCR', KEYS[1])
        if current == 1 then
            redis.call('EXPIRE', KEYS[1], 60)
        end
        return current
        """
        current = self.redis.eval(lua, 1, key)
        return current <= self.rpm_limit

    def check_tpm(self, token_count: int) -> bool:
        key = f"ratelimit:{self.tenant_id}:tpm"
        lua = """
        local current = redis.call('INCRBY', KEYS[1], ARGV[1])
        if current == tonumber(ARGV[1]) then
            redis.call('EXPIRE', KEYS[1], 60)
        end
        return current
        """
        current = self.redis.eval(lua, 1, key, token_count)
        return current <= self.tpm_limit

import asyncio
from asyncio import Semaphore

class StreamingRateLimiter:
    def __init__(self, max_concurrent: int = 50, rpm_limit: int = 200):
        self.semaphore = Semaphore(max_concurrent)
        self.rpm_limit = rpm_limit
        self.request_count = 0
        self.window_start = time.monotonic()

    async def acquire(self):
        # 先检查 RPM
        now = time.monotonic()
        if now - self.window_start >= 60:
            self.request_count = 0
            self.window_start = now
        
        if self.request_count >= self.rpm_limit:
            raise RateLimitExceeded("RPM 限制已达上限")
        
        # 再检查并发连接数
        await self.semaphore.acquire()
        self.request_count += 1

    def release(self):
        self.semaphore.release()

from locust import HttpUser, task, between, events

class AIChatUser(HttpUser):
    wait_time = between(1, 3)  # 每个用户间隔 1-3 秒

    @task(3)
    def send_question(self):
        questions = [
            "什么是机器学习？",
            "帮我写一段 Python 代码",
            "解释一下量子计算",
        ]
        import random
        question = random.choice(questions)
        
        with self.client.post("/api/chat", 
                              json={"question": question},
                              catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("被限流了")
            else:
                response.failure(f"错误: {response.status_code}")

    @task(1)
    def send_long_question(self):
        long_question = "请详细解释" + "。" * 500
        with self.client.post("/api/chat",
                              json={"question": long_question},
                              catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("被限流了")

SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])
local member = ARGV[4]

-- 移除窗口外的请求
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- 当前窗口内的请求数
local current = redis.call('ZCARD', key)

if current < max_requests then
    -- 添加新请求
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window)
    return 0  -- 允许
else
    return 1  -- 拒绝
end
"""

class SlidingWindowRateLimiter:
    def __init__(self, redis_client, max_rpm: int = 100):
        self.redis = redis_client
        self.max_rpm = max_rpm
        self.window_ms = 60000  # 60 秒
        self.script = self.redis.register_script(SLIDING_WINDOW_LUA)
        import uuid
        self._uuid = uuid.uuid4

    def is_allowed(self, key: str = "default") -> bool:
        now_ms = int(time.time() * 1000)
        member = f"{now_ms}:{self._uuid()}"
        result = self.script(
            keys=[f"sliding:{key}"],
            args=[now_ms, self.window_ms, self.max_rpm, member]
        )
        return result == 0

import asyncio
import time

class AsyncTokenBucket:
    def __init__(self, capacity: int = 100, refill_rate: float = 10.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

    async def acquire_with_wait(self, timeout: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if await self.acquire():
                return True
            await asyncio.sleep(0.1)
        return False
