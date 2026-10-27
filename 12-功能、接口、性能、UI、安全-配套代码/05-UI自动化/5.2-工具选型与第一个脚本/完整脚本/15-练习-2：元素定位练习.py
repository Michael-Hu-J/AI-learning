from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.baidu.com")
    
    # 练习定位：找到搜索输入框
    # 方法1：用 CSS selector
    search_input = page.query_selector("#kw")
    print(f"找到搜索框: {search_input is not None}")
    
    # 方法2：用 name 属性
    search_input2 = page.query_selector('input[name="wd"]')
    print(f"找到搜索框(name): {search_input2 is not None}")
    
    # 截图验证
    page.screenshot(path="baidu_search.png")
    browser.close()
