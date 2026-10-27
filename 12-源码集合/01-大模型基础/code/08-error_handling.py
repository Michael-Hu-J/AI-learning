import time
import random
from functools import wraps

RETRYABLE = {429, 500, 502, 503}

def is_retryable(exc):
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return code in RETRYABLE

def retry(tries=3, delay=2, max_delay=60, jitter=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(tries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == tries - 1:
                        raise
                    if is_retryable(e):
                        wait = delay * (2 ** attempt)
                        if jitter:
                            wait = wait * random.uniform(0.5, 1.5)
                        wait = min(wait, max_delay)
                        print(f"第{attempt+1}次失败，{wait:.1f}秒后重试: {e}")
                        time.sleep(wait)
                    else:
                        raise
            return None
        return wrapper
    return decorator

import time
import random
import logging
from typing import Set, Type, Callable, Any

logger = logging.getLogger(__name__)

class RetryConfig:
    def __init__(self, max_retries=3, base_delay=2.0, max_delay=60.0,
                 jitter=True, retryable_exceptions=None, on_retry=None, on_exhausted=None):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or set()
        self.on_retry = on_retry
        self.on_exhausted = on_exhausted

class ProductionRetry:
    def __init__(self, config):
        self.config = config

    def execute(self, func, *args, **kwargs):
        for attempt in range(self.config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"重试成功，第{attempt}次尝试")
                return result
            except Exception as e:
                if not self._is_retryable(e):
                    logger.warning(f"不可重试的错误: {e}")
                    raise
                if attempt == self.config.max_retries:
                    logger.error(f"重试次数耗尽: {e}")
                    if self.config.on_exhausted:
                        self.config.on_exhausted(e, args, kwargs)
                    raise
                wait = self._calculate_delay(attempt)
                logger.warning(f"第{attempt+1}次失败，{wait:.1f}秒后重试: {e}")
                if self.config.on_retry:
                    self.config.on_retry(e, attempt, wait)
                time.sleep(wait)

    def _is_retryable(self, exc):
        if not self.config.retryable_exceptions:
            return True
        return any(isinstance(exc, t) for t in self.config.retryable_exceptions)

    def _calculate_delay(self, attempt):
        delay = self.config.base_delay * (2 ** attempt)
        if self.config.jitter:
            delay = delay * random.uniform(0.5, 1.5)
        return min(delay, self.config.max_delay)

import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60.0,
                 success_threshold=3, time_window=30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.time_window = time_window
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
            else:
                raise Exception("熔断器打开，拒绝调用")
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def _on_failure(self):
        now = time.time()
        if now - self.last_failure_time > self.time_window:
            self.failure_count = 0
        self.failure_count += 1
        self.last_failure_time = now
        if self.failure_count >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state):
        old_state = self.state
        self.state = new_state
        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
        logger.warning(f"熔断器状态变更: {old_state.value} -> {new_state.value}")

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
def call_api():
    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": "你好"}],
        timeout=30,
    )
    return response.choices[0].message.content

def call_llm_with_resilience(prompt):
    """带完整容错的LLM调用"""
    @retry(tries=3, delay=2)
    def _call():
        return client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": prompt}],
            timeout=30,
        )

    try:
        result = circuit_breaker.call(_call)
        return result.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        return get_fallback_response(prompt)

def test_error_handling():
    """测试错误处理逻辑"""

    # 测试 1：400 不应重试
    with pytest.raises(ValueError):
        call_llm_with_retry("")  # 空 Prompt → 400

    # 测试 2：401 不应重试
    with pytest.raises(AuthError):
        call_llm_with_retry("test", api_key="invalid")  # 无效 Key → 401

    # 测试 3：429 应重试
    call_count = 0

    def mock_429_then_success():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError("429")
        return "success"

    result = call_with_retry(mock_429_then_success)
    assert result == "success"
    assert call_count == 3  # 重试了 2 次

    # 测试 4：500 应重试
    call_count = 0

    def mock_500_then_success():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ServerError("500")
        return "success"

    result = call_with_retry(mock_500_then_success)
    assert result == "success"

import random

def test_retry_cost():
    """测试重试对成本的影响"""
    total_calls = 0
    for _ in range(100):
        total_calls += 1
        if random.random() < 0.1:  # 10% 概率需要重试 1 次
            total_calls += 1

    # 实际 110 次 vs 预期 100 次，成本放大 10%
    print(f"实际调用: {total_calls} 次 (预期 100 次, 放大 {total_calls/100:.1f}x)")

import requests

def test_error_codes():
    """测试各种错误码"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    test_cases = [
        ("无效 API Key", {"Authorization": "Bearer invalid_key"}, 401),
        ("缺少 model", {"Authorization": "Bearer YOUR_API_KEY"}, 400),
        ("无效 model", {"Authorization": "Bearer YOUR_API_KEY"}, 400),
    ]

    for name, headers, expected_code in test_cases:
        data = {
            "messages": [{"role": "user", "content": "测试"}],
            "max_tokens": 100,
        }
        if name != "缺少 model":
            data["model"] = "invalid-model" if name == "无效 model" else "qwen-plus"

        resp = requests.post(url, headers=headers, json=data)
        status = "✅" if resp.status_code == expected_code else "❌"
        print(f"{status} {name}: 预期{expected_code}, 实际{resp.status_code}")

# test_error_codes()

import time
import random

class RetryTester:
    """重试策略测试器"""

    def __init__(self, max_retries=3, base_delay=1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.attempts = 0

    def call_with_retry(self, func, *args, **kwargs):
        for attempt in range(self.max_retries + 1):
            self.attempts += 1
            try:
                result = func(*args, **kwargs)
                if result.get("status_code") == 200:
                    return result
                elif result.get("status_code") == 429:
                    delay = self.base_delay * (2 ** attempt)
                    print(f"  ⚠️ 429 限流，等待 {delay:.1f}s 后重试 (第{attempt+1}次)")
                    time.sleep(delay)
                else:
                    print(f"  ❌ 状态码 {result.get('status_code')}，不重试")
                    return result
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    print(f"  ⚠️ 异常 {e}，等待 {delay:.1f}s 后重试 (第{attempt+1}次)")
                    time.sleep(delay)
                else:
                    print(f"  ❌ 重试次数用尽: {e}")
                    return None
        return None

def mock_api():
    if random.random() < 0.3:
        return {"status_code": 429}
    return {"status_code": 200, "data": "success"}

tester = RetryTester()
result = tester.call_with_retry(mock_api)
print(f"总尝试次数: {tester.attempts}, 最终结果: {result}")

import logging
import re

def sanitize_log(text: str) -> str:
    """日志脱敏"""
    text = re.sub(r"sk-[a-zA-Z0-9-]+", "sk-***-***-***", text)
    text = re.sub(r"\d{17}[\dXx]", lambda m: m.group()[:3] + "***" + m.group()[-4:], text)
    text = re.sub(r"1[3-9]\d{9}", lambda m: m.group()[:3] + "****" + m.group()[-4:], text)
    return text

logging.basicConfig(level=logging.DEBUG, format="%(message)s")
logger = logging.getLogger(__name__)

error_response = {
    "error": {
        "message": "Invalid API key: sk-xxxxx-xxxxx-xxxxx",
        "type": "invalid_request_error",
        "code": "invalid_api_key",
    }
}

logger.debug(f"错误响应(脱敏): {sanitize_log(str(error_response))}")
