-- 每次测试前，先清理测试数据
DELETE FROM orders WHERE phone LIKE '139%';
DELETE FROM users WHERE phone LIKE '139%';

-- 然后再造新数据
INSERT INTO users ...
