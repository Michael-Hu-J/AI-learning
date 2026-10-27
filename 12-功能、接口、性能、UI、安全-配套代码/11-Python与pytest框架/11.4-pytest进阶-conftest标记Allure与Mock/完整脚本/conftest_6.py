# conftest.py — 注册自定义标记
def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: 冒烟测试，核心流程")
    config.addinivalue_line("markers", "p0: 最高优先级")
    config.addinivalue_line("markers", "slow: 慢速测试，可能>30秒")
