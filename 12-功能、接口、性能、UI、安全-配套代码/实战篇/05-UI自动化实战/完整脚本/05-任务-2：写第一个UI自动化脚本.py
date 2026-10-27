from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 打开浏览器
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # 打开登录页面
    page.goto("http://localhost:5000")
    
    # 输入用户名密码
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin123")
    
    # 点击登录
    page.click('button[type="submit"]')
    
    # 等待跳转到首页
    page.wait_for_url("**/dashboard")
    
    # 验证登录成功
    assert "dashboard" in page.url
    print("✅ 登录成功")
    
    # 关闭浏览器
    browser.close()
