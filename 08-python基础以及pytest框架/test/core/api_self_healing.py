#!/usr/bin/env python3
# api_self_healing.py - API 自愈引擎
"""
API 自愈引擎

功能：
1. 智能重试 — 网络抖动/5xx 自动重试，断言失败不重试
2. 状态轮询 — 异步接口自动等待而非 fixed sleep
3. 智能跳过 — 前置步骤失败时，后续步骤标记为 skip

与 self_healing/retry_engine.py 的区别：
- retry_engine.py 是 pytest hook 级别，工作在用例级别
- api_self_healing.py 是 API 客户端级别，工作在请求级别
"""
import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


# ==================== 重试配置 ====================

class APIRetryConfig:
    """API 重试配置"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 10.0,
                 backoff_factor: float = 2.0,
                 retry_on_status_codes: list = None,
                 retry_on_exceptions: tuple = None):
        """
        参数：
        - max_retries: 最大重试次数（默认3次）
        - base_delay: 首次重试等待秒数（默认1秒）
        - max_delay: 最大等待秒数（默认10秒）
        - backoff_factor: 退避因子（默认2.0，即每次翻倍）
        - retry_on_status_codes: 需要重试的 HTTP 状态码列表
        - retry_on_exceptions: 需要重试的异常类型元组
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retry_on_status_codes = retry_on_status_codes or [500, 502, 503, 504, 429]
        self.retry_on_exceptions = retry_on_exceptions or (
            ConnectionError,
            TimeoutError,
            ConnectionRefusedError,
            ConnectionResetError,
        )
    
    def get_delay(self, attempt: int) -> float:
        """计算第 N 次重试的等待时间（指数退避）"""
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)
    
    def should_retry(self, status_code: int = None, exception: Exception = None, attempt: int = 0) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_retries:
            return False
        
        # 逻辑错误（4xx）不重试
        if status_code and 400 <= status_code < 500:
            if status_code == 429:  # 限流可以重试
                return True
            return False
        
        # 5xx 错误可以重试
        if status_code and status_code in self.retry_on_status_codes:
            return True
        
        # 网络异常可以重试
        if exception and isinstance(exception, self.retry_on_exceptions):
            return True
        
        return False


# ==================== 重试统计 ====================

