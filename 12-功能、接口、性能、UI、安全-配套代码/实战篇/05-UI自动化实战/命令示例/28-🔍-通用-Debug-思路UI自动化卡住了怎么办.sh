# 1. CI 环境通常是 headless，确保 headless 模式下也能跑
# 2. CI 环境可能没装浏览器字体，中文显示异常
# 3. 加 viewport 设置和 slow_mo
browser = p.chromium.launch(
    headless=True,
    slow_mo=500,  # 每次操作间隔 500ms，方便观察
    args=['--no-sandbox']
)
