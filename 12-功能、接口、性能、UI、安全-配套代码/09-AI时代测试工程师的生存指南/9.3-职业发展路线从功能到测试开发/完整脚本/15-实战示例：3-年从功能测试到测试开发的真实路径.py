# 第一年：功能测试（月薪 8K）
"""
- 手工测试所有功能
- 写 Excel 用例
- 提 Bug，跟踪 Bug
- 写测试报告
- 每天 80% 时间在点点点
"""

# 第二年：接口测试（月薪 12K）
def test_login_api():
    resp = requests.post("http://api.example.com/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert resp.status_code == 200
    assert "token" in resp.json()

# 第三年：测试开发（月薪 18K）
@pytest.fixture(scope="session")
def auto_env():
    """一键搭建测试环境"""
    subprocess.run(["docker-compose", "up", "-d"])
    time.sleep(10)
    yield
    subprocess.run(["docker-compose", "down"])
