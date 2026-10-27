# conftest.py - Appium 测试框架 pytest 配置
import pytest
import os
import sys
import logging

logger = logging.getLogger("appium_test")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def pytest_collection_modifyitems(config, items):
    """
    1) test_appium_demo 依赖手机 Chrome + MOCK_SERVER_URL，与「仅原生 App」会话不能混在同一 pytest 进程里
       （在已正确设置 ANDROID_BROWSER=chrome 的前提下）。
    2) 未设置 ANDROID_BROWSER 时，跳过 demo 用例，避免 session driver 先按 APP_PACKAGE 拉起错误会话。
    """
    demo_items = []
    native_driver_items = []
    for item in items:
        p = str(item.path).replace("\\", "/")
        if "test_appium_demo.py" in p:
            demo_items.append(item)
        elif "driver" in getattr(item, "fixturenames", ()):
            native_driver_items.append(item)

    chrome_ok = os.getenv("ANDROID_BROWSER", "").strip().lower() in ("chrome", "chromium", "browser")

    if demo_items and not chrome_ok:
        skip = pytest.mark.skip(
            reason="test_appium_demo 需在真机 Chrome 中打开 Mock：设置 ANDROID_BROWSER=chrome，"
            "并取消 APP_PACKAGE/APP_ACTIVITY；MOCK_SERVER_URL 使用电脑局域网 IP（手机可访问）。"
        )
        for item in demo_items:
            item.add_marker(skip)
        return

    if demo_items and native_driver_items and chrome_ok:
        pytest.exit(
            "不能在同一 pytest 会话中混跑 tests/test_appium_demo.py（须 ANDROID_BROWSER=chrome，无 APP_PACKAGE）"
            "与其它需要原生 App 会话的用例。请先跑一类，再换环境变量跑另一类。",
            returncode=3,
        )


# Appium 相关导入延迟加载，避免未安装 appium 时直接报错
_driver_cache = {}


def _appium_server_ready(server_url: str = "http://localhost:4723") -> bool:
    """检查 Appium Server 是否可连接（未启动时 UI 用例应 skip 而非 error）"""
    import requests

    base = server_url.rstrip("/")
    for path in ("/status", "/wd/hub/status"):
        try:
            resp = requests.get(f"{base}{path}", timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            continue
    return False


def _get_appium():
    """延迟导入 appium，未安装时返回 None"""
    try:
        from appium import webdriver
        from base.base_driver import BaseDriver
        return webdriver, BaseDriver
    except ImportError:
        return None, None


@pytest.fixture(scope="session")
def driver_setup(request):
    """
    驱动初始化 fixture（会话级别）
    在整个测试会话中只初始化一次
    """
    webdriver, BaseDriver = _get_appium()
    if BaseDriver is None:
        pytest.skip("Appium 未安装，跳过 UI 测试")

    server_url = os.getenv("APPIUM_SERVER_URL", "http://localhost:4723")
    if not _appium_server_ready(server_url):
        pytest.skip(
            f"Appium Server 未启动（{server_url}），跳过 UI 测试。"
            "请先执行 appium，或仅跑 API 冒烟：pytest tests/test_login_api.py tests/test_products_api.py tests/test_user_flow_api.py -v"
        )

    platform = os.getenv("PLATFORM", "android")
    logger.info(f"开始初始化移动端驱动 - 平台: {platform}")

    base_driver = BaseDriver(platform=platform, appium_server_url=server_url)
    try:
        driver = base_driver.get_driver()
    except Exception as exc:
        pytest.skip(f"Appium 驱动初始化失败，跳过 UI 测试: {exc}")

    def driver_teardown():
        try:
            driver.quit()
            logger.info("驱动关闭成功")
        except Exception as e:
            logger.error(f"驱动关闭异常: {str(e)}")

    request.addfinalizer(driver_teardown)
    yield driver


@pytest.fixture(scope="function")
def driver(request, driver_setup):
    """函数级别的 driver fixture，复用 session 级 driver"""
    yield driver_setup


@pytest.fixture(scope="session")
def api_client(request):
    """API 客户端 fixture（会话级别）"""
    from api.base_api import BaseAPI

    base_url = os.getenv("API_BASE_URL", "")
    timeout = int(os.getenv("API_TIMEOUT", "30"))
    client = BaseAPI(base_url=base_url, timeout=timeout)

    api_token = os.getenv("API_TOKEN", "")
    if api_token:
        client.set_auth("bearer", api_token)

    yield client


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """pytest hook：让 fixture 能判断测试是否失败"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def log_test_info(request):
    """自动记录测试用例信息的 fixture"""
    logger.info(f"开始执行测试用例: {request.node.name}")
    yield
    logger.info(f"测试用例执行完成: {request.node.name}")
