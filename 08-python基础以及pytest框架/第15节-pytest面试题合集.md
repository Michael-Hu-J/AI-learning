# 15-pytest面试题合集

面试时问 pytest，问的从来不是 API 记忆，而是你有没有踩过坑。

本文整理了本系列 22 节中的全部面试题（共 47 道），按知识点分类编排。

**使用方式**：先自己回答，再对照参考答案。能答对 70% 以上，说明 pytest 基础扎实。

---

## 一、Python基础（第01-02节）

### 1. 字符串与字典

**Q1：`dict.get(key, default)` 和 `dict[key]` 的区别是什么？测试代码中应该用哪个？**

A：`dict[key]` 在键不存在时抛 `KeyError` 异常，`dict.get(key, default)` 返回默认值而不抛异常。测试代码中优先用 `.get()`，因为测试数据经常有可选字段，用 `[]` 取值在字段缺失时会直接报错，用 `.get()` 更健壮。

### 2. 循环与重试

**Q2：写一个带重试机制的循环，最多重试3次，每次间隔2秒。**

```python
import time

max_attempts = 3
delay = 2.0
for attempt in range(max_attempts):
    try:
        result = do_something_unstable()
        break
    except Exception as e:
        if attempt < max_attempts - 1:
            print(f"第{attempt + 1}次失败，{delay}秒后重试: {e}")
            time.sleep(delay)
        else:
            raise
```

### 3. 函数封装

**Q3：什么情况下应该把代码封装成函数？判断标准是什么？**

A：同一个操作写了两次以上就该封装。测试代码中，重复的 API 请求、元素定位、数据构造都应该封装成函数。封装的好处是统一处理、减少重复、方便修改。

### 4. 类与继承

**Q4：Page Object 模式的核心思想是什么？为什么测试项目需要它？**

A：Page Object 的核心思想是"每个页面是一个类，类中包含该页面的元素定位和操作方法"。好处是：元素定位变了只改一个地方，操作流程变了只改一个方法，验证逻辑变了只改测试用例。没有 Page Object，元素定位散落在 20 个测试函数中，页面改版后改 20 个文件。

### 5. 装饰器

**Q5：`@pytest.fixture` 和 `@pytest.mark.smoke` 是装饰器，装饰器的本质是什么？**

A：装饰器的本质是"在不修改原函数代码的前提下，给函数增加额外功能"。`@pytest.fixture` 给函数增加了"可以作为测试依赖注入"的功能，`@pytest.mark.smoke` 给函数增加了"可以被 `-m smoke` 筛选"的功能。底层实现是"函数作为参数传入，返回一个新函数"。

### 6. 异常处理

**Q6：pytest 的 fixture 中，`yield` 之后的代码即使测试失败也会执行吗？**

A：会。这是 pytest 的设计保证——`yield` 之后的 teardown 代码一定会执行，即使测试函数抛异常。这保证了资源（如 WebDriver、数据库连接）一定会被清理。但 teardown 代码本身如果抛异常，会打印警告而不影响测试结果。

---

## 二、pytest入门（第03节）

### 7. 测试发现规则

**Q7：pytest 怎么知道哪些文件是测试文件？文件名、类名、函数名的默认规则是什么？**

A：三个默认规则：文件 `test_*.py`、类 `Test*`（不能有 `__init__`）、函数 `test_*`。这三个规则可以在 `pytest.ini` 中修改，但不建议——默认规则是社区约定，改了自己爽，别人接手时一脸懵。

### 8. 命令行参数

**Q8：`pytest -v -s` 和 `pytest -x --tb=short` 分别适合什么场景？**

A：`-v -s` 适合开发调试——显示详细信息 + 显示 print 输出，方便边写边看。`-x --tb=short` 适合 CI 环境——第一个失败就停 + 简短 traceback，快速发现问题。

### 9. pytest.ini

**Q9：`pytest.ini` 放在哪生效？`testpaths = .` 有什么风险？**

A：pytest 从当前工作目录起向父目录逐级查找，最先找到的那份配置生效。团队习惯上放在仓库根目录。`testpaths = .` 会扫描整个项目（包括 `node_modules`、`.git` 等目录），拖慢测试发现速度。应该明确指定 `tests` 或 `testcases`。

---

## 三、pytest断言体系（第04节）

### 10. 断言重写

**Q10：pytest 的 assert 和 Python 原生 assert 失败时的表现有什么区别？**

A：Python 原生 assert 失败只输出 `AssertionError`（就五个字）。pytest 会输出详细的 diff 信息——哪个元素不同、完整列表对比。这是因为 pytest 在字节码层面重写了 assert 语句（assertion rewriting）。

