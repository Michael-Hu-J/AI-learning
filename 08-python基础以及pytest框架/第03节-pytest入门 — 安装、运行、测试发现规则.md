# 03-pytest入门 — 安装、运行、测试发现规则

> 对应代码：`test/pytest.ini`
>

---

## 概念讲解

Python的测试框架有两个选择：unittest（Python标准库自带）和 pytest（第三方库）。

**为什么90%的Python测试项目选 pytest？**

不是因为 unittest 不好——unittest 是标准库，稳定可靠。而是因为 pytest 在三个地方做得更舒服：

1. **不用继承类**。unittest 要求你的测试类继承 `unittest.TestCase`，pytest 不需要。任何函数加 `test_` 前缀就是测试。
2. **assert 更强大**。unittest 要用 `self.assertEqual()`、`self.assertTrue()`，pytest 直接用 `assert`，而且失败时会显示详细的 diff 信息。
3. **fixture 系统**。unittest 的 `setUp/tearDown` 只能在一个类里用，pytest 的 fixture 可以跨文件复用、可以依赖注入、可以控制作用域。

**pytest 的哲学很简单：简单的事情简单做，复杂的事情也能做。**

---

## 安装与环境配置

### 1. 安装与验证

```bash
# 安装 pytest
pip install pytest

# 验证安装
pytest --version
# 输出示例：pytest 8.3.4
```

如果项目用了 Allure 报告、HTML报告等插件，需要一起安装：

```bash
pip install pytest allure-pytest pytest-html
```

### 2. 测试发现三规则

pytest 怎么知道哪些文件是测试文件、哪些函数是测试用例？靠三个匹配规则：

| 规则 | 默认值 | 说明 |
|------|--------|------|
| `python_files` | `test_*.py` | 以 `test_` 开头的 .py 文件 |
| `python_classes` | `Test*` | 以 `Test` 开头的类（不能有 `__init__` 方法） |
| `python_functions` | `test_*` | 以 `test_` 开头的函数和方法 |

**这意味着**：
- 文件名必须是 `test_login.py`，不能是 `login_test.py` 或 `login.py`
- 类名必须是 `TestLogin`，不能是 `LoginTest`
- 函数名必须是 `test_login_success`，不能是 `login_success_test`

**这三个规则可以在 `pytest.ini` 中修改**：

```ini
[pytest]
# 测试文件匹配模式
python_files = test_*.py *_test.py

# 测试类匹配模式
python_classes = Test* Specs

# 测试函数匹配模式
python_functions = test_* should_*
```

但**不建议修改**。默认规则是社区约定，改了自己爽，别人接手时一脸懵。

### 3. 命令行参数详解

pytest 的命令行参数很多，但日常用的就这几个：

| 参数 | 作用 | 示例 |
|------|------|------|
| `-v` | 显示每个用例的名称和结果 | `pytest -v` |
| `-s` | 显示 print 输出（默认不显示） | `pytest -s` |
| `-x` | 第一个用例失败就停止 | `pytest -x` |
| `--tb=short` | 失败时显示简短的traceback | `pytest --tb=short` |
| `-k "关键词"` | 只运行名称包含关键词的用例 | `pytest -k "login"` |
| `-m "标记"` | 只运行指定标记的用例 | `pytest -m smoke` |
| `--maxfail=N` | 最多允许N个失败 | `pytest --maxfail=5` |
| `-n N` | 并行执行（需要 pytest-xdist） | `pytest -n 4` |

**最常用的组合**：

```bash
# 开发调试：显示详细信息 + 显示print输出
pytest -v -s

# CI环境：第一个失败就停 + 简短traceback
pytest -x --tb=short

# 只跑冒烟测试
pytest -m smoke -v
```

### 4. pytest.ini 配置文件

pytest 支持通过配置文件设置默认参数，不用每次都敲命令行。

来看真实项目中的 `pytest.ini`：

```ini
[pytest]
# 测试文件匹配模式
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 测试目录
testpaths = tests

# 命令行参数（每次运行自动加上这些参数）
addopts = 
    -v
    --strict-markers
    --tb=short
    --html=reports/html-report.html
    --self-contained-html
    --maxfail=5

# 标记定义（注册自定义marker，避免警告）
markers =
    android: Android平台测试
    ios: iOS平台测试
    smoke: 冒烟测试
    regression: 回归测试
    critical: 关键用例

# 日志配置
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# 禁用警告
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

**逐项解释**：

- **`testpaths = tests`**：指定测试目录。pytest 只在这个目录下找测试文件，不扫描整个项目。
- **`addopts`**：默认命令行参数。每次运行 `pytest` 都自动加上这些参数，不用手动敲。
- **`--strict-markers`**：严格模式。用了没在 `markers` 中注册的标记，pytest 会报错而不是警告。防止拼写错误导致标记不生效。
- **`--maxfail=5`**：最多5个失败就停止。CI环境中，如果前5个用例都挂了，后面大概率也挂，及时止损。
- **`log_cli = true`**：在控制台输出日志。调试时非常有用，能看到每个步骤的执行日志。
- **`filterwarnings`**：忽略弃用警告。第三方库经常有 deprecation warning，不影响功能但污染日志。

### 5. 运行单个测试

测试用例多了之后，全量跑很慢。pytest 支持精准运行：

```bash
# 运行单个文件
pytest tests/test_login.py

# 运行单个类
pytest tests/test_login.py::TestLogin

