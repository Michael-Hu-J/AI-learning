except redis.exceptions.ConnectionError as e:
    print(f"[WARN] Redis连接失败: {e}")
    redis_client = None
    return False
