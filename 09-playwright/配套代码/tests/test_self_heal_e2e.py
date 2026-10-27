"""
端到端自愈演示 — 走 healing_graph + §5.3 日志
"""
from __future__ import annotations

import os
import sys

import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from healer.heal_logging import log_heal_from_subgraph, log_heal_trigger, try_alternatives_on_page
from healer.healing_graph import invoke_healing_subgraph_sync
from healer.repair_executor import run_page_action

BASE_URL = "http://127.0.0.1:5000"


def _run_self_heal(wrong_selector: str, is_button: bool, button_hint: dict) -> None:
    pytest.importorskip("langgraph")
    logs: list = []
    act = "点击元素" if is_button else "输入文本"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
            page.fill("#username", "admin")
            page.fill("#password", "admin123")
            page.set_default_timeout(3000)

            try:
                if is_button:
                    page.click(wrong_selector)
                else:
                    page.fill(wrong_selector, "x")
                raise AssertionError("应该失败")
            except Exception as e:
                raw_step = {
                    "action": act,
                    "target": wrong_selector,
                    "locator_hints": button_hint,
                }
                log_heal_trigger(logs)
                sg = invoke_healing_subgraph_sync(
                    str(e),
                    {"selector": wrong_selector, "raw_step": raw_step},
                )
                log_heal_from_subgraph(logs, sg)
                assert (sg.get("diagnosis") or {}).get("auto_repairable")

                repair = sg.get("repair_result") or {}
                ok, _ = try_alternatives_on_page(
                    page,
                    act,
                    "admin" if not is_button else None,
                    5000,
                    repair,
                    logs,
                    try_action=lambda sel: run_page_action(
                        page, act, sel, "admin" if not is_button else None, 5000
                    ),
                )
                assert ok, "\n".join(x["message"] for x in logs)
        finally:
            browser.close()


class TestSelfHealE2E:
    def test_element_not_found_heal(self, demo_app):
        _run_self_heal(
            "#wrong-username-input",
            False,
            {"text": "用户名", "placeholder": "请输入用户名", "role": "textbox"},
        )

    def test_wrong_button_heal(self, demo_app):
        _run_self_heal(
            "#submit-btn-wrong",
            True,
            {"text": "登录", "role": "button"},
        )
