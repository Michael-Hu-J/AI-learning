# 第03节-推动初始化 — BaseDriver 的设计与实现

> 对应代码：配套代码 `base/base_driver.py`
>
> 说明：本节代码示例与配套代码中的 `BaseDriver` 类一一对应。

---

## 这节讲什么

Appium 测试的第一步是获取 driver。但 driver 不是 `webdriver.Remote()` 一句话那么简单。

Android 要配 UiAutomator2 引擎、APK 包名、Activity、权限授予。iOS 要配 XCUITest 引擎、Bundle ID、WDA 地址。配完一个 10-30 秒的启动时间跑不掉。

**100 个测试用例，每个都初始化一次 driver = 100 次初始化 = 半个小时耗在启动上。**

解决办法：用 session 级 fixture 在整个测试会话里只初始化一次 driver，所有用例复用。

配套代码的 `base_driver.py` 封装了这套逻辑。这节把它拆开讲清楚。

---

## BaseDriver 的核心设计

```python
class BaseDriver:
    def __init__(self, platform="android", appium_server_url="http://localhost:4723"):
        self.platform = platform.lower()
        self.appium_server_url = appium_server_url
        self.driver = None

    def get_driver(self):
        if self.driver:
            return self.driver  # 已初始化过，直接用

        if self.platform == "android":
            self.driver = self._init_android_driver()
        elif self.platform == "ios":
            self.driver = self._init_ios_driver()
        else:
            raise ValueError(f"不支持的平台: {self.platform}")

        return self.driver
```

**关键设计**：`if self.driver: return self.driver`

这就是个简单的单例模式。第一次调用 `get_driver()` 时初始化 driver，后面调用直接返回已有的实例。配合 pytest 的 session 级 fixture，整个测试会话只初始化一次。

---

## Android 推动初始化

```python
def _init_android_driver(self):
    android_version = os.getenv("ANDROID_PLATFORM_VERSION", "")
    if not android_version:
        # 自动检测 Android 版本
        import subprocess
        result = subprocess.run(
            ["adb", "shell", "getprop", "ro.build.version.release"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            android_version = result.stdout.strip()
        else:
            android_version = "11.0"  # 检测不到就用默认值

    # 检查 Appium Settings 是否已安装
    skip_install = self._check_appium_settings_installed()

    capabilities = {
        "platformName": "Android",
        "platformVersion": android_version,
        "deviceName": os.getenv("ANDROID_DEVICE_NAME", "Android Emulator"),
        "automationName": "UiAutomator2",
        "noReset": True,           # 不重置应用数据
        "fullReset": False,        # 不完全重置
        "autoGrantPermissions": True,  # 自动授权
        "newCommandTimeout": 300,
        "skipServerInstallation": skip_install,
        "uiautomator2ServerInstallTimeout": 60000,
        "uiautomator2ServerLaunchTimeout": 60000,
    }

    # 包名和 Activity
    app_package = os.getenv("APP_PACKAGE", "")
    app_activity = os.getenv("APP_ACTIVITY", "")
    if app_package:
        capabilities["appPackage"] = app_package
    if app_activity:
        capabilities["appActivity"] = app_activity

    options = UiAutomator2Options().load_capabilities(capabilities)
    driver = webdriver.Remote(self.appium_server_url, options=options)
    return driver
```

**参数说明**：

| 参数 | 作用 | 为什么这么设 |
|------|------|-------------|
| `noReset=True` | 不重置应用数据 | 避免每次测试都重新登录 |
| `autoGrantPermissions=True` | 自动授权弹窗 | 不授权的话测试会被弹窗卡住 |
| `skipServerInstallation` | 跳过 UiAutomator2 安装 | 装过了就别再装了，省时间 |
| `uiautomator2ServerInstallTimeout=60000` | 安装超时 60 秒 | 默认 20 秒不够，慢的设备会超时 |

---

## iOS 推动初始化（Tidevice 模式）

```python
def _init_ios_driver_with_tidevice(self):
    bundle_id = os.getenv("BUNDLE_ID", "")
    udid = os.getenv("IOS_UDID", "")
    tidevice_port = int(os.getenv("TIDEVICE_PORT", "8100"))

    wda_url = f"http://127.0.0.1:{tidevice_port}"

    capabilities = {
        "platformName": "iOS",
        "platformVersion": os.getenv("IOS_PLATFORM_VERSION", "15.0"),
        "deviceName": os.getenv("IOS_DEVICE_NAME", "iPhone 13"),
        "automationName": "XCUITest",
        "noReset": True,
        "fullReset": False,
        "newCommandTimeout": 300,
        "webDriverAgentUrl": wda_url,       # 关键：连 Tidevice 代理
        "useNewWDA": False,                  # 不要重新装 WDA
        "shouldUseSingletonTestManager": False,
        "skipServerInstallation": True,
    }

    if udid:
        capabilities["udid"] = udid
    if bundle_id:
        capabilities["bundleId"] = bundle_id

    options = XCUITestOptions().load_capabilities(capabilities)
    driver = webdriver.Remote(self.appium_server_url, options=options)
    return driver
```

**关键点**：`webDriverAgentUrl` 指向 Tidevice 的 wdaproxy 地址。这样 Appium Server 就不需要自己管理 WDA 了，直接用 Tidevice 提供好的代理。省掉了 Xcode 编译 WDA 的麻烦。

---

## Appium Settings 安装检测

```python
def _check_appium_settings_installed(self) -> bool:
    """检查设备上是否已安装 Appium Settings，已装则跳过安装"""
    result = subprocess.run(
        ["adb", "shell", "pm", "list", "packages", "io.appium.settings"],
        capture_output=True, text=True, timeout=5
    )
    if result.returncode == 0 and "io.appium.settings" in result.stdout:
        return True
    return False
```

这个小优化能省 10-20 秒。每次初始化都重新装一遍 Appium Settings 太浪费时间了，装过就不装了。

---

## 和 conftest.py 配合

配套代码的 `conftest.py` 里这样用：

```python
@pytest.fixture(scope="session")
def driver_setup(request):
    """会话级 fixture，整个测试只初始化一次 driver"""
    platform = os.getenv("PLATFORM", "android")
    base_driver = BaseDriver(platform=platform)
    driver = base_driver.get_driver()

    def driver_teardown():
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"推动关闭异常: {str(e)}")

    request.addfinalizer(driver_teardown)
    yield driver

`scope="session"` 是关键。不加的话默认是 function 级别，每个测试函数重新初始化一次 driver，100 个测试就是 100 次初始化的时间。

---

## 踩过的坑

### 1. 每次初始化都重新装 UiAutomator2
第一次跑测试花了 30 秒初始化，以为正常。跑了 10 个用例后才发现每次都在重新装 Server。加 `skipServerInstallation` 检测后，每次省 15 秒。

### 2. Android 版本号写死
一开始 `platformVersion` 写死了 `"11.0"`。换了个 Android 14 的设备跑，Capabilities 里的版本跟实际不匹配，部分操作异常。改成自动检测后解决。

### 3. iOS 用 Tidevice 时忘了先启动 wdaproxy
症状：driver 初始化超时。
原因：`webDriverAgentUrl` 配置了，但 `tidevice wdaproxy` 没跑。跟 Appium Server 没启动是一个道理。

### 4. `noReset=False` 导致每次重新登录
默认 `noReset=True`，但有人为了"干净环境"改成 `False`。结果每次测试前都要重新装 App、重新登录，一个用例跑 2 分钟。还是 `noReset=True` 快。
