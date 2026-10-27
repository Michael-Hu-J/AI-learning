# toast_helper.py - Toast消息和弹窗处理工具
"""
Toast消息和系统弹窗处理工具

功能：
1. 获取Toast消息文本（如"登录成功"、"网络错误"等短暂提示）
2. 等待特定Toast出现
3. 处理系统权限弹窗（如定位、相机、通知权限）
4. 处理通用弹窗（Alert）

通俗理解：Toast是手机上那些"一闪而过"的小提示（比如"操作成功"），
弹窗是需要你点击确认或取消的对话框。
"""

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Optional
import time
from utils.logger import Logger

logger = Logger().get_logger()

# Toast默认XPath（适用于Appium 2.0）
DEFAULT_TOAST_XPATH = "//*[@class='android.widget.Toast']"

# 系统权限弹窗常见文本特征（可按项目扩展）
SYSTEM_ALERT_TEXT_KEYWORDS = [
    "允许", "拒绝", "权限", "permission", "allow", "deny",
    "确定", "取消", "同意",
]

# 系统权限弹窗常见按钮文本
SYSTEM_ALERT_BUTTONS = {
    "accept": ["允许", "同意", "allow", "permit", "while using the app", "仅在使用中允许"],
    "deny": ["拒绝", "deny", "禁止"],
}


def get_toast_text(driver, toast_xpath: Optional[str] = None, timeout: int = 5) -> Optional[str]:
    """
    获取当前页面上的Toast消息文本

    通俗理解：在页面上找那个一闪而过的小提示，读取它上面的文字。
    比如登录成功后出现的"登录成功"四个字。

    参数说明：
    - driver: Appium WebDriver实例
    - toast_xpath: 自定义Toast的XPath（默认使用 DEFAULT_TOAST_XPATH）
    - timeout: 等待Toast出现的最大时间（秒），默认5秒

    返回：
    - str: Toast消息文本（如"登录成功"）
    - None: 如果未找到Toast

    支持的Toast获取方式：
    1. XPath定位：//*[@class='android.widget.Toast']（Appium 2.0原生支持）
    2. UiAutomator2：通过 driver.find_element 查找 toast 类
    """
    xpath = toast_xpath or DEFAULT_TOAST_XPATH
    logger.info(f"开始获取Toast消息（超时: {timeout}秒）")
    logger.debug(f"使用的XPath: {xpath}")

    # 方法1：通过XPath查找Toast
    try:
        wait = WebDriverWait(driver, timeout)
        toast_element = wait.until(
            EC.presence_of_element_located((AppiumBy.XPATH, xpath))
        )
        toast_text = toast_element.text
        if toast_text:
            logger.info(f"成功获取到Toast消息（XPath方式）: {toast_text}")
            return toast_text
        else:
            logger.warning("找到Toast元素但文本为空")
            return None
    except TimeoutException:
        logger.debug("XPath方式未找到Toast，尝试其他方式...")

    # 方法2：通过UiAutomator2查找Toast（appPackage + Toast特征）
    try:
        # 查找文本中包含"Toast"特征的元素
        uiautomator_xpath = "//*[contains(@text, '') and @class='android.widget.Toast']"
        toast_element = driver.find_element(AppiumBy.XPATH, uiautomator_xpath)
        toast_text = toast_element.text
        if toast_text:
            logger.info(f"成功获取到Toast消息（UiAutomator方式）: {toast_text}")
            return toast_text
    except (NoSuchElementException, TimeoutException):
        logger.debug("UiAutomator方式也未找到Toast")
    except Exception as e:
        logger.debug(f"UiAutomator方式查找异常: {str(e)}")

    # 方法3：尝试通过appPackage + text属性查找
    try:
        # 某些App的Toast使用自定义布局
        custom_toast_xpath = "//*[contains(@text, '' ) and (@clickable='false' or @long-clickable='false')]"
        # 获取所有可能包含文本的小控件
        candidates = driver.find_elements(AppiumBy.XPATH, custom_toast_xpath)
        for elem in candidates:
            text = elem.text
            if text and len(text) < 100:  # Toast一般较短
                # 排除普通界面元素（通常有特定属性）
                is_toast = True
                for attr_name in ["clickable", "focusable", "scrollable"]:
                    attr_val = elem.get_attribute(attr_name)
                    if attr_val == "true":
                        is_toast = False
                        break
                if is_toast:
                    logger.info(f"成功获取到Toast消息（自定义方式）: {text}")
                    return text
    except Exception as e:
        logger.debug(f"自定义方式查找异常: {str(e)}")

    logger.warning("所有方式均未找到Toast消息")
    return None


