# ❌ 错误：直接定位
page.click('text=登录')

# ✅ 正确：等元素出现再定位
page.wait_for_selector('text=登录')
page.click('text=登录')

# ✅ Playwright 自动等待（推荐）
page.click('text=登录')  # Playwright 会自动等待元素可见
