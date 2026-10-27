# 实时看日志
tail -f /var/log/app.log  # 如果日志在标准输出，直接看终端

# 搜错误
grep "ERROR" /var/log/app.log

# 搜登录
grep "login" /var/log/app.log
