-- 看看用户表
SELECT * FROM users;

-- 看看订单表
SELECT * FROM orders;

-- 看看每个用户的订单
SELECT u.name, o.amount, o.status
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
