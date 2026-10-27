# 定义一个函数
def login(base_url, username, password):
    """登录接口，返回 token"""
    url = f"{base_url}/api/auth/login"
    payload = {"username": username, "password": password}
    
    # 这里我们先用 print 模拟，后面实际调接口
    print(f"调用登录接口：{url}")
    print(f"请求参数：{payload}")
    
    # 假设返回了 token
    token = "eyJhbGciOiJIUzI1Ni..."
    return token

# 调用函数
token = login("http://localhost:5001", "admin", "admin123")
print(f"拿到 token：{token}")
