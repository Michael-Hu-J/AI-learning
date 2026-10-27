"""
Playwright 测试真实业务系统 — 新增商品 + 商品查询
对应秒杀财务系统 (seckill_finance_system)

注意：默认 BASE_URL 使用本机 5000 端口，与配套内置 demo_app 冲突；
跑秒杀联调时不要同时启动 demo_app，或改为业务系统实际地址与端口。
"""
import pytest
import requests
import time

BASE_URL = "http://localhost:5000"  # 与 demo_app 同端口时二选一运行
LOGIN_URL = f"{BASE_URL}/api/login"
PRODUCTS_URL = f"{BASE_URL}/api/products"

# 登录获取 token
def get_token():
    r = requests.post(LOGIN_URL, json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, f"登录失败：{r.text}"
    return r.json()["token"]

class TestSeckillProduct:
    """秒杀系统商品测试"""
    
    def test_login_via_ui(self, page):
        """测试 UI 登录"""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_timeout(1500)
        
        # 填写登录表单
        page.fill('#username', "admin")
        page.fill('#password', "admin123")
        page.click('button[type="submit"]')
        
        # 等待跳转
        page.wait_for_url("**/products", timeout=5000)
        
        # 验证登录成功
        assert "products" in page.url, f"登录未跳转，当前 URL: {page.url}"
        print(f" UI 登录成功，当前 URL: {page.url}")
    
    def test_login_via_api(self):
        """测试 API 登录"""
        r = requests.post(LOGIN_URL, json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        print(f" API 登录成功，token: {data['token'][:20]}...")
    
    def test_query_products_via_ui(self, page):
        """测试 UI 查询商品列表"""
        token = get_token()
        
        # 先登录
        page.goto(f"{BASE_URL}/login")
        page.wait_for_timeout(1000)
        page.fill('#username', "admin")
        page.fill('#password', "admin123")
        page.click('button[type="submit"]')
        page.wait_for_timeout(3000)
        
        # 访问商品列表
        page.goto(f"{BASE_URL}/products")
        page.wait_for_timeout(1500)
        
        # 验证页面内容
        body_text = page.text_content("body")
        assert "商品" in body_text or "product" in body_text.lower()
        print(f" UI 商品列表查询成功")
    
    def test_query_products_via_api(self):
        """测试 API 查询商品列表"""
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        r = requests.get(PRODUCTS_URL, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f" API 商品列表查询成功，共 {len(data)} 个商品")
    
    def test_add_product_via_ui(self, page):
        """测试 UI 新增商品"""
        token = get_token()
        
        # 先登录
        page.goto(f"{BASE_URL}/login")
        page.wait_for_timeout(1000)
        page.fill('#username', "admin")
        page.fill('#password', "admin123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/products", timeout=5000)
        
        # 点击"新增商品"按钮打开弹窗
        page.click('button:has-text("新增商品")')
        page.wait_for_timeout(1000)
        
        # 填写商品表单（弹窗中只有名称、价格、库存三个字段）
        product_name = f"Playwright_UI_测试商品_{int(time.time())}"
        page.fill('#product-name', product_name)
        page.fill('#product-price', "199.9")
        page.fill('#product-stock', "50")
        
        # 点击"确认添加"按钮
        page.click('#confirm-add-btn')
        page.wait_for_timeout(3000)
        
        # 验证创建成功
        body_text = page.text_content("body")
        assert product_name in body_text, f"新增商品未显示在列表中，页面内容: {body_text[:300]}"
        print(f" UI 新增商品成功：{product_name}")
    
    def test_add_product_via_api(self):
        """测试 API 新增商品"""
        token = get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        product_data = {
            "name": f"Playwright_API_测试商品_{int(time.time())}",
            "price": 299.9,
            "stock": 100,
            "category_id": 1,
            "description": "这是 Playwright API 测试商品"
        }
        
        r = requests.post(PRODUCTS_URL, json=product_data, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == product_data["name"]
        assert data["price"] == product_data["price"]
        assert data["stock"] == product_data["stock"]
        print(f" API 新增商品成功：{data['name']} (ID: {data['id']})")
    
    def test_add_and_query_product(self, page):
        """测试新增后查询（完整流程）"""
        token = get_token()
        
        # 1. 先通过 API 新增商品
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        product_data = {
            "name": f"Playwright_完整测试_{int(time.time())}",
            "price": 399.9,
            "stock": 200,
            "category_id": 1,
            "description": "完整流程测试商品"
        }
        r = requests.post(PRODUCTS_URL, json=product_data, headers=headers)
        assert r.status_code == 201
        new_product = r.json()
        product_id = new_product["id"]
        
        # 2. 通过 UI 查询商品
        page.goto(f"{BASE_URL}/login")
        page.wait_for_timeout(1000)
        page.fill('#username', "admin")
        page.fill('#password', "admin123")
        page.click('button[type="submit"]')
        page.wait_for_timeout(3000)
        
        page.goto(f"{BASE_URL}/products")
        page.wait_for_timeout(1500)
        
        # 验证商品在列表中
        body_text = page.text_content("body")
        assert new_product["name"] in body_text
        print(f" 完整流程测试成功：新增商品 ID={product_id}，UI 查询验证通过")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
