# test_product_api.py - 商品接口测试
"""
注意：本测试需要 seckill_finance_system 后端服务。
如果服务未启动，会自动跳过。
"""

import pytest
from utils.backend_check import seckill_api_available

pytestmark = pytest.mark.skipif(
    not seckill_api_available(),
    reason="需要 seckill_finance_system 后端（/api/auth/login），见 README 路径 C",
)
"""
新增商品 + 查询商品 接口测试
被测系统：电商秒杀与财务一体化系统 (http://localhost:5000)
"""
import os
import time
import random
import pytest
import allure
import requests

BASE_URL = os.getenv("SECKILL_BASE_URL", "http://localhost:5000")
DEMO_USER = os.getenv("TEST_LOGIN_USERNAME", "admin")
DEMO_PASS = os.getenv("TEST_LOGIN_PASSWORD", "admin123")

# 接口自动化创建的商品名统一前缀（便于在后台列表、数据库中筛选）
PRODUCT_NAME_PREFIX = "API测试商品pytest"


@pytest.fixture(scope="module")
def admin_token():
    """管理员 Token（模块级别，一组用例共享）"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": DEMO_USER, "password": DEMO_PASS},
        timeout=10
    )
    assert response.status_code == 200, f"登录失败: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    }


@allure.epic("商品接口测试")
@allure.feature("商品CRUD")
class TestProductAPI:

    @allure.story("新增商品")
    @allure.title("管理员创建普通商品")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_create_product(self, admin_headers):
        """测试新增商品：验证创建成功并返回商品ID"""
        timestamp = int(time.time())
        product_name = f"{PRODUCT_NAME_PREFIX}_{timestamp}"

        with allure.step("构造商品数据"):
            product_data = {
                "name": product_name,
                "description": "通过自动化测试创建的商品",
                "price": round(random.uniform(10, 1000), 2),
                "stock": random.randint(100, 10000),
                "category": "自动化测试"
            }

        with allure.step("发送POST请求创建商品"):
            response = requests.post(
                f"{BASE_URL}/api/products",
                json=product_data,
                headers=admin_headers,
                timeout=10
            )

        with allure.step("验证返回状态码"):
            assert response.status_code in [200, 201], \
                f"创建商品失败，状态码: {response.status_code}"

        with allure.step("验证返回数据"):
            data = response.json()
            assert data.get("name") == product_name, f"商品名不匹配"
            assert data.get("id") is not None, "缺少商品ID"
            assert data.get("price") == product_data["price"], "价格不匹配"

        allure.attach(
            f"创建商品: {product_name}, ID: {data.get('id')}, 价格: {data.get('price')}",
            "创建结果", allure.attachment_type.TEXT
        )

    @allure.story("新增商品")
    @allure.title("创建商品验证必填字段")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_product_missing_fields(self, admin_headers):
        """测试缺少必填字段时应该返回错误"""
        # 只传名字，不传价格
        response = requests.post(
            f"{BASE_URL}/api/products",
            json={"name": "不完整商品"},
            headers=admin_headers,
            timeout=10
        )
        # 缺少必填字段应该返回 400 参数校验错误
        assert response.status_code == 400, \
            f"缺少必填字段应该返回400，实际: {response.status_code}"
        error_data = response.json()
        assert 'error' in error_data or 'details' in error_data, \
            f"错误响应缺少 error 字段: {error_data}"

    @allure.story("查询商品")
    @allure.title("查询全部商品列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_get_all_products(self, admin_headers):
        """测试查询全部商品：验证返回列表格式正确"""
        with allure.step("发送GET请求查询商品"):
            response = requests.get(
                f"{BASE_URL}/api/products",
                headers=admin_headers,
                timeout=10
            )

        with allure.step("验证状态码"):
            assert response.status_code == 200, \
                f"查询失败，状态码: {response.status_code}"

        with allure.step("解析并验证商品列表"):
            data = response.json()
            if isinstance(data, dict):
                products = data.get("products", data.get("data", []))
            elif isinstance(data, list):
                products = data
            else:
                products = []

            assert isinstance(products, list), "商品列表应为数组格式"

        allure.attach(
            f"共查询到 {len(products)} 个商品",
            "查询结果", allure.attachment_type.TEXT
        )

    @allure.story("查询商品")
    @allure.title("查询指定ID的商品详情")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.smoke
    def test_get_product_by_id(self, admin_headers):
        """测试查询单个商品详情"""
        with allure.step("先获取所有商品列表"):
            list_resp = requests.get(
                f"{BASE_URL}/api/products",
                headers=admin_headers,
                timeout=10
            )
            assert list_resp.status_code == 200, "获取商品列表失败"

            data = list_resp.json()
            if isinstance(data, dict):
                products = data.get("products", data.get("data", []))
            else:
                products = data if isinstance(data, list) else []

            assert len(products) > 0, "商品列表为空，无法查询详情"

        # 取第一个商品
        first_product = products[0]
        product_id = first_product.get("id") if isinstance(first_product, dict) else None
        product_name = first_product.get("name", "") if isinstance(first_product, dict) else str(first_product)

        with allure.step(f"查询商品详情 (ID={product_id})"):
            detail_resp = requests.get(
                f"{BASE_URL}/api/products/{product_id}",
                headers=admin_headers,
                timeout=10
            )

        with allure.step("验证商品详情"):
            assert detail_resp.status_code == 200, \
                f"查询商品详情失败，ID: {product_id}"

            detail = detail_resp.json()
            if isinstance(detail, dict):
                assert detail.get("name") == product_name, \
                    f"商品名不匹配: {detail}"

        allure.attach(
            f"商品ID: {product_id}, 名称: {product_name}",
            "查询详情", allure.attachment_type.TEXT
        )

    @allure.story("新增+查询")
    @allure.title("创建商品后立即查询验证一致性")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_create_then_query(self, admin_headers):
        """端到端测试：创建商品 → 查询列表 → 验证商品存在"""
        timestamp = int(time.time())
        product_name = f"{PRODUCT_NAME_PREFIX}_e2e_{timestamp}"
        product_price = 88.88
        product_stock = 3000

        with allure.step("步骤1：创建商品"):
            create_resp = requests.post(
                f"{BASE_URL}/api/products",
                json={
                    "name": product_name,
                    "description": "端到端验证测试",
                    "price": product_price,
                    "stock": product_stock,
                    "category": "E2E测试"
                },
                headers=admin_headers,
                timeout=10
            )
            assert create_resp.status_code in [200, 201], \
                f"创建商品失败: {create_resp.status_code}"
            created = create_resp.json()
            created_id = created.get("id")
            allure.attach(f"创建成功，ID: {created_id}", "步骤1结果", allure.attachment_type.TEXT)

        with allure.step("步骤2：查询商品列表"):
            time.sleep(0.3)
            list_resp = requests.get(
                f"{BASE_URL}/api/products",
                headers=admin_headers,
                timeout=10
            )
            assert list_resp.status_code == 200

            list_data = list_resp.json()
            if isinstance(list_data, dict):
                products = list_data.get("products", list_data.get("data", []))
            else:
                products = list_data if isinstance(list_data, list) else []

        with allure.step(f"步骤3：验证新创建的商品 '{product_name}' 在列表中"):
            found = False
            for p in products:
                if isinstance(p, dict) and p.get("name") == product_name:
                    found = True
                    assert p.get("price") == product_price, \
                        f"价格不匹配: 预期{product_price}，实际{p.get('price')}"
                    break
            assert found, f"商品 '{product_name}' 不在列表中"

        allure.attach("创建和查询验证通过", "最终结果", allure.attachment_type.TEXT)

    @allure.story("权限验证")
    @allure.title("无Token创建商品应被拒绝")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.regression
    def test_create_without_token(self):
        """验证无Token访问管理员接口返回401"""
        response = requests.post(
            f"{BASE_URL}/api/products",
            json={"name": "无权限商品", "price": 10, "stock": 100},
            timeout=10
        )
        assert response.status_code in [401, 403], \
            f"无Token应返回401/403，实际: {response.status_code}"
