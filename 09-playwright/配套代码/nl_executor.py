"""
自然语言步骤执行器 — 针对秒杀财务系统页面结构的稳健定位。
"""
import time
from typing import Any, Dict, List, Optional

from playwright.sync_api import Page, sync_playwright

# 登录 / 商品页常用定位（秒杀系统 + demo_app 兼容）
INPUT_SELECTORS = {
    "用户名": ["#username", 'input[name="username"]', '[placeholder*="用户名"]'],
    "密码": ["#password", 'input[name="password"]', '[placeholder*="密码"]', 'input[type="password"]'],
}

FILL_LABEL_TO_SELECTOR = {
    "商品名称": ["#product-name", 'input[placeholder*="商品名称"]'],
    "价格": ["#product-price", 'input[placeholder*="价格"]'],
    "单价": ["#product-price", 'input[placeholder*="价格"]'],
    "库存": ["#product-stock", 'input[placeholder*="库存"]'],
}

CLICK_TEXT_TO_SELECTOR = {
    "新增商品": ["#add-btn", "#add-product-btn", 'button:has-text("新增商品")'],
    "确认添加": ["#confirm-add-btn", 'button:has-text("确认添加")'],
    "登录": ['button[type="submit"]', 'button:has-text("登录")', 'text="登录"'],
}


def _accept_dialogs(page: Page) -> None:
    """自动确认 alert/confirm，避免阻塞后续步骤。"""
    def _on_dialog(dialog):
        try:
            dialog.accept()
        except Exception:
            pass

    page.on("dialog", _on_dialog)


def _wait_after_confirm_add(page: Page, timeout_ms: int = 15000) -> None:
    """提交新增商品后等待 API 与列表刷新。"""
    try:
        page.wait_for_response(
            lambda r: "/api/products" in r.url and r.request.method == "POST",
            timeout=timeout_ms,
        )
    except Exception:
        pass
    try:
        page.locator("#product-table-body").get_by_text("加载中").wait_for(
            state="hidden", timeout=timeout_ms
        )
    except Exception:
        page.wait_for_timeout(1500)


def _verify_text(page: Page, text: str, timeout_ms: int = 15000) -> bool:
    """轮询等待页面出现目标文案（含表格异步刷新）。"""
    if not text:
        return False
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        body = page.text_content("body") or ""
        if text in body:
            return True
        for sel in (
            f"#product-table-body >> text={text}",
            f"#product-table >> text={text}",
            f'text="{text}"',
        ):
            try:
                page.locator(sel).first.wait_for(state="visible", timeout=800)
                return True
            except Exception:
                continue
        page.wait_for_timeout(400)
    return False


def _try_selectors(page: Page, selectors: List[str], action: str, value: Optional[str] = None, timeout: int = 5000) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if action == "fill":
                loc.fill(str(value or ""), timeout=timeout)
            elif action == "click":
                loc.click(timeout=timeout, no_wait_after=True)
            elif action == "wait_visible":
                loc.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            continue
    return False


