# 实时看日志
tail -f /var/log/app.log

# 搜错误
grep "ERROR" /var/log/app.log

# 带上下文
grep -C 5 "login" /var/log/app.log
