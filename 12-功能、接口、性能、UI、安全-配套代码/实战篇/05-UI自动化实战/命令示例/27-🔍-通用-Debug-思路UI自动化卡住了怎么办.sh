# 1. 加超时时间，让脚本快速失败而不是卡死
page.wait_for_selector('.product-list', timeout=5000)

# 2. 截图看当前页面状态
page.screenshot(path='debug.png')
print("当前页面已截图保存")
