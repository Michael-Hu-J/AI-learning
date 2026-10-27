# 预热脚本
for i in {1..100}; do
    curl http://localhost:5000/api/products
done
