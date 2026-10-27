# ✅ 切换到 WebView 上下文
contexts = driver.contexts
print(f"可用上下文：{contexts}")  # ['NATIVE_APP', 'WEBVIEW_com.example.seckill']

# 切到 WebView
driver.switch_to.context('WEBVIEW_com.example.seckill')

# 现在可以用 selenium 的方法定位 H5 元素
element = driver.find_element(by="css selector", value="#login-btn")

# 切回原生
driver.switch_to.context('NATIVE_APP')
