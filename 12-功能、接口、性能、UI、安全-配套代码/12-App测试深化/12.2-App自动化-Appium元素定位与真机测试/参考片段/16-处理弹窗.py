# 接受弹窗
try:
    alert = driver.switch_to.alert
    alert.accept()
except:
    pass  # 没有弹窗

# 定位系统弹窗按钮
allow_btn = driver.find_element(by="xpath",
    value="//android.widget.Button[@text='允许']")
allow_btn.click()
