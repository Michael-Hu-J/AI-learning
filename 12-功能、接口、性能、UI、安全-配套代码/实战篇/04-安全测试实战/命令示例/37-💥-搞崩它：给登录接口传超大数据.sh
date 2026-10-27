# 生成 10 万个字符的用户名
python3 -c "
print('A' * 100000)
" | xargs -I {} curl -X POST http://localhost:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "'{}'", "password": "***"}'

# 看接口返回了什么
# 如果返回 413 Payload Too Large → 有大小限制，安全
# 如果返回 500 Internal Server Error → 可能超出了数据库字段长度，服务端没处理
# 如果卡住不动了 → 可能数据库在爆内存，DoS 漏洞
