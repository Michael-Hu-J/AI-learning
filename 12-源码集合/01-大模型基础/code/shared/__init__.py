"""
大模型基础 - 公共函数模块
提供 API 调用、Token 计算、成本估算等通用功能。

支持三种运行模式：
1. 正常模式：设置 DASHSCOPE_API_KEY / ZHIPUAI_API_KEY / OPENAI_API_KEY，调用真实 API
2. Mock 模式：未设置任何 API Key 时自动启用，返回模拟数据
3. 自定义 Base URL：通过 DASHSCOPE_BASE_URL 环境变量指定兼容 OpenAI 的端点
"""

import os
import json
import time
import requests
from pathlib import Path

# ── API 配置 ──────────────────────────────────────────────

# 支持的模型及其价格（元/千 Token）
MODEL_PRICES = {
    "qwen-turbo":      {"input": 0.008,  "output": 0.008},
    "qwen-plus":       {"input": 0.02,   "output": 0.02},
    "qwen-max":        {"input": 0.04,   "output": 0.04},
    "glm-5.1":         {"input": 0.01,   "output": 0.01},
    "glm-4":           {"input": 0.05,   "output": 0.05},
    "glm-4-air":       {"input": 0.001,  "output": 0.001},
}

# 默认 API 端点
API_ENDPOINTS = {
    "qwen":  "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "glm":   "https://open.bigmodel.cn/api/paas/v4/chat/completions",
}


def _is_mock_mode(provider: str = "qwen") -> bool:
    """判断是否处于 Mock 模式"""
    if provider == "glm":
        return not os.getenv("ZHIPUAI_API_KEY", "") and not os.getenv("OPENAI_API_KEY", "")
    return not os.getenv("DASHSCOPE_API_KEY", "") and not os.getenv("OPENAI_API_KEY", "")


def _mock_reply(prompt: str, **kwargs) -> str:
    """Mock 模式下的模拟回复"""
    temperature = kwargs.get("temperature", 0.7)
    if "翻译" in prompt or "translate" in prompt.lower():
        return "预测未来的最好方式就是去创造它。"
    elif "总结" in prompt or "摘要" in prompt:
        return "自1956年以来，AI经历了多次发展浪潮，近年来深度学习在图像识别和自然语言处理领域取得显著突破。"
    elif "排序" in prompt or "sort" in prompt.lower():
        return "```python\ndef quick_sort(arr: list) -> list:\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)\n```"
    elif "诗" in prompt:
        if temperature >= 0.8:
            return "春风拂柳绿成行，桃花映日笑迎阳。燕归旧巢寻旧梦，一江烟雨一江芳。"
        else:
            return "春风拂面柳丝长，桃李芬芳满院香。"
    elif "首都" in prompt:
        return "中国的首都是北京。"
    elif "你好" in prompt or "hello" in prompt.lower():
        return "你好！我是大语言模型，很高兴为你服务。"
    else:
        return f"（Mock 模式）收到输入：{prompt[:50]}... 请设置 API Key 获取真实回复。"


def get_api_key(provider: str = "qwen") -> str:
    """
    获取 API Key（从环境变量读取，不硬编码）。
    支持 DASHSCOPE_API_KEY / ZHIPUAI_API_KEY / OPENAI_API_KEY。

    Args:
        provider: 服务商名称，qwen 或 glm

    Returns:
        API Key 字符串

    Raises:
        ValueError: 环境变量未设置时抛出
    """
    env_vars = {
        "qwen": "DASHSCOPE_API_KEY",
        "glm":  "ZHIPUAI_API_KEY",
    }
    env_name = env_vars.get(provider, "DASHSCOPE_API_KEY")
    key = os.environ.get(env_name, "")
    if not key:
        # 回退到 OPENAI_API_KEY
        key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError(
            f"请设置环境变量 {env_name} 或 OPENAI_API_KEY。\n"
            f"示例: export {env_name}='your-api-key-here'"
        )
    return key


def call_llm(
    prompt: str,
    model: str = "qwen-plus",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    stream: bool = False,
    system_prompt: str = "你是一个有帮助的助手。",
    history: list | None = None,
) -> str | requests.Response:
    """
    调用大语言模型 API。支持真实调用和 Mock 模式。

    Args:
        prompt:      用户输入
        model:       模型名称
        temperature: 采样温度
        max_tokens:  最大输出 Token 数
        stream:      是否流式输出
        system_prompt: 系统提示词
        history:     历史对话列表 [{"role": "user/assistant", "content": "..."}]

    Returns:
        非流式: 返回模型回复文本
        流式:   返回 requests Response 对象
    """
    # Mock 模式
    if _is_mock_mode():
        if stream:
            raise ValueError("Mock 模式不支持流式输出，请设置 API Key 后重试")
        return _mock_reply(prompt, model=model, temperature=temperature)

    # 判断模型归属
    if model.startswith("glm"):
        provider = "glm"
        api_key = get_api_key("glm")
    else:
        provider = "qwen"
        api_key = get_api_key("qwen")

    url = API_ENDPOINTS[provider]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 构建消息列表
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    if stream:
        return response

    data = response.json()
    return data["choices"][0]["message"]["content"]


def calculate_tokens(text: str, model: str = "qwen-plus") -> int:
    """
    估算文本的 Token 数量（简易规则）。

    规则：
    - 英文单词约 1 Token/词
    - 中文字符约 1 Token/字
    - 标点符号约 2 个/Token

    Args:
        text:  输入文本
        model: 模型名称（预留扩展）

    Returns:
        估算的 Token 数量
    """
    import re
    # 中文字符数
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 移除中文后的英文部分
    english_text = re.sub(r'[\u4e00-\u9fff\s]', '', text)
    # 英文词数
    english_words = len(english_text.split()) if english_text.strip() else 0
    # 标点符号数
    punctuation = len(re.findall(r'[^\w\s\u4e00-\u9fff]', text))

    # 估算：中文 1 字 ≈ 1.5 token，英文 1 词 ≈ 1 token，标点 2 个 ≈ 1 token
    tokens = chinese_chars * 1.5 + english_words + punctuation * 0.5
    return int(tokens)


def estimate_cost(
    input_text: str,
    output_tokens: int = 512,
    model: str = "qwen-plus",
) -> dict:
    """
    估算调用成本。

    Args:
        input_text:    输入文本
        output_tokens: 预估输出 Token 数
        model:         模型名称

    Returns:
        包含输入/输出/总 Token 和费用的字典
    """
    input_tokens = calculate_tokens(input_text, model)
    prices = MODEL_PRICES.get(model, {"input": 0.04, "output": 0.04})

    input_cost = input_tokens / 1000 * prices["input"]
    output_cost = output_tokens / 1000 * prices["output"]

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(input_cost + output_cost, 6),
    }


def save_json(data: dict | list, filepath: str) -> None:
    """保存数据为 JSON 文件。"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(filepath: str) -> dict | list:
    """从 JSON 文件加载数据。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