def wait_for_toast(driver, text: Optional[str] = None, timeout: int = 5) -> bool:
    """
    等待特定Toast出现

    通俗理解：等着看某个提示信息会不会出现。
    比如点击"登录"按钮后，等一等看会不会弹出"登录成功"的提示。

    参数说明：
    - driver: Appium WebDriver实例
    - text: 期望的Toast文本内容（部分匹配）。如果为None，则只要出现任意Toast就算成功
    - timeout: 最大等待时间（秒），默认5秒

    返回：
    - bool: True=找到了期望的Toast，False=超时未找到

    示例：
    # 等待任意Toast出现
    wait_for_toast(driver)  # 只要出现Toast就返回True

    # 等待特定文字的Toast
    wait_for_toast(driver, text="登录成功")  # 等到包含"登录成功"的Toast
    wait_for_toast(driver, text="网络错误")  # 等到"网络错误"的Toast
    """
    logger.info(f"等待Toast出现（文本: {text or '任意'}, 超时: {timeout}秒）")

    xpath = DEFAULT_TOAST_XPATH
    if text:
        # 如果指定了文本，使用包含文本的XPath来精确查找
        xpath = f"//*[@class='android.widget.Toast' and contains(@text, '{text}')]"
        logger.debug(f"精确查找Toast，XPath: {xpath}")

    try:
        wait = WebDriverWait(driver, timeout)
        toast_element = wait.until(
            EC.presence_of_element_located((AppiumBy.XPATH, xpath))
        )
        toast_text = toast_element.text or "（无文本）"
        logger.info(f"找到期望的Toast: {toast_text}")
        return True
    except TimeoutException:
        if text:
            logger.warning(f"等待特定Toast超时（期望文本: {text}, 超时: {timeout}秒）")
        else:
            logger.warning(f"等待任意Toast出现超时（超时: {timeout}秒）")
        return False
    except Exception as e:
        logger.error(f"等待Toast时发生异常: {str(e)}")
        return False


