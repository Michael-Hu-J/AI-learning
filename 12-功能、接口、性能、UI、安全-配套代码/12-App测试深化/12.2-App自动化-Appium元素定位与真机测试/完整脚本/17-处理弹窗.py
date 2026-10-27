"""App 自动化测试 — 秒杀系统"""
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy
import pytest

class TestSeckillApp:
    
    @pytest.fixture(scope="class")
    def driver(self):
        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.device_name = "emulator-5554"
        options.platform_version = "14"
        options.automation_name = "UiAutomator2"
        options.app_package = "com.example.seckill"
        options.app_activity = ".MainActivity"
        options.no_reset = True
        
        driver = webdriver.Remote("http://localhost:4723", options=options)
        yield driver
        driver.quit()
    
    def test_login(self, driver):
        """App 登录功能"""
        wait = WebDriverWait(driver, 10)
        
        # 输入用户名
        username = wait.until(EC.visibility_of_element_located(
            (AppiumBy.XPATH, "//android.widget.EditText[@text='请输入用户名']")))
        username.clear()
        username.send_keys("admin")
        
        # 输入密码
        password = driver.find_element(
            by=AppiumBy.XPATH, value="//android.widget.EditText[@text='请输入密码']")
        password.send_keys("admin123")
        
        # 点击登录
        login_btn = driver.find_element(
            by=AppiumBy.XPATH, value="//android.widget.Button[@text='登录']")
        login_btn.click()
        
        # 验证登录成功 → 首页标题可见
        home_title = wait.until(EC.visibility_of_element_located(
            (AppiumBy.XPATH, "//android.widget.TextView[@text='首页']")))
        assert home_title is not None
    
    def test_seckill(self, driver):
        """App 秒杀流程"""
        wait = WebDriverWait(driver, 10)
        
        # 点击秒杀活动
        seckill_btn = wait.until(EC.element_to_be_clickable(
            (AppiumBy.XPATH, "//android.widget.Button[@text='立即抢购']")))
        seckill_btn.click()
        
        # 查看订单
        time.sleep(2)
        order_text = driver.find_element(
            by=AppiumBy.XPATH, value="//android.widget.TextView[contains(@text, '订单')]")
        assert order_text is not None
