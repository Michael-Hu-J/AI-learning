#!/bin/bash
# 启动自然语言 UI 服务（对话页 + API）
set -e
cd "$(dirname "$0")"
export NL_API_HOST="${NL_API_HOST:-127.0.0.1}"
export NL_API_PORT="${NL_API_PORT:-5010}"
echo "对话页: http://${NL_API_HOST}:${NL_API_PORT}/"
echo "请确保秒杀系统已运行: python run.py (端口 5000)"
exec python3 nl_api_server.py
