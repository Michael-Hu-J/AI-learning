"""
扩展工具层测试 — build_healing_tool_plan + safe_call_tool（教学 stub）
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from healer.healing_tools import (
    ALLOWED_HEALING_TOOLS,
    build_healing_tool_plan,
    reset_teaching_stub_state,
    safe_call_tool,
)


@pytest.fixture(autouse=True)
def _clean_stub():
    reset_teaching_stub_state()
    yield
    reset_teaching_stub_state()


class TestToolPlan:
    def test_element_plan_has_dom_tools(self):
        plan = build_healing_tool_plan(
            {"error_type": "element", "confidence": 0.9, "root_cause": "元素不可达"},
            {"selector": "#login-btn", "error_message": "element not found"},
        )
        names = [p["tool_name"] for p in plan]
        assert "capture_dom_snapshot" in names
        assert "clear_browser_context" in names

    def test_auth_plan_refresh_session(self):
        plan = build_healing_tool_plan(
            {"error_type": "authentication", "confidence": 0.9},
            {"scope": "ui"},
        )
        assert plan[0]["tool_name"] == "refresh_session"

    def test_missing_data_inserts_create_test_data(self):
        plan = build_healing_tool_plan(
            {"error_type": "unknown", "confidence": 0.4, "root_cause": "订单不存在"},
            {"error_message": "订单不存在", "entity": "order"},
        )
        assert plan[0]["tool_name"] == "create_test_data"

    def test_low_confidence_adds_incident(self):
        plan = build_healing_tool_plan(
            {"error_type": "unknown", "confidence": 0.3},
            {"error_message": "weird"},
        )
        assert any(p["tool_name"] == "open_incident_or_bug" for p in plan)


class TestSafeCallTool:
    def test_refresh_session_stub(self):
        r = safe_call_tool("refresh_session", {"scope": "ui"})
        assert r["success"]
        assert r["mode"] == "teaching_stub"
        assert "token" in r["payload"]

    def test_create_test_data_writes_file(self):
        r = safe_call_tool("create_test_data", {"entity": "order", "hint": "demo"})
        assert r["success"]
        assert os.path.exists(r["payload"]["dataset_path"])

    def test_not_allowed_tool(self):
        r = safe_call_tool("evil_tool", {})
        assert not r["success"]
        assert r["error"] == "tool_not_allowed"

    def test_all_whitelisted_tools_callable(self):
        for name in sorted(ALLOWED_HEALING_TOOLS):
            r = safe_call_tool(name, {})
            assert r["success"], f"{name} failed: {r.get('error')}"


class TestSubgraphIntegration:
    def test_element_subgraph_runs_tools(self):
        pytest.importorskip("langgraph")
        from healer.healing_graph import invoke_healing_subgraph_sync

        sg = invoke_healing_subgraph_sync(
            "Timeout: waiting for locator('#login-btn'): Element not found",
            {"selector": "#login-btn", "error_message": "element not found"},
        )
        assert len(sg.get("tool_calls") or []) >= 2
        assert "tools:2" in " ".join(sg.get("heal_log") or []) or "tools:3" in " ".join(
            sg.get("heal_log") or []
        )
        assert any("tool_success:" in x for x in sg.get("heal_log") or [])
