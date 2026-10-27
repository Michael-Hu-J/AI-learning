from playwright.sync_api import sync_playwright
from page_objects.login_page import LoginPage
from page_objects.product_page import ProductPage

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # 登录
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login("admin", "admin123")
    
    # 商品管理
    product_page = ProductPage(page)
    product_page.goto_products()
    product_page.search_product("手机")
    product_page.verify_product_exists("手机")
    
    print("✅ 商品搜索成功")
    
    browser.close()
