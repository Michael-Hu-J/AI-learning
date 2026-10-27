from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 打开浏览器
    browser = p.chromium.launch(headless=False)  # headless=False 能看到浏览器操作
    page = browser.new_page()
    
    # 打开页面
    page.goto("http://localhost:8080/login")
    
    # 输入用户名密码
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "Admin1234")
    
    # 点击登录
    page.click('button[type="submit"]')
    
    # 等待跳转到首页
    page.wait_for_url("**/home")
    
    # 验证登录成功
    assert "首页" in page.title()
    print("✅ 登录成功")
    
    # 关闭浏览器
    browser.close()
