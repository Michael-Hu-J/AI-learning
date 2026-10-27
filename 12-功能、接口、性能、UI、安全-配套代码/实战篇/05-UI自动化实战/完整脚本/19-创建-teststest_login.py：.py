from playwright.sync_api import sync_playwright
from page_objects.login_page import LoginPage

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login("admin", "admin123")
    
    assert "dashboard" in page.url
    print("✅ 登录成功")
    
    browser.close()
