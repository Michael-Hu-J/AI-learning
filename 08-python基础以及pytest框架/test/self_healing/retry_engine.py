# retry_engine.py - 智能重试引擎
"""
智能重试引擎

功能：
1. 条件重试 — 只有特定异常才重试（如网络超时），断言失败不重试
2. 指数退避 — 第1次等2秒，第2次等4秒，第3次等8秒
3. 最大重试次数和超时时间双重控制

和 utils/retry.py 的区别：
- utils/retry.py 是装饰器模式，适合单函数重试
- self_healing/retry_engine.py 是 pytest hook 集成，工作在用例级别
"""
import time
import logging

logger = logging.getLogger(__name__)


# 常见"可重试"的异常类型
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    ConnectionRefusedError,
    ConnectionResetError,
    ConnectionAbortedError,
)

# 常见"不可重试"的异常类型（重试也没用）
NON_RETRYABLE_EXCEPTIONS = (
    AssertionError,
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    ImportError,
    SyntaxError,
    NameError,
)


def is_timeout_or_network(exc: Exception) -> bool:
    """判断异常是否属于网络/超时类（重试可能有用）"""
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


def is_logic_error(exc: Exception) -> bool:
    """判断异常是否属于逻辑错误（重试也没用）"""
    return isinstance(exc, NON_RETRYABLE_EXCEPTIONS)


class RetryConfig:
    """重试配置"""

    def __init__(self, max_retries: int = 3, base_delay: float = 2.0,
                 max_delay: float = 30.0, backoff_factor: float = 2.0):
        """
        参数说明：
        - max_retries: 最大重试次数（默认3次）
        - base_delay: 首次重试等待秒数（默认2秒）
        - max_delay: 最大等待秒数（默认30秒）
        - backoff_factor: 退避因子（默认2.0，即每次翻倍）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def get_delay(self, attempt: int) -> float:
        """计算第 N 次重试的等待时间（指数退避）"""
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        判断是否应该重试。
        逻辑错误不重试，只有网络/超时类异常才重试。
        """
        if is_logic_error(exception):
            logger.debug(f"逻辑错误（{type(exception).__name__}），不重试")
            return False
        if attempt >= self.max_retries:
            return False
        return True


# 全局默认配置
DEFAULT_CONFIG = RetryConfig()


def should_retry_by_outcome(outcome: str) -> bool:
    """
    根据 pytest 的 outcome 判断是否应该重试。
    outcome 取值：'passed', 'failed', 'skipped'
    """
    if outcome == "passed":
        return False  # 通过了还重试什么
    if outcome == "skipped":
        return False  # 跳过了不重试
    if outcome == "failed":
        return True   # 失败了，具体是否重试还要看异常类型
    return False


class RetryTracker:
    """
    重试跟踪器（跨 pytest 会话共享状态）。
    记录每个用例的重试次数和最终结果。
    """

    def __init__(self):
        self._retries = {}  # {nodeid: attempt_count}
        self._history = []  # [(nodeid, attempt, outcome, reason)]

    def record_attempt(self, nodeid: str, attempt: int, outcome: str,
                       reason: str = ""):
        """记录一次尝试"""
        key = f"{nodeid}#attempt{attempt}"
        self._retries[key] = outcome
        self._history.append((nodeid, attempt, outcome, reason))

    def get_attempt_count(self, nodeid: str) -> int:
        """获取某个用例已重试的次数"""
        count = 0
        for item in self._history:
            if item[0] == nodeid and item[1] > 1:
                count += 1
        return count

    def get_summary(self) -> dict:
        """获取重试统计摘要"""
        total = len(set(h[0] for h in self._history))
        retried = len(set(h[0] for h in self._history if h[1] > 1))
        failed_after_retry = len(set(
            h[0] for h in self._history
            if h[2] == "failed" and h[1] > 1
        ))
        saved_by_retry = len(set(
            h[0] for h in self._history
            if h[2] == "passed" and h[1] > 1
        ))
        return {
            "total_tests": total,
            "retried_tests": retried,
            "failed_after_retry": failed_after_retry,
            "saved_by_retry": saved_by_retry,
        }


# 全局重试跟踪器
retry_tracker = RetryTracker()
