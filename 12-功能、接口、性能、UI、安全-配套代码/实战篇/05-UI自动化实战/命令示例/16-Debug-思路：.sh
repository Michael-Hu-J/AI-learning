# 1. 设置 viewport 大小（headless 默认 viewport 可能跟有界面不一样）
browser = p.chromium.launch(headless=True)
page = browser.new_page(viewport={"width": 1920, "height": 1080})

# 2. 有时 headless 需要加参数
browser = p.chromium.launch(
    headless=True,
    args=['--no-sandbox', '--disable-setuid-sandbox']
)
