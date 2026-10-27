# base_driver.py - 驱动管理基类
"""
驱动管理类
功能：管理Android和iOS的Appium驱动初始化
通俗理解：就像是一个"司机"，负责启动和管理自动化测试的"车"（移动设备）
"""
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions
import os
from utils.logger import Logger

logger = Logger().get_logger()


class BaseDriver:
    """
    驱动管理基类
    
    作用：
    1. 初始化Android或iOS的Appium驱动
    2. 配置连接参数（设备信息、App信息等）
    3. 返回可用的驱动实例供后续操作使用
    """
    
    def __init__(self, platform="android", appium_server_url="http://localhost:4723"):
        """
        初始化驱动管理器
        
        参数说明：
        - platform: 平台类型，"android" 或 "ios"
        - appium_server_url: Appium服务器地址，默认本地4723端口
        """
        self.platform = platform.lower()
        self.appium_server_url = appium_server_url
        self.driver = None
        logger.info(f"初始化驱动管理器 - 平台: {self.platform}")
    
    def get_driver(self):
        """
        获取驱动实例
        
        返回：
        - driver: Appium WebDriver实例，用于后续所有操作
        
        通俗理解：这个方法会启动"车"，给你一个"方向盘"（driver），
        有了这个"方向盘"你就可以控制手机进行各种操作了
        """
        if self.driver:
            return self.driver
        
        if self.platform == "android":
            self.driver = self._init_android_driver()
        elif self.platform == "ios":
            self.driver = self._init_ios_driver()
        else:
            raise ValueError(f"不支持的平台类型: {self.platform}，请使用 'android' 或 'ios'")
        
        logger.info("驱动初始化成功")
        return self.driver
    
    def _init_android_driver(self):
        """
        初始化Android驱动
        
        通俗理解：配置Android手机连接信息，就像给Android手机配钥匙
        """
        # 自动检测Android版本（如果环境变量未设置）
        android_version = os.getenv("ANDROID_PLATFORM_VERSION", "")
        if not android_version:
            try:
                import subprocess
                result = subprocess.run(
                    ["adb", "shell", "getprop", "ro.build.version.release"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    android_version = result.stdout.strip()
                    logger.info(f"自动检测到Android版本: {android_version}")
            except Exception as e:
                logger.warning(f"自动检测Android版本失败: {e}，使用默认值")
                android_version = "11.0"
        
        # 检查Appium Settings是否已安装
        skip_server_installation = self._check_appium_settings_installed()

        # 真机 Chrome 打开网页（配合 demo_app / Mock，用于 driver.get 类用例）
        # 设置 ANDROID_BROWSER=chrome 时走浏览器会话，避免与原生 App 的 APP_PACKAGE 冲突
        android_browser = os.getenv("ANDROID_BROWSER", "").strip().lower()
        use_android_chrome = android_browser in ("chrome", "chromium", "browser")

        # 从环境变量读取Android设备信息
        capabilities = {
            "platformName": "Android",
            "platformVersion": android_version,
            "deviceName": os.getenv("ANDROID_DEVICE_NAME", "Android Emulator"),
            "automationName": "UiAutomator2",  # Android自动化引擎
            "noReset": True,  # 不重置应用数据
            "fullReset": False,  # 不完全重置
            "unicodeKeyboard": False,  # 不使用Unicode键盘（避免影响正常输入法）
            "resetKeyboard": False,  # 不重置键盘（避免改变系统输入法设置）
            "autoGrantPermissions": True,  # 自动授予权限
            "newCommandTimeout": 300,  # 命令超时时间（秒）
            "uiautomator2ServerInstallTimeout": 60000,  # UiAutomator2服务器安装超时时间（毫秒，默认20000，增加到60000）
            "uiautomator2ServerLaunchTimeout": 60000,  # UiAutomator2服务器启动超时时间（毫秒）
            "skipServerInstallation": skip_server_installation,  # 如果Appium Settings已安装，跳过服务器安装
            "skipUnlock": True,  # 跳过解锁屏幕
            "skipLogcatCapture": False,  # 是否跳过日志捕获
            "settingsAppWaitTimeout": 30000,  # Settings应用等待超时时间（毫秒，默认5000，增加到30000）
        }

        android_udid = os.getenv("ANDROID_UDID", "").strip()
        if android_udid:
            capabilities["udid"] = android_udid
            logger.info(f"使用指定设备 UDID: {android_udid}")

        if use_android_chrome:
            capabilities["browserName"] = "Chrome"
            logger.info(
                "已启用 Android Chrome 会话（ANDROID_BROWSER=%s），"
                "请在手机上能访问的地址设置 MOCK_SERVER_URL（建议电脑局域网 IP:端口）",
                android_browser,
            )
        else:
            # 如果指定了应用包名和Activity，则添加
            app_package = os.getenv("APP_PACKAGE", "")
            app_activity = os.getenv("APP_ACTIVITY", "")
            if app_package:
                capabilities["appPackage"] = app_package
            if app_activity:
                capabilities["appActivity"] = app_activity

            # 如果指定了APK路径，则使用 installApp 方式
            apk_path = os.getenv("APK_PATH", "")
            if apk_path and os.path.exists(apk_path):
                capabilities["app"] = apk_path
                logger.info(f"使用APK安装: {apk_path}")

        options = UiAutomator2Options().load_capabilities(capabilities)
        logger.info(f"Android驱动配置: {capabilities}")
        if skip_server_installation:
            logger.info(" 检测到Appium Settings已安装，将跳过服务器安装步骤")
        
        driver = webdriver.Remote(self.appium_server_url, options=options)
        return driver
    
    def _check_appium_settings_installed(self) -> bool:
        """
        检查Appium Settings是否已安装在设备上
        
        返回：
        - bool: True表示已安装，可以跳过安装；False表示未安装，需要安装
        """
        try:
            import subprocess
            
            # Appium Settings的包名
            appium_settings_package = "io.appium.settings"
            
            # 检查设备上是否已安装Appium Settings
            result = subprocess.run(
                ["adb", "shell", "pm", "list", "packages", appium_settings_package],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and appium_settings_package in result.stdout:
                logger.info(f" 检测到Appium Settings已安装 ({appium_settings_package})")
                
                # 同时检查UiAutomator2 Server是否已安装
                uiautomator2_package = "io.appium.uiautomator2.server"
                result2 = subprocess.run(
                    ["adb", "shell", "pm", "list", "packages", uiautomator2_package],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result2.returncode == 0 and uiautomator2_package in result2.stdout:
                    logger.info(f" 检测到UiAutomator2 Server已安装 ({uiautomator2_package})")
                    logger.info("   将跳过服务器安装步骤，加快测试启动速度")
                    return True
                else:
                    logger.info(f"  UiAutomator2 Server未安装，仍需要安装")
                    return False
            else:
                logger.info(f"  Appium Settings未安装，将自动安装")
                return False
                
        except Exception as e:
            logger.warning(f"检查Appium Settings安装状态失败: {str(e)}")
            logger.info("   将尝试安装Appium Settings")
            return False
    
    def _init_ios_driver(self):
        """
        初始化iOS驱动
        
        支持两种方式：
        1. 使用Tidevice（推荐，不需要Xcode）：设置USE_TIDEVICE=true
        2. 使用传统WebDriverAgent（需要Xcode）：默认方式
        """
        # 检查是否使用Tidevice
        use_tidevice = os.getenv("USE_TIDEVICE", "false").lower() == "true"
        
        if use_tidevice:
            return self._init_ios_driver_with_tidevice()
        else:
            return self._init_ios_driver_with_wda()
    
    def _init_ios_driver_with_tidevice(self):
        """
        使用Tidevice初始化iOS驱动（不需要Xcode）
        
        Tidevice通过wdaproxy提供WebDriverAgent的代理服务
        """
        bundle_id = os.getenv("BUNDLE_ID", "")
        udid = os.getenv("IOS_UDID", "")
        tidevice_port = int(os.getenv("TIDEVICE_PORT", "8100"))
        
        # Tidevice的WebDriverAgent代理地址
        wda_url = f"http://127.0.0.1:{tidevice_port}"
        
        logger.info("=" * 50)
        logger.info("使用Tidevice模式（不需要Xcode）")
        logger.info(f"Tidevice wdaproxy地址: {wda_url}")
        logger.info("请确认已运行: tidevice wdaproxy -B <bundle_id> --port <port>")
        logger.info("=" * 50)
        
        capabilities = {
            "platformName": "iOS",
            "platformVersion": os.getenv("IOS_PLATFORM_VERSION", "15.0"),
            "deviceName": os.getenv("IOS_DEVICE_NAME", "iPhone 13"),
            "automationName": "XCUITest",
            "noReset": True,
            "fullReset": False,
            "newCommandTimeout": 300,
            # 关键：指定WebDriverAgent URL为Tidevice代理地址
            "webDriverAgentUrl": wda_url,
            # 避免每次重新安装WDA
            "useNewWDA": False,
            # 跳过WDA启动（因为Tidevice已经管理WDA）
            "shouldUseSingletonTestManager": False,
            # 跳过设备检测（避免SDK检查）
            "skipServerInstallation": True,
        }
        
        # 如果指定了UDID，则添加
        if udid:
            capabilities["udid"] = udid
            logger.info(f"使用指定设备UDID: {udid}")
        
        # 如果指定了Bundle ID，则添加（使用Tidevice时，可以不指定bundleId让Appium连接已打开的应用）
        if bundle_id:
            # 注意：使用Tidevice时，如果指定bundleId，Appium会尝试启动该应用
            # 如果应用未安装或Bundle ID错误，会报错
            # 如果不指定bundleId，Appium会连接到当前已打开的应用
            capabilities["bundleId"] = bundle_id
            logger.info(f"使用Bundle ID: {bundle_id}")
        else:
            logger.info("未指定Bundle ID，将连接当前已打开的应用（请先手动打开要测试的应用）")
        
        # 如果指定了IPA路径，则使用安装方式
        ipa_path = os.getenv("IPA_PATH", "")
        if ipa_path and os.path.exists(ipa_path):
            capabilities["app"] = ipa_path
            logger.info(f"使用IPA安装: {ipa_path}")
        
        options = XCUITestOptions().load_capabilities(capabilities)
        logger.info(f"iOS驱动配置（Tidevice模式）: {capabilities}")
        
        # 注意：使用Tidevice时，仍然需要Appium服务器
        # Appium服务器会通过webDriverAgentUrl连接到Tidevice的wdaproxy
        driver = webdriver.Remote(self.appium_server_url, options=options)
        return driver
    
    def _init_ios_driver_with_wda(self):
        """
        使用传统WebDriverAgent初始化iOS驱动（需要Xcode）
        """
        bundle_id = os.getenv("BUNDLE_ID", "")
        udid = os.getenv("IOS_UDID", "")
        
        logger.info("使用传统WebDriverAgent模式（需要Xcode）")
        
        capabilities = {
            "platformName": "iOS",
            "platformVersion": os.getenv("IOS_PLATFORM_VERSION", "15.0"),
            "deviceName": os.getenv("IOS_DEVICE_NAME", "iPhone 13"),
            "automationName": "XCUITest",  # iOS自动化引擎
            "noReset": True,  # 不重置应用数据
            "fullReset": False,  # 不完全重置
            "newCommandTimeout": 300,  # 命令超时时间（秒）
            "wdaLaunchTimeout": 60000,  # WebDriverAgent启动超时
        }
        
        # 如果指定了UDID，则添加（用于连接特定设备）
        if udid:
            capabilities["udid"] = udid
            logger.info(f"使用指定设备UDID: {udid}")
        
        # Xcode相关配置（可选）
        xcode_org_id = os.getenv("XCODE_ORG_ID", "")
        if xcode_org_id:
            capabilities["xcodeOrgId"] = xcode_org_id
        capabilities["xcodeSigningId"] = os.getenv("XCODE_SIGNING_ID", "iPhone Developer")
        
        # 如果指定了Bundle ID，则添加
        if bundle_id:
            capabilities["bundleId"] = bundle_id
        
        # 如果指定了IPA路径，则使用安装方式
        ipa_path = os.getenv("IPA_PATH", "")
        if ipa_path and os.path.exists(ipa_path):
            capabilities["app"] = ipa_path
            logger.info(f"使用IPA安装: {ipa_path}")
        
        options = XCUITestOptions().load_capabilities(capabilities)
        logger.info(f"iOS驱动配置（传统模式）: {capabilities}")
        
        driver = webdriver.Remote(self.appium_server_url, options=options)
        return driver
    
    def quit(self):
        """
        关闭驱动
        
        通俗理解：测试结束后，"停车熄火"，关闭连接
        """
        if self.driver:
            try:
                self.driver.quit()
                logger.info("驱动已关闭")
            except Exception as e:
                logger.error(f"关闭驱动时出错: {str(e)}")
            finally:
                self.driver = None

