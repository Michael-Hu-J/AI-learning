"""
UI Execution Service — 并发控制与资源管理
asyncio.Semaphore + subprocess 管理多浏览器实例
去掉 DB 依赖，使用 JSON 文件持久化
对应文章：第7篇-并发控制与资源管理
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio, subprocess, sys, json, os, uuid

def paths(eid):
    return {"config": f"/tmp/pw_{eid}_cfg.json", "result": f"/tmp/pw_{eid}_res.json", "stop": f"/tmp/pw_{eid}_stop.flag"}

def history():
    f = "/tmp/pw_exec_history.json"
    if os.path.exists(f):
        try: return json.load(open(f))
        except: return []
    return []

def save_history(items):
    os.makedirs("/tmp", exist_ok=True)
    json.dump(items, open("/tmp/pw_exec_history.json","w"), ensure_ascii=False, indent=2)

class UIExecutionService:
    def __init__(self, max_concurrent: int = 4):
        self._sem = asyncio.Semaphore(max_concurrent)
        self._active: Dict[str, asyncio.Task] = {}
        os.makedirs("/tmp", exist_ok=True)
    async def execute(self, config: Dict) -> Dict:
        eid = config.get("exec_id") or str(uuid.uuid4())[:8]
        config["exec_id"] = eid
        async def _run(): return await self._exec(config, eid)
        t = asyncio.create_task(_run())
        self._active[eid] = t
        try: return await t
        finally: self._active.pop(eid, None)
    async def _exec(self, config, eid):
        async with self._sem:
            p = paths(eid)
            json.dump(config, open(p["config"],"w"), ensure_ascii=False, indent=2)
            if os.path.exists(p["result"]): os.remove(p["result"])
            ws = os.path.join(os.path.dirname(__file__), "ui_worker.py")
            if not os.path.exists(ws):
                ws2 = os.path.join(os.path.dirname(os.path.dirname(__file__)), "worker", "ui_worker.py")
                if os.path.exists(ws2): ws = ws2
            start = datetime.now()
            proc = await asyncio.create_subprocess_exec(sys.executable, ws, p["config"], p["result"], p["stop"],
                                                       stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=float(config.get("timeout",300)))
            except asyncio.TimeoutError:
                proc.kill()
                result = {"exec_id": eid, "status": "timeout", "error": f"超时({config.get('timeout',300)}s)"}
            else:
                if os.path.exists(p["result"]): result = json.load(open(p["result"]))
                else: result = {"exec_id": eid, "status": "failed", "error": stderr.decode() if stderr else "未知错误"}
            result["duration"] = round((datetime.now() - start).total_seconds(), 2)
            h = history()
            h.append({"exec_id": eid, "status": result.get("status"), "start": start.isoformat(), "duration": result["duration"]})
            save_history(h[-100:])
            return result
    def stop(self, eid):
        p = paths(eid)
        try: open(p["stop"], "w").write("stop"); return True
        except: return False
    async def stop_all(self):
        for eid in list(self._active.keys()): self.stop(eid)
        if self._active: await asyncio.gather(*self._active.values(), return_exceptions=True)
    @property
    def active_count(self): return len(self._active)
    @property
    def max_concurrent(self): return self._sem._value

ui_execution_service = UIExecutionService(max_concurrent=4)
