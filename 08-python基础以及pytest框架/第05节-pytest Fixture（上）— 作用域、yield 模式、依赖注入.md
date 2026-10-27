# 05-pytest Fixture（上）— 作用域、yield 模式、依赖注入

> 对应代码：`test/conftest.py`（fixture定义部分）
>

---

## 概念讲解

unittest 的 `setUp` 和 `tearDown` 有个致命问题：**它们只能在一个测试类内部用，跨类复用很麻烦**。

假设你有10个测试类都需要 WebDriver，unittest 的做法是每个类都写一个 `setUp` 方法初始化 driver。10个类 = 10份重复代码。

**pytest 的 fixture 解决了这个问题**：fixture 定义一次，任何测试函数都能用。而且可以控制作用域（每个用例创建一次？还是整个测试会话只创建一次？），可以依赖其他 fixture，可以自动注入。

**fixture 是 pytest 最核心的特性。不理解 fixture，就不算真正用过 pytest。**

---

## Fixture作用域与使用要点

### 1. 四种作用域

fixture 的 `scope` 参数决定了它被调用多少次：

| scope | 调用时机 | 适用场景 |
|-------|---------|---------|
| `function`（默认） | 每个测试函数调用一次 | 测试数据、轻量级资源 |
| `class` | 每个测试类调用一次 | 类级别的共享资源 |
| `module` | 每个测试文件调用一次 | 文件级别的共享资源 |
| `session` | 整个测试会话调用一次 | 数据库连接、WebDriver、API客户端 |

**选择原则**：能大就大，能小就小。初始化慢的资源用 `session`（只初始化一次），需要隔离的资源用 `function`（每个用例独立）。

### 2. yield 模式 — setup → yield → teardown

fixture 用 `yield` 实现"先准备、后清理"的生命周期：

```python
@pytest.fixture(scope="session")
def driver_setup(request):
    """
    驱动初始化fixture（会话级别）
    在整个测试会话中只初始化一次
    """
    # ===== setup 阶段：测试开始前执行 =====
    logger.info("开始初始化移动端驱动")
    
    platform = "android"  # 从配置读取
    base_driver = create_driver(platform=platform)
    driver = base_driver.get_driver()
    
    logger.info(f"驱动初始化成功 - 平台: {platform}")
    
    # ===== yield：把资源传给测试函数 =====
    yield driver
    
    # ===== teardown 阶段：测试结束后执行 =====
    try:
        logger.info("开始关闭驱动")
        driver.quit()
        logger.info("驱动关闭成功")
    except Exception as e:
        logger.error(f"驱动关闭异常: {str(e)}")
```

**执行流程**：
1. pytest 发现测试函数需要 `driver_setup` 参数
2. 执行 yield 之前的代码（setup）
3. 把 yield 的值传给测试函数
4. 测试函数执行
5. 执行 yield 之后的代码（teardown）

**关键特性**：即使测试函数抛异常，yield 之后的 teardown 代码也会执行。这保证了资源一定会被清理。

### 3. fixture 依赖链

fixture 可以依赖其他 fixture，形成依赖链：

```python
@pytest.fixture(scope="session")
def driver_setup(request):
    """会话级别的driver"""
    driver = create_driver()
    yield driver
    driver.quit()


@pytest.fixture(scope="function")
def driver(request, driver_setup):
    """
    函数级别的driver fixture
    依赖 driver_setup，每个测试用例独立执行
    """
    driver = driver_setup  # 从父fixture获取driver
    
    yield driver
    
    # 测试执行后的清理
    # 注意：rep_call 属性需要 conftest.py 中注册 pytest_runtest_makereport hook
    # （详见第07节），此处为示例代码
    if request.node.rep_call.failed:  # 如果测试失败了
        take_screenshot(driver, f"failure_{request.node.name}")
```

**这里 `driver` 依赖 `driver_setup`**。pytest 会自动解析依赖关系，先执行 `driver_setup`，再执行 `driver`。

### 4. request 对象 — 获取测试上下文

fixture 函数可以接收 `request` 参数，获取当前测试的上下文信息：

```python
@pytest.fixture(scope="function")
def driver(request, driver_setup):
    driver = driver_setup
    yield driver
    
    # request.node 是当前测试用例的信息
    # 注意：rep_call 属性需要 conftest.py 中注册 pytest_runtest_makereport hook
    # （详见第07节），此处为示例代码
    if request.node.rep_call.failed:
        # 测试失败了，截图
        error_message = request.node.rep_call.longreprtext
        take_screenshot(driver, f"failure_{request.node.name}")
        
        # 记录错误信息
        logger.error(f"测试 {request.node.name} 失败: {error_message}")
```

**常用的 request 属性**：
- `request.node.name`：测试函数名
- `request.node.rep_call.failed`：测试是否失败
- `request.node.rep_call.longreprtext`：失败的详细traceback
- `request.fspath`：测试文件路径
- `request.instance`：测试类实例（如果是类中的方法）

### 5. autouse — 自动注入的 fixture

加了 `autouse=True` 的 fixture 不需要测试函数显式声明参数，pytest 会自动执行：

