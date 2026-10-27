"""
页面侧修复执行 — 备选 selector 逐个尝试、原步骤重试
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from healer.heal_logging import try_alternatives_on_page


def run_page_action(page, act: str, sel: str, val: Any, timeout: int) -> None:
    if act == "点击元素":
        page.click(sel, timeout=timeout)
    elif act == "输入文本":
        page.fill(sel, str(val or ""), timeout=timeout)
    elif act == "等待元素":
        page.locator(sel).first.wait_for(state="visible", timeout=timeout)
    elif act == "验证文本":
        body = page.content()
        if str(val or "") and str(val) not in body:
            raise AssertionError(f"AssertionError: expected contains '{val}'")
    else:
        raise ValueError(f"unsupported action: {act}")


def apply_repair_on_page(
    page,
    act: str,
    val: Any,
    timeout: int,
    repair: Dict[str, Any],
    logs: List[Dict],
    *,
    resolve_selector: Optional[Callable[[], str]] = None,
) -> bool:
    if not repair.get("success"):
        return False

    action = repair.get("action", "")
    if action == "retry_with_alternatives":

        def _try(sel: str) -> None:
            run_page_action(page, act, sel, val, timeout)

        ok, _ = try_alternatives_on_page(page, act, val, timeout, repair, logs, try_action=_try)
        return ok

    if action == "retry":
        delay = int(repair.get("delay_seconds", 1))
        time.sleep(min(delay, 10))
        if resolve_selector:
            sel = resolve_selector()
            run_page_action(page, act, sel, val, timeout)
            return True
        return False

    if action == "refresh_token":
        if resolve_selector:
            sel = resolve_selector()
            run_page_action(page, act, sel, val, timeout)
            return True
        return False

    return False
