from openai import OpenAI
client = OpenAI(api_key="xxx", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
response = client.chat.completions.create(model="qwen-max", messages=[{"role": "user", "content": "你好"}])

# 全局初始化一次
client = OpenAI(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    timeout=30.0,          # 全局超时
    max_retries=0,         # 关闭默认重试，我们自己控制
)

response = client.chat.completions.create(
    model="qwen-max",
    messages=[{"role": "user", "content": "请写一篇文章"}],
    stream=True,  # 开启流式
)

full_content = ""
for chunk in response:
    if chunk.choices and chunk.choices[0].delta.content:
        content = chunk.choices[0].delta.content
        full_content += content
        print(content, end="", flush=True)

print(f"\n[完成] 共收到 {len(full_content)} 字符")

from openai import OpenAI
import httpx

# 设置连接超时和读取超时
client = OpenAI(
    api_key="xxx",
    timeout=httpx.Timeout(
        connect=10.0,    # 连接超时10秒
        read=60.0,       # 读取超时60秒
        write=10.0,      # 写入超时10秒
        pool=10.0,       # 从连接池获取连接的超时
    ),
)

import os
from openai import OpenAI

# 从环境变量读取
api_key = os.environ.get("DASHSCOPE_API_KEY")
if not api_key:
    raise RuntimeError("DASHSCOPE_API_KEY 环境变量未设置")

client = OpenAI(api_key=api_key, base_url="...")

from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
resp = client.chat.completions.create(model="qwen-max",
    messages=[{"role": "user", "content": "你好，请介绍一下你自己"}],
    temperature=0.3, max_tokens=500)
print(resp.choices[0].message.content)

from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError
import os, logging

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", timeout=30.0)

def call_api(messages):
    try:
        resp = client.chat.completions.create(model="qwen-max", messages=messages,
            temperature=0.3, max_tokens=1000)
        choice = resp.choices[0]
        if choice.finish_reason == "length":
            logger.warning("输出被截断，建议增加max_tokens")
        elif choice.finish_reason == "content_filter":
            logger.warning("内容被过滤")
        return choice.message.content
    except RateLimitError:
        logger.error("触发限流，请稍后重试")
        raise
    except APITimeoutError:
        logger.error("请求超时")
        raise
    except APIConnectionError:
        logger.error("连接失败，检查网络")
        raise

from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError
import os, time, random, logging
from functools import wraps

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    timeout=30.0, max_retries=0)  # 关闭SDK默认重试

RETRYABLE_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError)

def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0, jitter=1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RETRYABLE_ERRORS as e:
                    if attempt == max_retries - 1:
                        logger.error(f"重试{max_retries}次后仍失败: {e}")
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay) + random.uniform(0, jitter)
                    logger.warning(f"请求失败，第{attempt+1}次重试，等待{delay:.1f}秒")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3)
def call_api(messages, temperature=0.3, max_tokens=1000):
    resp = client.chat.completions.create(model="qwen-max", messages=messages,
        temperature=temperature, max_tokens=max_tokens)
    choice = resp.choices[0]
    logger.info(f"Token消耗: prompt={resp.usage.prompt_tokens}, completion={resp.usage.completion_tokens}")
    if choice.finish_reason == "length":
        logger.warning("输出被截断")
    return choice.message.content

from openai import OpenAI, APIConnectionError
import os, logging

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", timeout=60.0)

def stream_call_api(messages, max_retries=2):
    full_content = ""
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(model="qwen-max", messages=messages,
                stream=True, temperature=0.7, max_tokens=4000)
            for chunk in resp:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield content
            return
        except APIConnectionError:
            if attempt < max_retries:
                messages.append({"role": "assistant", "content": full_content})
                messages.append({"role": "user", "content": "[继续]"})
            else:
                raise
    yield full_content

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
import os

client = OpenAI(api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", timeout=30.0)

@retry(stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)))
def call_api(messages):
    resp = client.chat.completions.create(model="qwen-max", messages=messages,
        temperature=0.3, max_tokens=1000)
    return resp.choices[0].message.content

import asyncio
from openai import AsyncOpenAI
import os

