# test_order.py - 测试脚本
from login_page import LoginPage

def test_order(page):
    login_page = LoginPage(page)
    login_page.login("admin", "Admin1234")  # 复用登录逻辑
    page.click('text=商品列表')
    # ... 下单逻辑
