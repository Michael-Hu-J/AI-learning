# 1. 先查数据库有没有慢查询
mysql -u root -p -e "SHOW FULL PROCESSLIST;"
# 如果看到大量 SQL 在 "Sending data" → 数据库慢

# 2. 看服务器资源
top  # CPU 高 → 代码问题；CPU 低但等待时间长 → 数据库/网络问题

# 3. 看日志
grep "timeout\|ERROR\|slow" /var/log/app.log
