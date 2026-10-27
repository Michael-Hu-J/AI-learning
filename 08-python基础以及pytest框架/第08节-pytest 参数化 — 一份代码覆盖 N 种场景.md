# 08-pytest 参数化 — 一份代码覆盖 N 种场景

> 对应代码：`test/tests/test_login_data_driven_example.py`、`test/testcases/data/login_users.yaml`
>

---

## 概念讲解

一个登录测试，你要测多少种情况？

正常登录、密码错误、账号不存在、账号被锁定、网络超时、服务器错误……至少10种。

**传统写法**：写10个测试函数。每个函数重复相同的登录流程，只是输入数据和预期结果不同。

**参数化写法**：写1个测试函数，准备10组测试数据。pytest 自动把每组数据生成一个独立的测试用例。

**代码量从 10×50行 = 500行 降到 1×50行 + 10组数据 = 150行。**

这就是参数化（Data-Driven Testing，数据驱动测试）的价值：**测试逻辑只写一次，测试数据外部管理。**

---

## 参数化使用方法

### 1. @pytest.mark.parametrize 基本用法

`@pytest.mark.parametrize` 是 pytest 的参数化装饰器。它把一个测试函数"展开"成多个测试用例，每组参数对应一个用例。

**单参数参数化**：

```python
@pytest.mark.parametrize("username,password,expected", [
    ("user001@example.com", "ValidPass123!", "success"),
    ("user001@example.com", "wrong_password", "fail"),
    ("nobody@fake.com", "AnyPass123!", "fail"),
])
def test_login(username, password, expected):
    """登录测试——3组参数 = 3个测试用例"""
    if expected == "success":
        assert do_login(username, password) == True
    else:
        assert do_login(username, password) == False
```

**运行结果**：pytest 会生成3个独立的测试用例：

```
test_login[user001@example.com-ValidPass123!-success] PASSED
test_login[user001@example.com-wrong_password-fail] PASSED
test_login[nobody@fake.com-AnyPass123!-fail] PASSED
```

**多参数参数化**：

```python
@pytest.mark.parametrize("platform,device_name", [
    ("android", "Android Emulator"),
    ("ios", "iPhone 13"),
])
@pytest.mark.parametrize("test_type", ["smoke", "regression"])
def test_cross_platform(platform, device_name, test_type):
    """跨平台测试——2×2 = 4个测试用例"""
    ...
```

**多个 parametrize 装饰器会做笛卡尔积**：2个平台 × 2种测试类型 = 4个用例。

### 2. 从 YAML 加载测试数据

参数化的数据不一定写在代码里。更常见的做法是写在 YAML 文件中，测试运行时动态加载。

**YAML 数据文件**（`testcases/data/login_users.yaml`）：

```yaml
- name: "正常登录"
  username: "user001@example.com"
  password: "ValidPass123!"
  expected_result: "success"
  error_message: ""

- name: "密码错误"
  username: "user001@example.com"
  password: "wrong_password"
  expected_result: "fail"
  error_message: "密码不正确，请重试"

- name: "账号不存在"
  username: "nobody@fake.com"
  password: "AnyPass123!"
  expected_result: "fail"
  error_message: "该账号未注册"

- name: "账号被锁定"
  username: "locked_user@example.com"
  password: "ValidPass123!"
  expected_result: "fail"
  error_message: "账号已被锁定，请联系客服"

- name: "空用户名"
  username: ""
  password: "ValidPass123!"
  expected_result: "fail"
  error_message: "请输入用户名"
```

**DataDriver 工具类**（从 YAML 加载数据）：

```python
import yaml
import os


class DataDriver:
    """
    数据驱动工具类
    从YAML文件加载测试数据
    """
    
    @staticmethod
    def load_data(file_path):
        """
        从YAML文件加载测试数据
        
        参数：
        - file_path: YAML文件路径（相对于项目根目录）
        
        返回：
        - 测试数据列表（每个元素是一个字典）
        """
        # 获取项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, file_path)
        
        with open(full_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return data if data else []
```

### 3. 参数化 + YAML 的组合

```python
import pytest
import allure
from core.data_driver import DataDriver


@allure.epic("用户登录")
@allure.feature("登录功能数据驱动测试")
class TestLoginDataDriven:
    """
    登录功能数据驱动测试类
    
    使用数据驱动测试，一次编写流程，覆盖所有登录用例
    """
    
    @pytest.mark.parametrize("test_data", DataDriver.load_data("testcases/data/login_users.yaml"))
    @pytest.mark.android
    def test_login(self, driver, test_data):
        """
        数据驱动登录测试
        
        参数：
        - test_data: 从YAML文件加载的测试数据
        """
        # 从测试数据中获取参数
        username = test_data.get("username", "")
        password = test_data.get("password", "")
        expected_result = test_data.get("expected_result", "success")
        error_message = test_data.get("error_message", "")
        case_name = test_data.get("name", f"登录测试-{username}")
        
        # 设置Allure报告信息（动态标题）
        allure.dynamic.title(case_name)
        
        logger.info(f"开始执行登录测试: {case_name}")
        logger.info(f"用户名: {username}, 预期结果: {expected_result}")
        
        # 执行登录
        login_page = LoginPage(driver)
        login_page.input_username(username)
        login_page.input_password(password)
        login_page.click_login_button()
        
        # 等待登录结果
        import time
        time.sleep(2)
        
        # 验证登录结果
        if expected_result == "success":
            assert login_page.is_on_home_page(), "登录应该成功但跳转失败"
            logger.info(" 验证登录成功")
        else:
            error_text = login_page.get_error_message()
            assert error_message in error_text, \
                f"应该显示'{error_message}'，实际显示'{error_text}'"
            logger.info(f" 验证登录失败，错误信息正确")
```

