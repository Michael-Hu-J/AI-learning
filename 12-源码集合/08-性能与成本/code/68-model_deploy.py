import requests

response = requests.post("http://localhost:11434/api/chat", json={
    "model": "qwen2.5:7b",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": False
})
print(response.json()["message"]["content"])

import requests
import time
import pytest

class TestModelDeployment:
    """模型部署验证测试"""
    
    def test_health_check(self):
        """健康检查"""
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200
    
    def test_basic_generation(self):
        """基础生成测试"""
        response = requests.post("http://localhost:8000/v1/chat/completions", json={
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "messages": [{"role": "user", "content": "1+1等于几？"}],
            "max_tokens": 50
        })
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        content = data["choices"][0]["message"]["content"]
        assert "2" in content
    
    def test_chinese_understanding(self):
        """中文理解测试"""
        response = requests.post("http://localhost:8000/v1/chat/completions", json={
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "messages": [{"role": "user", "content": "请用一句话介绍中国的首都"}],
            "max_tokens": 100
        })
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        assert "北京" in content
    
    def test_streaming(self):
        """流式输出测试"""
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "messages": [{"role": "user", "content": "写一首诗"}],
                "stream": True
            },
            stream=True
        )
        # 验证流式输出
        chunks = []
        for line in response.iter_lines():
            if line:
                chunks.append(line.decode())
        assert len(chunks) > 0  # 至少有一个 chunk

def benchmark_deployment(base_url: str, model_name: str, prompts: list) -> dict:
    """部署性能基准测试"""
    results = {
        "total_requests": len(prompts),
        "success": 0,
        "failed": 0,
        "latencies": [],
        "throughput_tokens": 0
    }
    
    for prompt in prompts:
        start = time.time()
        try:
            response = requests.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200
                },
                timeout=60
            )
            end = time.time()
            
            latency_ms = (end - start) * 1000
            results["latencies"].append(latency_ms)
            results["success"] += 1
            
            # 统计 token 数
            if response.status_code == 200:
                data = response.json()
                token_count = data.get("usage", {}).get("completion_tokens", 0)
                results["throughput_tokens"] += token_count
        except Exception as e:
            results["failed"] += 1
    
    results["avg_latency_ms"] = sum(results["latencies"]) / len(results["latencies"]) if results["latencies"] else 0
    results["p99_latency_ms"] = sorted(results["latencies"])[int(len(results["latencies"]) * 0.99)] if results["latencies"] else 0
    results["qps"] = results["success"] / (sum(results["latencies"]) / 1000) if results["latencies"] else 0
    
    return results

# 测试用例
prompts = [f"请解释第{i}个概念：人工智能" for i in range(100)]
result = benchmark_deployment("http://localhost:8000", "Qwen/Qwen2.5-7B-Instruct", prompts)
print(f"QPS: {result['qps']:.2f}")
print(f"平均延迟: {result['avg_latency_ms']:.2f}ms")
print(f"P99延迟: {result['p99_latency_ms']:.2f}ms")

from locust import HttpUser, task, between

class ModelUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def chat(self):
        self.client.post("/v1/chat/completions", json={
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "messages": [{"role": "user", "content": "你好，请介绍一下你自己"}],
            "max_tokens": 100
        })

# prometheus 配置示例
# scrape_configs:
#   - job_name: 'vllm'
#     static_configs:
#       - targets: ['localhost:8000']

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import time

app = FastAPI()

class ChatRequest(BaseModel):
    messages: list
    max_tokens: int = 200
    temperature: float = 0.7

@app.post("/chat")
async def chat(request: ChatRequest):
    start = time.time()
    try:
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            },
            timeout=30
        )
        latency = time.time() - start
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="模型服务异常")
        
        data = response.json()
        return {
            "content": data["choices"][0]["message"]["content"],
            "latency_ms": latency * 1000,
            "tokens_used": data.get("usage", {}).get("total_tokens", 0)
        }
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="请求超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# 连接到本地 vLLM 服务
llm = ChatOpenAI(
    model="Qwen/Qwen2.5-7B-Instruct",
    openai_api_base="http://localhost:8000/v1",
    openai_api_key="fake-key",  # 本地部署不需要真实 key
    temperature=0.7
)

# 创建 prompt 模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的客服助手"),
    ("user", "{question}")
])

# 构建 chain
chain = prompt | llm

# 调用
result = chain.invoke({"question": "如何办理医保报销？"})
print(result.content)
