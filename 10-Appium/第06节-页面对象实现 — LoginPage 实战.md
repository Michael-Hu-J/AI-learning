# 第06节-页面对象实现 — LoginPage 实战

> 对应代码：原项目 `pages/login_page.py`（143行）
>
> 说明：本节所有代码示例均来自一个真实的移动端自动化测试项目，业务名称和API路径已做模糊化处理。

---

上一节把 BasePage 基类搭好了，里面封装了 `click()`、`input_text()`、`find_element()` 这些通用操作。现在轮到具体页面了——拿登录页面开刀。

LoginPage 的全部代码就 143 行。我拆成几块聊：元素定位常量、业务操作方法、验证方法、文本获取。另外实际项目里还有日志集成，这块很多教程不提，但线上跑脚本没日志你根本不知道哪崩的。

### 先看继承关系

```python
from base.base_page import BasePage
from utils.logger import Logger

logger = Logger().get_logger()

class LoginPage(BasePage):
    def __init__(self, driver):
        super().__init__(driver)
        logger.info("初始化登录页面")
```

继承 BasePage，`super().__init__(driver)` 把 driver 传上去，顺带把 BasePage 里的 `self.wait`（`WebDriverWait(driver, 10)`）、`self.screenshot_helper` 都初始化好。`logger` 是类级别的，整个 LoginPage 共享一个日志实例。

### 元素定位常量为什么用元组

翻到 `base_page.py` 第 86 行，`find_element` 的签名是：

```python
def find_element(self, locator_type: str, locator_value: str, timeout: int = 10):

两个参数：定位方式 + 定位值。`click()` 和 `input_text()` 也是类似的签名。所以 LoginPage 里把定位信息存成元组，用 `*` 解包传参：

```python
# login_page.py 第 18-23 行
LOGIN_TITLE = ("accessibility_id", "login_title")
PHONE_EMAIL_INPUT = ("accessibility_id", "phone_email_input")
PASSWORD_INPUT = ("acce...id", "password_input")  # 实际取值需要替换
LOGIN_BUTTON = ("accessibility_id", "login_button")
FORGOT_PASSWORD_LINK = ("acce...id", "forgot_password_link")
REGISTER_LINK = ("accessibility_id", "register_link")

调用时：

```python
self.click(*self.LOGIN_BUTTON)
# 等价于 self.click("accessibility_id", "login_button")

注意 `PASSWORD_INPUT` 和 `FORGOT_PASSWORD_LINK` 的定位值写的是 `"acce...id"`——这是故意的还是失误？看注释就知道，这些 accessibility_id 是占位符，实际必须用 Appium Inspector 抓真实值替换。忘掉这一步直接跑，你会看到这种报错：

```
selenium.common.exceptions.NoSuchElementException: Message: An element could not be located on the page using the given search parameters.

或者更具体一点的：

```python
selenium.common.exceptions.TimeoutException: Message: Expected condition failed: waiting for presence of element located by: ByAccessibilityId: acce...id (tried for 10 second(s) with 500 milliseconds interval)
```

定位值写 `"acce...id"` 这种假的字符串，`find_element` 等 10 秒超时后抛 `TimeoutException`，测试直接红。所以项目里注释也写了：**需要用 Appium Inspector 获取真实 ID**。

### 业务操作方法——组合 BasePage 的基础操作

`base_page.py` 的 `input_text()`（第 209 行）和 `click()`（第 168 行）已经处理了找元素、等待、点击、异常截图这些脏活。LoginPage 要做的就是传正确的定位常量：

```python
def input_phone_email(self, value: str):
    logger.info(f"输入手机号/邮箱: {value}")
    self.input_text(*self.PHONE_EMAIL_INPUT, value)
    time.sleep(0.5)

def input_password(self, value: str):
    logger.info(f"输入密码: {value}")
    self.input_text(*self.PASSWORD_INPUT, value)
    time.sleep(0.5)

def click_login_button(self):
    logger.info("点击登录按钮")
    self.click(*self.LOGIN_BUTTON)
    time.sleep(2)

def click_forgot_password_link(self):
    logger.info("点击忘记密码链接")
    self.click(*self.FORGOT_PASSWORD_LINK)
    time.sleep(2)

def click_register_link(self):
    logger.info("点击注册链接")
    self.click(*self.REGISTER_LINK)
    time.sleep(2)
```

每个方法后面都跟了 `time.sleep()`。有人觉得这是硬等、不优雅，但移动端自动化里这些 sleep 是有道理的：

- 输入后 `sleep(0.5)`——键盘弹起/收起需要时间。不等的话下一个操作可能点到键盘而不是页面元素。实际遇到过 `send_keys` 成功但后续 `click` 抛 `WebDriverException: Message: An unknown server-side error occurred while processing the command. Original error: 'POST /element/:id/click' cannot be proxied to UiAutomator2 server because the element is not in the active view`——就是键盘动画还没结束。

