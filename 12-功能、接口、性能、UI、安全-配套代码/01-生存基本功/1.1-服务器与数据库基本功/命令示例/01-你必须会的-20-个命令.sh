# 看日志最后 100 行
tail -100 /var/log/app.log

# 实时看日志（最常用，没有之一）
tail -f /var/log/app.log

# 在日志里搜关键字
grep "ERROR" /var/log/app.log

# 搜关键字，带上下文（前后各 5 行）
grep -C 5 "NullPointerException" /var/log/app.log

# 搜关键字，统计出现次数
grep -c "timeout" /var/log/app.log
