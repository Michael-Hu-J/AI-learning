"""共享工具函数 - Prompt工程示例代码的基础模块

支持三种运行模式：
1. 正常模式：设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY，调用真实 API
2. Mock 模式：未设置任何 API Key 时自动启用，返回模拟数据
3. 自定义 Base URL：通过 DASHSCOPE_BASE_URL 环境变量指定兼容 OpenAI 的端点
"""
import os
import json
import time
import requests
from typing import Optional, Dict, List


def get_api_key() -> str:
    """获取 API Key（支持 DashScope / OpenAI）"""
    key = os.getenv("DASHSCOPE_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise ValueError(
            "请设置环境变量 DASHSCOPE_API_KEY 或 OPENAI_API_KEY\n"
            "  export DASHSCOPE_API_KEY='sk-xxx'    # 通义千问\n"
            "  export OPENAI_API_KEY='sk-xxx'       # 任意兼容 OpenAI 的 API"
        )
    return key


def get_base_url() -> str:
    """获取 API Base URL"""
    custom = os.getenv("DASHSCOPE_BASE_URL", "")
    if custom:
        return custom.rstrip("/") + "/chat/completions"
    return "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def _is_mock_mode() -> bool:
    """判断是否处于 Mock 模式"""
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


def call_llm(prompt: str, model: str = "qwen-plus", temperature: float = 0.7,
             max_tokens: int = 2048, api_key: Optional[str] = None) -> str:
    """
    调用 LLM API（支持 DashScope / OpenAI 兼容接口）
    
    Args:
        prompt: 用户输入
        model: 模型名称（默认 qwen-plus）
        temperature: 温度参数（0.0-2.0）
        max_tokens: 最大输出 Token 数
        api_key: 可选的 API Key（优先于环境变量）
    
    Returns:
        正常模式：API 回复文本
        Mock 模式：模拟回复文本
    """
    # Mock 模式
    if _is_mock_mode():
        return _mock_reply(prompt, model=model, temperature=temperature)
    
    if api_key is None:
        api_key = get_api_key()
    
    base_url = get_base_url()
    
    response = requests.post(
        base_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def calculate_tokens(text: str) -> int:
    """粗略计算 Token 数（中文约 1.5 字/Token，英文约 0.75 词/Token）"""
    import re
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    non_chinese = re.sub(r'[\u4e00-\u9fff]', ' ', text)
    english_words = len(non_chinese.split())
    return int(chinese_chars * 1.5 + english_words * 0.75)


def estimate_cost(tokens: int, price_per_1k: float = 0.02) -> float:
    """估算成本（默认千问 Plus: 0.02 元/千 Token）"""
    return tokens / 1000 * price_per_1k


def save_json(data, path: str):
    """保存 JSON 文件"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: str):
    """加载 JSON 文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
