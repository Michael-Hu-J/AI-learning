# 第11节-Toast+弹窗处理 — 移动端最让人头疼的几种弹窗

> 对应代码：配套代码 `utils/toast_helper.py`
>
> 说明：本节代码示例与配套代码中的 `toast_helper.py` 完全对应。

---

## 这节讲什么

移动端测试最烦人的事之一，就是那些**不知道什么时候会冒出来的东西**。

你正在执行一个点击操作，突然屏幕上弹出一个「是否允许获取位置信息」的权限请求，测试脚本直接卡死——因为脚本以为下一步是登录页面，结果出来的是系统弹窗。

还有 Toast——那些一闪而过的小提示。登录成功后显示「登录成功」，操作失败后显示「网络连接失败」。出现几秒就消失，你还没来得及定位元素它就没了。

Toast 和弹窗处理是移动端自动化的必修课。这节讲清楚：

1. **Toast 是什么**——短暂提示、不可交互、几秒自动消失
2. **如何捕获 Toast 文本**——XPath 方式、UiAutomator2 方式
3. **系统权限弹窗怎么处理**——定位/通知/相机权限，中英文按钮
4. **通用弹窗策略**——版本更新弹窗、广告弹窗、活动弹窗
5. **实际项目中的踩坑经验**

---

## 1. Toast 是什么

**Toast** 是 Android 系统提供的一种轻量级消息提示。它的特点是：

- **短暂**：默认 2-3 秒自动消失
- **不可交互**：你不能点击它，只能看
- **不打断操作**：它不会阻塞用户交互（跟弹窗不一样）

```python
# 典型的 Toast 场景
# 点击"登录"按钮后，页面上出现"登录成功"四个字，2 秒后消失
# 这不是一个可以点击的元素 — 它就是给你看一眼
```

**Toast 和 Alert 弹窗的区别**：

| 特性 | Toast | Alert 弹窗 |
|------|-------|-----------|
| 持续时间 | 2-3 秒自动消失 | 必须用户操作才消失 |
| 交互性 | 不可点击 | 可点击按钮 |
| 打断性 | 不打断操作 | 阻塞当前操作 |
| 捕获难度 | 难（一闪而过） | 容易（一直在那） |

测试中，Toast 主要用来**做断言**——验证操作是否成功。登录完成后，等 Toast 出现，检查文本是不是「登录成功」。

---

## 2. Android Toast 捕获

Appium 捕获 Toast 有两种主流方式。

### 方式一：XPath 定位

这是最直接的方式。Android 的 Toast 控件 class 是 `android.widget.Toast`，直接用 XPath 找：

```python
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Toast 默认 XPath
DEFAULT_TOAST_XPATH = "//*[@class='android.widget.Toast']"

def get_toast_text(driver, timeout=5):
    """获取当前页面上的 Toast 文本"""
    try:
        wait = WebDriverWait(driver, timeout)
        toast_element = wait.until(
            EC.presence_of_element_located(
                (AppiumBy.XPATH, DEFAULT_TOAST_XPATH)
            )
        )
        return toast_element.text
    except:
        return None
```

**XPath 方式的要求**：Appium 2.0 配合 UiAutomator2 推动原生支持 Toast 定位。Appium 1.x 可能需要额外配置。

### 方式二：UiAutomator2 方式

如果 XPath 方式获取不到，可以换 UiAutomator2 的方式：

```python
def get_toast_text_uiautomator(driver, timeout=5):
    """通过 UiAutomator2 查找 Toast"""
    try:
        # 查找文本中包含特征的 Toast 元素
        xpath = "//*[contains(@text, '') and @class='android.widget.Toast']"
        toast_element = driver.find_element(AppiumBy.XPATH, xpath)
        return toast_element.text
    except:
        return None
```

### 方式三：兜底策略

个别 App 的 Toast 使用自定义 View，不走标准的 `android.widget.Toast`。这种情况下需要用启发式方法：

```python
def get_toast_text_fallback(driver, timeout=5):
    """自定义 View 实现的 Toast 兜底查找"""
    try:
        # 找所有不可点击、不可滚动的短文本元素
        xpath = "//*[contains(@text, '') and (@clickable='false' or @long-clickable='false')]"
        candidates = driver.find_elements(AppiumBy.XPATH, xpath)
        for elem in candidates:
            text = elem.text
            if text and len(text) < 100:  # Toast 一般比较短
                # 排除普通界面元素
                is_toast = True
                for attr in ["clickable", "focusable", "scrollable"]:
                    if elem.get_attribute(attr) == "true":
                        is_toast = False
                        break
                if is_toast:
                    return text
        return None
    except:
        return None
```