### 11. 断言信息

**Q11：`assert page.is_on_home_page()` 和 `assert page.is_on_home_page(), "登录应该成功但跳转失败"` 有什么区别？**

A：前者失败时只告诉你"断言失败了"，后者失败时直接告诉你"预期是什么、实际是什么"。在 CI 日志中，后者能让你 3 秒定位问题，前者需要翻日志、截图、加 print。

### 12. 复杂断言

**Q12：怎么断言两个字典相等但忽略某些字段？**

A：pytest 没有内置的"忽略字段"断言。常用做法是：
1. 手动比较需要的字段：`assert data["code"] == 0 and data["message"] == "success"`
2. 用第三方库：`pytest-assume` 支持多个独立断言
3. 用 `dict.items()` 比较：`assert expected.items() <= actual.items()`（检查 expected 的所有键值对都在 actual 中）

---

## 四、pytest Fixture（第05-06节）

### 13. 作用域选择

**Q13：`session`、`module`、`class`、`function` 四种 scope 怎么选？**

A：原则是"能大就大，能小就小"。初始化慢的资源（数据库连接、WebDriver、API Token）用 `session`（只初始化一次）。需要隔离的资源（测试数据、临时文件）用 `function`（每个用例独立）。`module` 和 `class` 用得少，一般用于文件级别或类级别的共享资源。

### 14. yield 模式

**Q14：fixture 中 `yield` 之后的代码即使测试失败也会执行吗？为什么？**

A：会。这是 pytest 的设计保证——`yield` 之后的 teardown 代码一定会执行，即使测试函数抛异常。这保证了资源一定会被清理。但 teardown 代码本身如果抛异常，会打印警告而不影响测试结果。

### 15. 依赖注入

**Q15：fixture 之间可以依赖吗？如果有 A → B → C 的依赖链，执行顺序是什么？**

A：可以依赖。执行顺序是：C 的 setup → B 的 setup → A 的 setup → 测试函数 → A 的 teardown → B 的 teardown → C 的 teardown。pytest 自动解析依赖关系，按深度优先顺序执行。

### 16. tmp_path

**Q16：`tmp_path` 和 `tmpdir` 的区别是什么？应该用哪个？**

A：`tmp_path` 返回 `pathlib.Path` 对象（现代 Python 推荐），`tmpdir` 返回 py.path.local 对象（旧版兼容）。pytest 官方推荐用 `tmp_path`，因为 `pathlib` 是 Python 3 的标准路径操作方式。两者功能相同——都是唯一的临时目录，测试结束后自动删除。

### 17. capsys

**Q17：怎么测试一个函数是否正确输出了 print 内容？**

A：用 `capsys` fixture：
```python
def test_print_output(capsys):
    print("Hello, World!")
    captured = capsys.readouterr()
    assert "Hello, World!" in captured.out
```
`capsys.readouterr()` 返回 `CaptureResult(out=..., err=...)`，可以分别检查 stdout 和 stderr。

### 18. monkeypatch

**Q18：`monkeypatch` 能做什么？举一个测试环境变量的例子。**

A：`monkeypatch` 可以在测试期间临时修改环境变量、模块属性、字典值等。测试结束后自动恢复。
```python
def test_with_env_var(monkeypatch):
    monkeypatch.setenv("API_URL", "http://test.example.com")
    import os
    assert os.getenv("API_URL") == "http://test.example.com"
# 测试结束后，环境变量自动恢复
```

---

## 五、pytest Hook（第07节）

### 19. Hook 机制

**Q19：pytest Hook 是什么？和 Fixture 有什么区别？**

A：Hook 是 pytest 暴露的"生命周期钩子"，你可以在测试生命周期的任何节点插入自定义逻辑。Fixture 是依赖注入（测试函数需要什么，pytest 就给它什么），Hook 是事件监听（pytest 执行到某个阶段，自动调用你的函数）。两者都靠 conftest.py 实现，但用途不同。

### 20. 常用 Hook

**Q20：`pytest_configure`、`pytest_runtest_makereport`、`pytest_sessionfinish` 分别什么时候执行？**

A：
- `pytest_configure`：pytest 启动后、收集测试用例之前（适合做全局配置）
- `pytest_runtest_makereport`：每个测试用例的 setup/call/teardown 阶段之后（适合让 fixture 判断测试是否失败）
- `pytest_sessionfinish`：所有测试用例执行完成后（适合生成最终报告）

### 21. tryfirst / trylast

**Q21：当多个 conftest.py 都注册了同一个 Hook 时，怎么控制执行顺序？**

