"""
UI Worker — 独立进程运行 Playwright 测试
通过 JSON 文件接收配置和回传结果
对应文章：第2篇-执行引擎、第4篇-自愈子图、第7篇-并发控制
"""
import sys, os, json, time, traceback
from datetime import datetime
from typing import Any, Dict, List

def load_config(p): return json.load(open(p, "r", encoding="utf-8"))
def save_result(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

_UI_ACTIONS = ("点击元素", "输入文本", "等待元素", "验证文本")

def run(cfg_path, res_path, stop_path):
    cfg = load_config(cfg_path)
    eid = cfg.get("exec_id", "unknown")
    steps = cfg.get("steps", [])
    headless = bool(cfg.get("headless", True))
    browser_name = str(cfg.get("browser", "chromium")).lower()
    timeout = int(cfg.get("timeout", 15000))
    logs, stats, step_results = [], {"total": 0, "passed": 0, "failed": 0, "repaired": 0}, []
    self_healing_plans: List[Dict] = []
    logs.append({"time": datetime.now().strftime("%H:%M:%S"), "message": f" Worker启动 eid={eid}", "level": "info"})
    try:
        from playwright.sync_api import sync_playwright
        from locator.resolver import UILocatorResolver
        from healer.healing_graph import invoke_healing_subgraph_sync
        from healer.heal_logging import log_heal_trigger, log_heal_from_subgraph, log_heal_success
        from healer.repair_executor import apply_repair_on_page, run_page_action
        resolver = UILocatorResolver()
        with sync_playwright() as p:
            launcher = {"chrome": p.chromium, "chromium": p.chromium, "firefox": p.firefox, "webkit": p.webkit, "edge": p.chromium}
            browser = launcher.get(browser_name, p.chromium).launch(headless=headless)
            page = browser.new_page()
            abort = False
            for idx, step in enumerate(steps, 1):
                if os.path.exists(stop_path):
                    logs.append({"time": "", "message": " 收到停止信号", "level": "warning"})
                    abort = True
                    break
                act = str(step.get("action", "")).strip()
                tgt = str(step.get("target", "")).strip()
                val = step.get("value")
                stats["total"] += 1
                sr = {"index": idx, "action": act, "target": tgt, "status": "passed", "duration_ms": 0, "error": ""}
                t0 = time.time()

                def _run_step() -> None:
                    if act == "打开页面":
                        page.goto(tgt, wait_until="domcontentloaded", timeout=timeout)
                    elif act in _UI_ACTIONS:
                        res = resolver.resolve(page, dict(step))
                        if not res.get("found"):
                            raise RuntimeError(f"element not found: {tgt}")
                        run_page_action(page, act, res["selector"], val, timeout)
                    else:
                        raise ValueError("skip")

                try:
                    if act not in ("打开页面",) + _UI_ACTIONS:
                        sr["status"] = "skipped"
                        stats["total"] -= 1
                    else:
                        _run_step()
                    stats["passed"] += 1
                    sr["duration_ms"] = int((time.time() - t0) * 1000)
                    logs.append({"time": "", "message": f" [步骤{idx}] {act} 成功", "level": "success"})
                except ValueError:
                    sr["status"] = "skipped"
                    stats["total"] -= 1
                except Exception as e:
                    stats["failed"] += 1
                    sr["status"] = "failed"
                    sr["error"] = str(e)
                    sr["duration_ms"] = int((time.time() - t0) * 1000)
                    logs.append({"time": "", "message": f" [步骤{idx}] {act} {tgt} → 失败: {e}", "level": "error"})
                    if act in _UI_ACTIONS or act == "打开页面":
                        try:
                            page_url = ""
                            try:
                                page_url = page.url or ""
                            except Exception:
                                pass
                            log_heal_trigger(logs)
                            sg = invoke_healing_subgraph_sync(
                                str(e),
                                {
                                    "url": page_url,
                                    "action": act,
                                    "selector": tgt,
                                    "value": val,
                                    "error_message": str(e),
                                    "raw_step": step,
                                    "page": page,
                                    "scope": "ui_playwright",
                                    "session_id": eid,
                                },
                                step={"index": idx, "action": act, "target": tgt},
                                max_retries=2,
                            )
                            log_heal_from_subgraph(logs, sg)
                            repair = sg.get("repair_result") or {}
                            self_healing_plans.append({
                                "test": f"step_{idx}",
                                "diagnosis": sg.get("diagnosis") or {},
                                "repair_plan": sg.get("repair_plan") or {},
                                "repair": repair,
                                "healed": False,
                                "heal_log": sg.get("heal_log") or [],
                            })

                            def _resolve_sel() -> str:
                                if act == "打开页面":
                                    return tgt
                                res = resolver.resolve(page, dict(step))
                                if not res.get("found"):
                                    raise RuntimeError(f"element not found: {tgt}")
                                return res["selector"]

                            if act == "打开页面" and repair.get("action") == "retry":
                                import time as _time
                                _time.sleep(min(int(repair.get("delay_seconds", 1)), 10))
                                try:
                                    page.goto(tgt, wait_until="domcontentloaded", timeout=timeout)
                                    ok = True
                                    logs.append({"time": "", "message": "[自愈] 执行: 网络重试后重新打开页面成功", "level": "success"})
                                except Exception:
                                    ok = False
                            else:
                                ok = apply_repair_on_page(
                                    page, act, val, timeout, repair, logs,
                                    resolve_selector=_resolve_sel if act in _UI_ACTIONS else None,
                                )

                            if ok:
                                self_healing_plans[-1]["healed"] = True
                                stats["failed"] -= 1
                                stats["repaired"] += 1
                                sr["status"] = "repaired"
                                sr["error"] = ""
                                log_heal_success(logs, idx)
                        except Exception as heal_err:
                            logs.append({"time": "", "message": f" [自愈] 异常: {heal_err}", "level": "warning"})
                step_results.append(sr)
            status = "completed" if stats["failed"] == 0 else "failed"
            if abort:
                status = "stopped"
            browser.close()
    except Exception as e:
        status = "failed"
        logs.append({"time": "", "message": f" 执行器异常: {e}", "level": "error"})
        logs.append({"time": "", "message": traceback.format_exc(), "level": "error"})
    save_result(res_path, {
        "exec_id": eid,
        "status": status,
        "stats": stats,
        "step_results": step_results[:200],
        "self_healing": {"plans": self_healing_plans[:50]},
        "logs": logs,
        "end_time": datetime.now().isoformat(),
    })

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: ui_worker.py <config_path> <result_path> <stop_flag_path>", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3])
