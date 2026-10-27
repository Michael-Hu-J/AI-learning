import pytest

@pytest.fixture
def test_data():
    """测试数据 fixture — 测试前造，测试后清"""
    factory = TestDataFactory("http://localhost:5001")
    
    # 测试前：造数据
    user = factory.create_user()
    product = factory.create_product()
    
    yield factory  # 把工厂传给测试用例
    
    # 测试后：清理数据
    factory.cleanup()

def test_purchase(test_data):
    """使用 fixture 的测试用例"""
    factory = test_data
    # 用 factory 创建的数据跑测试
    # ...
