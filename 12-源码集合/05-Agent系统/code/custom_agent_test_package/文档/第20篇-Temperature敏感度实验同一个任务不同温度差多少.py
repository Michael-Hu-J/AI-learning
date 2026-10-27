import os
import requests

API_KEY = os.getenv("DASHSCOPE_API_KEY")
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-plus"
N_RUNS = 10
TEMPERATURES = [0.3, 0.7, 1.0]

def call_llm(prompt, temperature):
    resp = requests.post(API_URL, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": temperature,
    }, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }, timeout=60)
    
    if resp.status_code == 200:
        result = resp.json()
        return {"success": True, "content": result["choices"][0]["message"]["content"],
                "tokens": result.get("usage", {}).get("total_tokens", 0)}
    return {"success": False, "error": f"HTTP {resp.status_code}"}

# 对每个任务、每个温度跑 N 次，统计成功率和输出多样性
for task in TASKS:
    for temp in TEMPERATURES:
        results = [call_llm(task["prompt"], temp) for _ in range(N_RUNS)]
        # 统计...
