# 第08节-pytest 集成 — conftest.py 中的 fixture 与 hook

> 配套代码：`配套代码/test/conftest.py`

---

## conftest.py 是干什么的

pytest 有个约定：`conftest.py` 里的东西，对同目录和子目录下的所有测试文件自动生效。你不用写 import，不用到处复制代码，pytest 自己就能找到它。

这就很适合放一些"每个测试用例都可能用到的东西"——比如 Appium 的 driver、API 客户端、各个 hook 回调。简单说，conftest.py 就是测试框架的骨架，测试用例只管写业务逻辑，基础设施的事全交给 conftest 处理。

---

## session 级 driver fixture

Appium driver 初始化一次要十秒起步，100 个用例每个都 new 一个 driver，光启动就半小时。所以 driver 肯定是 session 级别的——整个测试跑下来只创建一次。

```python
@pytest.fixture(scope="session")
def driver_setup(request):
    webdriver, BaseDriver = _get_appium()
    if BaseDriver is None:
        pytest.skip("Appium 未安装，跳过 UI 测试")

    platform = os.getenv("PLATFORM", "android")
    logger.info(f"开始初始化移动端推动 - 平台: {platform}")

    base_driver = BaseDriver(platform=platform)
    driver = base_driver.get_driver()

    def driver_teardown():
        try:
            driver.quit()
            logger.info("推动关闭成功")
        except Exception as e:
            logger.error(f"推动关闭异常: {str(e)}")

    request.addfinalizer(driver_teardown)
    yield driver
```

`scope="session"` 的意思是：pytest 只调一次这个 fixture，所有测试用例共用同一个 driver。

注意那个 `_get_appium()`——它做了延迟导入。如果机器上没装 Appium，不会一启动就挂掉，而是跳过所有 UI 测试。这个在实际项目里很实用，CI 环境里经常只跑非 UI 的测试。

`request.addfinalizer(driver_teardown)` 注册了一个清理函数。不管测试成功还是失败，甚至中间崩了，这个 finalizer 一定会执行。用 `yield` 后面跟代码也能做 teardown，但 finalizer 更可靠——`yield` 后面的代码在 fixture 内部异常时可能被跳过，finalizer 不会。

---

## function 级 driver fixture

session 级 fixture 只初始化一次，但有时候你需要在每个用例执行完做点事——比如截个图。

```python
@pytest.fixture(scope="function")
def driver(request, driver_setup):
    yield driver_setup
```

这个 fixture 直接依赖 `driver_setup`，pytest 会自动解析依赖关系：先执行 session 级的 `driver_setup`，再把这个结果传给 function 级的 `driver`。

看起来好像啥也没干，就是透传了一下。但它给未来留了个口子——如果哪天你想在每个用例结束后截个图、清个缓存、重置 App 到首页，直接在这里加代码就行，不用改测试用例里的任何东西。

---

## API 客户端 fixture

UI 测试经常需要配合 API 做数据准备或结果校验。

```python
@pytest.fixture(scope="session")
def api_client(request):
    from api.base_api import BaseAPI

    base_url = os.getenv("API_BASE_URL", "")
    timeout = int(os.getenv("API_TIMEOUT", "30"))
    client = BaseAPI(base_url=base_url, timeout=timeout)

    api_token = os.getenv("API_TOKEN", "")
    if api_token:
        client.set_auth("bearer", api_token)

    yield client
```

同样是 session 级别，整个测试过程只创建一次。用环境变量来控制 API 地址和 token，测试代码里不硬编码，换环境时改环境变量就行。

---

## hook 收集测试结果

fixture 拿不到测试执行的结果。fixture 执行的时候，测试用例还没跑（setup 阶段），或者已经跑完了（teardown 阶段），但 fixture 自己不知道测试过了还是没过。

hook 可以。

```python
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

这个 hook 做的事情不多：pytest 每执行一次 setup/call/teardown，它就把结果报告挂在 `item` 对象上。比如 `item.rep_call` 就能拿到测试函数执行的结果，里面包含 `failed`/`passed` 状态。

`tryfirst=True` 保证这个 hook 最早执行——其他插件或 fixture 要想读取 `rep_call`，得等它先挂上去。`hookwrapper=True` 的意思是"包一层"：`yield` 之前是 setup 阶段的代码，yield 之后拿到的 `outcome.get_result()` 才是执行结果。

这样 fixture 就能这么用了：

```python
# 在 function 级 driver fixture 的 teardown 里
if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
    # 取个截图
    screenshot_helper.take_screenshot(f"failure_{request.node.name}")
```

也就是：测试失败了 → 自动截图。不用在每个测试用例里写 try/except，全都由 conftest 统一处理。

---

## autouse fixture：自动打日志

```python
@pytest.fixture(autouse=True)
def log_test_info(request):
    logger.info(f"开始执行测试用例: {request.node.name}")
    yield
    logger.info(f"测试用例执行完成: {request.node.name}")

`autouse=True` 意味着所有测试用例自动执行这个 fixture，不需要显式声明参数。每个用例前后各打一行日志，CI 里排错时很有用，能看清楚跑到了哪个用例、卡在了哪里。

---

## 整个流程串起来

一个测试用例的完整生命周期是这样的：

```
pytest 启动
  ↓
session 级 driver_setup → 初始化 driver（只一次）
  ↓
session 级 api_client → 创建 API 客户端（只一次）
  ↓
对每个测试用例：
  ① autouse→log_test_info → 打印开始日志
  ② driver fixture（function 级）→ 拿到 driver
  ③ 执行测试函数
  ④ pytest_runtest_makereport hook → 把执行结果挂到 item 上
  ⑤ driver fixture teardown → 如果失败可以截图
  ⑥ autouse→log_test_info → 打印结束日志
  ↓
session 结束 → driver_setup 的 finalizer → driver.quit()

---

## 常见坑

**`request.addfinalizer` 比 `yield` 后面放代码更可靠。** yield 后面的代码如果 fixture 内部抛了异常可能会跳过，finalizer 不管怎样都会执行。清理 driver 这类操作，用 finalizer。

**hook 的异常不会影响测试。** hook 里抛异常，pytest 只打一行警告，测试该过过该挂挂。但你的截图、报告生成这些功能就没了。所以 hook 里的操作最好包 try/except。

**`tryfirst=True` 和 `trylast=True` 的含义。** tryfirst 保证这个 hook 比其他同类型的先执行，适用于"我要先设置一些东西供别人使用"。trylast 则相反。

**autouse 不要放耗时操作。** 每个用例都跑一次，如果里面做了网络请求或文件读写，跑 500 个用例就多了 500 次。

---

## 几点总结

conftest.py 的核心价值就是四个字：**分离关注**。测试用例只管"测什么"和"怎么测"，driver 从哪来、失败怎么办、结果怎么收集，conftest 处理。

实际项目里 conftest.py 可以很大——有人把 fixture、hook、工具函数全塞一个文件里，跑着也没问题。但如果 conftest.py 超过两三百行，可以考虑拆分：fixture 放一个文件，hook 放一个文件，用 conftest.py 统一 import 进来。不过这是口味问题，不是硬性规定。
