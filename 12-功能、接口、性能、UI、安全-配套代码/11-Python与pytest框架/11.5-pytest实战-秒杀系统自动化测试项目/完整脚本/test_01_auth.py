"""认证模块测试"""
import pytest
import json

@pytest.mark.smoke
@pytest.mark.p0
class TestAuth:
    """登录/登出相关测试"""
    
    @pytest.mark.parametrize("case_data", [
        {"username": "admin", "password": "admin123", "expect": 200},
        {"username": "admin", "password": "wrong",    "expect": 401},
        {"username": "",      "password": "admin123", "expect": 400},
        {"username": "admin' OR '1'='1", "password": "admin123", "expect": 401},
    ])
    def test_login_param(self, api, case_data):
        """参数化登录测试"""
        resp = api.post("/api/auth/login", json=case_data)
        assert resp.status_code == case_data["expect"]
    
    def test_login_without_password(self, api):
        """不传密码"""
        resp = api.post("/api/auth/login", json={"username": "admin"})
        assert resp.status_code == 400
    
    def test_login_wrong_method(self, api):
        """用 GET 请求登录接口"""
        resp = api.get("/api/auth/login")
        # 405 Method Not Allowed
        assert resp.status_code == 405
    
    def test_login_response_has_token(self, api):
        """验证登录成功返回 token"""
        resp = api.post("/api/auth/login", 
                       json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert len(data["token"]) > 20  # token 长度至少 20
