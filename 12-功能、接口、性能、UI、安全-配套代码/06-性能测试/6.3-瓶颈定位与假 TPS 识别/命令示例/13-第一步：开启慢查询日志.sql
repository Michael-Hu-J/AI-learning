-- 临时开启（重启失效，适合压测时用）
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.5;  -- 超过 0.5 秒的 SQL 记入慢查询
