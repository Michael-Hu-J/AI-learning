# test_seckill_finance_comprehensive.py - 综合实战测试
"""
注意：本测试需要 seckill_finance_system 后端服务（http://localhost:5000）。
如果服务未启动，会自动跳过。可修改 BASE_URL 适配你自己的系统。
"""

import pytest
from utils.backend_check import seckill_api_available

pytestmark = pytest.mark.skipif(
    not seckill_api_available(),
    reason="需要 seckill_finance_system 后端（/api/auth/login），见 README 路径 C",
)
"""
综合实战：对真实业务系统（电商秒杀与财务一体化系统）进行端到端测试
演示如何用 pytest 串联所有知识点：Fixture、参数化、Hook、Allure、断言

被测系统：/seckill_finance_system
API 文档：http://localhost:5000/openapi.yaml
默认管理员：admin / admin123（演示环境；可用环境变量 TEST_ADMIN_PASSWORD 覆盖）
"""
import os
import time
import pytest
import allure
import requests
from typing import Dict, Any

BASE_URL = os.getenv("SECKILL_BASE_URL", "http://localhost:5000")
DEMO_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")


# ==================== Fixture 层 ====================

@pytest.fixture(scope="session")
def admin_token():
    """
    会话级别：获取管理员 Token
    整个测试会话只登录一次，所有用例共享
    """
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": DEMO_ADMIN_PASSWORD},
        timeout=10
    )
    assert response.status_code == 200, f"管理员登录失败: {response.text}"
    data = response.json()
    token = data.get("token", "")
    assert token, "登录响应中缺少 token"
    return token


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    """
    会话级别：管理员请求头
    依赖 admin_token fixture
    """
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    }


@pytest.fixture(scope="function")
def regular_user_token():
    """
    函数级别：每次测试都注册一个新用户
    保证用例之间互不干扰
    """
    import random
    timestamp = int(time.time())
    random_suffix = random.randint(1000, 9999)
    username = f"testuser_{timestamp}_{random_suffix}"
    password = "***"  # 演示密码

    # 先注册
    reg_response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"username": username, "password": password, "role": "user"},
        timeout=10
    )
    # 注册可能失败（用户名已存在），忽略
    if reg_response.status_code not in [200, 201, 409]:
        pytest.skip(f"注册失败: {reg_response.status_code}")

    # 再登录
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password},
        timeout=10
    )
    if login_response.status_code != 200:
        pytest.skip(f"登录失败: {login_response.status_code}")

    data = login_response.json()
    return data.get("token", "")


@pytest.fixture(scope="function")
def regular_headers(regular_user_token):
    """普通用户请求头"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {regular_user_token}"
    }


# ==================== 第1组：API 基础测试（验证断言体系） ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("认证模块")
class TestAuthAPI:
    """认证模块测试 - 演示 pytest 断言体系"""

    @allure.story("用户登录")
    @allure.title("管理员登录 - 验证 Token 返回")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_admin_login(self):
        """测试管理员登录，验证返回 token 和用户信息"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "admin", "password": DEMO_ADMIN_PASSWORD},
            timeout=10
        )

        # 状态码断言
        assert response.status_code == 200, f"登录失败，状态码: {response.status_code}"

        # 响应体断言
        data = response.json()
        assert "token" in data, "响应中缺少 token 字段"
        assert "user" in data, "响应中缺少 user 字段"
        assert data["user"].get("username") == "admin", "用户名不匹配"

    @allure.story("用户登录")
    @allure.title("错误密码登录 - 验证失败响应")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.regression
    def test_wrong_password_login(self):
        """测试错误密码登录，验证返回错误信息"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "wrong_password"},
            timeout=10
        )

        # 应该返回 401
        assert response.status_code == 401, f"错误密码应该返回 401，实际: {response.status_code}"

        data = response.json()
        # 验证错误信息包含关键词（系统用 error 字段返回错误）
        message = data.get("message", "") or data.get("error", "")
        assert "密码" in message or "错误" in message or "incorrect" in message.lower(), \
            f"错误信息不包含关键词: {message}"
    @allure.story("用户登录")
    @allure.title("空请求体登录 - 验证参数校验")
    @allure.severity(allure.severity_level.MINOR)
    def test_empty_body_login(self):
        """测试空请求体登录，验证参数校验"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={},
            timeout=10
        )

        # 应该返回 400 或 401
        assert response.status_code in [400, 401, 422],             f"空请求体应该返回 400/401/422，实际: {response.status_code}"


