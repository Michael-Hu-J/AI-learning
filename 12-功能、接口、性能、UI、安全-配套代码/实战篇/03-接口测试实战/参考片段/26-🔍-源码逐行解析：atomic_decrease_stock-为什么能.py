def atomic_decrease_stock(activity_id, product_id):
    """原子扣减库存，返回剩余库存（-1表示库存不足）"""
    stock_key = f"seckill_stock:{activity_id}:{product_id}"
    
    # Lua脚本：Redis原子操作
    lua_script = """
    local stock = redis.call("DECR", KEYS[1])
    if stock >= 0 then
        return stock
    else
        redis.call("INCR", KEYS[1])  -- 恢复库存
        return -1
    end
    """
    
    # 执行Lua脚本
    result = redis_client.eval(lua_script, 1, stock_key)
    return int(result)
