"""
自愈扩展工具层（教学版）— 与生产 build_healing_tool_plan / safe_call_tool 流程一致
工具能力均为内存 / 本地文件模拟，不接 DB、不接远端 MCP Server。
对应文章：第4篇 §1.2 扩展工具层
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_STUB_ROOT = Path(__file__).resolve().parent.parent / "test_data" / "healing_stub"

HEALING_TOOL_TIERS: Dict[str, List[str]] = {
    "P0": ["create_test_data", "refresh_session", "reset_test_state", "get_recent_service_logs"],
    "P1": ["capture_dom_snapshot", "clear_browser_context", "feature_flag_get_or_set"],
    "P2": ["open_incident_or_bug", "rollback_test_data"],
}
ALLOWED_HEALING_TOOLS = {t for arr in HEALING_TOOL_TIERS.values() for t in arr}

_SESSION_CACHE: Dict[str, Dict[str, Any]] = {}
_FEATURE_FLAGS: Dict[str, Any] = {}


def _ensure_stub_dirs() -> None:
    for sub in ("datasets", "snapshots", "logs", "incidents"):
        (_STUB_ROOT / sub).mkdir(parents=True, exist_ok=True)


def _tool_result(
    tool_name: str,
    success: bool,
    payload: Optional[Dict[str, Any]] = None,
    error: str = "",
) -> Dict[str, Any]:
    return {
        "tool_name": tool_name,
        "success": bool(success),
        "payload": payload or {},
        "error": error,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "mode": "teaching_stub",
    }


def _keyword_in_text(text: str, keywords: List[str]) -> bool:
    lower = (text or "").lower()
    return any(k in lower for k in keywords)


def build_healing_tool_plan(diagnosis: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """根据诊断结果输出工具执行计划（规则与生产版对齐，教学裁剪）。"""
    error_type = str(diagnosis.get("error_type", "unknown")).lower()
    root_cause = str(diagnosis.get("root_cause", ""))
    err_msg = str(context.get("error_message", ""))
    text = f"{root_cause}\n{err_msg}"
    plan: List[Dict[str, Any]] = []

    if error_type == "authentication":
        plan.append({
            "tool_name": "refresh_session",
            "arguments": {"scope": context.get("scope", "ui"), "session_id": context.get("session_id", "")},
        })
    elif error_type == "element":
        plan.append({
            "tool_name": "capture_dom_snapshot",
            "arguments": {"selector": context.get("selector", ""), "include_screenshot": False},
        })
        plan.append({
            "tool_name": "clear_browser_context",
            "arguments": {"scope": context.get("scope", "ui"), "clear": ["cookies", "storage"]},
        })
    elif error_type == "network":
        plan.append({"tool_name": "reset_test_state", "arguments": {"scope": context.get("scope", "ui"), "reason": "network_recovery"}})
        plan.append({"tool_name": "get_recent_service_logs", "arguments": {"limit": 50}})
    elif error_type in ("assertion", "business", "unknown"):
        plan.append({"tool_name": "get_recent_service_logs", "arguments": {"limit": 100}})

    if _keyword_in_text(text, ["not found", "不存在", "missing", "no such", "订单不存在", "用户不存在"]):
        plan.insert(0, {
            "tool_name": "create_test_data",
            "arguments": {
                "entity": context.get("entity", "generic"),
                "hint": err_msg[:200],
            },
        })

    confidence = float(diagnosis.get("confidence", 0.0) or 0.0)
    if confidence < 0.45:
        plan.append({
            "tool_name": "open_incident_or_bug",
            "arguments": {
                "title": "Self-healing low-confidence diagnosis",
                "summary": err_msg[:300],
            },
        })

    seen: set = set()
    deduped: List[Dict[str, Any]] = []
    for item in plan:
        name = item.get("tool_name")
        if name in seen:
            continue
        seen.add(name)
        deduped.append(item)
    return deduped


def _run_create_test_data(arguments: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_stub_dirs()
    entity = str(arguments.get("entity", "generic")).strip() or "generic"
    record = {
        "entity": entity,
        "generated_id": f"{entity}_{uuid.uuid4().hex[:8]}",
        "hint": str(arguments.get("hint", ""))[:200],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path = _STUB_ROOT / "datasets" / f"heal_{entity}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"dataset_path": str(path), "records": [record]}


def _run_refresh_session(arguments: Dict[str, Any]) -> Dict[str, Any]:
    scope = str(arguments.get("scope", "ui")).strip() or "ui"
    token = f"stub_session_{uuid.uuid4().hex[:12]}"
    refreshed = {
        "token": token,
        "scope": scope,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expires_in": 3600,
    }
    _SESSION_CACHE[scope] = refreshed
    return refreshed


def _run_reset_test_state(arguments: Dict[str, Any]) -> Dict[str, Any]:
    scope = str(arguments.get("scope", "ui")).strip() or "ui"
    removed = _SESSION_CACHE.pop(scope, None)
    flag_path = _STUB_ROOT / "reset_flags.json"
    _ensure_stub_dirs()
    flags = {}
    if flag_path.exists():
        try:
            flags = json.loads(flag_path.read_text(encoding="utf-8"))
        except Exception:
            flags = {}
    flags[scope] = {"reset_at": datetime.now(timezone.utc).isoformat(), "reason": arguments.get("reason", "")}
    flag_path.write_text(json.dumps(flags, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"scope": scope, "removed_session_cache": bool(removed), "reset_flag": flags.get(scope)}


def _run_get_recent_service_logs(arguments: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_stub_dirs()
    limit = min(int(arguments.get("limit", 50) or 50), 500)
    log_path = _STUB_ROOT / "logs" / "demo_service.log"
    if not log_path.exists():
        demo = [
            {"level": "info", "message": "demo_app started", "time": datetime.now(timezone.utc).isoformat()},
            {"level": "warning", "message": "healing stub log sample", "time": datetime.now(timezone.utc).isoformat()},
        ]
        log_path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in demo), encoding="utf-8")
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()[-limit:]
    logs = []
    for line in lines:
        try:
            logs.append(json.loads(line))
        except Exception:
            logs.append({"level": "info", "message": line, "time": None})
    return {"count": len(logs), "logs": logs}


def _run_capture_dom_snapshot(arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_stub_dirs()
    selector = str(arguments.get("selector", "")).strip()
    page = context.get("page")
    html = ""
    if page is not None:
        try:
            html = page.content()
        except Exception:
            html = ""
    if not html:
        html = f"<stub html for selector={selector!r} />"
    snap_path = _STUB_ROOT / "snapshots" / f"snap_{uuid.uuid4().hex[:8]}.html"
    snap_path.write_text(html[:500_000], encoding="utf-8")
    return {"selector": selector, "snapshot_path": str(snap_path), "html_size": len(html)}


def _run_clear_browser_context(arguments: Dict[str, Any]) -> Dict[str, Any]:
    scope = str(arguments.get("scope", "ui")).strip() or "ui"
    clear_items = arguments.get("clear", ["cookies", "storage"])
    removed = _SESSION_CACHE.pop(scope, None)
    return {
        "scope": scope,
        "clear": clear_items,
        "removed_session_cache": bool(removed),
        "note": "teaching_stub: no real browser context",
    }


def _run_feature_flag(arguments: Dict[str, Any]) -> Dict[str, Any]:
    key = str(arguments.get("key", "heal_demo_flag")).strip()
    if "value" in arguments:
        _FEATURE_FLAGS[key] = arguments["value"]
        return {"key": key, "value": arguments["value"], "op": "set"}
    return {"key": key, "value": _FEATURE_FLAGS.get(key, False), "op": "get"}


def _run_open_incident(arguments: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_stub_dirs()
    incident = {
        "id": f"INC-{uuid.uuid4().hex[:8]}",
        "title": str(arguments.get("title", "healing incident"))[:200],
        "summary": str(arguments.get("summary", ""))[:500],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path = _STUB_ROOT / "incidents" / "incidents.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(incident, ensure_ascii=False) + "\n")
    return incident


def _run_rollback_test_data(arguments: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_stub_dirs()
    entity = str(arguments.get("entity", "generic")).strip() or "generic"
    path = _STUB_ROOT / "datasets" / f"heal_{entity}.jsonl"
    rolled = 0
    if path.exists():
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        rolled = max(0, len(lines) - 1)
        path.write_text("\n".join(lines[:-1]) + ("\n" if len(lines) > 1 else ""), encoding="utf-8")
    return {"entity": entity, "rolled_back_lines": rolled}


def safe_call_tool(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """安全调用自愈工具（白名单 + 教学 stub 实现）。"""
    arguments = arguments or {}
    context = context or {}

    if tool_name not in ALLOWED_HEALING_TOOLS:
        return _tool_result(tool_name, False, error="tool_not_allowed")

    try:
        if tool_name == "create_test_data":
            return _tool_result(tool_name, True, payload=_run_create_test_data(arguments))
        if tool_name == "refresh_session":
            return _tool_result(tool_name, True, payload=_run_refresh_session(arguments))
        if tool_name == "reset_test_state":
            return _tool_result(tool_name, True, payload=_run_reset_test_state(arguments))
        if tool_name == "get_recent_service_logs":
            return _tool_result(tool_name, True, payload=_run_get_recent_service_logs(arguments))
        if tool_name == "capture_dom_snapshot":
            return _tool_result(tool_name, True, payload=_run_capture_dom_snapshot(arguments, context))
        if tool_name == "clear_browser_context":
            return _tool_result(tool_name, True, payload=_run_clear_browser_context(arguments))
        if tool_name == "feature_flag_get_or_set":
            return _tool_result(tool_name, True, payload=_run_feature_flag(arguments))
        if tool_name == "open_incident_or_bug":
            return _tool_result(tool_name, True, payload=_run_open_incident(arguments))
        if tool_name == "rollback_test_data":
            return _tool_result(tool_name, True, payload=_run_rollback_test_data(arguments))
    except Exception as e:
        return _tool_result(tool_name, False, error=str(e))

    return _tool_result(tool_name, False, error="tool_not_implemented")


def reset_teaching_stub_state() -> None:
    """测试用：清空内存态 stub。"""
    _SESSION_CACHE.clear()
    _FEATURE_FLAGS.clear()