配套代码的 `get_toast_text` 函数，内部按 **XPath → UiAutomator2 → 自定义兜底** 三级降级策略依次尝试，保证尽可能捕获到 Toast。

---

## 3. wait_for_toast 的使用

很多时候咱们不只是获取 Toast 文本，而是**等一个特定内容的 Toast 出现**。

比如：点击「登录」按钮后，等「登录成功」的 Toast 弹出来，来验证登录成功。

```python
def wait_for_toast(driver, text=None, timeout=5):
    """
    等待特定内容的 Toast 出现

    参数：
    - text: 期望的 Toast 文本（部分匹配），为 None 则等待任意 Toast
    - timeout: 最大等待时间（秒）

    返回：
    - True: 找到了期望的 Toast
    - False: 超时未找到
    """
    xpath = "//*[@class='android.widget.Toast']"

    if text:
        # 指定了文本就用精确 XPath
        xpath = f"//*[@class='android.widget.Toast' and contains(@text, '{text}')]"

    try:
        wait = WebDriverWait(driver, timeout)
        toast_element = wait.until(
            EC.presence_of_element_located((AppiumBy.XPATH, xpath))
        )
        toast_text = toast_element.text or "（无文本）"
        print(f"找到期望的 Toast: {toast_text}")
        return True
    except:
        return False
```

**实战用法**：

```python
# 点击登录
login_page.login("admin", "admin123")

# 等 Toast 出现
if wait_for_toast(driver, text="登录成功", timeout=5):
    print("登录成功 — Toast 验证通过")
else:
    print("登录可能失败 — 未看到登录成功的 Toast")

注意 timeout 的设置。Toast 只显示 2-3 秒，所以 timeout 设 5 秒就够了。设太长是浪费——Toast 2 秒就消失了，你等 20 秒也没用。

---

## 4. 系统权限弹窗

这是移动端测试最烦人的弹窗，没有之一。

Android 6.0（API 23）之后引入了运行时权限机制。App 在用到定位、相机、通讯录、存储等功能时，必须弹窗让用户授权。**不同 App 用到的权限不同，弹窗出现的时机也不同**。

常见的系统权限弹窗：

| 弹窗类型 | 触发场景 | 典型按钮 |
|---------|---------|---------|
| 定位权限 | App 首次打开 | 「允许」/「拒绝」/「仅在使用中允许」 |
| 相机权限 | 打开扫码/拍照 | 「允许」/「拒绝」 |
| 存储权限 | 读写文件 | 「允许」/「拒绝」 |
| 通知权限 | Android 13+ | 「允许」/「不允许」 |
| 通讯录权限 | 读取联系人 | 「允许」/「拒绝」 |

**中英文按钮处理**：测试 App 可能在不同语言环境下运行。按钮文本可能是「允许」，也可能是「Allow」。

```python
# 系统权限按钮文本配置
SYSTEM_ALERT_BUTTONS = {
    "accept": [
        "允许", "同意", "allow", "permit",
        "while using the app", "仅在使用中允许"
    ],
    "deny": [
        "拒绝", "deny", "禁止"
    ],
}
```python

处理代码在 `handle_system_alert` 中实现，支持三种策略。

---

## 5. handle_system_alert 三种策略

配套代码的 `handle_system_alert` 函数内部按优先级依次尝试三种方法。

### 策略 1：Appium 内置 Alert 处理（最快）

```python
def handle_system_alert_strategy1(driver, action="accept", timeout=5):
    """策略1：使用 Appium 内置的 switch_to.alert"""
    try:
        alert = WebDriverWait(driver, timeout / 2).until(
            lambda d: d.switch_to.alert
        )
        alert_text = alert.text
        if action == "accept":
            alert.accept()
        else:
            alert.dismiss()
        return True
    except:
        return False
```python

这是最快的方式，但**只适用于系统原生的 AlertDialog**。很多国产 ROM（MIUI、EMUI、ColorOS）的自定义权限弹窗不走标准 Alert，用这个方法会失效。

### 策略 2：XPath 定位按钮（最通用）

```python
def handle_system_alert_strategy2(driver, action="accept", timeout=5):
    """策略2：通过 XPath 查找权限弹窗按钮"""
    button_texts = SYSTEM_ALERT_BUTTONS["accept"] if action == "accept" else SYSTEM_ALERT_BUTTONS["deny"]

    time.sleep(1)  # 等弹窗渲染

    for btn_text in button_texts:
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
                return True
            except:
                continue
    return False
