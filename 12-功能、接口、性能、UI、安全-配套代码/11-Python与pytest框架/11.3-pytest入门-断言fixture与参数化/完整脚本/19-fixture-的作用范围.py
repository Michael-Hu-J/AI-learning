@pytest.fixture(scope="session")
def base_url():
    """整个测试只用配置一次"""
    return "http://localhost:5001"

@pytest.fixture(scope="session")
def admin_token(base_url):
    """整个会话只登录一次，所有用例共用"""
    resp = requests.post(f"{base_url}/api/auth/login",
                        json={"username": "admin", "password": "admin123"})
    return resp.json()["token"]

def test_create_product(base_url, admin_token):
    pass

def test_get_products(base_url, admin_token):
    pass
