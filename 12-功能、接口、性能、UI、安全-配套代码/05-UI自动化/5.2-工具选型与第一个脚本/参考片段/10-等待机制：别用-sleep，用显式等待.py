# ✅ 正确：等元素出现
page.click('text=登录')
page.wait_for_selector('h1:has-text("首页")')
assert "首页" in page.title()