```python

这是**最通用的方法**，不管什么 ROM 的弹窗，只要有按钮文本就能点。缺点是轮询多个文本和 XPath 组合，稍微慢一点。

### 策略 3：WebView 上下文处理（混合应用）

有的混合 App，权限弹窗在 WebView 层弹出来，原生上下文里找不到。需要切上下文：

```python
def handle_system_alert_strategy3(driver):
    """策略3：切换到 WebView 上下文处理弹窗"""
    contexts = driver.contexts
    if len(contexts) > 1:
        for ctx in contexts:
            if "NATIVE" not in ctx:
                driver.switch_to.context(ctx)
                try:
                    accept_btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable(
                            ("xpath", "//button[contains(text(), '允许') or contains(text(), 'Allow')]")
                        )
                    )
                    accept_btn.click()
                    return True
                except:
                    pass
                finally:
                    driver.switch_to.context(contexts[0])  # 切回原生
    return False
```python

### 三种策略的完整流程

配套代码的 `handle_system_alert` 内部顺序执行：**策略1 → 策略2 → 策略3**。前面的成功了就直接返回，失败了才进入下一个。

```python
def handle_system_alert(driver, action="accept", timeout=5):
    """处理系统权限弹窗（三种策略依次尝试）"""
    # 策略1：switch_to.alert
    if handle_system_alert_strategy1(driver, action, timeout):
        return True
    # 策略2：XPath 定位按钮
    if handle_system_alert_strategy2(driver, action, timeout):
        return True
    # 策略3：WebView 上下文
    if handle_system_alert_strategy3(driver):
        return True
    return False  # 三种策略都没搞定
```python

**注意**：`autoGrantPermissions=True` 是在 Capabilities 里设置的，能在推动初始化时自动授权一部分权限。但它管不了所有弹窗——某些 ROM 的自定义弹窗它处理不了，还是得用 `handle_system_alert` 兜底。

---

## 6. 通用弹窗处理

除了系统权限弹窗，App 内部还有各种业务弹窗：

- **版本更新弹窗**：「发现新版本，是否更新？」
- **广告弹窗**：开屏广告、插屏广告
- **活动弹窗**：「恭喜获得优惠券」「签到有礼」
- **网络错误弹窗**：「网络连接失败，是否重试？」
- **确认退出弹窗**：「确定退出应用吗？」

这些弹窗的特点是**出现时机不确定、按钮文本五花八门**。

配套代码的 `handle_alert` 函数封装了通用处理逻辑：

```python
def handle_alert(driver, action="accept", timeout=5):
    """
    处理通用弹窗

    参数 action 支持：
    - "accept": 点击确定/确认/是/OK/好
    - "dismiss": 点击取消/否/关闭
    - "accept_all": 有确定就点确定，没有就点取消
    - "我知道了": 自定义按钮文本，直接点击该文本的按钮
    """

内部同样按优先级尝试三种方式：

1. **switch_to.alert** — 最快，但只对原生 AlertDialog 有效
2. **XPath 定位按钮** — 匹配文本库（确定/确认/是/OK/好/允许/同意/知道了/继续...），逐个尝试
3. **坐标点击** — 实在找不到按钮时，估算弹窗确认按钮的位置（屏幕中间偏下），直接 tap

```python
# 坐标兜底：弹窗"确定"按钮通常在屏幕 65% 高度处
size = driver.get_window_size()
click_x = size['width'] // 2
click_y = int(size['height'] * 0.65)
driver.tap([(click_x, click_y)], 100)
```

**什么时候用 handle_alert**：在 `conftest.py` 的 fixture 里统一调用，或者每个操作步骤之后调用。比如：

```python
def safe_click(driver, locator):
    """安全点击：先处理弹窗，再点击目标元素"""
    handle_alert(driver, action="dismiss")  # 先关掉可能弹出来的广告
    handle_system_alert(driver, action="accept")  # 处理系统权限
    # 再进行真正的点击
    driver.find_element(*locator).click()
```

---

## 7. 在 conftest.py 中统一集成

最好的做法不是在每个测试里单独处理弹窗，而是在 fixture 层统一处理。配套代码的做法：

