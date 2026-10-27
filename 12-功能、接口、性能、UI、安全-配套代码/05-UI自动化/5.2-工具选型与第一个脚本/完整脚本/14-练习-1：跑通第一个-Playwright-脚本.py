from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 打开一个网页
    page.goto("https://www.baidu.com")
    
    # 获取页面标题
    title = page.title()
    print(f"页面标题: {title}")
    
    # 截图
    page.screenshot(path="baidu.png")
    print("✅ 截图已保存")
    
    browser.close()
