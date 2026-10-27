# ❌ 弱断言：只断言 URL 变了
page.click('text=登录')
page.wait_for_url("**/home")
# 首页可能加载失败了，但 URL 已经变了

# ✅ 强断言：断言页面内容
page.click('text=登录')
page.wait_for_selector('h1:has-text("欢迎回来")')
assert "欢迎回来" in page.inner_text('h1')
