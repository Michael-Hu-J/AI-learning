# 搜某个订单号
grep "orderId=12345" /var/log/order-service.log

# 搜错误，只看 ERROR 级别
grep "ERROR" /var/log/order-service.log

# 搜某个时间段的日志
grep "2024-01-15 10:23" /var/log/order-service.log

# 搜多个关键字（比如同时有 ERROR 和 timeout）
grep "ERROR" /var/log/order-service.log | grep "timeout"

# 搜错误，按时间排序
grep "ERROR" /var/log/order-service.log | sort

# 统计某个错误出现多少次
grep -c "Connection refused" /var/log/order-service.log
