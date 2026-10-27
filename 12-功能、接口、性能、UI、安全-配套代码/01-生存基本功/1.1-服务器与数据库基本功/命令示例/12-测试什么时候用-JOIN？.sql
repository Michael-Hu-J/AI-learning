SELECT u.name, o.amount, o.status, o.create_time
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.phone = '13800138000'
ORDER BY o.create_time DESC
LIMIT 5;
