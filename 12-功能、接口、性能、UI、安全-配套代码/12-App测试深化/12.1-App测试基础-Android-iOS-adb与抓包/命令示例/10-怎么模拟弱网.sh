# 模拟丢包
adb shell iptables -A INPUT -m statistic --mode random --probability 0.1 -j DROP

# 恢复
adb shell iptables -F
