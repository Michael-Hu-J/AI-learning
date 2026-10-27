# 提取所有 ERROR 的时间、级别、内容
grep "ERROR" /var/log/order-service.log | awk -F' - ' '{print $1, $NF}'

# 输出：
# 2025-06-07 10:23:46 ERROR Connection refused
# 2025-06-07 10:25:12 ERROR Timeout after 30000ms
# 2025-06-07 10:30:00 ERROR NullPointerException
