import pytest

@pytest.mark.parametrize("username, password, expect_code", [
    ("admin",    "admin123", 200),   # 正常登录
    ("admin",    "wrong",    401),   # 密码错误
    ("",         "admin123", 400),   # 用户名为空
    ("admin",    "",         400),   # 密码为空
    ("notexist", "admin123", 401),   # 用户不存在
    ("admin' OR '1'='1", "admin123", 401),  # SQL 注入尝试
])
def test_login(username, password, expect_code):
    """参数化的登录测试"""
    response = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"username": username, "password": password})
    assert response.status_code == expect_code
