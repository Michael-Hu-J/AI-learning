# macOS 模拟断网（需要管理员权限）
sudo tc qdisc add dev en0 root netem loss 100%

# 手机上操作 App，看看有没有"网络连接失败"的提示
# 不应该是白屏或者闪退

# 恢复网络
sudo tc qdisc del dev en0 root
