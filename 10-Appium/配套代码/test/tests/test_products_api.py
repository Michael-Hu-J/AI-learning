"""
商品接口测试 — 真实 API 调用（示例代码）

通过 requests 调用 Mock Server 商品 API 进行真实验证。
可作为 Appium UI 测试的前置数据准备（混合测试模式）。

前置条件：Mock Server 已启动（cd demo_app && python app.py）

对应文章：第06节-API测试封装、第08节-数据驱动测试、第10节-混合测试执行器
"""
import pytest
import requests
from config import MOCK_SERVER_URL


class TestProductsAPI:
    """商品接口测试"""

    BASE_URL = MOCK_SERVER_URL

    def setup_method(self):
        self.session = requests.Session()

    def test_product_list_returns_data(self):
        """ 商品列表返回数据"""
        resp = self.session.get(f"{self.BASE_URL}/api/products")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list), f"应返回列表，实际类型: {type(data)}"
        assert len(data) >= 5, f"至少应有5个商品，实际: {len(data)}"
        assert data[0]["name"] == "iPhone 15", f"第一个商品应为 iPhone 15，实际: {data[0].get('name')}"

    def test_product_detail(self):
        """ 商品详情查询"""
        resp = self.session.get(f"{self.BASE_URL}/api/products/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert "name" in data and data["name"]
        assert "price" in data and data["price"] > 0
        assert "stock" in data and data["stock"] >= 0

    def test_product_detail_not_found(self):
        """ 不存在的商品ID返回404"""
        resp = self.session.get(f"{self.BASE_URL}/api/products/9999")
        assert resp.status_code == 404, f"不存在商品应返回404，实际: {resp.status_code}"

    def test_all_products_have_required_fields(self):
        """ 所有商品都有必填字段"""
        resp = self.session.get(f"{self.BASE_URL}/api/products")
        products = resp.json()
        for p in products:
            assert "id" in p, f"商品缺少id: {p}"
            assert "name" in p, f"商品缺少name: {p}"
            assert "price" in p, f"商品缺少price: {p}"
            assert "stock" in p, f"商品缺少stock: {p}"

    def test_highest_price_product(self):
        """ 价格最高的商品是 MacBook Pro"""
        resp = self.session.get(f"{self.BASE_URL}/api/products")
        products = resp.json()
        max_price = max(p["price"] for p in products)
        most_expensive = [p for p in products if p["price"] == max_price][0]
        assert most_expensive["name"] == "MacBook Pro"
        assert most_expensive["price"] == 14999.0
