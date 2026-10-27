"""
pytest 全局配置
"""
import pytest, subprocess, time, os, sys

@pytest.fixture(scope="session")
def demo_app():
    app = os.path.join(os.path.dirname(__file__), "demo_app", "app.py")
    if not os.path.exists(app): pytest.skip("演示应用不存在")
    print("\n 启动演示应用...")
    proc = subprocess.Popen([sys.executable, app], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    yield proc
    proc.terminate()
    try: proc.wait(timeout=5)
    except: proc.kill()

@pytest.fixture(scope="function")
def page(browser):
    p = browser.new_page()
    yield p
    p.close()
