#!/bin/bash
# 企业知识库问答系统 - 一键启动脚本

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================"
echo "企业知识库问答系统 - 一键启动"
echo "======================================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python 版本: $PYTHON_VERSION"

# 创建虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate
echo "✅ 虚拟环境已激活"

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt -q

# 检查文档目录
if [ ! -d "docs" ] || [ -z "$(ls -A docs 2>/dev/null)" ]; then
    echo "⚠️  文档目录为空，使用内置示例知识库"
fi

# 运行模式
MODE="${1:-demo}"
echo ""
echo "🚀 启动知识库问答系统 (模式: $MODE)..."
echo ""

python3 main.py --mode "$MODE"
