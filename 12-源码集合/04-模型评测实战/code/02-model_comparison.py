import pytest
import requests
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://http://http://localhost:8000"

@pytest.mark.parametrize("page,size,expected_count", [
    (1, 10, 10),
    (2, 10, 10),
    (999, 10, 0),
])
def test_product_list(page, size, expected_count):
    """商品列表查询"""
    logger.info(f"查询商品列表: page={page}, size={size}")
    resp = requests.get(f"{BASE_URL}/api/products", params={"page": page, "size": size})
    assert resp.status_code == 200
    data = resp.json()
    assert "products" in data
    assert len(data["products"]) == expected_count

import pytest
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "http://http://http://localhost:8000"

class TestProductAPI:
    """商品相关接口测试"""
    
    @pytest.mark.parametrize("page,size,expected_min", [
        (1, 10, 1),
        (2, 10, 0),
    ])
    def test_list(self, page, size, expected_min):
        logger.info(f"GET /api/products?page={page}&size={size}")
        r = requests.get(f"{BASE_URL}/api/products", params={"page": page, "size": size})
        assert r.status_code == 200
        body = r.json()
        assert "products" in body
        assert len(body["products"]) >= expected_min

from locust import HttpUser, task, between
import random
import logging

logging.basicConfig(level=logging.INFO)

class SeckillUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """用户启动时登录"""
        resp = self.client.post("/api/auth/login", json={
            "username": f"user_{random.randint(1,1000)}",
            "password": "***"
        })
        if resp.status_code == 200:
            self.token = resp.json().get("token")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
    
    @task(10)
    def browse_products(self):
        """浏览商品列表"""
        self.client.get("/api/products")
    
    @task(8)
    def view_product(self):
        """查看商品详情"""
        self.client.get(f"/api/products/{random.randint(1, 100)}")
    
    @task(2)
    def seckill(self):
        """参与秒杀"""
        resp = self.client.post("/api/seckill/start")
        if resp.status_code != 200:
            logging.warning(f"秒杀失败: {resp.status_code}")
    
    @task(3)
    def view_orders(self):
        """查询订单"""
        self.client.get("/api/orders")

from locust import HttpUser, task, between
# import random
# import logging

# logging.basicConfig(level=logging.INFO)

# class SeckillUser(HttpUser):
#     wait_time = between(1, 3)
#     host = "http://http://http://localhost:8000"
#     
#     def on_start(self):
#         """登录获取token"""
#         r = self.client.post("/api/auth/login", json={
#             "username": f"user_{random.randint(1, 1000)}",
#             "password": "***"
#         })
#         if r.status_code == 200:
#             self.token = r.json()["token"]
#             self.headers = {"Authorization": f"Bearer {self.token}"}
#         else:
#             logging.warning(f"登录失败: {r.status_code}")
#     
#     @task(10)
#     def browse_products(self):
#         """浏览商品列表"""
#         r = self.client.get("/api/products", catch_response=True)
#         if r.status_code != 200:
#             r.failure(f"商品列表查询失败: {r.status_code}")
#     
#     @task(8)
#     def view_product(self):
#         """查看商品详情"""
#         self.client.get(f"/api/products/{random.randint(1, 100)}")
#     
#     @task(2)
#     def seckill(self):
#         """参与秒杀"""
#         r = self.client.post("/api/seckill/start")
#         if r.status_code != 200:
#             logging.warning(f"秒杀失败: {r.status_code}")
#     
#     @task(3)
#     def view_orders(self):
#         """查询订单"""
#         self.client.get("/api/orders")

import requests

def test_login():
    r = requests.post('http://http://http://localhost:8000/api/auth/login', 
                      json={'username': 'test', 'password': '123'})
    assert r.status_code == 200
    
def test_get_products():
    r = requests.get('http://http://http://localhost:8000/api/products')
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
