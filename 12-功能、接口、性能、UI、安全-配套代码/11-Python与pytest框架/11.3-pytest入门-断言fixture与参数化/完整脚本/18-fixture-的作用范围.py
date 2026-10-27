@pytest.fixture(scope="function")  # 默认：每个测试函数执行一次
@pytest.fixture(scope="class")     # 每个测试类执行一次
@pytest.fixture(scope="module")    # 每个文件执行一次
@pytest.fixture(scope="session")   # 整个测试会话只执行一次
