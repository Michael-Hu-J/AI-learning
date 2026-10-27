# 09-pytest Mark 标记 — 分类、筛选、skip/xfail

> 对应代码：`test/pytest.ini`（markers 定义）、`test/tests/test_login_example.py`（mark 用法）

---

## 概念讲解

标记测试用例，听起来是个小功能，但当你有 200 个用例要跑时，它就是能不能按时交付的分水岭。

**全量跑一次要多久？5分钟？30分钟？2小时？**

CI 环境中，每次代码提交都跑全量测试是不现实的。你需要的是：
- 代码提交后：只跑冒烟测试（5分钟）
- 每天凌晨：跑全量回归测试（2小时）
- 发版前：跑全量 + 关键用例（3小时）
- iOS 平台：跳过 Android 专属用例

**marker 就是用来做这个的——给测试用例打标签，然后按需筛选。**

---

## 自定义标记注册与使用

### 1. 注册 marker

在 `pytest.ini` 中注册自定义 marker，避免 `PytestUnknownMarkWarning`：

```ini
[pytest]
markers =
    android: Android平台测试
    ios: iOS平台测试
    smoke: 冒烟测试
    regression: 回归测试
    critical: 关键用例
```

**不注册也能用**，但 pytest 会输出警告。CI 日志里几百行警告，真正的错误就被淹没了。

### 2. 应用 marker

在测试用例或测试类上加 marker：

```python
@pytest.mark.smoke      # 冒烟测试
@pytest.mark.android    # Android平台
def test_login_success(driver):
    """正常登录——冒烟+Android"""
    ...


@pytest.mark.regression  # 回归测试
@pytest.mark.android
def test_login_with_wrong_password(self, driver):
    """错误密码登录——回归+Android"""
    ...


@pytest.mark.smoke
@pytest.mark.ios
def test_login_success_ios(self, driver):
    """正常登录iOS版——冒烟+iOS"""
    ...
```

**marker 可以叠加**：一个用例可以同时有多个 marker。

**类级别的 marker 对类中所有方法生效**：

```python
@pytest.mark.android  # 类级别marker，类中所有方法都是Android测试
class TestLoginAndroid:
    def test_login_success(self, driver):
        ...
    
    def test_login_with_wrong_password(self, driver):
        ...
```

### 3. 命令行筛选

用 `-m` 参数筛选 marker：

```bash
# 只跑冒烟测试
pytest -m smoke -v

# 只跑Android平台的测试
pytest -m android -v

# 只跑Android平台的冒烟测试（and 表示同时满足）
pytest -m "smoke and android" -v

# 跑冒烟测试，但排除iOS（not 表示排除）
pytest -m "smoke and not ios" -v

# 跑冒烟或回归测试（or 表示满足任一即可）
pytest -m "smoke or regression" -v

# 用括号分组
pytest -m "(smoke or critical) and android" -v
```

**marker 表达式的语法**：
- `and`：同时满足
- `or`：满足任一
- `not`：排除
- `()`：分组

### 4. skip — 无条件跳过

`@pytest.mark.skip` 让测试用例不被执行：

```python
@pytest.mark.skip(reason="iOS平台暂不支持此功能")
def test_android_only_feature(self, driver):
    """这个用例不会被执行"""
    ...
```

**适用场景**：
- 某个功能还没实现，先跳过
- 某个平台不支持，跳过
- 某个用例已知有问题，临时跳过

### 5. skipif — 条件跳过

`@pytest.mark.skipif` 在满足条件时跳过：

```python
import sys

@pytest.mark.skipif(sys.platform != "darwin", reason="只在macOS上运行")
def test_ios_build():
    """iOS构建测试——只在macOS上执行"""
    ...


import os

@pytest.mark.skipif(
    os.getenv("RUN_SLOW_TESTS") != "1",
    reason="未设置RUN_SLOW_TESTS=1，跳过慢测试"
)
def test_full_regression():
    """全量回归测试——需要显式开启"""
    ...
```

**适用场景**：
- 平台相关测试（iOS 测试只在 macOS 上跑）
- 慢测试（默认跳过，CI 夜间全量跑时开启）
- 依赖外部资源的测试（网络、数据库不可用时跳过）

### 6. xfail — 预期失败

`@pytest.mark.xfail` 标记"预期会失败"的用例。失败了不算错，成功了反而提醒你"这个 bug 可能已经修了"。

```python
@pytest.mark.xfail(reason="已知bug：修改手机号接口偶发500错误")
def test_change_phone_number(self, api_client):
    """这个用例失败了不算错"""
    response = api_client.post("/api/user/mobile/change/step1", json_data={
        "areaCode": "+63",
        "mobile": "9123456789"
    })
    assert response.status_code == 200
```

**xfail vs skip 的区别**：

