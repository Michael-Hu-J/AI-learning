"""商品管理模块测试"""
import pytest

class TestProducts:
    """商品 CRUD 测试"""
    
    @pytest.mark.smoke
    def test_create_product(self, admin_api):
        """正常创建商品"""
        resp = admin_api.post("/api/products",
                             json={"name": "测试手机", "price": 2999.00})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["name"] == "测试手机"
    
    @pytest.mark.parametrize("name, price, expect_code", [
        ("",           2999,  400),   # 名称为空
        ("测试手机",   -1,    400),   # 价格为负
        ("测试手机",   0,     400),   # 价格为 0
        ("测试手机",   99999, 200),   # 正常
        ("a" * 200,    99,    400),   # 名称超长
    ])
    def test_create_product_invalid(self, admin_api, name, price, expect_code):
        """创建商品 - 异常参数"""
        resp = admin_api.post("/api/products",
                             json={"name": name, "price": price})
        assert resp.status_code == expect_code

    def test_create_product_without_auth(self, api):
        """未认证用户不能创建商品"""
        resp = api.post("/api/products",
                       json={"name": "测试", "price": 99})
        assert resp.status_code == 401
    
    def test_create_product_by_normal_user(self, user_api):
        """普通用户无权创建商品"""
        resp = user_api.post("/api/products",
                            json={"name": "测试", "price": 99})
        assert resp.status_code == 403
    
    def test_query_products(self, admin_api):
        """查询商品列表"""
        resp = admin_api.get("/api/products")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data or "data" in data
        # 验证分页结构
        if "total" in data:
            assert data["total"] >= 0
    
    def test_delete_product(self, admin_api):
        """删除商品"""
        # 先创建
        create_resp = admin_api.post("/api/products",
                                    json={"name": "待删除商品", "price": 1})
        product_id = create_resp.json()["data"]["id"]
        
        # 再删除
        delete_resp = admin_api.delete(f"/api/products/{product_id}")
        assert delete_resp.status_code == 200
    
    def test_delete_nonexist_product(self, admin_api):
        """删除不存在的商品"""
        resp = admin_api.delete("/api/products/99999")
        assert resp.status_code == 404
