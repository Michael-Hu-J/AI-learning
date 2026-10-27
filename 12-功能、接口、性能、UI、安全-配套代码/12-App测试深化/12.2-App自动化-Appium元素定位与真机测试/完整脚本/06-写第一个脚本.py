from appium import webdriver
from appium.options.android import UiAutomator2Options
import time

# 配置参数
options = UiAutomator2Options()
options.platform_name = "Android"
options.device_name = "0123456789ABCDEF"  # 从 adb devices 获取
options.platform_version = "14"           # Android 版本
options.automation_name = "UiAutomator2"
options.app_package = "com.example.app"   # App 包名
options.app_activity = ".MainActivity"    # 启动页
options.no_reset = True                   # 不重置 App 数据

# 连接 Appium Server
driver = webdriver.Remote("http://localhost:4723", options=options)
time.sleep(3)  # 等待 App 加载

# 找到登录按钮并点击
login_btn = driver.find_element(by="accessibility_id", value="登录")
login_btn.click()

# 输入用户名
username_input = driver.find_element(by="xpath", value="//android.widget.EditText[@text='请输入用户名']")
username_input.send_keys("admin")

# 输入密码
password_input = driver.find_element(by="xpath", value="//android.widget.EditText[@text='请输入密码']")
password_input.send_keys("admin123")

# 点击登录
submit_btn = driver.find_element(by="xpath", value="//android.widget.Button[@text='立即登录']")
submit_btn.click()

time.sleep(2)

# 断言：登录后页面标题是"首页"
assert "首页" in driver.page_source

# 关闭
driver.quit()
