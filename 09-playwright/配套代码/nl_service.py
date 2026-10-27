"""
自然语言 UI 自动化 — 服务层（供 HTTP API / Skills 桥接调用）。
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

from nl_executor import run_nl_steps
from seckill_config import PRODUCTS_URL, SECKILL_BASE_URL


def execute_nl(
    text: str,
    *,
    base_url: Optional[str] = None,
    headless: bool = True,
    parser: Optional[str] = None,
) -> Dict[str, Any]:
    """
    解析用户一句话并在真实浏览器中执行。

    返回结构化结果，供 API / Skills 使用。
    """
    from step_parser_service import step_parser_service
    from llm_step_parser import llm_available

    if parser:
        os.environ["NL_PARSER"] = parser

    target = (base_url or PRODUCTS_URL).strip()
    run_id = str(uuid.uuid4())[:8]
    t0 = time.time()

    parsed: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    error: Optional[str] = None

    try:
        parsed = step_parser_service.parse_description(text, target)
        if not parsed:
            error = "未能从自然语言中拆分出任何步骤"
        else:
            results = run_nl_steps(parsed, target, headless=headless, verbose=False)
    except Exception as e:
        error = str(e)

    passed = sum(1 for r in results if r.get("status") == "passed")
    failed = len(results) - passed
    success = error is None and results and failed == 0

    return {
        "run_id": run_id,
        "success": success,
        "text": text,
        "base_url": target,
        "seckill_base": SECKILL_BASE_URL,
        "parser_mode": os.getenv("NL_PARSER", "auto"),
        "llm_available": llm_available(),
        "steps_parsed": parsed,
        "step_results": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "duration_ms": int((time.time() - t0) * 1000),
        },
        "error": error,
        "message": (
            "全部步骤执行成功，请在业务系统页面查看真实数据。"
            if success
            else (error or f"有 {failed} 个步骤失败")
        ),
    }


def parse_only(text: str, base_url: Optional[str] = None, parser: Optional[str] = None) -> Dict[str, Any]:
    """仅 LLM/规则拆分，不启动浏览器。"""
    from step_parser_service import step_parser_service

    if parser:
        os.environ["NL_PARSER"] = parser
    target = (base_url or PRODUCTS_URL).strip()
    steps = step_parser_service.parse_description(text, target)
    return {"text": text, "base_url": target, "steps": steps, "count": len(steps)}
