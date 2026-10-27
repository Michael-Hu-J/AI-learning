# 统计每种错误出现的次数
grep "ERROR" /var/log/order-service.log | awk -F' - ' '{print $NF}' | sort | uniq -c | sort -rn

# 输出：
# 150 Connection refused
# 89  Timeout after 30000ms
# 45  NullPointerException
# 12  OutOfMemoryError

# 提取所有响应时间超过 3 秒的请求
grep "elapsed=" /var/log/order-service.log | awk -F'elapsed=' '{if ($2+0 > 3000) print $0}'

# 输出：
# 2025-06-07 10:23:45 WARN - 支付接口响应慢, elapsed=5000ms
# 2025-06-07 10:25:12 WARN - 查询接口响应慢, elapsed=8000ms
