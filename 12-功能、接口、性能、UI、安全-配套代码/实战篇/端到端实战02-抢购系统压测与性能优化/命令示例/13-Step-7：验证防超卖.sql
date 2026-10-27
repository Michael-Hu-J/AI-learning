# 模拟 200 个用户同时抢购 10 件商品
# 预期：只有 10 个用户抢购成功，190 个用户返回"库存不足"

# 压测后查数据库
docker exec -it seckill_finance_system-mysql-1 mysql -u root -pseckill123 -e "
SELECT COUNT(*) as total FROM seckill_records WHERE product_id=1;
SELECT COUNT(*) as success FROM orders WHERE status='paid' AND product_id=1;
"