class RetryStats:
    """重试统计器"""
    
    def __init__(self):
        self.total_requests = 0
        self.total_retries = 0
        self.saved_by_retry = 0
        self.failed_after_retry = 0
        self.retry_history = []  # [(endpoint, attempt, status_code, success)]
    
    def record_request(self, endpoint: str, attempt: int, status_code: int = None, 
                       success: bool = False, reason: str = ""):
        """记录一次请求"""
        self.total_requests += 1
        if attempt > 1:
            self.total_retries += 1
        
        self.retry_history.append({
            'endpoint': endpoint,
            'attempt': attempt,
            'status_code': status_code,
            'success': success,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        if attempt > 1 and success:
            self.saved_by_retry += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        return {
            'total_requests': self.total_requests,
            'total_retries': self.total_retries,
            'saved_by_retry': self.saved_by_retry,
            'failed_after_retry': self.failed_after_retry,
            'retry_rate': f"{self.total_retries / max(1, self.total_requests) * 100:.1f}%"
        }
    
    def reset(self):
        """重置统计"""
        self.__init__()


# ==================== 状态轮询 ====================

class StatusPoller:
    """状态轮询器 — 用于异步接口等待"""
    
    def __init__(self, max_wait: float = 30.0, interval: float = 2.0):
        """
        参数：
        - max_wait: 最大等待秒数（默认30秒）
        - interval: 轮询间隔秒数（默认2秒）
        """
        self.max_wait = max_wait
        self.interval = interval
    
    def wait_for_condition(self, check_func: Callable, 
                           success_condition: Callable = None,
                           endpoint: str = "unknown") -> Dict[str, Any]:
        """
        等待条件满足
        
        参数：
        - check_func: 检查函数，返回 (success: bool, data: Any)
        - success_condition: 成功条件函数，返回 bool
        - endpoint: 接口标识（用于日志）
        
        返回：
        - Dict: {'success': bool, 'data': Any, 'attempts': int, 'elapsed': float}
        """
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < self.max_wait:
            attempts += 1
            
            try:
                success, data = check_func()
                
                if success:
                    if success_condition is None or success_condition(data):
                        elapsed = time.time() - start_time
                        logger.info(f"✅ 条件满足 ({endpoint}): 耗时 {elapsed:.1f}s, 尝试 {attempts} 次")
                        return {
                            'success': True,
                            'data': data,
                            'attempts': attempts,
                            'elapsed': elapsed
                        }
            except Exception as e:
                logger.debug(f"检查失败 ({endpoint}): {str(e)}")
            
            time.sleep(self.interval)
        
        elapsed = time.time() - start_time
        logger.warning(f"⏰ 等待超时 ({endpoint}): 耗时 {elapsed:.1f}s, 尝试 {attempts} 次")
        return {
            'success': False,
            'data': None,
            'attempts': attempts,
            'elapsed': elapsed
        }


# ==================== 智能跳过 ====================

class SmartSkipper:
    """智能跳过器 — 前置步骤失败时跳过后续步骤"""
    
    def __init__(self):
        self._failed_steps = set()  # 失败的步骤集合
    
    def mark_failed(self, step_name: str):
        """标记步骤失败"""
        self._failed_steps.add(step_name)
        logger.info(f"🔴 标记步骤失败: {step_name}")
    
    def should_skip(self, step_name: str, depends_on: list = None) -> bool:
        """
        判断是否应该跳过
        
        参数：
        - step_name: 当前步骤名称
        - depends_on: 依赖的步骤列表
        
        返回：
        - bool: True 表示应该跳过
        """
        if depends_on:
            for dep in depends_on:
                if dep in self._failed_steps:
                    logger.info(f"⏭️ 跳过步骤 {step_name}（依赖 {dep} 失败）")
                    return True
        return False
    
    def get_skipped_steps(self) -> list:
        """获取所有跳过的步骤"""
        return list(self._failed_steps)
    
    def reset(self):
        """重置"""
        self._failed_steps.clear()


# ==================== API 自愈客户端 ====================

class SelfHealingAPIClient:
    """
    API 自愈客户端
    
    包装现有的 API 客户端，添加自愈能力：
    1. 智能重试
    2. 状态轮询
    3. 智能跳过
    """
    
    def __init__(self, api_client, retry_config: APIRetryConfig = None):
        """
        参数：
        - api_client: 原始的 API 客户端
        - retry_config: 重试配置
        """
        self.api_client = api_client
        self.retry_config = retry_config or APIRetryConfig()
        self.stats = RetryStats()
        self.poller = StatusPoller()
        self.skipper = SmartSkipper()
    
    def request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        发送请求（带自愈能力）
        
        参数：
        - method: HTTP 方法（GET/POST/PUT/DELETE）
        - endpoint: 接口路径
        - **kwargs: 其他请求参数
        
        返回：
        - 响应对象
        """
        last_exception = None
        last_response = None
        
        for attempt in range(1, self.retry_config.max_retries + 1):
            try:
                # 调用原始客户端
                # 支持两种模式：
                # 1. SeckillAPIClient 模式：self.api_client.client.get() (client 是 requests.Session)
                # 2. 直接客户端模式：self.api_client.get()
                target = getattr(self.api_client, 'client', self.api_client)
                
                if method.upper() == 'GET':
                    response = target.get(endpoint, **kwargs)
                elif method.upper() == 'POST':
                    response = target.post(endpoint, **kwargs)
                elif method.upper() == 'PUT':
                    response = target.put(endpoint, **kwargs)
                elif method.upper() == 'DELETE':
                    response = target.delete(endpoint, **kwargs)
                else:
                    raise ValueError(f"不支持的 HTTP 方法: {method}")
                
                status_code = response.status_code
                
                # 记录统计
                self.stats.record_request(endpoint, attempt, status_code, 
                                         success=(200 <= status_code < 500))
                
                # 判断是否需要重试
                if not self.retry_config.should_retry(status_code=status_code, attempt=attempt):
                    return response
                
                # 需要重试
                delay = self.retry_config.get_delay(attempt)
                logger.warning(f"🔄 重试 {endpoint} (尝试 {attempt}/{self.retry_config.max_retries}), "
                             f"状态码 {status_code}, 等待 {delay:.1f}s")
                time.sleep(delay)
                last_response = response
                
            except Exception as e:
                last_exception = e
                
                # 记录统计
                self.stats.record_request(endpoint, attempt, reason=str(e))
                
                # 判断是否需要重试
                if not self.retry_config.should_retry(exception=e, attempt=attempt):
                    raise
                
                # 需要重试
                delay = self.retry_config.get_delay(attempt)
                logger.warning(f"🔄 重试 {endpoint} (尝试 {attempt}/{self.retry_config.max_retries}), "
                             f"异常 {type(e).__name__}, 等待 {delay:.1f}s")
                time.sleep(delay)
        
        # 所有重试都失败了
        if last_response:
            logger.error(f"❌ {endpoint} 重试 {self.retry_config.max_retries} 次后仍失败")
            self.stats.failed_after_retry += 1
            return last_response
        elif last_exception:
            logger.error(f"❌ {endpoint} 重试 {self.retry_config.max_retries} 次后仍异常")
            self.stats.failed_after_retry += 1
            raise last_exception
    
    def get(self, endpoint: str, **kwargs) -> Any:
        """GET 请求（带自愈）"""
        return self.request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> Any:
        """POST 请求（带自愈）"""
        return self.request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> Any:
        """PUT 请求（带自愈）"""
        return self.request('PUT', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Any:
        """DELETE 请求（带自愈）"""
        return self.request('DELETE', endpoint, **kwargs)
    
    def wait_for_status(self, endpoint: str, check_func: Callable, 
                       success_condition: Callable = None) -> Dict[str, Any]:
        """
        等待接口状态满足条件
        
        参数：
        - endpoint: 接口路径
        - check_func: 检查函数
        - success_condition: 成功条件
        
        返回：
        - Dict: 轮询结果
        """
        return self.poller.wait_for_condition(check_func, success_condition, endpoint)
    
    def mark_step_failed(self, step_name: str):
        """标记步骤失败"""
        self.skipper.mark_failed(step_name)
    
    def should_skip_step(self, step_name: str, depends_on: list = None) -> bool:
        """判断是否应该跳过步骤"""
        return self.skipper.should_skip(step_name, depends_on)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取自愈统计"""
        return self.stats.get_summary()
    
    def reset(self):
        """重置所有状态"""
        self.stats.reset()
        self.skipper.reset()
