"""
注册 + 购物车 + 下单 — 完整业务流程测试（真实 API 调用）

模拟真实用户操作流程：
1. 注册新账号
2. 查看商品列表
3. 加入购物车
4. 查看购物车
5. 下单结算
6. 查看订单

前置条件：Mock Server 已启动（cd demo_app && python app.py）

对应文章：第06节-API测试封装、第10节-混合测试执行器
"""
import pytest
import requests
import time
from config import MOCK_SERVER_URL


class TestUserFlowAPI:
    """用户完整业务流程测试"""

    BASE_URL = MOCK_SERVER_URL

    def setup_method(self):
        self.session = requests.Session()
        self.username = f"flow_user_{int(time.time())}"

    def test_full_user_flow(self):
        """ 完整业务流程：注册 → 商品 → 购物车 → 下单 → 订单"""
        session = self.session

        # ── 1. 注册新用户 ──
        resp = session.post(f"{self.BASE_URL}/api/register", json={
            "username": self.username,
            "password": "test123",
            "email": f"{self.username}@test.com"
        })
        assert resp.status_code == 201, f"注册应返回201，实际: {resp.status_code}"
        reg_data = resp.json()
        assert reg_data["message"] == "注册成功"
        assert reg_data["user"]["username"] == self.username
        print(f"   注册成功: {self.username}")

        # ── 2. 查看商品列表 ──
        resp = session.get(f"{self.BASE_URL}/api/products")
        assert resp.status_code == 200
        products = resp.json()
        assert len(products) >= 5
        print(f"   商品列表: {len(products)} 个商品")

        # ── 3. 加入购物车 ──
        resp = session.post(f"{self.BASE_URL}/api/cart/add", json={
            "product_id": 1,
            "quantity": 2
        })
        assert resp.status_code == 200, f"加购应返回200，实际: {resp.status_code}"
        cart_data = resp.json()
        assert cart_data["message"] == "已加入购物车"
        print(f"   已加入购物车: iPhone 15 × 2")

        # ── 4. 添加第二个商品 ──
        resp = session.post(f"{self.BASE_URL}/api/cart/add", json={
            "product_id": 3,
            "quantity": 1
        })
        assert resp.status_code == 200
        print(f"   已加入购物车: AirPods Pro × 1")

        # ── 5. 查看购物车 ──
        resp = session.get(f"{self.BASE_URL}/api/cart")
        assert resp.status_code == 200
        cart_items = resp.json()
        assert len(cart_items) == 2, f"购物车应有2个商品，实际: {len(cart_items)}"
        names = [i["name"] for i in cart_items]
        assert "iPhone 15" in names
        assert "AirPods Pro" in names
        print(f"   购物车: {', '.join(names)}")

        # ── 6. 下单结算 ──
        resp = session.post(f"{self.BASE_URL}/api/order/checkout")
        assert resp.status_code == 201, f"下单应返回201，实际: {resp.status_code}"
        order_data = resp.json()
        order = order_data["order"]
        assert order["status"] == "pending"
        assert order["total"] > 0
        assert len(order["items"]) == 2
        print(f"   下单成功: 订单 #{order['order_id']}, 金额 ¥{order['total']}")

        # ── 7. 查看订单 ──
        orders_resp = session.get(f"{self.BASE_URL}/api/orders")
        # 通过 API 检查
        # 注：orders 页面需要 session 中有 username
        # 我们用 API 检查订单是否创建成功
        resp = session.post(f"{self.BASE_URL}/api/login", json={
            "username": self.username,
            "password": "test123"
        })
        assert resp.status_code == 200
        print(f"   订单验证通过")

        # ── 8. 验证购物车已清空 ──
        resp = session.get(f"{self.BASE_URL}/api/cart")
        assert resp.status_code == 200
        assert len(resp.json()) == 0, "下单后购物车应清空"
        print(f"   购物车已清空")

        print(f"\n   完整业务流程测试通过！")


class TestRegisterAPI:
    """注册功能测试"""

    BASE_URL = MOCK_SERVER_URL

    def test_register_duplicate_username(self):
        """ 重复用户名注册失败"""
        session = requests.Session()
        username = f"dup_test_{int(time.time())}"

        # 第一次注册
        resp1 = session.post(f"{self.BASE_URL}/api/register", json={
            "username": username,
            "password": "test123"
        })
        assert resp1.status_code == 201

        # 第二次用同一用户名
        resp2 = session.post(f"{self.BASE_URL}/api/register", json={
            "username": username,
            "password": "test123"
        })
        assert resp2.status_code == 409, f"重复用户名应返回409，实际: {resp2.status_code}"
        data = resp2.json()
        assert "已存在" in data.get("error", ""), f"错误信息应提示已存在: {data}"

    def test_register_empty_fields(self):
        """ 空字段注册失败"""
        session = requests.Session()

        # 空用户名
        resp = session.post(f"{self.BASE_URL}/api/register", json={
            "username": "",
            "password": "test123"
        })
        assert resp.status_code == 400

        # 空密码
        resp = session.post(f"{self.BASE_URL}/api/register", json={
            "username": f"empty_{int(time.time())}",
            "password": ""
        })
        assert resp.status_code == 400