```python
@pytest.fixture(autouse=True)
def handle_popups(driver):
    """每个测试用例执行前自动处理弹窗"""
    yield
    # 用例执行完后，尝试关闭残留弹窗
    try:
        handle_system_alert(driver, action="accept", timeout=2)
        handle_alert(driver, action="dismiss", timeout=2)
    except:
        pass

用 `autouse=True` 自动在每个用例前后执行。这样测试代码里不用写任何弹窗处理逻辑，干净很多。

---

## 踩过的坑

### 1. 不同 Android 版本 Toast 机制不一样

Android 12+ 对 Toast 做了限制。后台 App 不能弹 Toast，部分自定义 Toast 可能被系统拦截。在 Android 12 上能正常捕获的 XPath，到 Android 14 上可能就找不到元素了。

**解决办法**：测试脚本的 Toast 捕获逻辑要兼容多个版本。配套代码的 `get_toast_text` 用三级降级策略就是为了应对这种情况——一个版本走不通，换另一个方式走。

### 2. 模拟器 vs 真机弹窗不一样

模拟器上的系统权限弹窗跟真机**完全不同**。

小米/华为/OPPO/Vivo 各自魔改了系统弹窗的界面。同一个「定位权限弹窗」，在模拟器上是标准的 Android 原生弹窗，在小米手机上变成了 MIUI 自定义弹窗（按钮文本也不一样），在华为手机上又是 EMUI 风格。

**典型表现**：
- 模拟器上测试通过了，发到真机上权限弹窗没处理，测试全挂
- 小米手机上能处理的脚本，换到三星手机上又报错

**解决方案**：
- 至少准备 2-3 台主流品牌真机做兼容验证
- `SYSTEM_ALERT_BUTTONS` 列表尽可能覆盖常见 ROM 的按钮文本
- `autoGrantPermissions=True` 在部分真机上无效，不能依赖它

### 3. Toast 出现时间太短，等不到

Toast 默认只显示 2 秒。如果用 `time.sleep(3)` 等 Toast 出现，大概率等到 2.5 秒时 Toast 已经消失了。

**正确做法**：用显式等待（`WebDriverWait`），不要用 `time.sleep`。

```python
#  错误
time.sleep(3)
toast = driver.find_element(By.XPATH, "//*[@class='android.widget.Toast']")

#  正确
toast = WebDriverWait(driver, 5).until(
    EC.presence_of_element_located((AppiumBy.XPATH, "//*[@class='android.widget.Toast']"))
)

### 4. 弹窗处理写太多，测试比生产代码还复杂

有些人每个操作步骤前都写一长串弹窗处理代码。一个步骤 20 行，其中 15 行是在处理弹窗。

**解决办法**：把弹窗处理抽成公共方法，在 fixture 层统一调用。配套代码的做法是在 `conftest.py` 里用 `autouse` fixture 统一处理，测试代码里不用写任何弹窗逻辑。

### 5. 国产 ROM 的「仅在使用中允许」

Android 11+ 引入了「仅在使用中允许」这个选项。它不是标准的「允许」或「拒绝」，按钮文本也不一样。如果脚本只处理「允许」和「拒绝」，「仅在使用中允许」就没法自动点击。

**解决办法**：在 `SYSTEM_ALERT_BUTTONS["accept"]` 列表中加上 `"while using the app"` 和 `"仅在使用中允许"`。

### 6. Toast 捕获不到的终极原因

如果所有方式都捕获不到 Toast，可能是这几个原因：

- **App 用的不是系统 Toast**——用的是第三方库（如 Snackbar、自定义 Popup）
- **Toast 在另一个 App 的界面上**——某些 App 的 Toast 实际上是跨进程显示的
- **UiAutomator2 版本问题**——某些旧版本 UiAutomator2 不支持 Toast 定位

**终极方案**：如果 Toast 实在捕获不到，就别死磕 Toast 了。改用其他方式验证操作结果——比如检查页面上某个元素是否出现/消失，或者抓接口响应。

---

## 要点回顾

| 问题 | 解决方案 | 对应函数 |
|------|---------|---------|
| 捕获 Toast 文本 | XPath + UiAutomator2 + 自定义兜底 | `get_toast_text` |
| 等待特定 Toast | 带文本匹配的显式等待 | `wait_for_toast` |
| 系统权限弹窗 | switch_to.alert → XPath → WebView 上下文 | `handle_system_alert` |
| 通用业务弹窗 | switch_to.alert → XPath 文本库 → 坐标点击 | `handle_alert` |
| 统一集成 | conftest.py autouse fixture | 配合 BasePage 使用 |

Toast 和弹窗处理是移动端自动化的基本功。做好了，测试脚本稳定跑几百次；做不好，每次 CI 都有几个用例因为弹窗挂掉。配套代码的 `toast_helper.py` 把这套逻辑都封装好了，直接引用就行。
