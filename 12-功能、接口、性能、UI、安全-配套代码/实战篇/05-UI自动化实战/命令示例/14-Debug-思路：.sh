# 1. 可能登录失败，页面根本没跳转
# 先检查输入的账号密码对不对

# 2. 可能跳转的 URL 不是 /dashboard
# 改成更宽松的匹配：
page.wait_for_url("**/dashboard**")  # 模糊匹配

# 3. 或者不用 wait_for_url，改用 wait_for_selector
page.wait_for_selector('.dashboard-title', timeout=10000)
# 等页面上出现某个具体元素更靠谱

# 4. 终极方案：加个 fallback
try:
    page.wait_for_url("**/dashboard", timeout=5000)
except:
    page.screenshot(path='timeout_debug.png')
    print("截图已保存，检查 timeoud_debug.png")
