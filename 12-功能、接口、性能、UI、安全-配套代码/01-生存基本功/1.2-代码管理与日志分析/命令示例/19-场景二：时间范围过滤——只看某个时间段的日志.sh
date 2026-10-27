# 方法 1：grep 时间前缀（适合日志格式固定的情况）
grep "2025-06-07 10:2[3-5]" /var/log/order-service.log

# 方法 2：sed 按时间范围截取（更精确）
sed -n '/2025-06-07 10:23:00/,/2025-06-07 10:25:00/p' /var/log/order-service.log

# 方法 3：awk 按时间过滤（最灵活）
awk '$1" "$2 >= "2025-06-07 10:23:00" && $1" "$2 <= "2025-06-07 10:25:00"' /var/log/order-service.log
