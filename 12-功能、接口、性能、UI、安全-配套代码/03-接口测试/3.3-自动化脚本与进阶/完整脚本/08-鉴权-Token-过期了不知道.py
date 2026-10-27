import requests
import time

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.token_time = 0
    
    def get_token(self):
        """获取 Token，2 小时内复用"""
        if self.token and time.time() - self.token_time < 7200:
            return self.token
        
        response = requests.post(f"{self.base_url}/api/v1/auth/login", json={
            "username": "test",
            "password": "Test1234"
        })
        self.token = response.json()["data"]["token"]
        self.token_time = time.time()
        return self.token
    
    def post(self, url, data):
        """带 Token 的 POST 请求"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.get_token()}"
        }
        return requests.post(f"{self.base_url}{url}", json=data, headers=headers)

# 使用
client = APIClient("http://test-api.example.com")
response = client.post("/api/v1/order/create", {
    "userId": 100,
    "items": [{"productId": 12345, "quantity": 2}]
})
