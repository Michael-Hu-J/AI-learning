SELECT user_id, COUNT(*) as order_count, SUM(amount) as total
FROM orders
WHERE create_time >= '2025-05-01'
GROUP BY user_id
HAVING COUNT(*) > 3 AND SUM(amount) > 500
ORDER BY total DESC;
