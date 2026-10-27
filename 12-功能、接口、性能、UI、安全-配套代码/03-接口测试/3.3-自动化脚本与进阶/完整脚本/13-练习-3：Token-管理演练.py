import requests
import time

class SimpleAPIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        """登录获取 Token"""
        resp = requests.post(f"{self.base_url}/auth/login", json={
            "username": username, "password": password
        }, headers={"Content-Type": "application/json"})
        self.token = resp.json().get("token")
        return self.token is not None
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

# 演练（注意：httpbin.org 没有真实的登录接口，这里只是演示结构）
client = SimpleAPIClient("https://httpbin.org")
print("Token 管理类已定义 ✅")
