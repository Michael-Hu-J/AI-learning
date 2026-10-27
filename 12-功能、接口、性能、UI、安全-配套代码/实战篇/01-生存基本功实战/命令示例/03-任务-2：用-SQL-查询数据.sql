-- 查所有商品
SELECT * FROM products LIMIT 10;

-- 查某个商品
SELECT * FROM products WHERE name LIKE '%手机%';

-- 统计商品数量
SELECT COUNT(*) FROM products;