def handle_system_alert(driver, action: str = "accept", timeout: int = 5) -> bool:
    """
    处理系统权限弹窗（如定位、相机、通知等权限请求）

    通俗理解：APP第一次打开时，手机系统经常会弹出"是否允许获取位置信息"
    "是否允许访问相册"这类对话框。这个方法就是帮我们自动点击"允许"或"拒绝"。

    参数说明：
    - driver: Appium WebDriver实例
    - action: 操作方式
        - "accept": 点击"允许"（默认）
        - "deny": 点击"拒绝"
    - timeout: 等待弹窗出现的最大时间（秒），默认5秒

    返回：
    - bool: True=成功处理了弹窗，False=未找到弹窗或处理失败

    支持的弹窗类型：
    1. Android原生权限弹窗（com.android.packageinstaller）
    2. 系统级Dialog（AlertDialog风格）
    3. 通过UiAutomator2的acceptAlert等方法

    示例：
    # 点击"允许"
    handle_system_alert(driver)  # 默认允许
    handle_system_alert(driver, action="accept")  # 同上

    # 点击"拒绝"
    handle_system_alert(driver, action="deny")
    """
    logger.info(f"处理系统权限弹窗（操作: {action}, 超时: {timeout}秒）")

    # 方法1：使用Appium内置的switch_to.alert处理（适用于原生Alert）
    try:
        alert = WebDriverWait(driver, timeout / 2).until(
            lambda d: d.switch_to.alert
        )
        alert_text = alert.text
        logger.info(f" 发现系统Alert弹窗，文本: {alert_text}")

        if action == "accept":
            alert.accept()
            logger.info(f" 点击允许系统Alert弹窗: {alert_text}")
        else:
            alert.dismiss()
            logger.info(f" 点击拒绝系统Alert弹窗: {alert_text}")
        time.sleep(0.5)
        return True
    except TimeoutException:
        logger.debug("未发现系统Alert弹窗（switch_to.alert方式）")
    except Exception as e:
        logger.debug(f"系统Alert弹窗处理异常: {str(e)}")

    # 方法2：通过XPath查找权限弹窗元素
    try:
        # 构建按钮文本列表
        if action == "accept":
            button_texts = SYSTEM_ALERT_BUTTONS["accept"]
        else:
            button_texts = SYSTEM_ALERT_BUTTONS["deny"]

        # 尝试查找权限弹窗容器
        # Android系统权限弹窗通常属于 com.android.packageinstaller 或系统UI
        alert_container_xpaths = [
            "//*[@class='android.widget.FrameLayout' and contains(@package, 'packageinstaller')]",
            "//*[@class='android.widget.FrameLayout' and contains(@package, 'permission')]",
            "//*[@class='android.widget.FrameLayout' and contains(@package, 'systemui')]",
        ]

        # 先等一会儿让弹窗完全渲染
        time.sleep(1)

        for btn_text in button_texts:
            try:
                # 使用多种定位方式查找按钮
                btn_xpaths = [
                    f"//android.widget.Button[@text='{btn_text}']",
                    f"//android.widget.TextView[@text='{btn_text}']",
                    f"//*[@text='{btn_text}']",
                    f"//*[contains(@text, '{btn_text}')]",
                ]
                for btn_xpath in btn_xpaths:
                    try:
                        button = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((AppiumBy.XPATH, btn_xpath))
                        )
                        button.click()
                        logger.info(f" 点击系统权限弹窗按钮: {btn_text}")
                        time.sleep(0.5)
                        return True
                    except (TimeoutException, NoSuchElementException):
                        continue
            except Exception:
                continue

        logger.debug("未找到系统权限弹窗按钮（XPath方式）")
    except Exception as e:
        logger.debug(f"系统权限弹窗XPath方式异常: {str(e)}")

    # 方法3：使用UiAutomator2的上下文切换（针对混合应用）
    try:
        # 获取当前所有上下文
        contexts = driver.contexts
        logger.debug(f"当前所有上下文: {contexts}")

        # 如果有NATIVE_APP之外的上下文，尝试处理
        if len(contexts) > 1:
            for ctx in contexts:
                if "NATIVE" not in ctx:
                    driver.switch_to.context(ctx)
                    logger.info(f" 切换到上下文: {ctx}")
                    # 在WebView上下文中处理弹窗
                    try:
                        from selenium.webdriver.common.by import By
                        accept_btn = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '允许') or contains(text(), 'Allow')]"))
                        )
                        accept_btn.click()
                        logger.info(" 在WebView上下文中点击允许按钮")
                        time.sleep(0.5)
                        return True
                    except Exception:
                        logger.debug("WebView上下文中未找到弹窗按钮")
                    finally:
                        # 切回原生上下文
                        driver.switch_to.context(contexts[0])
    except Exception as e:
        logger.debug(f"UiAutomator2上下文处理异常: {str(e)}")

    logger.info("未发现需要处理的系统权限弹窗")
    return False


