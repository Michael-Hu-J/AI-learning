# test_auth.py
BASE_URL = "http://localhost:5001"

@pytest.fixture(scope="session")
def admin_token():
    ...

# test_products.py
BASE_URL = "http://localhost:5001"  # 又写一遍！

@pytest.fixture(scope="session")
def admin_token():  # 又写一遍！
    ...
