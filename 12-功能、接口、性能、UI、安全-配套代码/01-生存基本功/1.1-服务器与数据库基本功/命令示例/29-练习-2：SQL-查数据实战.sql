-- 请写出 SQL：
SELECT u.name, o.amount, o.status, o.create_time
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.name = '张三'
  AND o.create_time >= '2025-06-01'
  AND o.create_time < '2025-07-01'
ORDER BY o.create_time DESC;