def execute_step(page: Page, step: Dict[str, Any], base_url: str = "") -> Dict[str, Any]:
    """执行单个解析步骤，返回 {status, action, error?}。"""
    skill = step.get("skill", "")
    params = step.get("params", {}) or {}
    desc = step.get("description", skill)

    try:
        if skill == "navigate":
            url = params.get("url") or base_url
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            return {"status": "passed", "action": "navigate", "detail": page.url}

        if skill == "input":
            placeholder = params.get("placeholder", "")
            value = params.get("value", "")
            selectors = INPUT_SELECTORS.get(placeholder, [f'[placeholder*="{placeholder}"]', f"#{placeholder}"])
            if _try_selectors(page, selectors, "fill", value):
                return {"status": "passed", "action": "input", "detail": f"{placeholder}={value}"}
            raise RuntimeError(f"找不到输入框: {placeholder}")

        if skill == "fill":
            label = params.get("label", "")
            value = params.get("value", "")
            selectors = FILL_LABEL_TO_SELECTOR.get(label, [f'#{label.lower().replace(" ", "-")}'])
            if _try_selectors(page, selectors, "fill", value):
                return {"status": "passed", "action": "fill", "detail": f"{label}={value}"}
            raise RuntimeError(f"找不到输入框: {label}")

        if skill == "click":
            text = (params.get("text") or "").strip()
            # 去掉尾部「按钮」
            if text.endswith("按钮"):
                text = text[:-2].strip()
            selectors = CLICK_TEXT_TO_SELECTOR.get(text, [])
            selectors = selectors + [f'text="{text}"', f'button:has-text("{text}")', f'[role="button"]:has-text("{text}")']
            if _try_selectors(page, selectors, "click"):
                page.wait_for_timeout(800)
                if text in ("确认添加", "确认"):
                    _wait_after_confirm_add(page)
                return {"status": "passed", "action": "click", "detail": text}
            raise RuntimeError(f"无法点击: {text}")

        if skill == "wait_url":
            pattern = params.get("pattern", "**/products")
            page.wait_for_url(pattern, timeout=15000)
            return {"status": "passed", "action": "wait_url", "detail": pattern}

        if skill == "wait":
            ms = int(params.get("ms", 1000))
            page.wait_for_timeout(ms)
            return {"status": "passed", "action": "wait", "detail": f"{ms}ms"}

        if skill == "verify":
            text = (params.get("text") or "").strip()
            timeout_ms = int(params.get("timeout_ms", 15000))
            if _verify_text(page, text, timeout_ms=timeout_ms):
                return {"status": "passed", "action": "verify", "detail": text}
            raise AssertionError(f"页面未包含: {text}（已等待 {timeout_ms}ms）")

        if skill == "select":
            label = params.get("label", "")
            value = params.get("value", "")
            if not _try_selectors(page, [f'select:near(:text("{label}"))'], "click"):
                page.click(f'text="{value}"', timeout=5000)
            return {"status": "passed", "action": "select", "detail": f"{label}={value}"}

        return {"status": "skipped", "action": skill, "detail": "未知技能"}

    except Exception as e:
        return {"status": "failed", "action": skill, "error": str(e), "description": desc}


def run_nl_steps(
    parsed_steps: List[Dict[str, Any]],
    base_url: str = "",
    headless: bool = True,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """在浏览器中顺序执行步骤列表。"""
    results: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        _accept_dialogs(page)

        for i, step in enumerate(parsed_steps, 1):
            desc = step.get("description", "")
            if verbose:
                print(f"\n  [步骤 {i}/{len(parsed_steps)}] {desc}")

            out = execute_step(page, step, base_url)
            out["step"] = i
            results.append(out)

            if verbose:
                if out["status"] == "passed":
                    print(f"     {out.get('action')}: {out.get('detail', '')}")
                else:
                    print(f"     {out.get('action')}: {out.get('error', '')}")

        if verbose:
            passed = sum(1 for r in results if r["status"] == "passed")
            print(f"\n{'='*40}\n  总计: {len(results)} |  {passed} |  {len(results) - passed}\n{'='*40}")

        browser.close()

    return results


def run_nl_command(
    natural_language: str,
    base_url: Optional[str] = None,
    headless: bool = True,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """解析 + 执行一条自然语言指令。"""
    import os

    from step_parser_service import step_parser_service
    from llm_step_parser import llm_available

    from seckill_config import PRODUCTS_URL

    target = (base_url or PRODUCTS_URL).strip()
    parser_mode = os.getenv("NL_PARSER", "auto")
    parsed = step_parser_service.parse_description(natural_language, target)

    if verbose:
        print("=" * 60)
        print(" 自然语言 UI 自动化（秒杀系统）")
        print("=" * 60)
        print(f"  输入: {natural_language}")
        print(f"  目标: {target}")
        print(f"  解析: {parser_mode} ({'LLM可用' if llm_available() else '仅规则'})")
        print(f"  步骤: {len(parsed)} 个\n")

    return run_nl_steps(parsed, target, headless=headless, verbose=verbose)