A：用 `@pytest.hookimpl(tryfirst=True)` 或 `@pytest.hookimpl(trylast=True)`。tryfirst 的 Hook 一定在 trylast 的 Hook 之前执行。这在"失败截图"场景中很常见——`makereport` Hook 必须先执行（设置 `rep_call`），fixture 才能读取判断是否失败。

---

## 六、pytest 参数化（第08节）

### 22. parametrize 基本用法

**Q22：`@pytest.mark.parametrize` 的作用是什么？一组参数 = 一个测试用例吗？**

A：`parametrize` 把一个测试函数"展开"成多个测试用例，每组参数对应一个独立的测试用例。例如 3 组参数 = 3 个用例，pytest 会分别执行、分别报告结果。失败时能精确定位到是哪组参数失败。

### 23. 外部数据源

**Q23：怎么从 YAML/JSON 文件加载测试数据并参数化？**

A：在装饰器中直接调用数据加载函数：
```python
@pytest.mark.parametrize("test_data", DataDriver.load_data("testcases/data/login_users.yaml"))
def test_login(test_data):
    username = test_data["username"]
    ...
```
`DataDriver.load_data()` 返回字典列表，pytest 会为每个字典生成一个测试用例。

### 24. 参数化陷阱

**Q24：参数化测试中，如果某组数据应该跳过，怎么实现？**

A：在测试函数内部用 `pytest.skip()`：
```python
def test_login(test_data):
    if test_data.get("skip"):
        pytest.skip("该用例标记为跳过")
    ...
```
或者用 `pytest.mark.skipif` 装饰器配合条件判断。

---

## 七、pytest Mark 标记（第09节）

### 25. Mark 注册

**Q25：不注册 marker 能用吗？为什么要注册？**

A：能用，但 pytest 会输出 `PytestUnknownMarkWarning` 警告。CI 日志中几百行警告，真正的错误就被淹没了。注册 marker 后，加上 `--strict-markers`，拼错 marker 名称会直接报错而不是静默忽略。

### 26. 筛选策略

**Q26：CI 环境中，代码提交后、每天凌晨、发版前分别应该跑哪些测试？**

A：
- 代码提交后：`pytest -m smoke`（冒烟测试，5 分钟）
- 每天凌晨：`pytest`（全量回归测试，2 小时）
- 发版前：`pytest -m "critical or smoke"`（关键用例 + 冒烟，3 小时）

### 27. skip vs xfail

**Q27：`@pytest.mark.skip` 和 `@pytest.mark.xfail` 的区别是什么？**

A：`skip` 是"这个用例不跑了"（如平台不兼容、依赖未安装），`xfail` 是"这个用例我知道会挂"（如已知 bug 还未修复）。`skip` 不计入失败，`xfail` 挂了不计入失败但过了会报 `XPASS`（意外通过，说明 bug 可能修了）。

---

## 八、Allure 报告（第10节）

### 28. 三级分类

**Q28：Allure 的 Epic → Feature → Story 三级分类怎么设计？粒度怎么把握？**

A：Epic 是项目级别（如"移动端 UI 自动化测试"），Feature 是功能模块（如"登录功能"），Story 是具体场景（如"用户登录"）。分类粒度建议：一个项目一个 Epic，每个功能模块一个 Feature，每个业务流程一个 Story。不要过度细分——超过 3 层就失去了分类的意义。

### 29. 测试步骤

**Q29：`allure.step()` 的嵌套不要超过几层？为什么？**

A：不要超过 3 层。太深的嵌套在报告中显示不清晰。每个 step 应该是一个有意义的操作（如"输入用户名"、"点击登录按钮"），而不是技术细节（如"调用 find_element"）。

### 30. 报告生成

**Q30：`allure serve` 和 `allure generate` 的区别是什么？CI 环境应该用哪个？**

A：`allure serve` 启动临时 HTTP 服务，关闭后报告消失（适合开发调试）。`allure generate` 生成静态 HTML 文件，可以部署到 Web 服务器（适合 CI/CD）。CI 环境用 `allure generate`，生成的报告可以归档、对比历史版本。

---

## 九、pytest 并行执行（第11节）

### 31. 并行策略

**Q31：`pytest -n 4` 和 `pytest -n auto` 的区别是什么？worker 数量怎么选？**

A：`-n auto` 自动等于 CPU 核心数，适合 CPU 密集型测试。`-n 4` 固定 4 个 worker，适合 I/O 密集型测试（如网络请求、UI 操作），因为瓶颈不在 CPU。worker 数量不要超过 CPU 核心数 × 2，否则上下文切换开销会抵消并行收益。

### 32. 共享状态陷阱

