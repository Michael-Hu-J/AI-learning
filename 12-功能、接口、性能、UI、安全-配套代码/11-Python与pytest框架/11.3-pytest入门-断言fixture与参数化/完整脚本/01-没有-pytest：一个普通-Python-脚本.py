# test_login_no_framework.py
import requests

def test_admin_login():
    response = requests.post("http://localhost:5001/api/auth/login",
                           json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200, f"状态码不对：{response.status_code}"
    
def test_user_login():
    response = requests.post("http://localhost:5001/api/auth/login",
                           json={"username": "testuser", "password": "test123"})
    assert response.status_code == 200

# 手动调用
test_admin_login()
test_user_login()
print("所有测试通过 ✅")
