# 02-Python基础（下）— 类、装饰器、异常处理、模块导入

> 对应代码：`test/base/base_page.py`、`test/api/base_api.py`、`test/conftest.py`、`test/utils/retry.py`
>

---

## 概念讲解

上节讲了Python的基础语法（变量、条件、循环、函数），覆盖了测试代码中80%的内容。

**剩下20%是什么？是类、装饰器、异常处理和模块导入。**

这20%的代码量不多，但它们是测试框架的"骨架"。你看到的 `@pytest.fixture`、`BasePage` 类、`try/except` 容错——都属于这20%。

**不学这20%，你能写测试用例，但看不懂测试框架是怎么工作的。** 框架出问题了，你只能干瞪眼。

这节把这四个知识点讲透，目标是：看完后你能理解项目中90%的Python代码。

---

## 面向对象与Page Object设计

### 1. 类与继承 — Page Object模式的核心

测试代码中最常用的面向对象模式就是**Page Object（页面对象）**。

**核心思想**：每个页面是一个类，类中包含该页面的元素定位和操作方法。测试用例只调用页面类的方法，不直接操作元素。

来看真实项目中的 `BasePage` 基类：

```python
class BasePage:
    """
    页面对象基类
    
    作用：
    1. 封装所有常用的移动端操作（点击、滑动、输入等）
    2. 提供统一的元素定位和等待方法
    3. 所有页面类都应该继承这个基类
    """
    
    def __init__(self, driver):
        """
        初始化页面对象
        
        参数：
        - driver: WebDriver实例（Appium/Selenium）
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)  # 默认等待10秒
    
    def click(self, locator_type, locator_value, timeout=10):
        """点击元素"""
        element = self.find_element(locator_type, locator_value, timeout)
        element.click()
        time.sleep(0.5)  # 点击后稍等，避免操作过快
    
    def input_text(self, locator_type, locator_value, text, clear_first=True):
        """输入文本"""
        element = self.find_element(locator_type, locator_value)
        if clear_first:
            element.clear()
        element.send_keys(text)
    
    def find_element(self, locator_type, locator_value, timeout=10):
        """查找单个元素（带显式等待）"""
        locator_map = {
            "id": (AppiumBy.ID, locator_value),
            "xpath": (AppiumBy.XPATH, locator_value),
            "accessibility_id": (AppiumBy.ACCESSIBILITY_ID, locator_value),
        }
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located(locator_map[locator_type]))
```

**然后具体的页面类继承 `BasePage`**：

```python
import time


class LoginPage(BasePage):
    """登录页面"""
    
    # 元素定位（页面级别的常量）
    USERNAME_INPUT = ("id", "username_field")
    PASSWORD_INPUT = ("id", "password_field")
    LOGIN_BUTTON = ("id", "login_btn")
    
    def login(self, username, password):
        """执行完整的登录流程"""
        self.input_text(*self.USERNAME_INPUT, username)
        self.input_text(*self.PASSWORD_INPUT, password)
        self.click(*self.LOGIN_BUTTON)
    
    def input_username(self, username):
        """仅输入用户名（分步操作用，与后续 pytest 示例一致）"""
        self.input_text(*self.USERNAME_INPUT, username)
    
    def input_password(self, password):
        """仅输入密码（分步操作用）"""
        self.input_text(*self.PASSWORD_INPUT, password)
    
    def click_login_button(self):
        """仅点击登录（分步操作用）"""
        self.click(*self.LOGIN_BUTTON)
    
    def wait(self, seconds):
        """固定等待（教学演示用；生产代码优先显式等待）"""
        time.sleep(seconds)
    
    def is_on_home_page(self):
        """是否已在主页：示例为检查首页特征元素是否存在"""
        try:
            self.find_element("id", "home_tab", timeout=5)
            return True
        except Exception:
            return False
    
    def get_error_message(self):
        """获取错误提示信息"""
        error_element = self.find_element("id", "error_message")
        return error_element.text
```