def handle_alert(driver, action: str = "accept", timeout: int = 5) -> bool:
    """
    处理通用弹窗（Alert对话框）

    通俗理解：App内部弹出的各种对话框，比如"确认退出？"、"提示更新"、
    "网络连接失败，是否重试？"等。这个方法会自动帮你点击"确定/确认"或"取消"。

    参数说明：
    - driver: Appium WebDriver实例
    - action: 操作方式
        - "accept": 点击"确定/确认/是/OK"（默认）
        - "dismiss": 点击"取消/否/取消"或关闭
        - "accept_all": 如果有多个按钮，都点击确定
        - text: 自定义按钮文本（如传入字符串 "我知道了"，则点击该按钮）
    - timeout: 等待弹窗出现的最大时间（秒），默认5秒

    返回：
    - bool: True=成功处理了弹窗，False=未找到弹窗或处理失败

    工作原理：
    1. 优先使用Appium内置的 switch_to.alert（最快）
    2. 如果内置方法无效，通过XPath定位弹窗按钮
    3. 支持各种弹窗样式（AlertDialog、PopupWindow等）

    示例：
    # 点击"确定"
    handle_alert(driver)  # 默认确定

    # 点击"取消"
    handle_alert(driver, action="dismiss")

    # 点击自定义按钮
    handle_alert(driver, action="我知道了")
    """
    logger.info(f"处理通用弹窗（操作: {action}, 超时: {timeout}秒）")

    # 判断action参数类型：自定义文本 vs 预设操作
    custom_text = None
    preset_action = action

    if action not in ["accept", "dismiss", "accept_all"]:
        # 传入的是自定义按钮文本
        custom_text = action
        preset_action = "custom"
        logger.info(f" 使用自定义按钮文本: {custom_text}")

    # 方法1：使用Appium内置的switch_to.alert
    try:
        alert = WebDriverWait(driver, timeout / 2).until(
            lambda d: d.switch_to.alert
        )
        alert_text = alert.text
        logger.info(f" 发现Alert弹窗，文本: {alert_text}")

        if preset_action == "accept":
            alert.accept()
            logger.info(f" 接受弹窗: {alert_text}")
        elif preset_action == "dismiss":
            alert.dismiss()
            logger.info(f" 取消弹窗: {alert_text}")
        elif preset_action == "accept_all":
            # 如果有确认按钮就确认，否则取消
            try:
                alert.accept()
                logger.info(f" 接受弹窗: {alert_text}")
            except Exception:
                alert.dismiss()
                logger.info(f" 取消弹窗: {alert_text}")
        else:
            # 自定义文本 - 内置方式不支持，走XPath方式
            logger.debug("custom_text不支持内置alert，切换到XPath方式")
            try:
                alert.dismiss()
            except Exception:
                pass
            # 不return，继续走XPath方式
            raise TimeoutException("custom_text需要XPath方式")

        time.sleep(0.5)
        return True
    except TimeoutException:
        logger.debug("未发现内置Alert弹窗，尝试XPath方式")
    except Exception as e:
        logger.debug(f"内置Alert处理异常: {str(e)}")

    # 方法2：通过XPath查找弹窗按钮
    try:
        # 等待弹窗出现（给点时间渲染）
        time.sleep(0.5)

        # 常见弹窗按钮文本映射
        accept_texts = ["确定", "确认", "是", "OK", "好", "允许", "同意", "知道了", "继续"]
        dismiss_texts = ["取消", "否", "关闭", "取消", "稍后", "以后再说", "暂不"]
        cancel_texts = ["取消"]

        if custom_text:
            target_texts = [custom_text]
        elif preset_action == "accept":
            target_texts = accept_texts
        elif preset_action == "dismiss":
            target_texts = dismiss_texts
        elif preset_action == "accept_all":
            # accept_all策略：先找确定按钮，找不到再点取消
            target_texts = accept_texts + dismiss_texts
        else:
            target_texts = []

        # 查找弹窗容器（多种弹窗样式）
        dialog_xpaths = [
            "//android.widget.LinearLayout[contains(@class, 'AlertDialog')]",
            "//*[@class='android.widget.FrameLayout' and contains(@package, 'app')]",
            "//*[@class='android.app.Dialog']",
        ]

        for btn_text in target_texts:
            try:
                btn_xpaths = [
                    f"//android.widget.Button[@text='{btn_text}']",
                    f"//android.widget.TextView[@text='{btn_text}']",
                    f"//*[@text='{btn_text}']",
                    f"//*[contains(@text, '{btn_text}')]",
                ]
                for btn_xpath in btn_xpaths:
                    try:
                        button = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((AppiumBy.XPATH, btn_xpath))
                        )
                        button.click()
                        logger.info(f" 点击弹窗按钮: {btn_text}")
                        time.sleep(0.5)
                        return True
                    except (TimeoutException, NoSuchElementException):
                        continue
            except Exception:
                continue

        # 尝试直接点击弹窗中的第一个按钮
        try:
            first_button_xpath = "//android.widget.Button[1]"
            first_button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((AppiumBy.XPATH, first_button_xpath))
            )
            first_button_text = first_button.text or "（无文本）"
            first_button.click()
            logger.info(f" 点击弹窗中第一个按钮: {first_button_text}")
            time.sleep(0.5)
            return True
        except (TimeoutException, NoSuchElementException):
            logger.debug("未找到弹窗中的任何按钮")

        logger.debug("未找到通用弹窗按钮（XPath方式）")
    except Exception as e:
        logger.debug(f"通用弹窗XPath方式异常: {str(e)}")

    # 方法3：尝试通过坐标点击（弹窗一般居中，点击确定一般在中下位置）
    if preset_action == "accept" and not custom_text:
        try:
            size = driver.get_window_size()
            width = size['width']
            height = size['height']

            # 弹窗"确定"按钮通常位于屏幕中间偏下位置
            click_x = width // 2
            click_y = int(height * 0.65)

            driver.tap([(click_x, click_y)], 100)
            logger.info(f" 通过坐标点击弹窗确认按钮（{click_x}, {click_y}）")
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.debug(f"坐标点击弹窗异常: {str(e)}")

    logger.info("未发现需要处理的通用弹窗")
    return False
