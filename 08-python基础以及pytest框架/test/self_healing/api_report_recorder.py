# api_report_recorder.py - API 入参/出参 JSON 报告
"""
自动拦截 requests 调用，按用例汇总请求入参、响应体，会话结束写入 JSON 报告。

默认输出: reports/api_test_report.json（相对 pytest rootdir）
关闭记录: API_REPORT=0
自定义路径: API_REPORT_PATH=reports/my_report.json
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime
from threading import local
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ctx = local()
_patched = False
_original_session_request = None
_original_api_request = None

# nodeid -> case record
_cases: Dict[str, Dict[str, Any]] = {}


def is_enabled() -> bool:
    return os.environ.get("API_REPORT", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _mask_headers(headers: Optional[Dict]) -> Dict:
    if not headers:
        return {}
    safe = {}
    for k, v in dict(headers).items():
        kl = k.lower()
        if kl == "authorization" and isinstance(v, str):
            safe[k] = re.sub(r"(Bearer\s+).+", r"\1***", v, flags=re.I)
        elif kl in ("cookie", "x-api-key", "api-key"):
            safe[k] = "***"
        else:
            safe[k] = v
    return safe


def _mask_sensitive_in_body(data: Any) -> Any:
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if str(k).lower() in ("password", "secret", "token", "access_token"):
                out[k] = "***"
            else:
                out[k] = _mask_sensitive_in_body(v)
        return out
    if isinstance(data, list):
        return [_mask_sensitive_in_body(i) for i in data]
    return data


def _safe_body(data: Any, limit: int = 8000) -> Any:
    if data is None:
        return None
    if isinstance(data, (dict, list, bool, int, float)):
        data = _mask_sensitive_in_body(data)
        text = json.dumps(data, ensure_ascii=False, default=str)
        if len(text) > limit:
            return {"_truncated": True, "preview": text[:limit]}
        return data
    text = str(data)
    if len(text) > limit:
        return {"_truncated": True, "preview": text[:limit]}
    return text


def _parse_response(resp) -> Dict[str, Any]:
    body: Any = None
    try:
        body = resp.json()
    except Exception:
        try:
            body = resp.text
        except Exception:
            body = None
    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers) if resp.headers else {},
        "body": _safe_body(body),
    }


def _build_request_record(method: str, url: str, kwargs: dict, resp, elapsed_s: float) -> Dict:
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "method": method.upper(),
        "url": url,
        "elapsed_ms": round(elapsed_s * 1000, 2),
        "request": {
            "headers": _mask_headers(kwargs.get("headers")),
            "params": _safe_body(kwargs.get("params")),
            "json": _safe_body(kwargs.get("json")),
            "data": _safe_body(kwargs.get("data")),
        },
        "response": _parse_response(resp),
    }
    return record


def _append_record(method: str, url: str, kwargs: dict, resp, elapsed_s: float) -> None:
    nodeid = getattr(_ctx, "nodeid", None)
    if not nodeid or nodeid not in _cases:
        return
    _cases[nodeid]["requests"].append(_build_request_record(method, url, kwargs, resp, elapsed_s))


def _patched_session_request(self, method, url, **kwargs):
    start = time.time()
    resp = _original_session_request(self, method, url, **kwargs)
    if is_enabled():
        _append_record(method, url, kwargs, resp, time.time() - start)
    return resp


def _patched_api_request(method, url, **kwargs):
    start = time.time()
    resp = _original_api_request(method, url, **kwargs)
    if is_enabled():
        _append_record(method, url, kwargs, resp, time.time() - start)
    return resp


def install_patch() -> None:
    global _patched, _original_session_request, _original_api_request
    if _patched or not is_enabled():
        return
    import requests
    import requests.api as api

    _original_session_request = requests.Session.request
    _original_api_request = api.request
    requests.Session.request = _patched_session_request
    api.request = _patched_api_request
    _patched = True
    logger.debug("API 报告记录器已启用（requests 拦截）")


def uninstall_patch() -> None:
    global _patched
    if not _patched:
        return
    import requests
    import requests.api as api

    requests.Session.request = _original_session_request
    api.request = _original_api_request
    _patched = False


def begin_case(nodeid: str, name: str) -> None:
    _ctx.nodeid = nodeid
    _cases[nodeid] = {
        "nodeid": nodeid,
        "name": name,
        "outcome": None,
        "duration_s": None,
        "requests": [],
    }


def end_case(nodeid: str, outcome: str, duration_s: float) -> None:
    if nodeid in _cases:
        _cases[nodeid]["outcome"] = outcome
        _cases[nodeid]["duration_s"] = round(duration_s, 3)


def build_report() -> Dict[str, Any]:
    cases = list(_cases.values())
    passed = sum(1 for c in cases if c.get("outcome") == "passed")
    failed = sum(1 for c in cases if c.get("outcome") == "failed")
    skipped = sum(1 for c in cases if c.get("outcome") == "skipped")
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_cases": len(cases),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total_http_calls": sum(len(c.get("requests") or []) for c in cases),
        },
        "cases": cases,
    }


def save_report(output_path: str) -> str:
    report = build_report()
    path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    logger.info("API JSON 报告已生成: %s", path)
    return path


def reset_session() -> None:
    _cases.clear()
    _ctx.nodeid = None