**测试用例的写法**：

```python
def test_login_success(driver):
    """测试正常登录"""
    login_page = LoginPage(driver)
    login_page.login("test_user", "test_password")
    
    # 验证登录结果
    assert login_page.is_on_home_page(), "登录应该成功但跳转失败"
```

**Page Object的好处**：
1. **代码复用**：点击、输入等基础操作写在 `BasePage` 里，所有页面类都能用
2. **维护方便**：元素定位变了，只改页面类里的常量，测试用例不用动
3. **职责清晰**：页面类管"怎么操作"，测试用例管"验证什么"

### 2. 装饰器 — `@` 符号背后的魔法

装饰器是Python最容易被误解的特性之一。很多人觉得它"很高深"，其实测试工程师只需要理解一个核心概念：

**装饰器就是一个函数包装器，它在原函数执行前后自动添加额外逻辑。**

测试中最常见的三个装饰器：

**① `@pytest.fixture` — 自动注入测试依赖**

```python
@pytest.fixture(scope="session")
def driver_setup(request):
    """会话级别的驱动初始化fixture"""
    driver = create_driver()  # 初始化WebDriver
    yield driver              # 把driver传给测试函数
    driver.quit()             # 测试结束后清理
```

**它做了什么**：测试函数声明需要 `driver` 参数时，pytest自动调用这个装饰的函数，把返回值传进去。你不需要手动创建driver。

**② `@allure.severity` — 标记测试用例的严重级别**

```python
@allure.severity(allure.severity_level.CRITICAL)
def test_login_success(driver):
    """登录成功测试"""
    ...
```

**它做了什么**：在测试报告中标记这个用例的优先级。CRITICAL的用例失败会在报告中高亮显示。

**③ `@retry_on_failure` — 失败自动重试**

真实项目中有一个重试装饰器，用于处理偶发性失败：

```python
def retry_on_failure(max_attempts=3, delay=2.0):
    """
    重试装饰器
    
    参数：
    - max_attempts: 最大重试次数
    - delay: 每次重试间隔（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)  # 执行原函数
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} 第{attempt+1}次失败，"
                            f"{delay}秒后重试: {e}"
                        )
                        time.sleep(delay)
            raise last_exception  # 所有重试都失败，抛出异常
        return wrapper
    return decorator

# 使用方式
@retry_on_failure(max_attempts=3, delay=2.0)
def test_with_retry(driver):
    """可能偶发性失败的测试"""
    login_page = LoginPage(driver)
    login_page.login("user", "pass")
    assert login_page.is_on_home_page()
```

**装饰器的本质**：`@decorator` 等价于 `func = decorator(func)`。装饰器接收原函数，返回一个包装后的新函数。

### 3. 异常处理 try/except — 测试中的容错与降级

测试代码中，异常处理有两个核心场景：

**场景一：清理资源（无论成功失败都要执行）**

```python
@pytest.fixture(scope="session")
def driver_setup(request):
    driver = create_driver()
    
    def driver_teardown():
        """清理函数——无论测试成功还是失败都会执行"""
        try:
            logger.info("开始关闭驱动")
            driver.quit()
            logger.info("驱动关闭成功")
        except Exception as e:
            logger.error(f"驱动关闭异常: {str(e)}")
            # 注意：这里不raise，清理失败不应该影响测试结果
    
    request.addfinalizer(driver_teardown)
    yield driver
```

**关键原则**：清理代码（teardown）中的异常不应该影响测试结果。所以 `except` 里只记日志，不 `raise`。

**场景二：容错处理（某个操作失败不影响整体流程）**

```python
def find_element_smart(self, locators, timeout=10):
    """智能元素定位——按优先级尝试多种方式"""
    last_exception = None
    for idx, (locator_type, locator_value) in enumerate(locators):
        try:
            element = self.find_element(locator_type, locator_value, timeout)
            return element
        except (TimeoutException, NoSuchElementException) as e:
            last_exception = e
            logger.debug(f"定位方式 {locator_type} 失败: {e}")
            continue  # 尝试下一个定位方式
    
    # 所有方式都失败了
    raise TimeoutException(f"无法定位元素: {last_exception}")
```

