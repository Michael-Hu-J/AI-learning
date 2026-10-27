"""
LangGraph 自愈子图（教学版）— diagnose → plan → execute → 条件重试
扩展工具层：healer.healing_tools（本地 stub，流程与生产一致）
对应文章：第4篇-AI自愈系统
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from healer.diagnostic import ErrorDiagnoser
from healer.healing_tools import build_healing_tool_plan, safe_call_tool
from healer.strategies import StrategyFactory

logger = logging.getLogger(__name__)

_diagnoser = ErrorDiagnoser()
_factory = StrategyFactory()


class HealingSubState(TypedDict):
    step: Dict[str, Any]
    error_message: str
    context: Dict[str, Any]
    diagnosis: Dict[str, Any]
    repair_plan: Dict[str, Any]
    repair_result: Dict[str, Any]
    tool_calls: List[Dict[str, Any]]
    current_attempt: int
    max_retries: int
    healed: bool
    heal_log: List[str]


def _heal_diagnose_node(state: HealingSubState) -> Dict[str, Any]:
    diagnosis = _diagnoser.diagnose(
        state.get("error_message", ""),
        state.get("context", {}),
    )
    return {
        "diagnosis": diagnosis,
        "heal_log": state.get("heal_log", [])
        + [f"diagnose:{diagnosis.get('error_type')}:{diagnosis.get('confidence', 0)}"],
    }


def _heal_plan_node(state: HealingSubState) -> Dict[str, Any]:
    diagnosis = state.get("diagnosis", {})
    context = state.get("context", {})
    tool_actions = build_healing_tool_plan(diagnosis, context)
    repair_plan = {
        "strategy": diagnosis.get("repair_strategy"),
        "auto_repairable": bool(diagnosis.get("auto_repairable")),
        "reason": diagnosis.get("root_cause", ""),
        "tool_actions": tool_actions,
    }
    return {
        "repair_plan": repair_plan,
        "heal_log": state.get("heal_log", [])
        + [
            f"plan:{repair_plan.get('strategy') or 'none'}",
            f"tools:{len(repair_plan.get('tool_actions') or [])}",
        ],
    }


async def _heal_execute_node(state: HealingSubState) -> Dict[str, Any]:
    diagnosis = state.get("diagnosis", {})
    context = dict(state.get("context", {}))
    context["current_retry"] = state.get("current_attempt", 0)
    context["max_retries"] = state.get("max_retries", 2)
    context["error_message"] = state.get("error_message", "")

    planned_tools = (state.get("repair_plan") or {}).get("tool_actions") or []
    tool_calls: List[Dict[str, Any]] = []
    for t in planned_tools:
        tool_name = str(t.get("tool_name", "")).strip()
        if not tool_name:
            continue
        tool_calls.append(safe_call_tool(tool_name, t.get("arguments") or {}, context))

    repair_result = _factory.execute(diagnosis, context)
    tool_success = any(bool(x.get("success")) for x in tool_calls)
    # 工具成功仅在「可自动修复」时计入 healed（unknown 仅跑观测类工具不算步骤已修复）
    healed = bool(repair_result.get("success")) or (
        tool_success and bool(diagnosis.get("auto_repairable"))
    )
    tool_ok = sum(1 for x in tool_calls if x.get("success"))
    return {
        "repair_result": repair_result,
        "tool_calls": tool_calls,
        "healed": healed,
        "current_attempt": state.get("current_attempt", 0) + 1,
        "heal_log": state.get("heal_log", [])
        + [
            f"execute:{repair_result.get('action', 'none')}:{healed}",
            f"tool_success:{tool_ok}/{len(tool_calls)}",
        ],
    }


def _heal_should_retry(state: HealingSubState) -> str:
    if state.get("healed"):
        return "done"
    if state.get("current_attempt", 0) >= state.get("max_retries", 2):
        return "done"
    if not (state.get("repair_plan") or {}).get("auto_repairable", False):
        return "done"
    return "retry"


def build_healing_subgraph():
    builder = StateGraph(HealingSubState)
    builder.add_node("diagnose", _heal_diagnose_node)
    builder.add_node("plan", _heal_plan_node)
    builder.add_node("execute", _heal_execute_node)
    builder.add_edge(START, "diagnose")
    builder.add_edge("diagnose", "plan")
    builder.add_edge("plan", "execute")
    builder.add_conditional_edges(
        "execute",
        _heal_should_retry,
        {"retry": "diagnose", "done": END},
    )
    return builder.compile()


healing_subgraph = build_healing_subgraph()


async def invoke_healing_subgraph_async(
    error_message: str,
    context: Dict[str, Any],
    *,
    step: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
) -> Dict[str, Any]:
    heal_state: HealingSubState = {
        "step": step or {},
        "error_message": error_message or "",
        "context": context or {},
        "diagnosis": {},
        "repair_plan": {},
        "repair_result": {},
        "tool_calls": [],
        "current_attempt": 0,
        "max_retries": max_retries,
        "healed": False,
        "heal_log": [],
    }
    return await healing_subgraph.ainvoke(heal_state)


def invoke_healing_subgraph_sync(
    error_message: str,
    context: Dict[str, Any],
    *,
    step: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
) -> Dict[str, Any]:
    async def _run() -> Dict[str, Any]:
        return await invoke_healing_subgraph_async(
            error_message,
            context,
            step=step,
            max_retries=max_retries,
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run())

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(asyncio.run, _run())
        try:
            return fut.result(timeout=180)
        except Exception as e:
            logger.exception("invoke_healing_subgraph_sync failed: %s", e)
            return {
                "healed": False,
                "diagnosis": {},
                "repair_result": {"success": False, "reason": str(e)},
                "tool_calls": [],
                "heal_log": [f"sync_bridge_error:{e}"],
            }