```python
@pytest.fixture(autouse=True)
def log_test_info(request):
    """自动记录测试用例信息的fixture"""
    logger.info(f"开始执行测试用例: {request.node.name}")
    yield
    logger.info(f"测试用例执行完成: {request.node.name}")
```

**每个测试用例执行前后都会自动打印日志**，不需要在每个测试函数里加 `log_test_info` 参数。

---

## 实战案例

从真实项目中提取三个 fixture，展示不同作用域和不同用途。

### 案例1：session 级别的 API 客户端

```python
@pytest.fixture(scope="session")
def api_client(request):
    """
    API客户端fixture（会话级别）
    整个测试会话只创建一个API客户端实例
    """
    base_url = "https://api.example.com"  # 从配置读取
    timeout = 30
    
    logger.info("初始化API客户端")
    logger.info(f"API Base URL: {base_url}")
    
    # 创建API客户端
    client = BaseAPI(base_url=base_url, timeout=timeout, verify_ssl=False)
    
    # 如果配置了认证token，自动设置
    api_token = "your_token_here"
    if api_token:
        client.set_auth("bearer", api_token)
    
    yield client
```

**为什么用 session 级别**：API 客户端是无状态的（只保存 base_url 和 headers），整个测试会话复用同一个实例，不需要每次创建。

### 案例2：function 级别的 driver + 失败截图

```python
@pytest.fixture(scope="function")
def driver(request, driver_setup):
    """
    函数级别的driver fixture
    每个测试用例都会执行一次，便于用例间的隔离
    """
    driver = driver_setup
    yield driver
    
    # 测试执行后的清理——失败时自动截图
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        screenshot_path = take_screenshot(driver, f"failure_{request.node.name}")
        
        # 收集错误信息
        error_message = ""
        if hasattr(request.node.rep_call, 'longreprtext'):
            error_message = request.node.rep_call.longreprtext
        
        logger.error(f"测试 {request.node.name} 失败，截图: {screenshot_path}")
        logger.error(f"错误信息: {error_message[:500]}")
```

**为什么用 function 级别**：每个测试用例需要独立的执行环境。用例A操作了页面，用例B不应该受A的影响。

### 案例3：autouse 级别的日志记录

```python
@pytest.fixture(autouse=True)
def log_test_info(request):
    """自动记录测试用例信息的fixture"""
    logger.info("")
    logger.info(f"开始执行测试用例: {request.node.name}")
    logger.info(f"测试用例文件: {request.fspath}")
    yield
    logger.info(f"测试用例执行完成: {request.node.name}")
    logger.info("=" * 50)
```

**autouse 的好处**：不需要在每个测试函数里加参数，所有测试自动记录日志。

---

## 注意事项和常见坑

- **session 级别 fixture 在并发执行时有陷阱**。如果用 `pytest-xdist` 并行执行，每个 worker 进程都会独立初始化 session 级 fixture。这不是 bug，但可能导致资源重复创建。
- **yield 之后的代码即使测试失败也会执行**。这是特性不是 bug。如果你的 teardown 代码可能抛异常，用 `try/except` 包裹，不要让 teardown 的异常掩盖测试本身的失败。
- **autouse fixture 的滥用会导致隐式依赖**。测试函数没有声明某个 fixture 参数，但 fixture 自动执行了。出了问题排查时很难发现"原来有个 fixture 在后台运行"。autouse 只用于真正全局的逻辑（日志、报告）。
- **fixture 名称冲突时，近的优先**。`conftest.py` 中的 fixture 优先级低于测试文件中的 fixture。如果两个地方定义了同名 fixture，测试文件中的会覆盖 conftest 中的。
- **fixture 不要返回 None**。yield 后面没有值等价于 yield None，测试函数收到 None 后大概率会报错。保证 yield 后面有明确的返回值。

---

## 总结与思考

> fixture 的本质是"依赖注入"。测试函数声明需要什么，pytest 就给它什么。你不需要在测试函数里写 setup 代码，不需要手动清理资源——fixture 帮你搞定。

**思考题**：你在项目中见过最"复杂"的 fixture 依赖链有多深？fixture 套 fixture 有没有上限？


---

## 面试题模块

### 1. 作用域选择

**Q1：`session`、`module`、`class`、`function` 四种 scope 怎么选？**

A：原则是"能大就大，能小就小"。初始化慢的资源（数据库连接、WebDriver、API Token）用 `session`（只初始化一次）。需要隔离的资源（测试数据、临时文件）用 `function`（每个用例独立）。`module` 和 `class` 用得少，一般用于文件级别或类级别的共享资源。

### 2. yield 模式

**Q2：fixture 中 `yield` 之后的代码即使测试失败也会执行吗？为什么？**

A：会。这是 pytest 的设计保证——`yield` 之后的 teardown 代码一定会执行，即使测试函数抛异常。这保证了资源一定会被清理。但 teardown 代码本身如果抛异常，会打印警告而不影响测试结果。

### 3. 依赖注入

**Q3：fixture 之间可以依赖吗？如果有 A → B → C 的依赖链，执行顺序是什么？**

A：可以依赖。执行顺序是：C 的 setup → B 的 setup → A 的 setup → 测试函数 → A 的 teardown → B 的 teardown → C 的 teardown。pytest 自动解析依赖关系，按深度优先顺序执行。

---