**这里 try/except 的作用是"捕获预期内的异常，继续尝试"**，而不是让程序崩溃。

### 4. 模块导入与包结构 — 测试项目的目录组织

测试项目的代码量大了之后，必须合理组织目录。否则找文件就要花半天。

来看真实项目的目录结构：

```
test/
├── conftest.py          # pytest配置：fixture + hook
├── pytest.ini           # pytest配置文件
├── config.yaml          # 业务配置：Appium、设备、测试参数
├── base/                # 基础层
│   ├── __init__.py
│   ├── base_page.py     # 页面对象基类
│   └── base_driver.py   # 驱动初始化
├── api/                 # API封装层
│   ├── __init__.py
│   └── base_api.py      # HTTP请求基类
├── pages/               # 页面对象层
│   ├── login_page.py    # 登录页面
│   └── register_page.py # 注册页面
├── tests/               # 测试用例层
│   ├── test_login.py
│   └── test_register.py
├── testcases/           # 测试数据
│   ├── yaml/            # YAML格式的测试用例
│   └── data/            # 测试数据文件
├── utils/               # 工具类
│   ├── logger.py        # 日志工具
│   ├── screenshot.py    # 截图工具
│   └── retry.py         # 重试工具
└── reports/             # 测试报告输出
    └── allure-results/
```

**导入规则**：

```python
# 同一目录下的导入（相对导入）
from base.base_page import BasePage
from utils.logger import Logger

# 跨目录的导入（从项目根目录开始）
from pages.login_page import LoginPage
from api.base_api import BaseAPI
```

**`__init__.py` 的作用**：在常见的**常规包**布局里，放一个 `__init__.py`（可为空）能稳定地把目录当作包来导入；Python 3.3 起也支持无 `__init__.py` 的命名空间包，但测试工程里仍**强烈建议**每个包目录保留 `__init__.py`，少踩导入路径与工具链上的边角问题。

---

## 实战案例

以"API测试基类"为场景，把类、异常处理、装饰器串起来。

**场景描述**：所有接口测试都继承 `BaseAPI` 类，它封装了HTTP请求的通用操作（发送请求、处理响应、异常容错）。

```python
class BaseAPI:
    """
    API测试基类
    
    作用：
    1. 封装HTTP请求方法（GET、POST、PUT、DELETE）
    2. 统一处理请求头、认证、超时
    3. 统一处理响应和异常
    """
    
    def __init__(self, base_url=None, timeout=30, verify_ssl=True):
        self.base_url = base_url or ""
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def set_auth(self, auth_type="bearer", token=None):
        """设置认证信息"""
        if auth_type.lower() == "bearer" and token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def _build_url(self, endpoint):
        """拼接完整URL"""
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        base = self.base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base}/{endpoint}"
    
    def _request(self, method, endpoint, json_data=None, headers=None, **kwargs):
        """
        发送HTTP请求（内部方法）
        
        所有具体的GET/POST等方法都调用这个内部方法
        """
        url = self._build_url(endpoint)
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        logger.info(f"发送{method}请求: {url}")
        
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                json=json_data,
                headers=request_headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                **kwargs
            )
            logger.info(f"响应状态码: {response.status_code}")
            return response
        
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            raise  # 超时异常直接抛出，让测试用例处理
        
        except requests.exceptions.ConnectionError:
            logger.error(f"连接错误: {url}")
            raise  # 连接错误直接抛出
        
        except Exception as e:
            logger.error(f"请求异常: {str(e)}")
            raise  # 其他异常也抛出
    
    def get(self, endpoint, params=None, **kwargs):
        """发送GET请求"""
        return self._request("GET", endpoint, params=params, **kwargs)
    
    def post(self, endpoint, json_data=None, **kwargs):
        """发送POST请求"""
        return self._request("POST", endpoint, json_data=json_data, **kwargs)
    
    def put(self, endpoint, json_data=None, **kwargs):
        """发送PUT请求"""
        return self._request("PUT", endpoint, json_data=json_data, **kwargs)
    
    def delete(self, endpoint, **kwargs):
        """发送DELETE请求"""
        return self._request("DELETE", endpoint, **kwargs)
```

