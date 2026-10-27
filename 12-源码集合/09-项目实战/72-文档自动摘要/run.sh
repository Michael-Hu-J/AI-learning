#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================"
echo "文档自动摘要系统 - 一键启动"
echo "======================================"

if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python 版本: $PYTHON_VERSION"

if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "✅ 虚拟环境已激活"

echo "📦 安装依赖..."
pip install -r requirements.txt -q

MODE="${1:-demo}"
echo ""
echo "🚀 启动文档自动摘要系统 (模式: $MODE)..."
echo ""

python3 main.py --mode "$MODE"
