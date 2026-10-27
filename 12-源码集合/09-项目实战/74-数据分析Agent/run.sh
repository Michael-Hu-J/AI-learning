#!/bin/bash
set -e
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================"
echo "数据分析Agent - 一键启动"
echo "======================================"

if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "📦 安装依赖..."
pip install -r requirements.txt -q

MODE="${1:-demo}"
echo "🚀 启动数据分析Agent (模式: $MODE)..."
python3 main.py --mode "$MODE"
