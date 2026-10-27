-- 统计每个用户的订单数
SELECT user_id, COUNT(*) as order_count
FROM orders
GROUP BY user_id;

-- 只要订单数大于 5 的用户（用 HAVING，不是 WHERE！）
SELECT user_id, COUNT(*) as order_count, SUM(amount) as total_amount
FROM orders
GROUP BY user_id
HAVING COUNT(*) > 5;

-- 区别：WHERE 在分组前过滤，HAVING 在分组后过滤
-- WHERE：过滤行（比如 status = 'paid'）
-- HAVING：过滤分组（比如 COUNT(*) > 5）