**使用方式**：

```python
# 创建API客户端
api = BaseAPI(base_url="https://api.example.com", timeout=30)
api.set_auth("bearer", "your_token_here")

# 发送请求
response = api.post("/api/auth/login", json_data={
    "email": "user@example.com",
    "password": "password123"
})

# 验证响应
assert response.status_code == 200
data = response.json()
assert data["code"] == "SUCCESS"
```

**这个案例展示了什么**：
- 类封装了重复的HTTP请求逻辑（不用每个接口都写一遍 `requests.request`）
- 异常处理区分了"预期内异常"（超时、连接错误）和"未知异常"
- 内部方法 `_request` 被所有公开方法（get/post/put/delete）复用

---

## 注意事项和常见坑

- **类名用大驼峰（PascalCase），方法名用小写+下划线（snake_case）。** 这是Python的命名规范（PEP 8），`BasePage` 是对的，`basepage` 是错的。
- **`__init__.py` 不要留空太久。** 空文件虽然能工作，但最好在里面放 `from .base_page import BasePage` 这样的导出声明，方便其他模块导入。
- **装饰器可以叠加，但执行顺序从下到上。** `@A` `@B` `def func():` 等价于 `func = A(B(func))`。先执行B装饰，再执行A装饰。
- **`except Exception` 不要滥用。** 捕获所有异常听起来安全，但会掩盖真正的bug（如 `KeyboardInterrupt` 被你捕获后，Ctrl+C 就失效了）。尽量捕获具体的异常类型。
- **相对导入在pytest中容易出错。** pytest运行测试时，当前工作目录可能不是你期望的。推荐用绝对导入（从项目根目录开始），或者在 `conftest.py` 中 `sys.path.insert(0, os.path.dirname(__file__))`。

---

## 总结与思考

> 类解决的是"重复代码"的问题，装饰器解决的是"横切关注点"的问题，异常处理解决的是"容错"的问题。测试代码不需要炫技，但需要理解这三个概念，否则框架出了问题你连排查的方向都没有。

**思考题**：你在项目中见过最"绕"的装饰器用法是什么？有没有见过装饰器叠加超过3层的情况？你觉得这样是好是坏？


---

## 面试题模块

### 1. 类与继承

**Q1：Page Object 模式的核心思想是什么？为什么测试项目需要它？**

A：Page Object 的核心思想是"每个页面是一个类，类中包含该页面的元素定位和操作方法"。好处是：元素定位变了只改一个地方，操作流程变了只改一个方法，验证逻辑变了只改测试用例。没有 Page Object，元素定位散落在 20 个测试函数中，页面改版后改 20 个文件。

### 2. 装饰器

**Q2：`@pytest.fixture` 和 `@pytest.mark.smoke` 是装饰器，装饰器的本质是什么？**

A：装饰器的本质是"在不修改原函数代码的前提下，给函数增加额外功能"。`@pytest.fixture` 给函数增加了"可以测试依赖注入"的功能，`@pytest.mark.smoke` 给函数增加了"可以被 `-m smoke` 筛选"的功能。底层实现是"函数参数传入，返回一个新函数"。

### 3. 异常处理

**Q3：pytest 的 fixture 中，`yield` 之后的代码即使测试失败也会执行吗？**

A：会。这是 pytest 的设计保证——`yield` 之后的 teardown 代码一定会执行，即使测试函数抛异常。这保证了资源（如 WebDriver、数据库连接）一定会被清理。但 teardown 代码本身如果抛异常，会打印警告而不影响测试结果。

---

