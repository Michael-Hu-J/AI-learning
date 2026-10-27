if not ensure_redis_connection():
    return {"success": False, "message": "Redis服务未启动，抢购功能不可用"}
