"""
shared/__init__.py - RAG系统 公共工具函数
提供 API 调用、Token 计算、JSON 读写等通用功能

支持三种运行模式：
1. 正常模式：设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY，调用真实 API
2. Mock 模式：未设置任何 API Key 时自动启用，返回模拟数据
3. 自定义 Base URL：通过 DASHSCOPE_BASE_URL 环境变量指定兼容 OpenAI 的端点
"""

import json
import os
import math
import re
import requests
from pathlib import Path


def get_api_key():
    """获取 API Key（从环境变量读取）"""
    api_key = os.environ.get("DASHSCOPE_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("[提示] 未设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY，将使用模拟模式")
        return ""
    return api_key


def get_base_url():
    """获取 API Base URL"""
    custom = os.getenv("DASHSCOPE_BASE_URL", "")
    if custom:
        return custom.rstrip("/") + "/chat/completions"
    return "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def call_llm(prompt, system_prompt="你是一个专业的AI助手。", api_key="", model="qwen-plus", max_tokens=1024):
    """
    调用大语言模型（支持真实调用和模拟模式）
    返回: (回答文本, token使用量)
    """
    if not api_key:
        api_key = get_api_key()
    
    if not api_key:
        # 模拟模式：返回占位回复
        return f"[模拟回复] 基于上下文，针对问题「{prompt[:30]}...」的回答已生成。", {"prompt_tokens": len(prompt), "completion_tokens": 50, "total_tokens": len(prompt) + 50}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        url = get_base_url()
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return content, usage
    except Exception as e:
        return f"[调用失败] {e}", {"prompt_tokens": len(prompt), "completion_tokens": 0, "total_tokens": len(prompt)}


def calculate_tokens(text):
    """简单估算 Token 数量（中文约1.5字符/token，英文约4字符/token）"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    estimated = int(chinese_chars / 1.5 + other_chars / 4)
    return max(estimated, 1)


def estimate_cost(token_count, price_per_1k=0.008):
    """估算 API 调用费用（默认按千 token 价格计算）"""
    return round(token_count / 1000 * price_per_1k, 6)


def save_json(data, filepath):
    """保存数据到 JSON 文件"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[保存] 数据已写入 {filepath}")


def load_json(filepath):
    """从 JSON 文件加载数据"""
    if not Path(filepath).exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