**Q32：并行执行时，全局变量会共享吗？怎么避免测试之间互相干扰？**

A：每个 worker 是独立进程，全局变量不共享。但共享资源（如数据库、文件、WebDriver）会互相干扰。避免方法：
1. 每个测试用独立的数据（如唯一用户名）
2. 用 `session` 级别的 Fixture 管理共享资源
3. 避免在测试中修改全局状态

### 33. Allure 报告并行

**Q33：并行执行时 Allure 报告怎么生成？会冲突吗？**

A：会冲突。pytest-xdist 并行时，每个 worker 会同时写 allure-results 目录。解决方案：
1. 用 `--dist=loadfile` 模式（按文件分配 worker）
2. 每个 worker 写独立的 allure-results 目录，最后合并
3. 用 `allure-pytest` 的并行兼容模式

---

## 十、测试项目结构设计（第12节）

### 34. 目录结构

**Q34：一个标准的 pytest 项目应该有哪些目录？每个目录的职责是什么？**

A：
- `base/`：基础操作封装（点击、输入、HTTP 请求）
- `pages/`：页面级操作（登录、注册等业务流程）
- `api/`：API 封装（HTTP 请求的通用方法）
- `core/`：核心引擎（数据驱动、测试执行）
- `tests/`：测试用例（具体的测试逻辑）
- `testcases/`：测试数据（YAML、数据文件）
- `utils/`：工具类（日志、截图、报告）
- `reports/`：报告输出

### 35. Page Object 模式

**Q35：Page Object 模式的好处是什么？过度封装的风险是什么？**

A：好处是元素定位变了只改一个地方，操作流程变了只改一个方法。过度封装的风险是"为了封装而封装"——3 层足够（base → pages → tests），超过 4 层就是过度设计。

### 36. conftest.py 放置

**Q36：`conftest.py` 可以放在多个层级吗？同名 fixture 哪个优先？**

A：可以放在多个层级。根目录的 `conftest.py` 所有测试都能用，子目录的只对同级和子目录生效。同名 fixture：测试文件中的覆盖 conftest 中的，子目录的覆盖根目录的。但 `conftest.py` 不要放业务逻辑，它只负责 fixture 和 hook。

---

## 十一、pytest 生态工具链（第13节）

### 37. 覆盖率统计

**Q37：`pytest-cov` 的覆盖率 100% 意味着什么？是不是越高越好？**

A：覆盖率 100% 意味着所有代码行都被测试执行过。但不是越高越好——有些代码（如 `if DEBUG:` 分支、异常处理路径）可能不需要测试。更合理的做法是设置覆盖率门槛（如 `--cov-fail-under=80`），保证核心代码被覆盖。

### 38. 超时控制

**Q38：怎么防止一个测试用例无限期挂起？**

A：用 `pytest-timeout` 插件：
```bash
pytest --timeout=30  # 每个用例最多 30 秒
```
或者在代码中设置：`@pytest.mark.timeout(30)`。超时后 pytest 会强制终止该用例并标记为失败。

### 39. 失败重试

**Q39：偶发性失败的测试用例怎么处理？pytest 有重试机制吗？**

A：用 `pytest-rerunfailures` 插件：
```bash
pytest --reruns 3  # 失败后重试 3 次
```
但重试不是银弹——偶发性失败的根本原因通常是资源竞争、网络不稳定、等待时间不足，应该优先修复根本原因。

---

## 十二、综合实战（第14节）

### 40. Fixture 相关

**Q40：pytest 中 `scope="session"` 和 `scope="function"` 的区别是什么？什么情况下应该用 session 级别？**

A：`session` 级别在整个测试会话中只执行一次，`function` 级别每个测试函数都执行一次。初始化慢的资源（如数据库连接、API Token、WebDriver）应该用 `session` 级别，避免重复初始化。需要隔离的资源（如测试数据、临时文件）应该用 `function` 级别。

**Q41：Fixture 之间可以依赖吗？如果有 A → B → C 的依赖链，执行顺序是什么？**

A：可以依赖。执行顺序是 C → B → A 的 setup 顺序（从最底层开始），然后是测试函数，最后是 A → B → C 的 teardown 顺序（从最外层开始）。pytest 自动解析依赖关系。

### 41. 参数化相关

**Q42：`@pytest.mark.parametrize` 和 `@pytest.mark.parametrize` 嵌套使用会发生什么？**

A：会生成笛卡尔积。如果第一个 parametrize 有 3 组参数，第二个有 2 组，最终会生成 3×2=6 个测试用例。但嵌套 parametrize 会让用例名称变得很长，建议用单个 parametrize + 元组代替。

