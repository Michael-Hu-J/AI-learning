# 1. 先手动打开浏览器，F12 → Elements 标签
# 确认 input[name="username"] 这个选择器对不对
# 可能实际是 input#username 或 input.login-input

# 2. 用 page.wait_for_selector() 确认元素存在再操作
page.wait_for_selector('input[name="username"]', timeout=5000)
page.fill('input[name="username"]', "admin")

# 3. 或者用 page.locator() 并截图调试
page.locator('input[name="username"]').screenshot(path='debug.png')
