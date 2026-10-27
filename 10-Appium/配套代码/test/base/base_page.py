# base_page.py - Page Object基类
"""
Page Object基类
功能：封装所有移动端操作（点击、滑动、输入等）
通俗理解：这是一个"操作手册"，里面包含了所有能对手机进行的操作

Page Object模式说明：
- 每个页面是一个类，类中包含该页面的元素定位和操作方法
- 好处：代码复用、易维护、清晰的结构
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Tuple, Optional
import time
from utils.logger import Logger
from utils.screenshot import ScreenshotHelper

logger = Logger().get_logger()


class BasePage:
    """
    Page Object基类
    
    作用：
    1. 封装所有常用的移动端操作（点击、滑动、输入等）
    2. 提供统一的元素定位和等待方法
    3. 所有页面类都应该继承这个基类
    """
    
    def __init__(self, driver):
        """
        初始化页面对象
        
        参数：
        - driver: Appium WebDriver实例
        """
        self.driver = driver
        self.screenshot_helper = ScreenshotHelper(driver)
        self.wait = WebDriverWait(driver, 10)  # 默认等待10秒
    
    # ==================== 元素定位方法 ====================
    
    def find_element_smart(self, locators: list, timeout: int = 10):
        """
        智能元素定位（按优先级尝试多个定位方式）
        
        参数说明：
        - locators: 定位方式列表，按优先级排列，格式：[("locator_type", "locator_value"), ...]
                   优先使用accessibility_id和resource-id，避免使用易变的XPath
        - timeout: 超时时间（秒）
        
        返回：
        - WebElement: 找到的元素对象
        
        示例：
        locators = [
            ("accessibility_id", "login_button"),
            ("resource-id", "com.app:id/login_btn"),
            ("id", "login_btn"),
            ("xpath", "//*[@text='登录']")  # XPath作为最后备选
        ]
        """
        if not locators:
            raise ValueError("locators列表不能为空")
        
        last_exception = None
        for idx, (locator_type, locator_value) in enumerate(locators):
            try:
                logger.debug(f"尝试定位方式 {idx+1}/{len(locators)}: {locator_type}={locator_value}")
                element = self.find_element(locator_type, locator_value, timeout=timeout)
                logger.info(f" 成功使用 {locator_type} 定位到元素: {locator_value}")
                return element
            except (TimeoutException, NoSuchElementException, ValueError) as e:
                last_exception = e
                logger.debug(f"定位方式 {locator_type} 失败: {str(e)}")
                continue
        
        # 所有定位方式都失败
        logger.error(f"所有定位方式都失败: {locators}")
        self.screenshot_helper.take_screenshot("element_not_found")
        raise TimeoutException(f"无法通过任何方式定位元素，最后错误: {str(last_exception)}")
    
    def find_element(self, locator_type: str, locator_value: str, timeout: int = 10):
        """
        查找单个元素（带显式等待）
        
        参数说明：
        - locator_type: 定位方式（id, resource-id, xpath, class_name, accessibility_id等）
        - locator_value: 定位值
        - timeout: 超时时间（秒）
        
        定位优先级建议：
        1. accessibility_id - 最稳定，跨平台
        2. resource-id - Android稳定（iOS使用id）
        3. id - 通用，但可能变化
        4. xpath - 最后备选，易变
        
        返回：
        - WebElement: 找到的元素对象
        """
        try:
            wait = WebDriverWait(self.driver, timeout)
            
            # 根据定位方式选择对应的By方法
            # 注意：Android的resource-id映射到ID，iOS的id也映射到ID
            locator_map = {
                "id": (AppiumBy.ID, locator_value),
                "resource-id": (AppiumBy.ID, locator_value),  # Android的resource-id
                "xpath": (AppiumBy.XPATH, locator_value),
                "class_name": (AppiumBy.CLASS_NAME, locator_value),
                "accessibility_id": (AppiumBy.ACCESSIBILITY_ID, locator_value),
                "android_uiautomator": (AppiumBy.ANDROID_UIAUTOMATOR, locator_value),
                "ios_predicate": (AppiumBy.IOS_PREDICATE, locator_value),
                "ios_class_chain": (AppiumBy.IOS_CLASS_CHAIN, locator_value),
            }
            
            if locator_type not in locator_map:
                raise ValueError(f"不支持的定位方式: {locator_type}")
            
            # 使用显式等待，等待元素可见且可交互
            element = wait.until(
                EC.presence_of_element_located(locator_map[locator_type])
            )
            logger.debug(f"找到元素: {locator_type}={locator_value}")
            return element
            
        except TimeoutException:
            logger.error(f"查找元素超时: {locator_type}={locator_value}")
            self.screenshot_helper.take_screenshot("element_not_found")
            raise
    
    def find_elements(self, locator_type: str, locator_value: str, timeout: int = 10):
        """
        查找多个元素
        
        通俗理解：在页面上找所有匹配的元素，就像找所有红色的按钮
        
        返回：
        - List[WebElement]: 元素列表
        """
        try:
            wait = WebDriverWait(self.driver, timeout)
            locator_map = {
                "id": (AppiumBy.ID, locator_value),
                "xpath": (AppiumBy.XPATH, locator_value),
                "class_name": (AppiumBy.CLASS_NAME, locator_value),
                "accessibility_id": (AppiumBy.ACCESSIBILITY_ID, locator_value),
            }
            
            if locator_type not in locator_map:
                raise ValueError(f"不支持的定位方式: {locator_type}")
            
            elements = wait.until(
                EC.presence_of_all_elements_located(locator_map[locator_type])
            )
            logger.debug(f"找到 {len(elements)} 个元素: {locator_type}={locator_value}")
            return elements
            
        except TimeoutException:
            logger.warning(f"未找到元素: {locator_type}={locator_value}")
            return []
    
    # ==================== 基础操作：点击 ====================
    
    def click(self, locator_type: str, locator_value: str, timeout: int = 10):
        """
        点击元素
        
        参数说明：
        - locator_type: 定位方式
        - locator_value: 定位值
        - timeout: 超时时间
        
        通俗理解：用手指点一下屏幕上的某个按钮或链接
        """
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            element.click()
            logger.info(f"点击元素: {locator_type}={locator_value}")
            time.sleep(0.5)  # 点击后稍等，避免操作过快
        except Exception as e:
            logger.error(f"点击元素失败: {locator_type}={locator_value}, 错误: {str(e)}")
            self.screenshot_helper.take_screenshot("click_failed")
            raise
    
    def click_by_coordinates(self, x: int, y: int):
        """
        根据坐标点击
        
        参数：
        - x: X坐标
        - y: Y坐标
        
        通俗理解：直接点屏幕上的某个位置，不管那里是什么
        """
        try:
            self.driver.tap([(x, y)], 100)  # 100毫秒的点击时长
            logger.info(f"坐标点击: ({x}, {y})")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"坐标点击失败: ({x}, {y}), 错误: {str(e)}")
            raise
    
    # ==================== 基础操作：输入 ====================
    
    def input_text(self, locator_type: str, locator_value: str, text: str, 
                   clear_first: bool = True, timeout: int = 10, char_by_char: bool = False):
        """
        输入文本
        
        参数说明：
        - locator_type: 定位方式
        - locator_value: 定位值
        - text: 要输入的文本
        - clear_first: 是否先清空原有内容
        - timeout: 超时时间
        - char_by_char: 是否逐字符输入（适用于验证码等多输入框场景）
        
        通俗理解：在输入框里打字，就像在手机上发微信输入文字
        """
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            
            if char_by_char and len(text) > 1:
                # 逐字符输入（适用于验证码等多输入框场景）
                logger.info(f"逐字符输入: {text} (共{len(text)}个字符)")
                if clear_first:
                    element.clear()
                
                for i, char in enumerate(text):
                    element.send_keys(char)
                    logger.debug(f"输入第 {i+1}/{len(text)} 个字符: {char}")
                    time.sleep(0.2)  # 每个字符之间稍作延迟
                    # 验证码输入框可能需要重新定位（因为输入后焦点会移动到下一个框）
                    if i < len(text) - 1:  # 不是最后一个字符
                        # 尝试查找下一个输入框
                        try:
                            # 查找所有输入框，选择下一个
                            from selenium.webdriver.common.by import By
                            all_inputs = self.driver.find_elements(By.XPATH, 
                                "//android.widget.TextView[@hint and @clickable='true'] | //android.widget.EditText")
                            if len(all_inputs) > 1 and i < len(all_inputs) - 1:
                                element = all_inputs[i + 1]
                                logger.debug(f"切换到第 {i+2} 个输入框")
                        except:
                            # 如果找不到下一个框，继续使用当前框
                            pass
            else:
                # 正常输入
                if clear_first:
                    element.clear()
                element.send_keys(text)
            
            logger.info(f"输入文本: {locator_type}={locator_value}, 内容: {text}")
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"输入文本失败: {locator_type}={locator_value}, 错误: {str(e)}")
            self.screenshot_helper.take_screenshot("input_failed")
            raise
    
    def input_otp_code(self, otp_code: str, timeout: int = 10):
        """
        输入OTP验证码（支持多个输入框的场景）
        
        参数：
        - otp_code: 验证码字符串（如"1313"）
        - timeout: 超时时间
        
        说明：
        - 验证码输入框可能是多个独立的输入框（每个数字一个框）
        - 会自动查找所有输入框并逐个输入
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            logger.info(f"输入OTP验证码: {otp_code} (长度: {len(otp_code)})")
            
            # 方法1：尝试查找所有验证码输入框（多个独立的输入框）
            # 查找所有小的、可点击的输入框（验证码输入框通常比较小）
            try:
                all_inputs = self.driver.find_elements(By.XPATH, 
                    "//android.widget.TextView[@hint and @clickable='true'] | //android.widget.EditText")
                
                # 过滤出可能是验证码输入框的元素（尺寸较小的）
                otp_inputs = []
                for inp in all_inputs:
                    try:
                        bounds = inp.get_attribute("bounds")
                        if bounds:
                            import re
                            match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                            if match:
                                x1, y1, x2, y2 = map(int, match.groups())
                                width = x2 - x1
                                height = y2 - y1
                                # 验证码输入框通常宽度小于150
                                if width < 200 and height < 200:
                                    otp_inputs.append(inp)
                    except:
                        pass
                
                # 如果找到多个小的输入框，逐个输入
                if len(otp_inputs) >= len(otp_code):
                    logger.info(f"发现 {len(otp_inputs)} 个验证码输入框，将逐个输入")
                    for i, char in enumerate(otp_code):
                        if i < len(otp_inputs):
                            inp = otp_inputs[i]
                            inp.click()
                            time.sleep(0.1)
                            inp.send_keys(char)
                            logger.debug(f"输入第 {i+1} 个字符 '{char}' 到输入框 {i+1}")
                            time.sleep(0.2)
                    logger.info(f" 验证码输入完成: {otp_code}")
                    return
            except Exception as e:
                logger.debug(f"方法1失败（多个输入框）: {str(e)}")
            
            # 方法2：单个输入框，使用逐字符输入
            logger.info("尝试方法2：单个输入框逐字符输入")
            try:
                # 查找验证码输入框
                otp_input = self.driver.find_element(By.XPATH,
                    "//android.widget.TextView[@hint and @clickable='true'][1] | //android.widget.EditText[1]")
                
                otp_input.click()
                time.sleep(0.2)
                
                # 清空现有内容
                otp_input.clear()
                time.sleep(0.1)
                
                # 逐字符输入
                for i, char in enumerate(otp_code):
                    otp_input.send_keys(char)
                    logger.debug(f"输入第 {i+1}/{len(otp_code)} 个字符: {char}")
                    time.sleep(0.15)  # 每个字符之间延迟
                
                logger.info(f" 验证码输入完成: {otp_code}")
                return
            except Exception as e:
                logger.debug(f"方法2失败（单输入框逐字符）: {str(e)}")
            
            # 方法3：直接一次性输入（fallback）
            logger.info("尝试方法3：一次性输入")
            try:
                otp_input = self.driver.find_element(By.XPATH,
                    "//android.widget.TextView[@hint and @clickable='true'][1] | //android.widget.EditText[1]")
                otp_input.click()
                time.sleep(0.2)
                otp_input.clear()
                otp_input.send_keys(otp_code)
                logger.info(f" 验证码输入完成: {otp_code}")
            except Exception as e:
                logger.error(f"所有验证码输入方法都失败: {str(e)}")
                raise
        
        except Exception as e:
            logger.error(f"输入验证码失败: {str(e)}")
            self.screenshot_helper.take_screenshot("otp_input_failed")
            raise
    
    def clear_text(self, locator_type: str, locator_value: str, timeout: int = 10):
        """
        清空文本
        
        通俗理解：把输入框里的字都删掉
        """
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            element.clear()
            logger.info(f"清空文本: {locator_type}={locator_value}")
        except Exception as e:
            logger.error(f"清空文本失败: {locator_type}={locator_value}, 错误: {str(e)}")
            raise
    
    # ==================== 基础操作：等待 ====================
    
    def wait_for_element(self, locator_type: str, locator_value: str, timeout: int = 10):
        """
        等待元素出现
        
        通俗理解：等某个东西出现，比如等页面加载完成
        """
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            logger.info(f"元素已出现: {locator_type}={locator_value}")
            return element
        except TimeoutException:
            logger.warning(f"等待元素超时: {locator_type}={locator_value}")
            self.screenshot_helper.take_screenshot("wait_element_timeout")
            raise
    
    def wait_for_element_disappear(self, locator_type: str, locator_value: str, timeout: int = 10):
        """
        等待元素消失
        
        通俗理解：等某个东西消失，比如等加载动画消失
        """
        try:
            wait = WebDriverWait(self.driver, timeout)
            locator_map = {
                "id": (AppiumBy.ID, locator_value),
                "xpath": (AppiumBy.XPATH, locator_value),
            }
            wait.until_not(EC.presence_of_element_located(locator_map[locator_type]))
            logger.info(f"元素已消失: {locator_type}={locator_value}")
        except TimeoutException:
            logger.warning(f"等待元素消失超时: {locator_type}={locator_value}")
    
    def wait(self, seconds: float):
        """
        固定等待（硬等待）
        
        参数：
        - seconds: 等待秒数
        
        通俗理解：什么都不做，等几秒钟
        """
        logger.debug(f"等待 {seconds} 秒")
        time.sleep(seconds)
    
    # ==================== 滑动操作 ====================
    
    def swipe_up(self, duration: int = 1000, distance: Optional[int] = None):
        """
        向上滑动
        
        参数说明：
        - duration: 滑动持续时间（毫秒），值越小滑动越快
        - distance: 滑动距离（像素），None表示滑动屏幕的一半
        
        通俗理解：手指从下往上划，像看朋友圈往上翻
        """
        try:
            size = self.driver.get_window_size()
            width = size['width']
            height = size['height']
            
            start_x = width // 2
            start_y = int(height * 0.8)  # 从屏幕80%位置开始
            end_y = int(height * 0.2) if distance is None else start_y - distance
            end_x = start_x
            
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            logger.info("向上滑动")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"向上滑动失败: {str(e)}")
            raise
    
    def swipe_down(self, duration: int = 1000, distance: Optional[int] = None):
        """
        向下滑动
        
        通俗理解：手指从上往下划，像往下看更多内容
        """
        try:
            size = self.driver.get_window_size()
            width = size['width']
            height = size['height']
            
            start_x = width // 2
            start_y = int(height * 0.2)  # 从屏幕20%位置开始
            end_y = int(height * 0.8) if distance is None else start_y + distance
            end_x = start_x
            
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            logger.info("向下滑动")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"向下滑动失败: {str(e)}")
            raise
    
    def swipe_left(self, duration: int = 1000, distance: Optional[int] = None):
        """
        向左滑动
        
        通俗理解：手指从右往左划，像翻书页向左翻
        """
        try:
            size = self.driver.get_window_size()
            width = size['width']
            height = size['height']
            
            start_x = int(width * 0.8)  # 从屏幕80%位置开始
            start_y = height // 2
            end_x = int(width * 0.2) if distance is None else start_x - distance
            end_y = start_y
            
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            logger.info("向左滑动")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"向左滑动失败: {str(e)}")
            raise
    
    def swipe_right(self, duration: int = 1000, distance: Optional[int] = None):
        """
        向右滑动
        
        通俗理解：手指从左往右划，像翻书页向右翻
        """
        try:
            size = self.driver.get_window_size()
            width = size['width']
            height = size['height']
            
            start_x = int(width * 0.2)  # 从屏幕20%位置开始
            start_y = height // 2
            end_x = int(width * 0.8) if distance is None else start_x + distance
            end_y = start_y
            
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            logger.info("向右滑动")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"向右滑动失败: {str(e)}")
            raise
    
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 1000):
        """
        自定义方向滑动
        
        参数说明：
        - start_x, start_y: 起始坐标
        - end_x, end_y: 结束坐标
        - duration: 滑动持续时间（毫秒）
        
        通俗理解：从A点滑到B点，可以任意方向
        """
        try:
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            logger.info(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"滑动失败: {str(e)}")
            raise
    
    # ==================== 长按操作 ====================
    
    def long_press(self, locator_type: str, locator_value: str, duration: int = 2000, timeout: int = 10):
        """
        长按元素
        
        参数说明：
        - locator_type: 定位方式
        - locator_value: 定位值
        - duration: 长按持续时间（毫秒），默认2秒
        - timeout: 超时时间
        
        通俗理解：按住一个按钮不松手，等弹出菜单或其他选项
        """
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            # 使用W3C Actions API进行长按（推荐方式）
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.click_and_hold(element).pause(duration / 1000).release().perform()
            except Exception:
                # 如果W3C Actions失败，回退到TouchAction
                from appium.webdriver.common.touch_action import TouchAction
                action = TouchAction(self.driver)
                action.long_press(element, duration=duration).release().perform()
            
            logger.info(f"长按元素: {locator_type}={locator_value}, 持续{duration}毫秒")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"长按元素失败: {locator_type}={locator_value}, 错误: {str(e)}")
            self.screenshot_helper.take_screenshot("long_press_failed")
            raise
    
    def long_press_by_coordinates(self, x: int, y: int, duration: int = 2000):
        """
        根据坐标长按
        
        通俗理解：按住屏幕上的某个位置不松手
        """
        try:
            # 使用TouchAction进行坐标长按
            from appium.webdriver.common.touch_action import TouchAction
            action = TouchAction(self.driver)
            action.long_press(x=x, y=y, duration=duration).release().perform()
            logger.info(f"坐标长按: ({x}, {y}), 持续{duration}毫秒")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"坐标长按失败: ({x}, {y}), 错误: {str(e)}")
            raise
    
    # ==================== 手机原生操作 ====================
    
    def press_back(self):
        """
        按手机返回键（Android）
        
        通俗理解：按手机的返回按钮，像按浏览器后退键
        """
        try:
            self.driver.back()
            logger.info("执行返回操作")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"返回操作失败: {str(e)}")
            raise
    
    def press_home(self):
        """
        按手机Home键
        
        通俗理解：按手机的主页键，回到桌面
        """
        try:
            self.driver.press_keycode(3)  # Android KeyCode 3 = Home键
            logger.info("执行Home键操作")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Home键操作可能不支持: {str(e)}")
    
    def press_menu(self):
        """
        按手机菜单键
        
        通俗理解：按手机的菜单键，打开选项菜单
        """
        try:
            self.driver.press_keycode(82)  # Android KeyCode 82 = Menu键
            logger.info("执行Menu键操作")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Menu键操作可能不支持: {str(e)}")
    
    def press_keycode(self, keycode: int):
        """
        按指定的按键码（Android）
        
        参数：
        - keycode: Android按键码
        常见按键码：
        - 4: 返回键
        - 3: Home键
        - 82: 菜单键
        - 24: 音量+
        - 25: 音量-
        - 26: 电源键
        - 66: 回车键
        
        通俗理解：直接告诉手机按哪个物理按键
        """
        try:
            self.driver.press_keycode(keycode)
            logger.info(f"执行按键码操作: {keycode}")
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"按键码操作失败: {str(e)}")
            raise
    
    def hide_keyboard(self):
        """
        隐藏键盘
        
        通俗理解：把输入法键盘收起来
        """
        try:
            self.driver.hide_keyboard()
            logger.info("隐藏键盘")
            time.sleep(0.3)
        except Exception as e:
            logger.debug(f"隐藏键盘: {str(e)}")  # 可能键盘已经隐藏，只记录debug日志
    
    # ==================== 应用操作 ====================
    
    def restart_app(self, app_package: str = None, app_activity: str = None):
        """
        重启应用
        
        参数说明：
        - app_package: 应用包名（Android）
        - app_activity: 启动Activity（Android）
        
        通俗理解：把应用关闭再重新打开，就像重启游戏一样
        """
        try:
            # 先关闭应用
            self.driver.close_app()
            logger.info("应用已关闭")
            time.sleep(2)
            
            # 重新启动应用
            if app_package and app_activity:
                self.driver.activate_app(f"{app_package}/{app_activity}")
            else:
                self.driver.launch_app()
            
            logger.info("应用已重启")
            time.sleep(3)  # 等待应用启动
        except Exception as e:
            logger.error(f"重启应用失败: {str(e)}")
            raise
    
    def close_app(self):
        """
        关闭应用
        
        通俗理解：把应用完全关闭，不是最小化
        """
        try:
            self.driver.close_app()
            logger.info("应用已关闭")
        except Exception as e:
            logger.error(f"关闭应用失败: {str(e)}")
            raise
    
    def launch_app(self):
        """
        启动应用
        
        通俗理解：打开应用
        """
        try:
            self.driver.launch_app()
            logger.info("应用已启动")
            time.sleep(2)
        except Exception as e:
            logger.error(f"启动应用失败: {str(e)}")
            raise
    
    # ==================== 获取信息 ====================
    
    def get_text(self, locator_type: str, locator_value: str, timeout: int = 10):
        """
        获取元素文本
        
        通俗理解：读取屏幕上某个地方的文字内容
        """
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            text = element.text
            logger.info(f"获取文本: {locator_type}={locator_value}, 内容: {text}")
            return text
        except Exception as e:
            logger.error(f"获取文本失败: {locator_type}={locator_value}, 错误: {str(e)}")
            raise
    
    def get_attribute(self, locator_type: str, locator_value: str, attribute_name: str, timeout: int = 10):
        """
        获取元素属性
        
        参数：
        - attribute_name: 属性名，如 "content-desc", "resource-id", "class" 等
        
        通俗理解：读取元素的某个属性值，就像读取图片的文件名一样
        """
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            attribute_value = element.get_attribute(attribute_name)
            logger.debug(f"获取属性: {locator_type}={locator_value}, {attribute_name}={attribute_value}")
            return attribute_value
        except Exception as e:
            logger.error(f"获取属性失败: {locator_type}={locator_value}, 错误: {str(e)}")
            raise
    
    def is_element_displayed(self, locator_type: str, locator_value: str, timeout: int = 5):
        """
        判断元素是否显示
        
        通俗理解：看看某个东西在不在屏幕上
        """
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            is_displayed = element.is_displayed()
            logger.debug(f"元素显示状态: {locator_type}={locator_value}, 显示: {is_displayed}")
            return is_displayed
        except (TimeoutException, NoSuchElementException):
            logger.debug(f"元素未找到或未显示: {locator_type}={locator_value}")
            return False
    
    def get_window_size(self):
        """
        获取屏幕尺寸
        
        通俗理解：看看手机屏幕有多大
        """
        size = self.driver.get_window_size()
        logger.debug(f"屏幕尺寸: {size}")
        return size
    
    # ==================== 滚动操作 ====================
    
    def scroll_to_element(self, locator_type: str, locator_value: str, direction: str = "down", 
                         max_scrolls: int = 10):
        """
        滚动到指定元素
        
        参数说明：
        - direction: 滚动方向，"up" 或 "down"
        - max_scrolls: 最大滚动次数，防止无限滚动
        
        通俗理解：一直往上或往下滑，直到找到某个东西
        """
        try:
            for i in range(max_scrolls):
                if self.is_element_displayed(locator_type, locator_value, timeout=2):
                    logger.info(f"找到目标元素，滚动次数: {i+1}")
                    return True
                
                if direction == "down":
                    self.swipe_up()
                else:
                    self.swipe_down()
                
                time.sleep(0.5)
            
            logger.warning(f"滚动{max_scrolls}次后仍未找到元素")
            return False
        except Exception as e:
            logger.error(f"滚动到元素失败: {str(e)}")
            return False