# 运行单个用例
pytest tests/test_login.py::TestLogin::test_login_success -v

# 运行多个文件
pytest tests/test_login.py tests/test_register.py

# 用关键词匹配
pytest -k "login" -v        # 运行名称包含 "login" 的所有用例
pytest -k "login and success" -v  # 同时包含两个关键词
pytest -k "not ios" -v      # 排除名称包含 "ios" 的用例
```

---

## 实战案例

从真实项目中提取一个完整的测试用例，展示从编写到运行的全流程。

**测试场景**：某移动App的登录功能测试。

**测试文件**：`test/tests/test_login_example.py`

```python
import pytest
import allure
from pages.login_page import LoginPage


@allure.epic("移动端UI自动化测试")
@allure.feature("登录功能")
class TestLogin:
    """登录功能测试类"""
    
    @allure.story("用户登录")
    @allure.title("正常登录测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke      # 标记为冒烟测试
    @pytest.mark.android    # 标记为Android平台
    def test_login_success(self, driver):
        """正常登录测试用例"""
        login_page = LoginPage(driver)
        login_page.login("test_user", "test_password")
        
        # 验证登录结果（与第02节 LoginPage.is_on_home_page 一致）
        assert login_page.is_on_home_page(), "登录应该成功但跳转失败"
    
    @allure.story("用户登录")
    @allure.title("错误密码登录测试")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.regression  # 标记为回归测试
    @pytest.mark.android
    def test_login_with_wrong_password(self, driver):
        """错误密码登录测试用例"""
        login_page = LoginPage(driver)
        
        login_page.input_username("test_user")
        login_page.input_password("wrong_password")
        login_page.click_login_button()
        
        login_page.wait(2)
        
        assert not login_page.is_on_home_page(), "错误密码不应进入主页"
        error_text = login_page.get_error_message()
        assert error_text, "错误密码时应展示错误提示"
        assert ("密码" in error_text) or ("不正确" in error_text), (
            f"错误提示应包含密码相关文案，实际: {error_text!r}"
        )
```

**运行方式**：

```bash
# 1. 运行整个登录测试类
pytest tests/test_login_example.py -v

# 输出示例：
# tests/test_login_example.py::TestLogin::test_login_success PASSED
# tests/test_login_example.py::TestLogin::test_login_with_wrong_password PASSED

# 2. 只运行正常登录用例
pytest tests/test_login_example.py::TestLogin::test_login_success -v

# 3. 只跑冒烟测试（会跑 test_login_success，不跑 test_login_with_wrong_password）
pytest -m smoke -v

# 4. 只跑Android平台的冒烟测试
pytest -m "smoke and android" -v

# 5. 显示日志输出
pytest tests/test_login_example.py -v -s
```

---

## 注意事项和常见坑

- **`pytest.ini` 放在哪生效？** pytest 会从**当前工作目录**起向父目录逐级查找，**最先找到**的那份配置生效。团队习惯上放在**仓库根目录**，这样无论从哪级子目录执行，通常都能命中同一份配置；若放得太深，在别的目录执行 `pytest` 时可能读到「意料之外的」另一份 `pytest.ini`。
- **`addopts` 中的参数会被命令行参数覆盖**。如果你在 `addopts` 里写了 `-v`，运行 `pytest -q`（安静模式）时，`-q` 会覆盖 `-v`。
- **不注册 marker 虽然能跑，但会污染 CI 日志**。pytest 会输出 `PytestUnknownMarkWarning`，在CI中几百行警告里找真正的错误很痛苦。
- **`--strict-markers` 建议 always on**。它会在你拼错 marker 名称时报错（如 `@pytest.mark.smoak` 拼错了），而不是静默忽略。
- **`testpaths` 不要设成 `.`（当前目录）**。这会扫描整个项目，包括 `node_modules`、`.git` 等目录，拖慢测试发现速度。明确指定 `tests` 或 `testcases`。

---

## 总结与思考

> pytest 的哲学是"约定优于配置"——用默认规则，少折腾。`test_*.py`、`Test*`、`test_*` 这三个约定，99%的项目都适用，别改。

**思考题**：你有没有遇到过"pytest 找不到我的测试文件"的情况？最后是怎么排查的？


---

## 面试题模块

### 1. 测试发现规则

**Q1：pytest 怎么知道哪些文件是测试文件？文件名、类名、函数名的默认规则是什么？**

A：三个默认规则：文件 `test_*.py`、类 `Test*`（不能有 `__init__`）、函数 `test_*`。这三个规则可以在 `pytest.ini` 中修改，但不建议——默认规则是社区约定，改了自己爽，别人接手时一脸懵。

### 2. 命令行参数

**Q2：`pytest -v -s` 和 `pytest -x --tb=short` 分别适合什么场景？**

A：`-v -s` 适合开发调试——显示详细信息 + 显示 print 输出，方便边写边看。`-x --tb=short` 适合 CI 环境——第一个失败就停 + 简短 traceback，快速发现问题。

### 3. pytest.ini

**Q3：`pytest.ini` 放在哪生效？`testpaths = .` 有什么风险？**

A：pytest 从当前工作目录起向父目录逐级查找，最先找到的那份配置生效。团队习惯上放在仓库根目录。`testpaths = .` 会扫描整个项目（包括 `node_modules`、`.git` 等目录），拖慢测试发现速度。应该明确指定 `tests` 或 `testcases`。

---

