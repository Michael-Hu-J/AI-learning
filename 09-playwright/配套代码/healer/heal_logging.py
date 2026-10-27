"""
自愈日志 — 与第4篇 §5.3 示意输出对齐
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

STRATEGY_LABELS = {
    "element_locator_repair": "元素定位修复",
    "auth_refresh": "认证刷新",
    "network_retry": "网络重试",
    "assertion_adjust": "断言调整",
    "locator_repair": "元素定位修复",
}


def strategy_label(name: Optional[str]) -> str:
    if not name:
        return "无"
    return STRATEGY_LABELS.get(name, name)


def push_log(logs: List[Dict], message: str, level: str = "info") -> None:
    logs.append({"time": "", "message": message, "level": level})


def log_heal_trigger(logs: List[Dict]) -> None:
    push_log(logs, "[自愈] 触发自愈子图")


def log_heal_from_subgraph(logs: List[Dict], sg: Dict[str, Any]) -> None:
    diag = sg.get("diagnosis") or {}
    plan = sg.get("repair_plan") or {}
    et = diag.get("error_type", "unknown")
    conf = diag.get("confidence", 0)
    push_log(logs, f"[自愈] 诊断: {et} (confidence={conf:.2f})")
    strat = plan.get("strategy") or diag.get("repair_strategy")
    push_log(logs, f"[自愈] 规划: {strategy_label(strat)}")
    tool_calls = sg.get("tool_calls") or []
    if tool_calls:
        ok = sum(1 for t in tool_calls if t.get("success"))
        push_log(logs, f"[自愈]   扩展工具 {ok}/{len(tool_calls)} 成功")
    repair = sg.get("repair_result") or {}
    alts = repair.get("alternative_selectors") or []
    if alts:
        preview = " ".join(f"[{i + 1}]" for i in range(min(len(alts), 8)))
        push_log(logs, f"[自愈]   生成备选选择器 {preview}...")


def try_alternatives_on_page(
    page,
    act: str,
    val: Any,
    timeout: int,
    repair: Dict[str, Any],
    logs: List[Dict],
    *,
    try_action: Callable[[str], None],
) -> Tuple[bool, Optional[str]]:
    """逐个尝试备选选择器，输出 §5.3 风格日志。返回 (是否成功, 成功的 selector)。"""
    alts = repair.get("alternative_selectors") or []
    if not alts:
        push_log(logs, "[自愈] 执行: 无备选选择器", "warning")
        return False, None

    for i, sel in enumerate(alts, 1):
        try:
            try_action(sel)
            push_log(logs, f"[自愈] 执行: 尝试 [{i}] 成功 → {sel}", "success")
            return True, sel
        except Exception:
            push_log(logs, f"[自愈] 执行: 尝试 [{i}] 失败", "info")
    push_log(logs, "[自愈] 执行: 全部备选失败", "warning")
    return False, None


def log_heal_success(logs: List[Dict], step_idx: int) -> None:
    push_log(logs, f"[自愈] 自愈成功，继续执行后续步骤...")
    push_log(logs, f" [步骤{step_idx}] 自愈后重试成功", "success")
