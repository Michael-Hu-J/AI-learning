#!/usr/bin/env python3
"""
温度对智能体稳定性的影响实验

对比 temperature=0.3/0.7/1.0 三种设置下，
同一任务跑 30 次的成功率和输出一致性。

注：CustomAgent 是你项目中的封装，实际使用时替换为你的 Agent 类。
核心逻辑：固定 temperature，多次运行，统计分布。
"""

import os
import statistics
import requests
from collections import Counter

# 你的 API Key，从环境变量读取
API_KEY = os.getenv("DASHSCOPE_API_KEY")
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-plus"

TASK = "计算 25 * 4 + 100 / 5，把结果存储到记忆中"
EXPECTED_ANSWER = "120"
N_RUNS = 30
TEMPERATURES = [0.3, 0.7, 1.0]


def call_llm(temperature: float) -> dict:
    """调用 LLM API"""
    resp = requests.post(API_URL, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": TASK}],
        "max_tokens": 2048,
        "temperature": temperature,
    }, timeout=60)
    
    if resp.status_code == 200:
        result = resp.json()
        return {
            "success": True,
            "content": result["choices"][0]["message"]["content"],
            "tokens": result.get("usage", {}).get("total_tokens", 0),
        }
    return {"success": False, "error": resp.text[:200]}


def check_success(result: dict) -> bool:
    """检查任务是否成功（输出包含正确答案）"""
    if not result.get("success"):
        return False
    return EXPECTED_ANSWER in result.get("content", "")


def check_output_consistency(results: list) -> float:
    """检查输出一致性：最高频输出占总成功数的比例"""
    outputs = [r.get("content", "").strip() for r in results if r.get("success")]
    if not outputs:
        return 0.0
    counts = Counter(outputs)
    most_common_count = counts.most_common(1)[0][1]
    return most_common_count / len(outputs)


def run_experiment():
    print(f"任务: {TASK}")
    print(f"运行次数: {N_RUNS} 次/温度")
    print(f"模型: {MODEL}")
    print()

    for temp in TEMPERATURES:
        results = []
        for i in range(N_RUNS):
            result = call_llm(temp)
            results.append(result)

        # 统计
        success_count = sum(1 for r in results if check_success(r))
        success_rate = success_count / N_RUNS
        consistency = check_output_consistency(results)

        tokens = [r.get("tokens", 0) for r in results if r.get("success")]
        avg_tokens = statistics.mean(tokens) if tokens else 0

        print(f"temperature={temp}: 成功率={success_rate:.0%}, "
              f"一致性={consistency:.0%}, 平均Token={avg_tokens:.0f}")


if __name__ == "__main__":
    run_experiment()
