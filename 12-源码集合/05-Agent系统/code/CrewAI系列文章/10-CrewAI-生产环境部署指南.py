# logging_config.py
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    """配置日志系统"""
    
    # 创建日志目录
    os.makedirs('logs', exist_ok=True)
    
    # 创建 logger
    logger = logging.getLogger('crewai')
    logger.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # 文件处理器（轮转）
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# 使用
logger = setup_logging()

# agents/logger_agent.py
import logging
from datetime import datetime

logger = logging.getLogger('crewai.agent')

def log_agent_action(agent_name: str, action: str, details: str = ""):
    """记录 Agent 动作"""
    logger.info(f"[{agent_name}] {action} - {details}")

def log_agent_error(agent_name: str, error: Exception):
    """记录 Agent 错误"""
    logger.error(f"[{agent_name}] Error: {str(error)}", exc_info=True)

def log_agent_performance(agent_name: str, duration: float):
    """记录 Agent 性能"""
    logger.info(f"[{agent_name}] Execution time: {duration:.2f}s")

# 在 Agent 中使用
from crewai import Agent

def create_logged_agent(name: str, **kwargs):
    """创建带日志的 Agent"""
    agent = Agent(role=name, **kwargs)
    
    # 包装 kickoff 方法
    original_kickoff = agent.kickoff
    
    def logged_kickoff(*args, **kwargs):
        start_time = datetime.now()
        log_agent_action(name, "started")
        
        try:
            result = original_kickoff(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            log_agent_performance(name, duration)
            log_agent_action(name, "completed")
            return result
        except Exception as e:
            log_agent_error(name, e)
            raise
    
    agent.kickoff = logged_kickoff
    return agent

# app/main.py
from fastapi import FastAPI
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
import os

app = FastAPI()

# 初始化 Sentry
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FastApiIntegration(),
    ],
    traces_sample_rate=1.0,  # 采样率
    environment=os.getenv("ENVIRONMENT", "production"),
    release="crewai@1.0.0"
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/test-error")
async def test_error():
    """测试错误上报"""
    raise ValueError("This is a test error")

# app/agents/error_handler.py
import sentry_sdk
from contextlib import contextmanager

@contextmanager
def agent_error_context(agent_name: str, task_description: str):
    """Agent 错误上下文管理器"""
    try:
        # 设置上下文
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("agent", agent_name)
            scope.set_tag("task", task_description)
            scope.set_extra("task_description", task_description)
            yield
    except Exception as e:
        # 记录错误
        sentry_sdk.capture_exception(e)
        raise

# 使用
def execute_agent_task(agent, task):
    with agent_error_context(agent.role, task.description):
        return agent.kickoff()

# app/core/cache.py
import redis
import json
from functools import wraps
import hashlib

redis_client = redis.Redis.from_url("redis://redis:6379/0")

def cache_result(expire_seconds: int = 3600):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            key_data = f"{func.__name__}:{args}:{kwargs}"
            key = hashlib.md5(key_data.encode()).hexdigest()
            
            # 尝试从缓存获取
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            redis_client.setex(
                key,
                expire_seconds,
                json.dumps(result, ensure_ascii=False)
            )
            
            return result
        return wrapper
    return decorator

# 使用
@cache_result(expire_seconds=3600)
def execute_agent_task(agent_role: str, task_desc: str):
    """执行 Agent 任务（带缓存）"""
    # ...

# app/core/rate_limiter.py
from fastapi import HTTPException
from datetime import datetime, timedelta
import redis

redis_client = redis.Redis.from_url("redis://redis:6379/0")

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, client_id: str) -> bool:
        """检查请求是否允许"""
        key = f"rate_limit:{client_id}"
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=self.window_seconds)
        
        # 移除过期记录
        redis_client.zremrangebyscore(key, 0, window_start.timestamp())
        
        # 统计当前窗口请求数
        request_count = redis_client.zcard(key)
        
        if request_count >= self.max_requests:
            return False
        
        # 添加新请求
        redis_client.zadd(key, {f"{current_time.timestamp()}": current_time.timestamp()})
        redis_client.expire(key, self.window_seconds * 2)
        
        return True

# 使用
rate_limiter = RateLimiter(max_requests=60, window_seconds=60)

@app.post("/api/execute")
async def execute_task(request: TaskRequest):
    client_id = request.client_id
    
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    # 执行任务
    return execute_agent_task(request)

# app/core/timeout.py
import asyncio
from functools import wraps

def timeout(seconds: int):
    """超时装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function timed out after {seconds} seconds")
        return wrapper
    return decorator

# 使用
@timeout(seconds=300)  # 5 分钟超时
async def execute_long_task(agent, task):
    return await agent.kickoff_async()