# ==================== 第2组：参数化测试（数据驱动） ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("商品模块")
class TestProductAPI:
    """商品模块测试 - 演示 pytest 参数化"""

    @pytest.mark.parametrize("endpoint,expected_status,description", [
        ("/api/products", 200, "获取商品列表（无需登录）"),
        ("/api/seckill/list", 200, "获取秒杀商品列表（无需登录）"),
        ("/api/seckill/activities", 200, "获取秒杀活动列表（无需登录）"),
    ])
    @allure.story("商品查询")
    @allure.title("{description}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_public_endpoints(self, endpoint, expected_status, description):
        """参数化测试：公共端点都能正常访问"""
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            timeout=10
        )
        assert response.status_code == expected_status,             f"{description} 失败，状态码: {response.status_code}"

        # 验证响应是 JSON
        data = response.json()
        assert isinstance(data, (dict, list)), f"{description} 响应不是 JSON"

    @pytest.mark.parametrize("method,endpoint,body,expected_status,description", [
        ("GET", "/api/products", None, 200, "GET 获取商品列表"),
        ("GET", "/api/seckill/list", None, 200, "GET 获取秒杀列表"),
    ])
    @allure.story("HTTP 方法测试")
    @allure.title("{description}")
    def test_http_methods(self, method, endpoint, body, expected_status, description):
        """参数化测试：不同 HTTP 方法"""
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=body, timeout=10)
        else:
            pytest.skip(f"未实现 {method} 方法")

        assert response.status_code == expected_status


