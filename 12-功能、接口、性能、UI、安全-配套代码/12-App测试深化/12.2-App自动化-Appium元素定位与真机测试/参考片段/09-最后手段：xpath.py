# 按文本定位
btn = driver.find_element(by="xpath", 
    value="//android.widget.Button[@text='登录']")

# 按包含文本定位
btn = driver.find_element(by="xpath",
    value="//android.widget.Button[contains(@text, '登')]")

# 按层级定位（慎用，脆弱）
btn = driver.find_element(by="xpath",
    value="//android.widget.LinearLayout[1]/android.widget.Button[2]")
