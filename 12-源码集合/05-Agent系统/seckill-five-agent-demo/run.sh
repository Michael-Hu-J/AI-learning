#!/bin/bash
# 秒杀五 Agent 演示 — 一键启动（对应 CrewAI 系列 20/21 篇）

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$PROJECT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

MODE="${1:-demo}"

echo "======================================"
echo "秒杀五 Agent 测试演示"
echo "======================================"

if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请安装 Python 3.8+"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "✅ 虚拟环境已激活"

pip install -r requirements.txt -q

if [ "$MODE" = "crew" ]; then
    echo "📦 安装 CrewAI 依赖..."
    pip install -r "$ROOT_DIR/requirements-crewai.txt" -q
fi

if [ "$MODE" = "test" ]; then
    pip install pytest -q
fi

echo ""
echo "🚀 启动 (模式: $MODE)..."
echo ""

python3 main.py --mode "$MODE"