**Q43：参数化测试失败时，怎么知道是哪组参数失败了？**

A：pytest 会在失败信息中显示参数值。例如 `test_login[user001-WrongPass-fail] FAILED` 表示用户名 `user001`、密码 `WrongPass`、预期 `fail` 的那组参数失败了。

### 42. 断言相关

**Q44：pytest 的 assert 和 Python 原生 assert 有什么区别？**

A：pytest 在字节码层面重写了 assert 语句。Python 原生 assert 失败时只输出 `AssertionError`，pytest 会输出详细的 diff 信息，包括两个对象的逐字段对比。这就是"assert 重写"机制。

### 43. 项目架构相关

**Q45：你的测试项目是怎么分层的？Page Object 模式在 API 测试中怎么应用？**

A：典型的分层是 `base/`（基础操作）→ `pages/` 或 `api/`（页面/API 封装）→ `tests/`（测试用例）。API 测试中，`BaseAPI` 封装 HTTP 请求方法，具体的 API 测试类继承或直接使用。测试用例只关注"验证什么"，不关注"怎么请求"。

### 44. 实战场景

**Q46：如果 500 个测试用例串行执行需要 2 小时，你怎么优化？**

A：分三步：
1. 先用 `pytest --durations=0 -v` 找出最慢的 20% 用例
2. 用 `pytest-xdist` 并行执行：`pytest -n 8`，理论上可以缩短到 15 分钟
3. 用 Mark 分级：CI 提交时只跑 `pytest -m smoke`（冒烟测试，5 分钟），每天凌晨跑全量回归

**Q47：测试用例失败了，你怎么判断是代码 bug 还是测试用例本身的问题？**

A：三步排查：
1. 看断言信息：pytest 的 diff 会告诉你预期值和实际值分别是什么
2. 手动复现：用 Postman/curl 手动调用同一个 API，看返回是否一致
3. 看日志：conftest.py 中的 Hook 会记录每个用例的执行日志，包括请求和响应

---

## 面试答题技巧

47 道题都过了一遍，最后分享几个面试实战经验：

**1. 别背答案，讲场景**

面试官问 `fixture scope 怎么选`，不要背诵"session 一次、function 每次"。换成：
> "我们项目里 WebDriver 初始化要 30 秒，16 个用例如果每个都初始化就是 8 分钟。我把 driver 设成 session 级别，整个会话只启动一次，省了 7 分多钟。"

**2. 说坑比说 API 有用**

面试官知道 pytest 的 API，他想听的是你踩过的坑：
> "我们并行执行踩过一个坑——全局变量被多个 worker 共享，结果断言随机失败。后来把所有状态都改成 fixture 返回，问题就没了。"

**3. 用数据说话**

> "引入 pytest-xdist 后，500 个用例从 4 小时降到 1 小时，加速比 4 倍。"
> "加了 --timeout=120 后，CI 再也没有因为某个用例卡死而挂一整夜。"

**4. 不会的就说不会，但补充思路**

> "这个 Hook 我确实没用过。但如果要我实现失败截图，我会在 `pytest_runtest_makereport` 里判断测试是否失败，然后调用 driver 截图。"

**5. 自测清单**

| 类别 | 题号 | 掌握程度 |
|------|------|---------|
| Python基础 | Q1-Q6 | □ 熟练 □ 了解 □ 不会 |
| pytest入门 | Q7-Q9 | □ 熟练 □ 了解 □ 不会 |
| 断言体系 | Q10-Q12 | □ 熟练 □ 了解 □ 不会 |
| Fixture | Q13-Q18 | □ 熟练 □ 了解 □ 不会 |
| Hook | Q19-Q21 | □ 熟练 □ 了解 □ 不会 |
| 参数化 | Q22-Q24 | □ 熟练 □ 了解 □ 不会 |
| Mark标记 | Q25-Q27 | □ 熟练 □ 了解 □ 不会 |
| Allure报告 | Q28-Q30 | □ 熟练 □ 了解 □ 不会 |
| 并行执行 | Q31-Q33 | □ 熟练 □ 了解 □ 不会 |
| 项目结构 | Q34-Q36 | □ 熟练 □ 了解 □ 不会 |
| 生态工具 | Q37-Q39 | □ 熟练 □ 了解 □ 不会 |
| 综合实战 | Q40-Q47 | □ 熟练 □ 了解 □ 不会 |

> **评分标准**：
> - 熟练：能不看答案直接回答，且能举例说明
> - 了解：能回答大意，但需要想一下
> - 不会：完全不知道或答错
>
> **目标**：至少 70% 的题目达到"熟练"水平。如果低于 50%，建议重新学习对应章节。
