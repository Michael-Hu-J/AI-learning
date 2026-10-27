#!/bin/bash
# check_device_connection.sh - 检查设备连接脚本

echo "=========================================="
echo "🔍 检查Android设备连接"
echo "=========================================="
echo ""

# 1. 检查ADB
echo "1️⃣  检查ADB..."
if command -v adb &> /dev/null; then
    echo "   ✅ ADB可用"
    adb version | head -1
else
    echo "   ❌ ADB未安装"
    exit 1
fi
echo ""

# 2. 重启ADB服务
echo "2️⃣  重启ADB服务..."
adb kill-server 2>/dev/null
sleep 1
adb start-server 2>/dev/null
sleep 2
echo "   ✅ ADB服务已重启"
echo ""

# 3. 检查设备
echo "3️⃣  检查设备连接..."
devices_output=$(adb devices 2>&1)
echo "$devices_output"
echo ""

# 分析结果
if echo "$devices_output" | grep -q "device$"; then
    device_id=$(echo "$devices_output" | grep "device$" | awk '{print $1}')
    echo "   ✅ 设备已连接: $device_id"
    echo ""
    echo "✅ 设备连接正常，可以开始测试！"
    exit 0
elif echo "$devices_output" | grep -q "unauthorized"; then
    echo "   ❌ 设备未授权"
    echo ""
    echo "📱 解决方法："
    echo "   1. 在手机上点击'允许USB调试'"
    echo "   2. 勾选'始终允许来自此计算机'"
    echo "   3. 重新运行此脚本验证"
    exit 1
else
    echo "   ❌ 未检测到设备"
    echo ""
    echo "📱 解决方法："
    echo "   1. 检查USB线是否连接"
    echo "   2. 在手机上启用USB调试（设置 → 开发者选项 → USB调试）"
    echo "   3. 在手机上选择USB连接模式为'文件传输'或'MTP'"
    echo "   4. 重新运行此脚本验证"
    exit 1
fi

