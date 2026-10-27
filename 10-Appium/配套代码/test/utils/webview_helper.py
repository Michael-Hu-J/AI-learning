# webview_helper.py - WebView/H5上下文切换工具类
"""
WebView/H5上下文切换工具类
功能：在App测试中，处理原生(Native)和WebView(H5)页面之间的上下文切换
通俗理解：App里经常内嵌网页（H5），这个工具帮助你在＂App原生界面＂和＂网页界面＂之间自由切换，
就像你在浏览器和App之间来回切换一样
"""
import time
from utils.logger import Logger

logger = Logger().get_logger()


def get_available_contexts(driver):
    """
    获取当前所有可用的上下文列表

    参数说明：
    - driver: Appium WebDriver实例

    返回：
    - list: 上下文名称列表，如 ['NATIVE_APP', 'WEBVIEW_com.package.name']

    通俗理解：看看当前App里有哪些＂窗口＂可用，原生界面和网页界面都算不同的窗口
    """
    try:
        contexts = driver.contexts
        logger.info(f"获取可用上下文列表: {contexts}")
        return contexts
    except Exception as e:
        logger.error(f"获取上下文列表失败: {str(e)}")
        raise


def switch_to_webview(driver, package_name=None):
    """
    切换到WebView上下文（H5页面）

    参数说明：
    - driver: Appium WebDriver实例
    - package_name: 应用包名（可选），用于精确匹配WebView上下文。
                    如果为None则自动切换到第一个可用的WebView

    返回：
    - bool: 是否成功切换到WebView

    通俗理解：从App原生界面切换到内嵌的网页界面，之后所有的操作（如点击、输入）
    都是在网页上进行了。就像你在浏览器里操作网页一样
    """
    try:
        # 获取所有可用上下文
        contexts = driver.contexts
        logger.info(f"当前可用上下文: {contexts}")

        # 查找目标WebView上下文
        target_context = None

        if package_name:
            # 根据包名精确匹配
            webview_name = f"WEBVIEW_{package_name}"
            if webview_name in contexts:
                target_context = webview_name
        else:
            # 自动选择第一个WebView上下文
            for ctx in contexts:
                if ctx.lower().startswith("webview"):
                    target_context = ctx
                    break

        if target_context is None:
            logger.warning("未找到可用的WebView上下文")
            return False

        # 切换到WebView
        driver.switch_to.context(target_context)
        logger.info(f"成功切换到WebView: {target_context}")
        return True

    except Exception as e:
        logger.error(f"切换到WebView失败: {str(e)}")
        return False


def switch_to_native(driver):
    """
    切换回原生（Native）上下文

    参数说明：
    - driver: Appium WebDriver实例

    返回：
    - bool: 是否成功切换回原生上下文

    通俗理解：从网页界面切换回App原生界面，之后的操作又变回操作App本身了
    """
    try:
        driver.switch_to.context("NATIVE_APP")
        logger.info("成功切换回原生上下文: NATIVE_APP")
        return True
    except Exception as e:
        logger.error(f"切换回原生上下文失败: {str(e)}")
        return False


def wait_for_webview(driver, timeout=10, package_name=None, interval=1):
    """
    等待WebView上下文出现

    参数说明：
    - driver: Appium WebDriver实例
    - timeout: 最大等待时间（秒），默认10秒
    - package_name: 应用包名（可选），用于精确匹配WebView上下文
    - interval: 轮询间隔（秒），默认1秒

    返回：
    - str: 成功时返回WebView上下文的名称，超时未找到返回None

    通俗理解：有时候网页加载比较慢，这个函数会一直等，直到网页出现或者超时。
    就像你等一个网页慢慢加载完成一样
    """
    start_time = time.time()
    logger.info(f"开始等待WebView上下文，超时时间: {timeout}秒")

    while time.time() - start_time < timeout:
        try:
            contexts = driver.contexts
            logger.debug(f"当前上下文: {contexts}")

            # 查找目标WebView
            target_context = None

            if package_name:
                webview_name = f"WEBVIEW_{package_name}"
                if webview_name in contexts:
                    target_context = webview_name
            else:
                for ctx in contexts:
                    if ctx.lower().startswith("webview"):
                        target_context = ctx
                        break

            if target_context:
                logger.info(f"WebView上下文已出现: {target_context}")
                return target_context

            # 等待一段时间再重试
            time.sleep(interval)

        except Exception as e:
            logger.warning(f"检查WebView上下文时出错: {str(e)}")
            time.sleep(interval)

    logger.warning(f"等待WebView上下文超时（{timeout}秒），未找到可用WebView")
    return None


def execute_js_in_webview(driver, script, *args):
    """
    在WebView中通过JavaScript操作页面

    参数说明：
    - driver: Appium WebDriver实例
    - script: 要执行的JavaScript代码字符串
    - args: 传递给JavaScript的参数（可选）

    返回：
    - any: JavaScript执行结果

    使用示例：
    # 获取页面标题
    title = execute_js_in_webview(driver, "return document.title")

    # 点击页面中的某个元素
    execute_js_in_webview(driver, "document.getElementById('submit-btn').click()")

    # 滚动到页面底部
    execute_js_in_webview(driver, "window.scrollTo(0, document.body.scrollHeight)")

    通俗理解：在网页里直接运行JavaScript代码，比如获取网页标题、点击按钮、
    滚动页面等。就像你在浏览器开发者工具的控制台里敲代码一样
    """
    try:
        # 确保当前在WebView上下文中
        current_context = driver.current_context
        if current_context == "NATIVE_APP":
            logger.warning("当前在原生上下文中，请先调用 switch_to_webview() 切换到WebView")

        result = driver.execute_script(script, *args)
        logger.info(f"执行JavaScript成功，脚本: {script[:80]}{'...' if len(script) > 80 else ''}")
        return result

    except Exception as e:
        logger.error(f"执行JavaScript失败: {str(e)}, 脚本: {script[:100]}")
        raise
