# ❌ 错误：用 sleep
page.click('text=登录')
time.sleep(3)  # 等 3 秒
assert "首页" in page.title()
