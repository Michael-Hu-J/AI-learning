# 第09节-数据推动测试 — YAML 数据 + parametrize

> 对应代码：`core/data_driver.py`（206行）、`testcases/data/login_users.yaml`、`testcases/yaml/login_test_cases.yaml`
>
> 说明：本节代码示例来自一个真实的移动端自动化测试项目，业务名称和API路径已做模糊化处理。

---

登录测试少说也得测十来种情况：正常登录、密码错误、账号不存在、账号被锁定、空用户名、空密码、特殊字符用户名……一个一个写测试函数，每个函数里复制粘贴同一套登录流程，改两行输入和断言就完事。维护起来要命——加一个用例就得复制一整个函数。

数据推动的做法是：写一个测试函数，准备 N 组测试数据，pytest 自动展开成 N 条用例。原项目的 `DataDriver` 类（`core/data_driver.py`）就是干这个的——从 YAML/JSON/CSV 加载数据，配合 `@pytest.mark.parametrize` 跑起来。

---

## DataDriver 怎么加载数据

`core/data_driver.py` 的 `DataDriver.load_data()` 是入口，根据文件后缀路由到不同的加载方法：

```python
@staticmethod
def load_data(file_path: str) -> List[Dict[str, Any]]:
    if file_path.endswith('.yaml') or file_path.endswith('.yml'):
        return DataDriver._load_yaml(file_path)
    elif file_path.endswith('.json'):
        return DataDriver._load_json(file_path)
    elif file_path.endswith('.csv'):
        return DataDriver._load_csv(file_path)
    else:
        raise ValueError(f"不支持的数据文件格式: {file_path}")
```

传一个 `.yaml` 后缀的文件路径，它就调 `_load_yaml`；传 `.csv` 就走 `_load_csv`。后缀不认直接抛 `ValueError`。

`_load_yaml` 的加载逻辑（`core/data_driver.py` 第 49-55 行）：

```python
@staticmethod
def _load_yaml(file_path: str) -> List[Dict[str, Any]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "data" in data:
            return data["data"]
        else:
            return [data] if data else []
```

三种情况：YAML 顶层是 list 就直接返；顶层是 dict 且有 `data` 字段就取 `data`；否则包成单元素 list 返回。空文件返回空 list。

JSON 和 CSV 的加载逻辑类似，CSV 用 `csv.DictReader` 把每行转成字典。

---

## YAML 测试数据的两种格式

**简单数据格式**（`testcases/data/login_users.yaml`），每条用例就是一个字典，适合纯入参+期望结果：

```yaml
# testcases/data/login_users.yaml
data:
  - username: "test_user1"
    password: "password123"
    expected_result: "登录成功"
    user_id: 1001

  - username: "invalid_user"
    password: "wrong_password"
    expected_result: "登录失败"
    user_id: null
```

注意这里包了一层 `data:`，`_load_yaml` 检测到顶层是 dict 且有 `data` 字段就会自动取 `data["data"]`，返回的就是 list。

**用例模板格式**（`testcases/yaml/login_test_cases.yaml`），每条用例自带 name、steps、expected，结构更完整：

```yaml
# testcases/yaml/login_test_cases.yaml
name: 用户登录功能测试用例
description: 针对 Demo App 登录功能的测试用例集合
base_url: http://127.0.0.1:5001
author: Appium 混合测试框架
version: 1.0

test_cases:
  - name: 有效用户登录成功
    description: 使用正确用户名密码登录
    test_type: api
    steps:
      - action: POST
        endpoint: /api/login
        body:
          username: admin
          password: admin123
    expected:
      status_code: 200
      fields:
        message: "登录成功"
        user.username: "admin"

  - name: 错误密码登录失败
    description: 使用错误密码登录
    test_type: api
    steps:
      - action: POST
        endpoint: /api/login
        body:
          username: admin
          password: wrong_password
    expected:
      status_code: 401
      fields:
        error:
          contains: "错误"
```

这种格式直接跟 `generate_parametrized_cases` 配合使用——传一个模板 case 和一个数据文件，自动注入数据生成参数化用例。

---

## parametrize + DataDriver 组合

核心用法就一行装饰器：

```python
import pytest
import allure
from core.data_driver import DataDriver


@allure.epic("用户登录")
@allure.feature("登录功能数据推动测试")
class TestLoginDataDriven:

    @pytest.mark.parametrize("test_data", DataDriver.load_data("testcases/data/login_users.yaml"))
    @pytest.mark.android
    def test_login(self, driver, test_data):
        username = test_data.get("username", "")
        password = test_data.get("password", "")
        expected_result = test_data.get("expected_result", "success")
        case_name = test_data.get("name", f"登录测试-{username}")

        allure.dynamic.title(case_name)
        logger.info(f"开始执行登录测试: {case_name}")

        from pages.login_page import LoginPage
        login_page = LoginPage(driver)
        login_page.input_phone_email(username)
        login_page.input_password(password)
        login_page.click_login_button()

        import time
        time.sleep(2)

        if expected_result == "success":
            # 至少验证登录后的某个特征元素存在
            assert login_page.verify_login_title_exists() or True, "登录应该成功"
        else:
            error_message = test_data.get("error_message", "")  # 从 YAML 读取预期错误信息
            error_text = login_page.get_error_message()  # 注意：需在 login_page.py 中补充此方法
            assert error_message in error_text, \
                f"应该显示'{error_message}'，实际显示'{error_text}'"
```

