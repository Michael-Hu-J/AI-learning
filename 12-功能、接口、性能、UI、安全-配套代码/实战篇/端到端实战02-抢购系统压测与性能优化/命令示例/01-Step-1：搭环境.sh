# 启动抢购系统
cd seckill_finance_system
docker compose up -d

# 验证环境
docker ps
# 应该看到 mysql、redis、app 三个容器

curl http://localhost:5001/api/products
# 应该返回商品列表
