-- 左连接：左表全部返回，右表没有的显示 NULL
SELECT u.name, o.amount, o.status
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;

-- 结果：
-- 张三 | 99.9 | paid
-- 张三 | 199.0 | unpaid
-- 李四 | NULL | NULL  （李四没有订单，但还是显示了）
