#!/usr/bin/env bash
# ============================================================
# 一键运行评测
# 用法: bash run_all_tests.sh
# 前提: export DASHSCOPE_API_KEY="<你的API Key>"
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT="custom"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="${SCRIPT_DIR}/results/${TIMESTAMP}"

echo "============================================================"
echo "  AgentBench 评测套件"
echo "  Agent: ${AGENT}"
echo "  时间: ${TIMESTAMP}"
echo "  结果目录: ${RESULTS_DIR}"
echo "============================================================"

# 检查 API Key
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo " 错误: 请先设置 DASHSCOPE_API_KEY"
    echo "   export DASHSCOPE_API_KEY='<你的API Key>'"
    exit 1
fi

# 创建结果目录
mkdir -p "${RESULTS_DIR}"
mkdir -p "${RESULTS_DIR}/logs"
mkdir -p "${RESULTS_DIR}/reports"

echo ""
echo " 步骤 1/2: 运行评测"
echo "------------------------------------------------------------"
python3 "${SCRIPT_DIR}/scripts/run_full_eval.py" \
    --agent "${AGENT}" \
    --out-dir "${RESULTS_DIR}/eval_results" \
    --log-file "${RESULTS_DIR}/logs/eval.log"
echo " 评测完成: ${RESULTS_DIR}/eval_results/"

echo ""
echo " 步骤 2/2: 生成报告"
echo "------------------------------------------------------------"
python3 "${SCRIPT_DIR}/scripts/generate_report.py" \
    --results-dir "${RESULTS_DIR}/eval_results" \
    --output "${RESULTS_DIR}/reports/eval_report.html"
echo " 报告生成: ${RESULTS_DIR}/reports/eval_report.html"

echo ""
echo "============================================================"
echo "   评测完成！"
echo "  结果目录: ${RESULTS_DIR}"
echo "  报告: ${RESULTS_DIR}/reports/eval_report.html"
echo "============================================================"

# ── 可选：启动 Dashboard ──
if [ "${WITH_DASHBOARD}" = "1" ]; then
    echo ""
    echo " 启动 Dashboard..."
    echo "   访问: http://localhost:8080"
    echo "   按 Ctrl+C 停止"
    echo ""
    python3 "${SCRIPT_DIR}/dashboard_server.py" --port 8080
fi
