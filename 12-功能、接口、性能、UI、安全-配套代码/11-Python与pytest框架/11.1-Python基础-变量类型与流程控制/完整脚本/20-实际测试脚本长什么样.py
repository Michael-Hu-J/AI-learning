import requests

def test_login(base_url, username, password, expect_success=True):
    """测试登录接口"""
    url = f"{base_url}/api/auth/login"
    payload = {"username": username, "password": password}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ 请求异常：{e}")
        return False
    
    if expect_success:
        if response.status_code == 200:
            print(f"✅ 登录成功：{username}")
            return True
        else:
            print(f"❌ 期望登录成功，实际状态码 {response.status_code}")
            return False
    else:
        if response.status_code == 401:
            print(f"✅ 登录失败（符合预期）：{username}")
            return True
        else:
            print(f"❌ 期望登录失败，实际状态码 {response.status_code}")
            return False

# 执行测试
BASE = "http://localhost:5001"

test_login(BASE, "admin", "admin123", expect_success=True)
test_login(BASE, "admin", "wrong", expect_success=False)
test_login(BASE, "", "admin123", expect_success=False)
