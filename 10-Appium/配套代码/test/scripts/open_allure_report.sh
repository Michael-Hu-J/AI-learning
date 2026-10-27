#!/bin/bash

# open_allure_report.sh - 打开Allure报告（修复404问题）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "╔════════════════════════════════════════════════════════╗"
echo "║        📊 Allure报告查看工具                           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 检查allure命令是否存在
if command -v allure &> /dev/null; then
    echo "✅ 检测到allure命令，使用allure serve（推荐方式）"
    echo ""
    echo "正在启动Allure报告服务器..."
    echo "报告将自动在浏览器中打开"
    echo ""
    
    if [ -d "reports/allure-results" ]; then
        allure serve reports/allure-results
    else
        echo "❌ 错误: reports/allure-results 目录不存在"
        echo "   请先运行测试生成Allure结果"
        exit 1
    fi
else
    echo "⚠️  allure命令未找到，使用Python HTTP服务器"
    echo ""
    
    if [ -d "reports/allure-report" ]; then
        echo "启动Python HTTP服务器..."
        echo ""
        echo "报告地址: http://localhost:8888/index.html"
        echo "按 Ctrl+C 停止服务器"
        echo ""
        
        cd reports/allure-report
        python3 -m http.server 8888
    else
        echo "❌ 错误: reports/allure-report 目录不存在"
        echo "   请先生成Allure报告:"
        echo "   allure generate reports/allure-results -o reports/allure-report --clean"
        exit 1
    fi
fi