| 特性 | skip | xfail |
|------|------|-------|
| 执行 | 不执行 | 执行 |
| 失败 | 显示为 skipped | 显示为 xfailed（不算失败） |
| 成功 | 显示为 skipped | 显示为 xpassed（提醒你） |
| 适用 | 确定跑不了 | 知道会失败但想看看修好没 |

**xfail 的实际价值**：你有一个已知 bug 导致测试失败。用 skip 跳过的话，bug 修好了你也不知道。用 xfail 的话，bug 修好后测试会通过（显示为 xpassed），你就知道可以移除 xfail 标记了。

---

## 实战案例

以"跨平台测试策略"为场景，展示 marker、skip、skipif 的组合使用。

**场景描述**：某移动App同时支持 Android 和 iOS。测试用例分为三类：
1. 双平台通用用例（两个平台都要跑）
2. Android 专属用例（只在 Android 上跑）
3. iOS 专属用例（只在 iOS 上跑）

```python
import pytest
import os


@allure.epic("移动端UI自动化测试")
class TestLoginCrossPlatform:
    """跨平台登录测试"""
    
    @allure.feature("登录功能")
    @pytest.mark.smoke
    @pytest.mark.android
    @pytest.mark.ios
    def test_login_success(self, driver):
        """正常登录——双平台通用冒烟测试"""
        login_page = LoginPage(driver)
        login_page.login("test_user", "test_password")
        assert login_page.is_on_home_page()
    
    @allure.feature("登录功能")
    @pytest.mark.regression
    @pytest.mark.android
    def test_android_fingerprint_login(self, driver):
        """Android指纹登录——Android专属"""
        # Android 专属功能
        ...
    
    @allure.feature("登录功能")
    @pytest.mark.regression
    @pytest.mark.ios
    @pytest.mark.skipif(
        os.getenv("PLATFORM") != "ios",
        reason="只在iOS平台上运行"
    )
    def test_ios_faceid_login(self, driver):
        """iOS面容ID登录——iOS专属"""
        # iOS 专属功能
        ...
    
    @allure.feature("登录功能")
    @pytest.mark.regression
    @pytest.mark.android
    @pytest.mark.xfail(reason="已知bug：Android 11上返回键偶发无响应")
    def test_android_back_button(self, driver):
        """Android返回键测试——已知偶发失败"""
        login_page = LoginPage(driver)
        login_page.press_back()
        assert login_page.is_on_previous_page()
```

**运行策略**：

```bash
# CI 代码提交：跑双平台通用冒烟（测试同时带 android + ios 标记）
pytest -m "smoke and android and ios" -v        # 跑双平台通用冒烟
pytest -m "smoke and android" -v                # 跑Android冒烟（含通用用例）
pytest -m "smoke and ios" -v                    # 跑iOS冒烟（含通用用例）

# 每天夜间：跑全量回归
pytest -m regression -v

# 发版前：跑全量 + 关键用例
pytest -m "regression or critical" -v
```

---

## 注意事项和常见坑

- **marker 表达式中的引号**：`-m "smoke and android"` 需要加引号，因为 shell 会把 `and` 当作命令分隔符。不加引号会报错。
- **类级别 marker 会被方法级别覆盖**。如果类标记了 `@pytest.mark.android`，但某个方法标记了 `@pytest.mark.ios`，这个方法会被同时标记为 android 和 ios。
- **skip 和 xfail 不要滥用**。跳过的测试越多，你的测试覆盖率越低。skip 只用于"确实跑不了"的场景，xfail 只用于"已知bug且正在修复"的场景。
- **xfail 的用例仍然会执行**。它不是 skip，只是"失败了不算错"。如果 xfail 的用例执行很慢，考虑用 skipif 代替。
- **不注册 marker 的警告在 CI 中很烦人**。`--strict-markers` 会让未注册的 marker 直接报错而不是警告，建议在 CI 中开启。

---

## 实战建议：marker 使用 checklist

在实际项目中用 marker，建议按这个顺序来：

- [ ] **第一步：在 `pytest.ini` 中注册所有 marker**，避免 CI 日志被警告淹没
- [ ] **第二步：至少定义 `smoke` 和 `regression` 两个标记**，这是 CI 分级的基础
- [ ] **第三步：按平台打标记**（`android` / `ios`），跨平台项目必备
- [ ] **第四步：关键用例标 `critical`**，发版前只跑 `critical or smoke`
- [ ] **第五步：CI 中开启 `--strict-markers`**，拼错 marker 名称直接报错
- [ ] **第六步：skip 只用于"确实跑不了"的场景**，xfail 只用于"已知 bug 正在修"的场景
- [ ] **第七步：定期清理不再需要的 marker**，marker 太多反而失去分类意义

> marker 的本质是"测试用例的分类系统"。没有 marker，你的测试就只有"全量跑"和"不跑"两个状态。有了 marker，你可以在"冒烟5分钟"和"全量2小时"之间灵活切换。
