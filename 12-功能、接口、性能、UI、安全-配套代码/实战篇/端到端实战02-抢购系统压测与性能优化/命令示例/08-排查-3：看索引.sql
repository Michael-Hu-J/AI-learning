-- 检查订单表索引
SHOW INDEX FROM orders;
-- 发现 user_id 没有索引

-- 检查抢购记录表索引
SHOW INDEX FROM seckill_records;
-- 发现 product_id 没有索引