- 点击跳转类操作后 `sleep(2)`——页面转场动画 + 网络请求。不等就操作下一个页面元素，大概率 `StaleElementReferenceException`：元素还停留在上一个页面的 DOM 里。

### 验证方法——吞异常返回布尔值

验证方法的目标是：**不抛异常**。测试用例不需要用 `pytest.raises` 包一层，直接用 `if` 判断就行。

```python
def verify_login_title_exists(self) -> bool:
    try:
        element = self.find_element(*self.LOGIN_TITLE, timeout=5)
        return element is not None and element.is_displayed()
    except Exception as e:
        logger.warning(f"验证登录标题失败: {str(e)}")
        return False

def verify_phone_email_input_enabled(self) -> bool:
    try:
        element = self.find_element(*self.PHONE_EMAIL_INPUT, timeout=5)
        return element is not None and element.is_enabled()
    except Exception as e:
        logger.warning(f"验证输入框失败: {str(e)}")
        return False

def verify_password_input_enabled(self) -> bool:
    try:
        element = self.find_element(*self.PASSWORD_INPUT, timeout=5)
        return element is not None and element.is_enabled()
    except Exception as e:
        logger.warning(f"验证密码输入框失败: {str(e)}")
        return False

def verify_login_button_enabled(self) -> bool:
    try:
        element = self.find_element(*self.LOGIN_BUTTON, timeout=5)
        return element is not None and element.is_enabled()
    except Exception as e:
        logger.warning(f"验证登录按钮失败: {str(e)}")
        return False

`timeout=5` 是个合理的妥协——页面渲染慢时等 5 秒够了，再长测试用例跑得慢。`element.is_displayed()` 检查元素有没有被遮挡或不在可视区域，`is_enabled()` 检查按钮是否灰掉（比如没输完手机号时登录按钮是 disabled 状态）。

这里有个实际踩过的坑：你在 Appium Inspector 里看到元素存在，但脚本里 `find_element` 就是超时。报错：

```
selenium.common.exceptions.TimeoutException: Message: Expected condition failed: waiting for presence of element located by: ByAccessibilityId: login_button (tried for 5 second(s) with 500 milliseconds interval)

可能的原因：元素在 native 上下文里但脚本切到了 webview 上下文，或者反过来。用 `driver.contexts` 打印一下当前可用上下文确认。

另一个坑：`is_displayed()` 在 Appium 1.x 某些版本里对某些 Android 原生控件会抛异常：

```python
selenium.common.exceptions.WebDriverException: Message: Unknown error: getText is not a function
```

这时候直接 `return element is not None` 就够用，跳过 `is_displayed()`。

### 文本获取方法

```python
def get_phone_email_input_text(self) -> str:
    try:
        element = self.find_element(*self.PHONE_EMAIL_INPUT, timeout=5)
        return element.text if element else ""
    except Exception as e:
        logger.warning(f"获取输入框文本失败: {str(e)}")
        return ""
```

适用场景挺直接的：
- 输入后回读验证——比如输入 "test@example.com" 后 `get_phone_email_input_text()` 确认内容一致
- 获取错误提示信息——登录失败后页面上出现 "密码不正确" 之类文案，用文本获取抓回来断言

`element.text` 返回的是元素上显示的文本。如果元素不在屏幕上或者页面还没渲染完，`find_element` 会抛异常，catch 住返回空字符串。测试用例里就可以写：

```python
error_text = login_page.get_phone_email_input_text()
assert "密码不正确" in error_text

### 几个容易翻车的地方

**元素定位常量别搁方法里面定义。** 有人喜欢在 `input_phone_email` 方法里写 `phone_input = ("accessibility_id", "phone_email_input")`，每个方法都写一遍，维护时改个定位值要改 N 处。写在类级别，一处改到处生效。

**验证方法里 try/except 的范围。** 有些人只 catch `TimeoutException`，结果 `element.is_displayed()` 抛了个 `AttributeError` 或者 `StaleElementReferenceException`，测试崩了。LoginPage 里直接 `except Exception`，所有异常一网打尽返回 `False`。验证方法稳如狗，测试用例不用操心异常处理。

**time.sleep 时长别瞎拍。** 输入后 0.5 秒够用了，点击跳转后 2 秒起步。设太短（比如 0.5 秒）页面还没跳完，下一个 `find_element` 直接超时。设太长（比如 10 秒），一个测试跑下来光 sleep 就占半分钟。2 秒是个经验值，如果页面特别慢可以提到 3 秒，但应该优先排查为什么慢。

**一个页面类就管一个屏幕。** 登录页是一个 screen，注册页是另一个 screen，分开写。不要把登录按钮和注册页面里的国家选择器塞进同一个类。见过有人把所有页面操作写进一个 800 行的 `AppPage` 类，后面改一个元素定位要找半天。

**不在配套代码里的 `verify_password_input_enabled()`**——实际项目里确实会用到这个来验证密码框是否可编辑，但原配套代码只有 143 行，没把所有排列组合都塞进去。你项目里需要什么验证方法就加什么，别硬套模板。
