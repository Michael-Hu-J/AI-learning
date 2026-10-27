# 1. 用超长密码登录
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}'
# 然后去服务端看日志：tail -f /var/log/app/app.log
# 如果日志里出现了你传的密码，说明日志在泄露敏感信息

# 2. 用特殊字符触发日志异常
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "***\n[INFO] 用户数据: SELECT * FROM users"}'
# 如果日志里出现了换行后的"用户数据"字段，说明日志格式可以被注入

# 3. 模拟内部人员偷看日志
# 在 ELK 上搜索 "password" 关键词
# 如果搜到了，说明日志系统没做脱敏处理
