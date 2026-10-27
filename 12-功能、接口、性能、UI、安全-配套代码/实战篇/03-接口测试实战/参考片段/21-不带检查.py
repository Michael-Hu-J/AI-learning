# 修改前（安全）：
# remaining_stock = atomic_decrease_stock(activity_id, product_id)

# 修改后（故意搞崩）：
from redis_client import redis_client
stock_key = f"seckill_stock:{activity_id}:{product_id}"
remaining_stock = redis_client.decr(stock_key)  # 没有负数检查！
if remaining_stock < 0:
    # 没有恢复库存的逻辑
    pass
