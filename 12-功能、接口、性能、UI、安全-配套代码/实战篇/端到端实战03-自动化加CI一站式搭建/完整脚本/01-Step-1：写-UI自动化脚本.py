# tests/ui/test_seckill.py
from playwright.sync_api import sync_playwright
import time

def test_seckill_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. 访问首页
        page.goto("http://localhost:5001")
        assert page.title() == "抢购系统"
        
        # 2. 登录
        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'admin123')
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard")
        
        # 3. 创建抢购活动
        page.click('text=抢购管理')
        page.fill('input[name="product_id"]', '1')
        page.fill('input[name="seckill_price"]', '1.00')
        page.fill('input[name="stock"]', '10')
        page.click('button[type="submit"]')
        page.wait_for_selector('.alert-success')
        
        # 4. 验证活动创建成功
        assert "抢购活动创建成功" in page.content()
        
        browser.close()
        print("✅ UI自动化测试通过")

if __name__ == "__main__":
    test_seckill_flow()
