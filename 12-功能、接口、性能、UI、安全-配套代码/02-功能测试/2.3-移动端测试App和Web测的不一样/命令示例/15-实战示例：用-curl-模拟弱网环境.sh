# macOS 上模拟 3G 网络（300ms 延迟，丢包率 1%）
sudo tc qdisc add dev en0 root netem delay 300ms loss 1%

# 测试下载功能
curl -o /dev/null -w "耗时: %{time_total}s\n" http://your-app.com/api/download

# 模拟断网
sudo tc qdisc add dev en0 root netem loss 100%

# 测试离线缓存
curl --connect-timeout 5 --max-time 10 http://your-app.com/api/offline-data

# 恢复网络
sudo tc qdisc del dev en0 root
