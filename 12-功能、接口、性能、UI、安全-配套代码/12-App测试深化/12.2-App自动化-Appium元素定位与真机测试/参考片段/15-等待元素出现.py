from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 等待元素可见，最长 10 秒
element = WebDriverWait(driver, 10).until(
    EC.visibility_of_element_located((AppiumBy.ACCESSIBILITY_ID, "登录按钮"))
)
