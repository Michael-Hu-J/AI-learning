# 用 curl 绕过前端，直接调后端接口
curl -X POST http://test-api.example.com/api/product/search \
  -H "Content-Type: application/json" \
  -d '{"keyword": "<script>alert(1)</script>"}'
