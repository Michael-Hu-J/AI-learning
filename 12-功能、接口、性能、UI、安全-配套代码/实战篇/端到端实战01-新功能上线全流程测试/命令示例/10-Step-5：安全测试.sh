# 在商品名称输入 ' OR 1=1 --
curl -X POST http://localhost:5001/api/products \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "'\'' OR 1=1 --", "price": 100}'
# 预期：返回错误，不执行SQL
