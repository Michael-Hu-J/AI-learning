"""
UI 执行 Worker — 独立进程运行 Playwright 测试
由 UIExecutionService 通过 subprocess.Popen 启动
通过 JSON 文件接收配置和回传结果
"""
import sys
import os
import json
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List


def _load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_result(result_path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _push_log(logs: List[Dict[str, Any]], message: str, level: str = "info") -> None:
    logs.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "message": message,
        "level": level,
    })
    if len(logs) > 500:
        logs[:] = logs[-500:]


def run(config_path: str, result_path: str, stop_flag_path: str) -> None:
    """主执行入口"""
    config = _load_config(config_path)
    exec_id = config.get("exec_id", "unknown")
    base_steps = config.get("steps", [])
    headless = bool(config.get("headless", True))
    browser_name = str(config.get("browser", "chromium")).lower()
    timeout_ms = int(config.get("timeout", 15000))
    enable_l3_ai = bool(config.get("enable_l3_ai", False))

    logs: List[Dict[str, Any]] = []
    stats = {"total": 0, "passed": 0, "failed": 0, "repaired": 0}
    step_results: List[Dict[str, Any]] = []
    locator_resolution: List[Dict[str, Any]] = []
    self_healing_plans: List[Dict[str, Any]] = []

    _push_log(logs, f" Worker 启动，exec_id={exec_id}", "info")

    try:
        from playwright.sync_api import sync_playwright
        from app.services.ui_locator_resolver import UILocatorResolver

        resolver = UILocatorResolver(enable_l3_ai=enable_l3_ai)

        with sync_playwright() as p:
            browser_launcher = {
                "chrome": p.chromium,
                "chromium": p.chromium,
                "firefox": p.firefox,
                "webkit": p.webkit,
                "edge": p.chromium,
            }.get(browser_name, p.chromium)
            browser = browser_launcher.launch(headless=headless)
            page = browser.new_page()

            _push_log(logs, f"🌐 浏览器已启动: {browser_name}", "info")
            abort = False

            for idx, step in enumerate(base_steps, start=1):
                # 检查停止标志
                if os.path.exists(stop_flag_path):
                    _push_log(logs, "⏹ 收到停止信号", "warning")
                    abort = True
                    break

                action = str(step.get("action") or "").strip()
                target = str(step.get("target") or "").strip()
                value = step.get("value")
                stats["total"] += 1

                step_result: Dict[str, Any] = {
                    "index": idx,
                    "action": action,
                    "target": target,
                    "status": "passed",
                    "duration_ms": 0,
                    "error": "",
                }
                t0 = time.time()

                try:
                    if action == "打开页面":
                        page.goto(target, wait_until="domcontentloaded", timeout=timeout_ms)
                    elif action in ["点击元素", "输入文本", "等待元素", "验证文本"]:
                        step_resolve = dict(step)
                        lh = dict(step_resolve.get("locator_hints") or {})
                        step_resolve["locator_hints"] = lh
                        step_resolve["action"] = action

                        resolution = resolver.resolve(page, step_resolve)
                        locator_resolution.append({
                            "action": action,
                            "original_selector": target,
                            "resolved_selector": resolution.get("selector", ""),
                            "level": resolution.get("level", "NONE"),
                            "attempts": resolution.get("attempts", []),
                        })
                        if not resolution.get("found"):
                            raise RuntimeError(f"element not found: {target}")

                        selector = resolution["selector"]
                        if action == "点击元素":
                            page.click(selector, timeout=timeout_ms)
                        elif action == "输入文本":
                            page.fill(selector, str(value or ""), timeout=timeout_ms)
                        elif action == "等待元素":
                            page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
                        elif action == "验证文本":
                            body = page.content()
                            expected = str(value or "")
                            if expected and expected not in body:
                                raise AssertionError(f"AssertionError: expected contains '{expected}'")
                    else:
                        step_result["status"] = "skipped"
                        stats["total"] -= 1

                    stats["passed"] += 1
                    step_result["duration_ms"] = int((time.time() - t0) * 1000)
                    _push_log(logs, f" [步骤{idx}] {action} 成功", "success")

                except Exception as e:
                    stats["failed"] += 1
                    step_result["status"] = "failed"
                    step_result["error"] = str(e)
                    step_result["duration_ms"] = int((time.time() - t0) * 1000)
                    _push_log(logs, f" [步骤{idx}] {action} 失败: {e}", "error")
                    try:
                        from app.graphs.healing_graph import invoke_healing_subgraph_sync

                        page_url = ""
                        try:
                            page_url = page.url or ""
                        except Exception:
                            page_url = ""
                        sg = invoke_healing_subgraph_sync(
                            str(e),
                            {
                                "entity": "ui_playwright",
                                "selector": target,
                                "action": action,
                                "url": page_url,
                                "session_id": exec_id,
                                "scope": "ui_playwright",
                            },
                            step={"index": idx, "target": target, "action": action},
                            run_name="ui-worker-healing",
                        )
                        self_healing_plans.append(
                            {
                                "test": f"step_{idx}",
                                "diagnosis": sg.get("diagnosis") or {},
                                "repair": sg.get("repair_result") or {},
                                "healed": bool(sg.get("healed")),
                                "heal_log": sg.get("heal_log") or [],
                                "tool_calls": sg.get("tool_calls") or [],
                            }
                        )
                        _push_log(
                            logs,
                            f" [步骤{idx}] 已走 healing_subgraph（healed={bool(sg.get('healed'))}）",
                            "info",
                        )
                    except Exception:
                        pass

                step_results.append(step_result)

            if not abort:
                status = "completed" if stats["failed"] == 0 else "failed"
            else:
                status = "stopped"

            browser.close()

    except Exception as e:
        status = "failed"
        error_detail = traceback.format_exc()
        _push_log(logs, f" 执行器异常: {e}", "error")
        _push_log(logs, error_detail, "error")
    else:
        error_detail = ""

    total = max(stats["total"], 1)
    success_rate = round((stats["passed"] / total) * 100, 2)
    _push_log(
        logs,
        f" 执行结束: total={stats['total']}, passed={stats['passed']}, "
        f"failed={stats['failed']}, repaired={stats['repaired']}, success_rate={success_rate}%",
        "info",
    )

    result = {
        "exec_id": exec_id,
        "status": status,
        "stats": stats,
        "step_results": step_results[:200],
        "locator_resolution": locator_resolution,
        "self_healing": {
            "summary": {
                "total": len(self_healing_plans),
                "repaired": sum(1 for p in self_healing_plans if p.get("healed")),
                "auto_repairable": sum(
                    1 for p in self_healing_plans if (p.get("diagnosis") or {}).get("auto_repairable")
                ),
            },
            "plans": self_healing_plans[:100],
        },
        "logs": logs,
        "end_time": datetime.now().isoformat(),
        "error": error_detail,
    }
    _save_result(result_path, result)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: ui_worker.py <config_path> <result_path> <stop_flag_path>", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3])
