# 进入 iframe
frame = page.frame_locator('iframe[name="content"]')
frame.fill('input[name="username"]', "admin")

# 或者
frame = page.frame(name="content")
frame.fill('input[name="username"]', "admin")
