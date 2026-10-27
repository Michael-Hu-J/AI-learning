-- 没有索引：全表扫描，100 万条数据要一条条看
SELECT * FROM users WHERE phone = '13800138000';
-- 耗时：3 秒

-- 有索引：直接定位，像查字典目录
SELECT * FROM users WHERE phone = '13800138000';
-- 耗时：0.01 秒
