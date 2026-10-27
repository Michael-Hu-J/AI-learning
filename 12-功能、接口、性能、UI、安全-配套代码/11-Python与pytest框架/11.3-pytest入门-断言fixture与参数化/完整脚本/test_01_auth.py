import requests

BASE_URL = "http://localhost:5001"

def test_login_success():
    """正常登录"""
    response = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "token" in data
    
def test_login_fail_wrong_password():
    """密码错误"""
    response = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    
def test_login_fail_empty_username():
    """用户名为空"""
    response = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"username": "", "password": "admin123"})
    # 预期返回 400，参数校验
    assert response.status_code == 400

def test_login_fail_nonexist_user():
    """用户不存在"""
    response = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"username": "notexist123", "password": "admin123"})
    assert response.status_code == 401
