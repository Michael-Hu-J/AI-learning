"""
第4篇 §5.1–5.3 登录按钮自愈 — 与对外文章一致
错误 #login-btn → 子图诊断 → button:has-text('登录') 成功
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
WRONG_SEL = "#login-btn"


@pytest.fixture
def healing():
    pytest.importorskip("langgraph")
    return invoke_healing_subgraph_sync


class TestArticleLoginBtnHeal:
    def test_login_btn_self_heal_flow(self, demo_app, healing):
        """复现文章：Timeout waiting for #login-btn → 备选 [2] button:has-text('登录') 成功"""
        logs: list = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
                page.fill("#username", "admin")
                page.fill("#password", "admin123")

                err_msg = ""
                try:
                    page.click(WRONG_SEL, timeout=3000)
                    pytest.fail("应因错误选择器失败")
                except Exception as e:
                    err_msg = str(e)

                assert "login-btn" in err_msg.lower() or "timeout" in err_msg.lower()

                raw_step = {
                    "action": "点击元素",
                    "target": WRONG_SEL,
                    "locator_hints": {"text": "登录", "role": "button"},
                }
                log_heal_trigger(logs)
                sg = healing(
                    f"Timeout: waiting for locator('{WRONG_SEL}'): Element not found",
                    {"selector": WRONG_SEL, "raw_step": raw_step, "url": page.url},
                    step={"index": 3, "action": "点击元素", "target": WRONG_SEL},
                )
                log_heal_from_subgraph(logs, sg)

                diag = sg.get("diagnosis") or {}
                assert diag.get("error_type") == "element"
                assert diag.get("confidence", 0) >= 0.8
                assert diag.get("auto_repairable")

                repair = sg.get("repair_result") or {}
                alts = repair.get("alternative_selectors") or []
                assert f"//*[@id='login-btn']" in alts
                assert any("登录" in a for a in alts), alts[:10]

                ok, used = try_alternatives_on_page(
                    page,
                    "点击元素",
                    None,
                    5000,
                    repair,
                    logs,
                    try_action=lambda sel: run_page_action(page, "点击元素", sel, None, 5000),
                )
                assert ok, "\n".join(x["message"] for x in logs)
                assert used and "登录" in used

                assert any("[自愈] 触发自愈子图" in x["message"] for x in logs)
                assert any("诊断: element" in x["message"] for x in logs)
                assert any("规划: 元素定位修复" in x["message"] for x in logs)
                assert any("尝试 [" in x["message"] and "成功" in x["message"] for x in logs)
            finally:
                browser.close()
