# ✅ 用类封装
class TestClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        """登录并保存 token"""
        url = f"{self.base_url}/api/auth/login"
        response = requests.post(url, json={
            "username": username,
            "password": password
        })
        self.token = response.json()["token"]
        print(f"登录成功，token：{self.token[:20]}...")
    
    def create_product(self, name, price):
        """创建商品"""
        url = f"{self.base_url}/api/products"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(url, json={
            "name": name,
            "price": price
        }, headers=headers)
        return response.json()
    
    def get_products(self):
        """查询商品列表"""
        url = f"{self.base_url}/api/products"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, headers=headers)
        return response.json()

# 使用
client = TestClient("http://localhost:5001")
client.login("admin", "admin123")          # 登录一次
client.create_product("手机", 2999)         # 直接调，不用传 token
client.create_product("电脑", 5999)         # 再调一次
products = client.get_products()           # 查列表
