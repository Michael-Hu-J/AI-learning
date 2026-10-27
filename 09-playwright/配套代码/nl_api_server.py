#!/usr/bin/env python3
"""
自然语言 UI 自动化 HTTP 服务 + 简易对话页。

启动:
  python nl_api_server.py
  # 默认 http://127.0.0.1:5010  对话页 http://127.0.0.1:5010/

环境变量:
  NL_API_HOST  NL_API_PORT  NL_PARSER  SECKILL_BASE_URL
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from nl_service import execute_nl, parse_only
from seckill_config import SECKILL_BASE_URL

APP_ROOT = Path(__file__).resolve().parent
STATIC_DIR = APP_ROOT / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR))
_run_lock = threading.Lock()


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "nl_chat.html")


@app.get("/api/health")
def health():
    import requests

    seckill_ok = False
    try:
        seckill_ok = requests.get(f"{SECKILL_BASE_URL}/login", timeout=2).status_code == 200
    except Exception:
        pass
    from llm_step_parser import llm_available

    return jsonify(
        {
            "status": "ok",
            "seckill_base": SECKILL_BASE_URL,
            "seckill_running": seckill_ok,
            "llm_available": llm_available(),
            "parser": os.getenv("NL_PARSER", "auto"),
        }
    )


@app.post("/api/nl/parse")
def api_parse():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "缺少 text 字段"}), 400
    base_url = body.get("base_url")
    parser = body.get("parser")
    return jsonify(parse_only(text, base_url=base_url, parser=parser))


@app.post("/api/nl/run")
def api_run():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "缺少 text 字段"}), 400

    base_url = body.get("base_url")
    headless = bool(body.get("headless", True))
    parser = body.get("parser")

    with _run_lock:
        result = execute_nl(text, base_url=base_url, headless=headless, parser=parser)

    code = 200 if result.get("success") else 422
    return jsonify(result), code


def main():
    host = os.getenv("NL_API_HOST", "127.0.0.1")
    port = int(os.getenv("NL_API_PORT", "5010"))
    print(f"NL UI API: http://{host}:{port}/")
    print(f"业务系统: {SECKILL_BASE_URL} （需已启动 python run.py）")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