**运行结果**：YAML 文件中有5组数据，pytest 会生成5个独立的测试用例。每个用例在 Allure 报告中显示为独立的条目，标题是 YAML 中的 `name` 字段。

### 4. allure.dynamic.title — 参数化用例的命名

参数化用例默认显示为 `[0]`、`[1]`、`[2]`，在报告中很难看懂。

`allure.dynamic.title()` 可以在运行时动态设置用例标题：

```python
allure.dynamic.title(case_name)  # 设置为 YAML 中的用例名称
```

**效果**：报告中显示的是"正常登录"、"密码错误"、"账号不存在"，而不是 `[0]`、`[1]`、`[2]`。

---

## 实战案例

以"登录功能"为场景，展示从 YAML 数据准备到参数化执行的完整流程。

**步骤1：准备 YAML 测试数据**

```yaml
# testcases/data/login_users.yaml
- name: "正常登录"
  username: "user001@example.com"
  password: "ValidPass123!"
  expected_result: "success"
  error_message: ""

- name: "密码错误"
  username: "user001@example.com"
  password: "wrong_password"
  expected_result: "fail"
  error_message: "密码不正确，请重试"

- name: "账号不存在"
  username: "nobody@fake.com"
  password: "AnyPass123!"
  expected_result: "fail"
  error_message: "该账号未注册"
```

**步骤2：编写参数化测试函数**

```python
@pytest.mark.parametrize("test_data", DataDriver.load_data("testcases/data/login_users.yaml"))
def test_login(driver, test_data):
    username = test_data.get("username", "")
    password = test_data.get("password", "")
    expected_result = test_data.get("expected_result", "success")
    error_message = test_data.get("error_message", "")
    case_name = test_data.get("name", "")
    
    allure.dynamic.title(case_name)
    
    login_page = LoginPage(driver)
    login_page.login(username, password)
    
    if expected_result == "success":
        assert login_page.is_on_home_page()
    else:
        error_text = login_page.get_error_message()
        assert error_message in error_text
```

**步骤3：运行测试**

```bash
# 运行所有登录数据驱动测试
pytest tests/test_login_data_driven_example.py -v

# 输出：
# test_login[正常登录] PASSED
# test_login[密码错误] PASSED
# test_login[账号不存在] PASSED
```

**数据流向**：
```
YAML文件 → DataDriver.load_data() → @pytest.mark.parametrize → 测试函数
  ↓              ↓                        ↓                    ↓
5组数据      5个字典列表          展开成5个用例        每组数据执行一次
```

---

## 注意事项和常见坑

- **YAML 文件路径是相对于项目根目录的**。`DataDriver.load_data("testcases/data/login_users.yaml")` 中的路径从项目根目录开始计算。如果路径错了，`FileNotFoundError` 会在测试收集阶段就报错。
- **参数化用例的默认名称是 `[0]`、`[1]`**。不用 `allure.dynamic.title()` 的话，报告里全是数字，根本看不出哪个用例失败了。
- **大数据量参数化会影响 pytest 收集速度**。100+ 组数据时，pytest 的收集阶段会变慢。如果数据量很大，考虑分页加载或分批执行。
- **参数化 vs 独立的测试方法**：如果测试逻辑完全相同只是数据不同，用参数化。如果每个用例的逻辑有明显差异，写独立的测试方法更清晰。
- **YAML 中的缩进必须用空格，不能用 Tab**。YAML 对缩进很敏感，Tab 和空格混用会导致解析错误。

---

## 总结与思考

> 参数化的核心思想是"逻辑与数据分离"。测试逻辑写一次，测试数据管起来。当你需要新增一个测试场景时，只需要在 YAML 里加一行数据，而不是复制粘贴一个测试函数。

**思考题**：你的项目中有没有"同一个测试流程跑了十几二十种数据"的场景？当时是怎么管理的？有没有用过参数化？


---

## 面试题模块

### 1. parametrize 基本用法

**Q1：`@pytest.mark.parametrize` 的作用是什么？一组参数 = 一个测试用例吗？**

A：`parametrize` 把一个测试函数"展开"成多个测试用例，每组参数对应一个独立的测试用例。例如 3 组参数 = 3 个用例，pytest 会分别执行、分别报告结果。失败时能精确定位到是哪组参数失败。

### 2. 外部数据源

**Q2：怎么从 YAML/JSON 文件加载测试数据并参数化？**

A：在装饰器中直接调用数据加载函数：
```python
@pytest.mark.parametrize("test_data", DataDriver.load_data("testcases/data/login_users.yaml"))
def test_login(test_data):
    username = test_data["username"]
    ...
```
`DataDriver.load_data()` 返回字典列表，pytest 会为每个字典生成一个测试用例。

### 3. 参数化陷阱

**Q3：参数化测试中，如果某组数据应该跳过，怎么实现？**

A：在测试函数内部用 `pytest.skip()`：
```python
def test_login(test_data):
    if test_data.get("skip"):
        pytest.skip("该用例标记为跳过")
    ...
```
或者用 `pytest.mark.skipif` 装饰器配合条件判断。

---

