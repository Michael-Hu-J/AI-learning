"""
统一 LLM 客户端 — 封装通义千问和智谱 API
所有评测器通过此模块调用 LLM，不再各自重复实现
"""

import os
import time
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """统一的 LLM 响应"""
    content: str
    latency_seconds: float
    model: str
    success: bool
    error: Optional[str] = None
    token_usage: Optional[Dict] = None


class LLMClient:
    """
    统一 LLM 客户端

    支持:
    - 通义千问 (dashscope)
    - 智谱 (zhipuai)

    用法:
        client = LLMClient(provider="tongyi", model="qwen-plus")
        response = client.chat("你好")
    """

    SUPPORTED_MODELS = {
        "tongyi": ["qwen-turbo", "qwen-plus", "qwen-max"],
        "zhipu": ["glm-4", "glm-4-plus", "glm-4-flash"],
    }

    def __init__(self, provider: str = "tongyi", model: str = "qwen-plus",
                 temperature: float = 0.7, max_tokens: int = 8192):
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = self._get_api_key()
        self.call_count = 0
        self.total_latency = 0.0
        self.total_tokens = 0

    def _get_api_key(self) -> str:
        """获取 API Key"""
        if self.provider == "tongyi":
            key = os.getenv("DASHSCOPE_API_KEY")
            if not key:
                raise EnvironmentError(
                    "未找到 DASHSCOPE_API_KEY 环境变量。"
                    "请设置: export DASHSCOPE_API_KEY='sk-xxx'"
                )
            return key
        elif self.provider == "zhipu":
            key = os.getenv("ZHIPU_API_KEY")
            if not key:
                raise EnvironmentError(
                    "未找到 ZHIPU_API_KEY 环境变量。"
                    "请设置: export ZHIPU_API_KEY='xxx'"
                )
            return key
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")

    def chat(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """
        发送对话请求

        Args:
            prompt: 用户输入
            system_prompt: 系统提示词 (可选)

        Returns:
            LLMResponse
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self._call(messages)

    def chat_multi_turn(self, messages: List[Dict]) -> LLMResponse:
        """
        多轮对话

        Args:
            messages: 完整消息列表

        Returns:
            LLMResponse
        """
        return self._call(messages)

    def _call(self, messages: List[Dict]) -> LLMResponse:
        """调用底层 API"""
        if self.provider == "tongyi":
            return self._call_tongyi(messages)
        elif self.provider == "zhipu":
            return self._call_zhipu(messages)

    def _call_tongyi(self, messages: List[Dict]) -> LLMResponse:
        """通义千问 API"""
        import dashscope
        from dashscope import Generation

        dashscope.api_key = self.api_key

        start = time.time()
        try:
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                result_format="message",
            )
            latency = time.time() - start

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                usage = response.usage if hasattr(response, 'usage') else None
                self.call_count += 1
                self.total_latency += latency
                if usage:
                    self.total_tokens += usage.get("total_tokens", 0)

                return LLMResponse(
                    content=content,
                    latency_seconds=round(latency, 2),
                    model=self.model,
                    success=True,
                    token_usage=usage if isinstance(usage, dict) else None,
                )
            else:
                return LLMResponse(
                    content="",
                    latency_seconds=round(latency, 2),
                    model=self.model,
                    success=False,
                    error=f"通义千问 API 错误: {response.code} - {response.message}",
                )

        except Exception as e:
            return LLMResponse(
                content="",
                latency_seconds=round(time.time() - start, 2),
                model=self.model,
                success=False,
                error=str(e),
            )

    def _call_zhipu(self, messages: List[Dict]) -> LLMResponse:
        """智谱 API"""
        from zhipuai import ZhipuAI

        client = ZhipuAI(api_key=self.api_key)

        start = time.time()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            latency = time.time() - start

            content = response.choices[0].message.content
            usage = response.usage if hasattr(response, 'usage') else None
            self.call_count += 1
            self.total_latency += latency
            if usage:
                self.total_tokens += usage.total_tokens

            return LLMResponse(
                content=content,
                latency_seconds=round(latency, 2),
                model=self.model,
                success=True,
                token_usage={"total_tokens": usage.total_tokens} if usage else None,
            )

        except Exception as e:
            return LLMResponse(
                content="",
                latency_seconds=round(time.time() - start, 2),
                model=self.model,
                success=False,
                error=str(e),
            )

    def get_stats(self) -> Dict:
        """获取调用统计"""
        return {
            "call_count": self.call_count,
            "total_latency_seconds": round(self.total_latency, 2),
            "avg_latency_seconds": round(self.total_latency / max(1, self.call_count), 2),
            "total_tokens": self.total_tokens,
            "avg_tokens_per_call": round(self.total_tokens / max(1, self.call_count)),
            "model": self.model,
            "provider": self.provider,
        }


def extract_json_from_response(response: str) -> Optional[Dict]:
    """
    从 LLM 回复中提取 JSON

    很多 LLM 会在 JSON 前后加解释文字，这个方法提取纯 JSON 部分
    """
    # 尝试直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    json_match = re.search(r'```(?:json)?\s*\n?({.*?})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试从任意位置提取 JSON 对象
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return None


def extract_list_from_response(response: str) -> Optional[List]:
    """从 LLM 回复中提取 JSON 数组"""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r'\[.*\]', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return None
