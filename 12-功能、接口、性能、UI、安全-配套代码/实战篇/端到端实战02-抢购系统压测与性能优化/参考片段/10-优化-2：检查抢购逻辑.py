# seckill_service.py 里的 atomic_decrease_stock 方法
def atomic_decrease_stock(product_id, quantity):
    # 用 Redis Lua 脚本原子扣库存
    lua_script = """
    local stock = redis.call('get', KEYS[1])
    if stock and tonumber(stock) >= tonumber(ARGV[1]) then
        redis.call('decrby', KEYS[1], ARGV[1])
        return 1
    end
    return 0
    """
    # 这里没问题，Redis 原子操作不会超卖
