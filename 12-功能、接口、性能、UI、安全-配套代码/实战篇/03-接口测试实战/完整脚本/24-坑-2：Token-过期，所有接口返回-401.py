# 在脚本里加 Token 检查
import time

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.token_time = 0
    
    def get_token(self):
        """Token 2 小时内复用，过期重新获取"""
        if self.token and time.time() - self.token_time < 7200:
            return self.token
        
        resp = requests.post(f"{self.base_url}/api/auth/login", json={
            "username": "admin", "password": "***"
        })
        self.token = resp.json()["token"]
        self.token_time = time.time()
        return self.token
    
    def post(self, url, data):
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        return requests.post(f"{self.base_url}{url}", json=data, headers=headers)

# 使用
client = APIClient("http://localhost:5000")
resp = client.post("/api/seckill/order", {"productId": 1})
