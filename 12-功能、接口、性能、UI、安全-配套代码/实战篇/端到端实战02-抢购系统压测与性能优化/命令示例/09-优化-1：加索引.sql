-- 加索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_seckill_product_id ON seckill_records(product_id);
CREATE INDEX idx_products_stock ON products(stock);
