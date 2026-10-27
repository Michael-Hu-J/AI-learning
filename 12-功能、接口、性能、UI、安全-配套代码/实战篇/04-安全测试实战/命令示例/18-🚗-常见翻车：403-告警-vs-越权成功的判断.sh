# 1. 先确认 token 是有效的
curl http://localhost:5000/api/users/1 -H "Authorization: Bearer ***"
# 如果能调通，说明 token 有效

# 2. 再试越权
curl http://localhost:5000/api/users/2 -H "Authorization: Bearer ***"
# 返回 403 → 安全
# 返回 200 + 用户2数据 → 漏洞！
# 返回 200 + 用户1数据 → 接口做了限制，安全
