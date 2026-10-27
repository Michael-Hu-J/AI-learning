"""
LLM 自然语言 → 操作步骤（不写死业务流程，由模型根据系统上下文拆分）。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from ui_catalog import build_ui_catalog, catalog_to_prompt_text

SKILL_SCHEMA = """
每个步骤为 JSON 对象，字段：
- skill: navigate | input | fill | click | select | verify | wait_url | wait
- params: 技能参数对象
- description: 中文简述

params 约定：
- navigate: {"url": "完整URL"}
- input: {"placeholder": "用户名|密码|...", "value": "..."}
- fill: {"label": "商品名称|价格|库存|...", "value": "..."}
- click: {"text": "按钮可见文字，如 登录、新增商品、确认添加"}
- select: {"label": "字段名", "value": "选项"}
- verify: {"text": "页面应出现的文字"}
- wait_url: {"pattern": "**/products"}  （Playwright glob）
- wait: {"ms": 1500}

规则：
1. 根据用户一句话推断完整 UI 流程（含必要时的登录、导航、打开弹窗、填表、提交、验证）。
2. 在商品管理页新增商品时，必须先 click「新增商品」打开弹窗，再 fill 各字段，最后 click「确认添加」。
3. 用户未给的字段用合理测试数据，验证步骤 verify 应检查用户关心的商品名或关键文案是否出现在页面。
4. 只输出 JSON 数组，不要 markdown 包裹，不要解释。
"""


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    # 尝试直接 parse；失败则截取第一个 [...]
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*\]", raw)
    if not m:
        raise ValueError("模型未返回 JSON 数组")
    data = json.loads(m.group(0))
    if not isinstance(data, list):
        raise ValueError("解析结果不是数组")
    return data


def _normalize_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    allowed = {"navigate", "input", "fill", "click", "select", "verify", "wait_url", "wait"}
    out = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        skill = str(s.get("skill", "")).strip().lower()
        if skill not in allowed:
            continue
        params = s.get("params")
        if not isinstance(params, dict):
            params = {}
        out.append(
            {
                "skill": skill,
                "params": params,
                "description": str(s.get("description") or skill),
            }
        )
    return out


def _call_dashscope(messages: List[Dict[str, str]], model: str) -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY")
    resp = httpx.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "input": {"messages": messages},
            "parameters": {"temperature": 0.1, "max_tokens": 2048, "result_format": "message"},
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return (
        data.get("output", {})
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )


def _call_openai_compatible(messages: List[Dict[str, str]], model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if not api_key:
        raise RuntimeError("未配置 OPENAI_API_KEY")
    resp = httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 2048},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _pick_provider() -> tuple[str, str]:
    mode = os.getenv("NL_LLM_PROVIDER", "auto").strip().lower()
    dash_model = os.getenv("NL_LLM_MODEL", os.getenv("DASHSCOPE_MODEL", "qwen-plus"))
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    has_dash = bool(os.getenv("DASHSCOPE_API_KEY", "").strip())
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())

    if mode == "dashscope" or (mode == "auto" and has_dash):
        return "dashscope", dash_model
    if mode == "openai" or (mode == "auto" and has_openai):
        return "openai", openai_model
    raise RuntimeError("请配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY（NL_LLM_PROVIDER=auto|dashscope|openai）")


def parse_with_llm(
    user_text: str,
    base_url: Optional[str] = None,
    *,
    app_root: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """将用户自然语言拆分为可执行步骤列表。"""
    catalog = build_ui_catalog(app_root)
    if base_url:
        catalog["target_url"] = base_url

    system = (
        "你是 UI 自动化测试步骤规划器。根据用户一句话和系统页面信息，输出 Playwright 可执行步骤 JSON 数组。\n\n"
        + SKILL_SCHEMA
        + "\n\n"
        + catalog_to_prompt_text(catalog)
    )
    if base_url:
        system += f"\n\n用户任务默认目标页: {base_url}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text.strip()},
    ]

    provider, model = _pick_provider()
    logger.info(f"LLM 解析: provider={provider} model={model}")

    if provider == "dashscope":
        content = _call_dashscope(messages, model)
    else:
        content = _call_openai_compatible(messages, model)

    steps = _normalize_steps(_extract_json_array(content))
    if not steps:
        raise ValueError("LLM 未产出有效步骤")
    logger.info(f"LLM 解析得到 {len(steps)} 个步骤")
    return steps


def llm_available() -> bool:
    try:
        _pick_provider()
        return True
    except RuntimeError:
        return False