client = AsyncOpenAI(api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", timeout=30.0)

async def call_api(messages):
    resp = await client.chat.completions.create(model="qwen-max", messages=messages,
        temperature=0.3, max_tokens=1000)
    return resp.choices[0].message.content

async def batch_call(prompts):
    tasks = [call_api([{"role": "user", "content": p}]) for p in prompts]
    return await asyncio.gather(*tasks, return_exceptions=True)

asyncio.run(batch_call(["你好", "介绍一下Python", "写一首诗"]))

import httpx, os, json

def call_api_raw(prompt):
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {"Authorization": f"Bearer {os.environ.get('DASHSCOPE_API_KEY')}"}
    payload = {"model": "qwen-max", "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.3, "max_tokens": 1000}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

def stream_api_raw(prompt):
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {"Authorization": f"Bearer {os.environ.get('DASHSCOPE_API_KEY')}"}
    payload = {"model": "qwen-max", "messages": [{"role": "user", "content": prompt}],
               "stream": True, "temperature": 0.7}
    with httpx.Client(timeout=60.0) as client:
        with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]": break
                    data = json.loads(data_str)
                    if data.get("choices") and data["choices"][0].get("delta", {}).get("content"):
                        yield data["choices"][0]["delta"]["content"]

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
import os

llm = ChatOpenAI(model="qwen-max", openai_api_key=os.environ.get("DASHSCOPE_API_KEY"),
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1", temperature=0.3)
response = llm.invoke([HumanMessage(content="你好")])
print(response.content)

import requests
import json

def test_basic_api_call():
    """测试基础 API 调用"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": "Bearer YOUR_API_KEY",
        "Content-Type": "application/json",
    }
    data = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": "你是测试助手"},
            {"role": "user", "content": "解释什么是测试用例"},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }

    response = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"状态码: {response.status_code}")

    result = response.json()
    print(f"输出: {result['choices'][0]['message']['content'][:100]}...")
    print(f"Token: 输入{result['usage']['prompt_tokens']}, 输出{result['usage']['completion_tokens']}")

test_basic_api_call()

def test_error_scenarios():
    """测试异常场景"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    # 场景1：无效 API Key
    print("=== 场景1：无效 API Key ===")
    resp = requests.post(url, headers={"Authorization": "Bearer invalid_key"}, json={
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": "测试"}],
    }, timeout=30)
    print(f"状态码: {resp.status_code}, 响应: {resp.text[:100]}")

    # 场景2：超长大文本
    print("\n=== 场景2：超长大文本 ===")
    long_text = "A" * 50000
    resp = requests.post(url, headers={"Authorization": "Bearer YOUR_API_KEY"}, json={
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": long_text}],
        "max_tokens": 100,
    }, timeout=30)
    print(f"状态码: {resp.status_code}")

    # 场景3：并发请求
    print("\n=== 场景3：并发请求 ===")
    import concurrent.futures

    def call_api(i):
        resp = requests.post(url, headers={"Authorization": "Bearer YOUR_API_KEY"}, json={
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": f"测试{i}"}],
            "max_tokens": 50,
        }, timeout=30)
        return resp.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(call_api, i) for i in range(10)]
        results = [f.result() for f in futures]
        print(f"并发结果: {results}")

test_error_scenarios()

import time

def test_retry_mechanism():
    """测试重试机制"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def call_with_retry(max_retries=3):
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers={"Authorization": "Bearer YOUR_API_KEY"}, json={
                    "model": "qwen-plus",
                    "messages": [{"role": "user", "content": "测试重试"}],
                    "max_tokens": 100,
                }, timeout=10)

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"  ⚠️ 限流，等待 {wait_time}s 后重试")
                    time.sleep(wait_time)
                elif resp.status_code == 401:
                    print(f"  ❌ 认证失败，不重试")
                    return None
                else:
                    print(f"  ❌ 状态码 {resp.status_code}")
                    return None
            except requests.exceptions.Timeout:
                print(f"  ⚠️ 超时，等待 {2 ** attempt}s 后重试")
                time.sleep(2 ** attempt)

        print("  ❌ 重试次数用尽")
        return None

    print("=== 重试机制测试 ===")
    result = call_with_retry()
    if result:
        print(f"✅ 成功: {result['choices'][0]['message']['content'][:50]}...")
    else:
        print("❌ 失败")

test_retry_mechanism()