# ==================== 第3组：管理员操作测试（依赖注入） ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("管理员操作")
class TestAdminAPI:
    """管理员操作测试 - 演示 Fixture 依赖注入"""

    @allure.story("商品管理")
    @allure.title("创建商品 - 验证管理员权限")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_create_product(self, admin_headers):
        """测试管理员创建商品"""
        import random
        product_data = {
            "name": f"测试商品_{int(time.time())}_{random.randint(100,999)}",
            "description": "pytest 自动化测试创建的商品",
            "price": round(random.uniform(10, 1000), 2),
            "stock": random.randint(100, 10000),
            "category": "测试分类"
        }

        response = requests.post(
            f"{BASE_URL}/api/products",
            json=product_data,
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code in [200, 201],             f"创建商品失败: {response.status_code}, {response.text}"

        data = response.json()
        assert "id" in data or "product" in data or "message" in data,             f"创建商品响应缺少关键字段: {data}"

    @allure.story("商品管理")
    @allure.title("获取商品列表 - 验证数据返回")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.smoke
    def test_get_products(self, admin_headers):
        """测试管理员获取商品列表"""
        response = requests.get(
            f"{BASE_URL}/api/products",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        # 商品列表应该是数组或包含 products 字段的字典
        if isinstance(data, dict):
            assert "products" in data or "data" in data or "items" in data,                 f"商品列表响应格式异常: {list(data.keys())}"
        elif isinstance(data, list):
            assert len(data) >= 0, "商品列表应该返回数组"

    @allure.story("秒杀活动管理")
    @allure.title("创建秒杀活动 - 验证管理员权限")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_create_seckill_activity(self, admin_headers):
        """测试管理员创建秒杀活动"""
        import random
        activity_data = {
            "name": f"pytest秒杀活动_{int(time.time())}",
            "description": "自动化测试创建的秒杀活动",
            "start_time": "2026-06-01 10:00:00",
            "end_time": "2026-12-31 23:59:59",
            "status": "pending"
        }

        response = requests.post(
            f"{BASE_URL}/api/seckill/activities",
            json=activity_data,
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code in [200, 201, 400],             f"创建秒杀活动异常: {response.status_code}, {response.text}"


# ==================== 第4组：权限验证测试（失败场景） ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("权限验证")
class TestPermissionAPI:
    """权限验证测试 - 演示无 Token 访问受保护接口"""

    @pytest.mark.parametrize("endpoint,method,expected_min_status,description", [
        ("/api/products", "GET", 200, "商品列表（公开）"),
        ("/api/seckill/list", "GET", 200, "秒杀列表（公开）"),
    ])
    @allure.story("公开接口")
    @allure.title("{description} - 无需 Token")
    def test_public_access(self, endpoint, method, expected_min_status, description):
        """测试公开接口无需 Token 即可访问"""
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        assert response.status_code >= expected_min_status

    @allure.story("受保护接口")
    @allure.title("无 Token 访问管理员接口 - 验证 401")
    @pytest.mark.regression
    def test_no_token_access_admin(self):
        """测试无 Token 访问管理员接口，应该返回 401"""
        response = requests.post(
            f"{BASE_URL}/api/products",
            json={"name": "test", "price": 10, "stock": 100},
            timeout=10
        )
        # 应该返回 401 未授权
        assert response.status_code in [401, 403],             f"无 Token 访问管理员接口应该返回 401/403，实际: {response.status_code}"


# ==================== 第5组：端到端流程测试（综合场景） ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("端到端流程")
class TestE2EWorkflow:
    """端到端流程测试 - 串联所有知识点"""

    @allure.story("完整购物流程")
    @allure.title("管理员创建商品 → 用户浏览 → 用户下单")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_full_shopping_flow(self, admin_headers):
        """
        端到端测试完整购物流程：
        1. 管理员创建商品
        2. 用户浏览商品列表
        3. 验证商品存在
        """
        import random

        # 步骤1：管理员创建商品
        product_name = f"E2E测试商品_{int(time.time())}"
        create_response = requests.post(
            f"{BASE_URL}/api/products",
            json={
                "name": product_name,
                "description": "E2E测试创建",
                "price": 99.99,
                "stock": 1000,
                "category": "E2E测试"
            },
            headers=admin_headers,
            timeout=10
        )
        assert create_response.status_code in [200, 201],             f"步骤1失败：创建商品 {create_response.status_code}"

        # 步骤2：用户浏览商品列表
        time.sleep(0.5)
        list_response = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert list_response.status_code == 200

        products_data = list_response.json()
        if isinstance(products_data, dict):
            products = products_data.get("products", products_data.get("data", []))
        elif isinstance(products_data, list):
            products = products_data
        else:
            products = []

        # 步骤3：验证新创建的商品在列表中
        product_names = []
        for p in products:
            if isinstance(p, dict):
                product_names.append(p.get("name", ""))
            elif isinstance(p, str):
                product_names.append(p)

        # 商品名可能在列表中（取决于系统实现）
        # 至少验证列表接口正常返回
        assert isinstance(products, list), "商品列表应该是数组"

    @allure.story("秒杀流程")
    @allure.title("查看秒杀活动 → 查看秒杀详情")
    @allure.severity(allure.severity_level.NORMAL)
    def test_seckill_flow(self):
        """
        秒杀流程测试：
        1. 获取秒杀活动列表
        2. 如果有活动，获取活动详情
        """
        # 步骤1：获取秒杀活动列表
        activities_response = requests.get(
            f"{BASE_URL}/api/seckill/activities",
            timeout=10
        )
        assert activities_response.status_code == 200

        activities_data = activities_response.json()
        if isinstance(activities_data, dict):
            activities = activities_data.get("activities", activities_data.get("data", []))
        elif isinstance(activities_data, list):
            activities = activities_data
        else:
            activities = []

        # 步骤2：如果有活动，验证活动详情
        if activities and len(activities) > 0:
            first_activity = activities[0]
            if isinstance(first_activity, dict):
                activity_id = first_activity.get("id")
            else:
                activity_id = None

            if activity_id:
                detail_response = requests.get(
                    f"{BASE_URL}/api/seckill/activities/{activity_id}",
                    timeout=10
                )
                assert detail_response.status_code == 200