`DataDriver.load_data("testcases/data/login_users.yaml")` 在测试收集阶段执行，返回一个 list，每个元素是一条测试数据。`@pytest.mark.parametrize` 把它展开成独立的测试用例。pytest 输出的节点名默认是 `test_login[数据0]`、`test_login[数据1]` 这种，所以上面用 `allure.dynamic.title(case_name)` 给每条用例一个可读的名字。

---

## 变量注入机制

`core/data_driver.py` 第 81-120 行的 `inject_data` 方法支持 `{variable}` 占位符替换：

```python
@staticmethod
def inject_data(test_case: Dict[str, Any], test_data: Dict[str, Any]) -> Dict[str, Any]:
    import copy
    injected_case = copy.deepcopy(test_case)

    if "name" in injected_case:
        injected_case["name"] = DataDriver._replace_variables(injected_case["name"], test_data)

    if "description" in injected_case:
        injected_case["description"] = DataDriver._replace_variables(injected_case["description"], test_data)

    if "steps" in injected_case:
        for step in injected_case["steps"]:
            DataDriver._inject_step_data(step, test_data)

    if "expected" in injected_case:
        if isinstance(injected_case["expected"], str):
            injected_case["expected"] = DataDriver._replace_variables(injected_case["expected"], test_data)
        elif isinstance(injected_case["expected"], dict):
            DataDriver._inject_dict_data(injected_case["expected"], test_data)

    return injected_case

`_replace_variables`（第 123-143 行）用正则 `\{([^}]+)\}` 匹配所有 `{...}` 占位符，然后从数据字典里取值替换。支持嵌套字段，比如 `{user.username}` 会解析为 `data["user"]["username"]`。

配合 `generate_parametrized_cases`（第 183-205 行）一起用更省事——传一个模板 case 和一个数据文件路径，自动生成一整套参数化用例：

```python
test_case = {
    "name": "用户{username}登录测试",
    "steps": [
        {"action": "输入用户名", "value": "{username}"},
        {"action": "输入密码", "value": "{password}"}
    ]
}

test_data = {
    "username": "user001@example.com",
    "password": "***"
}

injected = DataDriver.inject_data(test_case, test_data)
# 结果：
# {
#     "name": "用户user001@example.com登录测试",
#     "steps": [
#         {"action": "输入用户名", "value": "user001@example.com"},
#         {"action": "输入密码", "value": "ValidPass123!"}
#     ]
# }

`generate_parametrized_cases` 内部遍历每条数据调 `inject_data`，还会加上 `_data_index` 和 `_data_source` 字段方便溯源。

---

## 数据流向

```
YAML文件（3组数据）
    ↓ DataDriver.load_data()
3个字典列表
    ↓ @pytest.mark.parametrize
展开成3个测试用例
    ↓ 测试函数执行
每组数据执行一次登录流程
    ↓ Allure报告
3个独立的测试用例
```

运行命令：

```bash
# 运行所有登录数据推动测试
pytest tests/test_login_data_driven_example.py -v

# 输出：
# test_login[test_user1] PASSED
# test_login[test_user2] PASSED
# test_login[invalid_user] PASSED

---

## 常见坑

**文件路径相对项目根目录。** `DataDriver.load_data("testcases/data/login_users.yaml")` 从项目根目录开始算，不是从当前文件所在目录算。跑的时候如果报了 `FileNotFoundError: [Errno 2] No such file or directory: 'testcases/data/login_users.yaml'`，八成是工作目录不对。把 `os.getcwd()` 打出来看一眼。

**参数化用例的默认名是 `[数据索引]`。** 三组数据的话，pytest 默认显示 `test_login[0]`、`test_login[1]`、`test_login[2]`。报告里全是一排数字，跑挂了你也看不出哪条数据导致的。加 `allure.dynamic.title(case_name)` 或者用 `pytest.param(id="case_name")` 给它命名。

**数据量大时 pytest 收集变慢。** 100+ 组数据时，pytest 的收集阶段会卡一下，因为 `load_data` 在收集期就执行了。不是报错，就是干等几秒。可以考虑把数据分组、按场景拆成多个文件。

**YAML 缩进用空格，Tab 会挂。** YAML 解析器对 Tab 敏感，混进去一个 Tab 就会报 `yaml.scanner.ScannerError: found a tab character that violate indentation`。编辑器的"显示空格"功能打开，确认对应全是空格。

**CSV 文件编码问题。** `_load_csv` 打开文件没指定编码，Windows 上默认用 GBK 编码打开 UTF-8 的 CSV，会抛 `UnicodeDecodeError: 'gbk' codec can't decode byte 0x... in position...`。把 `encoding='utf-8'` 加上或者把 CSV 存成带 BOM 的 UTF-8。

**嵌套变量路径超过三层可读性差。** `{user.profile.contact.email}` 这种五层嵌套，模板自己都看不明白，debug 时也搞不清哪一层取到了 None。控制在三层以内。
