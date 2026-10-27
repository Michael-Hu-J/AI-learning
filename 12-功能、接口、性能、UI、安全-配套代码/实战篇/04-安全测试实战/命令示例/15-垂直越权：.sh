# 普通用户尝试调管理员接口
curl -X POST http://localhost:5000/api/admin/products \
  -H "Authorization: Bearer <普通用户token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "hack", "price": 0.01}'
