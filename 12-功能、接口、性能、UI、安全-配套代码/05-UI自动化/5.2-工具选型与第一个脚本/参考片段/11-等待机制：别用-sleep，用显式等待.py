# Playwright 会自动等待元素可见、可操作
# 你不需要手动写等待

page.fill('input[name="username"]', "admin")  # 自动等待 input 出现
page.click('text=登录')                        # 自动等待 button 可点击
page.wait_for_url("**/home")                   # 等待 URL 变化
