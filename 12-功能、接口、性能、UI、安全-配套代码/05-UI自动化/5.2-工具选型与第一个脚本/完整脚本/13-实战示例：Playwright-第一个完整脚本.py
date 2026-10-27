from playwright.sync_api import sync_playwright

def test_login():
    with sync_playwright() as p:
        # 启动浏览器（无头模式）
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 打开登录页面
        page.goto("http://localhost:5000/login")
        
        # 输入用户名和密码
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin123")
        
        # 点击登录按钮
        page.click("button[type='submit']")
        
        # 等待页面跳转
        page.wait_for_url("**/dashboard")
        
        # 验证登录成功
        assert "欢迎" in page.text_content("h1")
        
        # 截图
        page.screenshot(path="login_success.png")
        
        browser.close()
