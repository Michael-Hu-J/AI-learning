from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.baidu.com")
    
    # 输入搜索内容
    page.fill("input[name='wd']", "测试自动化")
    
    # 点击搜索按钮
    page.click("input[type='submit']")
    
    # 等待结果加载
    page.wait_for_timeout(2000)
    
    # 断言：页面标题包含搜索词
    assert "测试自动化" in page.title(), f"页面标题不包含搜索词，实际标题: {page.title()}"
    
    print("✅ 搜索测试通过")
    page.screenshot(path="search_result.png")
    browser.close()
