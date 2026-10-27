-- 内连接：只返回两个表都匹配的数据
SELECT u.name, o.amount, o.status
FROM users u
INNER JOIN orders o ON u.id = o.user_id;

-- 结果：
-- 张三 | 99.9 | paid
-- 张三 | 199.0 | unpaid
-- （李四没有订单，不显示）
