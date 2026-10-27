from playwright.sync_api import sync_playwright
from page_objects.login_page import LoginPage
from page_objects.seckill_page import SeckillPage

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # 登录
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login("admin", "admin123")
    
    # 抢购
    seckill_page = SeckillPage(page)
    seckill_page.goto_seckill()
    seckill_page.buy_seckill()
    seckill_page.verify_order_success()
    
    print("✅ 抢购成功")
    
    browser.close()
