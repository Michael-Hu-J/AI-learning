-- 永远先 SELECT 确认范围
SELECT * FROM users WHERE username = 'test001';
-- 确认无误再 DELETE
DELETE FROM users WHERE username = 'test001';
