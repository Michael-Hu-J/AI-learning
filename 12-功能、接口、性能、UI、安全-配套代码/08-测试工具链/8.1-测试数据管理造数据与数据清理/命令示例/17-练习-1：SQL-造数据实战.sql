-- 先插用户
INSERT INTO users (name, phone) VALUES ('分页测试用户', '13999999999');

-- 批量插订单
INSERT INTO orders (user_id, amount, status, create_time)
SELECT 
    (SELECT id FROM users WHERE phone = '13999999999'),
    ROUND(RAND() * 1000, 2),
    CASE 
        WHEN seq % 3 = 0 THEN 'PAID'
        WHEN seq % 3 = 1 THEN 'CANCELLED'
        ELSE 'SHIPPED'
    END,
    DATE_SUB(NOW(), INTERVAL seq DAY)
FROM (
    SELECT 1 as seq UNION SELECT 2 UNION SELECT 3 
    -- ... 写到 30（实际用存储过程更方便）
) t;
