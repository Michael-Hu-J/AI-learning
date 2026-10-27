#!/usr/bin/env python3
# run_seckill_api_test.py - 执行秒杀系统 API测试
"""
执行秒杀系统 API测试脚本
功能：演示完整的电商秒杀系统 API测试流程

测试流程（基于真实业务系统 seckill_finance_system）：
0. 预置：POST /api/test/init — 每次将 admin 口令重置为与脚本一致（默认 admin123，与 TEST_ADMIN_PASSWORD 对齐），并补演示数据
1. 用户注册 → /api/auth/register
2. 用户登录 → /api/auth/login
3. 获取用户信息 → /api/auth/profile
4. 商品管理 → 先以管理员登录（默认 admin / admin123，与演示种子一致；可用 TEST_ADMIN_PASSWORD 等覆盖），再 CRUD
5. 获取商品列表 → /api/products
6. 获取商品详情 → /api/products/{id}
7. 更新商品 → /api/products/{id}

API 自愈能力：
- 智能重试：网络抖动/5xx 自动重试（指数退避）
- 状态轮询：异步接口自动等待
- 智能跳过：前置步骤失败时后续步骤自动 skip

使用方式：
python scripts/run_seckill_api_test.py [--base-url ...] [--skip-test-init] [--admin-username admin] [--admin-password admin123]
环境变量：TEST_ADMIN_USERNAME、TEST_ADMIN_PASSWORD（未传命令行时生效）
"""
import sys
import os
import json
import argparse
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.test_data_generator import TestDataGenerator
from core.api_self_healing import SelfHealingAPIClient, APIRetryConfig

# 演示环境种子管理员（与 test_seckill_finance_comprehensive 一致）；口令勿用 TEST_LOGIN_PASSWORD 链式覆盖，避免与普通演示账号混淆
DEMO_ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", os.getenv("TEST_LOGIN_USERNAME", "admin"))
DEMO_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")


class SeckillAPIClient:
    """秒杀系统 API 客户端（基于 seckill_finance_system 真实接口）"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.token: Optional[str] = None
        self.session = requests.Session()

    @property
    def client(self):
        """供 SelfHealingAPIClient 使用（与 requests.Session 包装体一致，指向自身）。"""
        return self

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET，参数与 requests 及自愈层兼容（params）。"""
        return self._make_request('GET', endpoint, params=kwargs.get('params'))

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """POST；自愈层传 json_data，标准 requests 传 json。"""
        body = kwargs.get('json_data')
        if body is None and 'json' in kwargs:
            body = kwargs['json']
        return self._make_request('POST', endpoint, json_data=body, params=kwargs.get('params'))

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        body = kwargs.get('json_data')
        if body is None and 'json' in kwargs:
            body = kwargs['json']
        return self._make_request('PUT', endpoint, json_data=body, params=kwargs.get('params'))

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        return self._make_request('DELETE', endpoint, params=kwargs.get('params'))
    
    def _make_request(self, method: str, endpoint: str, json_data: Dict = None, params: Dict = None) -> requests.Response:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        response = self.session.request(
            method=method.upper(),
            url=url,
            json=json_data,
            params=params,
            headers=headers
        )
        return response
    
    # ==================== 认证相关 ====================
    
    def register(self, username: str, password: str, email: str = None) -> requests.Response:
        """用户注册"""
        data = {
            'username': username,
            'password': password,
            'email': email or f"{username}@example.com"
        }
        return self._make_request('POST', '/api/auth/register', json_data=data)
    
    def login(self, username: str, password: str) -> requests.Response:
        """用户登录"""
        data = {
            'username': username,
            'password': password
        }
        return self._make_request('POST', '/api/auth/login', json_data=data)
    
    def get_profile(self) -> requests.Response:
        """获取用户信息"""
        return self._make_request('GET', '/api/auth/profile')
    
    # ==================== 商品相关 ====================
    
    def get_products(self, status: str = None, category: str = None) -> requests.Response:
        """获取商品列表"""
        params = {}
        if status:
            params['status'] = status
        if category:
            params['category'] = category
        return self._make_request('GET', '/api/products', params=params)
    
    def get_product(self, product_id: int) -> requests.Response:
        """获取商品详情"""
        return self._make_request('GET', f'/api/products/{product_id}')
    
    def create_product(self, name: str, price: float, stock: int = 100,
                       description: str = "", seckill_price: float = None,
                       seckill_stock: int = 0) -> requests.Response:
        """创建商品"""
        data = {
            'name': name,
            'price': price,
            'stock': stock,
            'description': description,
        }
        if seckill_price and seckill_stock > 0:
            now = datetime.now()
            data['seckill_price'] = seckill_price
            data['seckill_stock'] = seckill_stock
            data['seckill_start_time'] = (now.replace(hour=0, minute=0, second=0)).isoformat()
            data['seckill_end_time'] = (now.replace(hour=23, minute=59, second=59)).isoformat()
        
        return self._make_request('POST', '/api/products', json_data=data)
    
    def update_product(self, product_id: int, **kwargs) -> requests.Response:
        """更新商品"""
        return self._make_request('PUT', f'/api/products/{product_id}', json_data=kwargs)
    
    def delete_product(self, product_id: int) -> requests.Response:
        """删除商品（软删除）"""
        return self._make_request('DELETE', f'/api/products/{product_id}')

    def post_test_init(self, json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """调用后端测试初始化（无 Token）。请求体可传 admin_password，与登录脚本保持一致。"""
        url = f"{self.base_url}/api/test/init"
        return self.session.post(
            url,
            json=json_data or {},
            headers={'Content-Type': 'application/json'},
            timeout=120,
        )


class SeckillAPITestRunner:
    """秒杀系统 API测试运行器"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        enable_self_healing: bool = True,
        admin_username: Optional[str] = None,
        admin_password: Optional[str] = None,
        skip_test_init: bool = False,
    ):
        self.client = SeckillAPIClient(base_url)
        self.test_results: List[Dict] = []
        self.context: Dict[str, Any] = {}  # 测试上下文，存储中间结果
        self.admin_username = admin_username if admin_username is not None else DEMO_ADMIN_USERNAME
        self.admin_password = admin_password if admin_password is not None else DEMO_ADMIN_PASSWORD
        self.skip_test_init = skip_test_init
        
        # API 自愈客户端
        self.self_healing_enabled = enable_self_healing
        if enable_self_healing:
            retry_config = APIRetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=10.0,
                backoff_factor=2.0
            )
            self.healing_client = SelfHealingAPIClient(self.client, retry_config)
        else:
            self.healing_client = None
    
    def _print_section(self, title: str):
        """打印章节标题"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    
    def _print_step(self, step_num: int, description: str):
        """打印步骤"""
        print(f"\n[步骤 {step_num}] {description}")
    
    def _print_result(self, response: requests.Response, expected_status: int = None):
        """打印请求结果"""
        status_icon = "✅" if response.status_code == expected_status else "⚠️"
        print(f"  {status_icon} 状态码: {response.status_code}")
        
        try:
            data = response.json()
            print(f"  📦 响应: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
            return data
        except:
            print(f"  📦 响应: {response.text[:200]}")
            return None
    
    def _record_result(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        self.test_results.append({
            'test_name': test_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    # ==================== 测试用例 ====================
    
    def test_user_registration(self) -> bool:
        """测试：用户注册"""
        self._print_section("测试 1：用户注册")
        
        username = TestDataGenerator.generate_username()
        password = TestDataGenerator.generate_password()
        email = TestDataGenerator.generate_email()
        
        self._print_step(1, f"注册用户: {username}")
        
        # 使用自愈客户端发送请求
        if self.self_healing_enabled:
            response = self.healing_client.post('/api/auth/register', json_data={
                'username': username,
                'password': password,
                'email': email
            })
        else:
            response = self.client.register(username, password, email)
        
        data = self._print_result(response, 201)
        
        passed = response.status_code in [201, 400]  # 201=成功, 400=用户已存在
        if passed and data and 'token' in data:
            self.client.token = data['token']
            self.context['username'] = username
            self.context['password'] = password
            self.context['token'] = data['token']
            if 'user' in data:
                self.context['user_id'] = data['user'].get('id')
        
        self._record_result("用户注册", passed)
        return passed
    
    def test_user_login(self) -> bool:
        """测试：用户登录"""
        self._print_section("测试 2：用户登录")
        
        username = self.context.get('username', 'testuser')
        password = self.context.get('password', 'Test@1234')
        
        self._print_step(1, f"登录用户: {username}")
        
        # 使用自愈客户端发送请求
        if self.self_healing_enabled:
            response = self.healing_client.post('/api/auth/login', json_data={
                'username': username,
                'password': password
            })
        else:
            response = self.client.login(username, password)
        
        data = self._print_result(response, 200)
        
        passed = response.status_code == 200
        if passed and data and 'token' in data:
            self.client.token = data['token']
            self.context['token'] = data['token']
        
        self._record_result("用户登录", passed)
        return passed
    
    def test_get_profile(self) -> bool:
        """测试：获取用户信息"""
        self._print_section("测试 3：获取用户信息")
        
        self._print_step(1, "获取当前用户信息")
        response = self.client.get_profile()
        data = self._print_result(response, 200)
        
        passed = response.status_code == 200
        if passed and data:
            print(f"  👤 用户名: {data.get('username')}")
            print(f"  📧 邮箱: {data.get('email')}")
        
        self._record_result("获取用户信息", passed)
        return passed
    
    def _bootstrap_backend_test_seed(self) -> None:
        """请求后端 POST /api/test/init，每次将 admin 重置为与脚本一致的口令（见 seckill_finance_system）。"""
        if self.skip_test_init:
            print("\n  ⏭️ 已跳过 /api/test/init（--skip-test-init）")
            return
        print("\n[预置] 调用 POST /api/test/init 重置 admin 并补演示数据 …")
        try:
            r = self.client.post_test_init(json_data={'admin_password': self.admin_password})
        except requests.RequestException as e:
            print(f"  ⚠️ 请求失败: {e}")
            return
        if r.status_code == 200:
            print("  ✅ 后端测试初始化成功（admin 口令已与当前脚本配置对齐）")
        else:
            print(f"  ⚠️ 返回 HTTP {r.status_code}；若非 seckill_finance_system 可忽略或使用 --skip-test-init")
    
    def test_product_crud(self) -> bool:
        """测试：商品 CRUD（需管理员 token；登录后仍恢复为前面普通用户的 token）"""
        self._print_section("测试 4：商品管理")
        plain_token = self.client.token
        
        self._print_step(1, f"管理员登录（{self.admin_username}）— 创建/更新商品需 admin 角色")
        if self.self_healing_enabled:
            response = self.healing_client.post('/api/auth/login', json_data={
                'username': self.admin_username,
                'password': self.admin_password,
            })
        else:
            response = self.client.login(self.admin_username, self.admin_password)
        data = self._print_result(response, 200)
        if response.status_code != 200 or not data or 'token' not in data:
            print("  💡 请先跑通本脚本开头的 POST /api/test/init，或设置 TEST_ADMIN_PASSWORD / --admin-password 与后端一致。")
            self._record_result("商品管理", False)
            return False
        self.client.token = data['token']
        self.context['token'] = data['token']
        
        passed = False
        try:
            # 创建商品
            product_name = TestDataGenerator.generate_product_name()
            price = TestDataGenerator.generate_price(50, 500)
            stock = TestDataGenerator.generate_stock(50, 200)
            
            self._print_step(2, f"创建商品: {product_name} (¥{price}, 库存:{stock})")
            
            if self.self_healing_enabled:
                response = self.healing_client.post('/api/products', json_data={
                    'name': product_name,
                    'price': price,
                    'stock': stock,
                    'description': "测试商品 - 自动生成"
                })
            else:
                response = self.client.create_product(
                    name=product_name,
                    price=price,
                    stock=stock,
                    description="测试商品 - 自动生成"
                )
            
            data = self._print_result(response, 201)
            
            passed = response.status_code == 201
            if passed and data and 'id' in data:
                product_id = data['id']
                self.context['product_id'] = product_id
                self.context['product_name'] = product_name
                print(f"  💾 商品 ID: {product_id}")
            
            # 获取商品列表
            self._print_step(3, "获取商品列表")
            response = self.client.get_products()
            data = self._print_result(response, 200)
            
            if passed and data:
                print(f"  📋 商品总数: {len(data)}")
                passed = len(data) > 0
            
            # 获取商品详情
            if 'product_id' in self.context:
                self._print_step(4, f"获取商品详情 (ID: {self.context['product_id']})")
                response = self.client.get_product(self.context['product_id'])
                data = self._print_result(response, 200)
                if data:
                    print(f"  📦 商品名称: {data.get('name')}")
                    print(f"  💰 商品价格: ¥{data.get('price')}")
            
            # 更新商品
            if 'product_id' in self.context:
                self._print_step(5, f"更新商品 (ID: {self.context['product_id']})")
                new_price = TestDataGenerator.generate_price(100, 800)
                response = self.client.update_product(
                    self.context['product_id'],
                    price=new_price,
                    stock=200
                )
                data = self._print_result(response, 200)
                if data:
                    print(f"  💰 新价格: ¥{data.get('price')}")
                    print(f"  📦 新库存: {data.get('stock')}")
        finally:
            self.client.token = plain_token
            if plain_token:
                self.context['token'] = plain_token
        
        self._record_result("商品管理", passed)
        return passed
    
    def test_error_handling(self) -> bool:
        """测试：错误处理"""
        self._print_section("测试 5：错误处理")
        
        passed = True
        
        # 测试 1：无效的商品 ID
        self._print_step(1, "请求不存在的商品 (ID: 99999)")
        response = self.client.get_product(99999)
        data = self._print_result(response, 404)
        if response.status_code == 404:
            print("  ✅ 正确返回 404")
        else:
            print(f"  ⚠️ 期望 404，实际 {response.status_code}")
            passed = False
        
        # 测试 2：未登录访问受保护接口
        self._print_step(2, "未登录访问用户信息")
        old_token = self.client.token
        self.client.token = None
        self.client.session.headers.pop('Authorization', None)  # 清除 Authorization header
        response = self.client.get_profile()
        data = self._print_result(response, 401)
        if response.status_code == 401:
            print("  ✅ 正确返回 401")
        else:
            print(f"  ⚠️ 期望 401，实际 {response.status_code}")
            passed = False
        # 恢复 token
        self.client.token = old_token
        if old_token:
            self.client.session.headers.update({
                'Authorization': f'Bearer {old_token}'
            })
        
        self._record_result("错误处理", passed)
        return passed
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print(" 🚀 秒杀系统 API 自动化测试")
        print("="*60)
        print(f"  目标地址: {self.client.base_url}")
        print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.self_healing_enabled:
            print("  🛡️ API 自愈: 已启用")
        else:
            print("  🛡️ API 自愈: 已禁用")
        print("="*60)
        
        # 重置上下文
        TestDataGenerator.reset_context()
        self.context.clear()
        if self.self_healing_enabled:
            self.healing_client.reset()
        
        self._bootstrap_backend_test_seed()
        
        # 运行测试
        self.test_user_registration()
        self.test_user_login()
        self.test_get_profile()
        self.test_product_crud()
        self.test_error_handling()
        
        # 打印测试报告
        self._print_report()
    
    def _print_report(self):
        """打印测试报告"""
        self._print_section("测试报告")
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['passed'])
        failed = total - passed
        
        print(f"\n  总计: {total} 个测试")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        
        # 打印自愈统计
        if self.self_healing_enabled and self.healing_client:
            stats = self.healing_client.get_stats()
            print(f"\n  🛡️ API 自愈统计:")
            print(f"    总请求数: {stats['total_requests']}")
            print(f"    重试次数: {stats['total_retries']}")
            print(f"    重试率: {stats['retry_rate']}")
            print(f"    自愈成功: {stats['saved_by_retry']} 次")
            print(f"    自愈失败: {stats['failed_after_retry']} 次")
        
        print()
        
        for result in self.test_results:
            icon = "✅" if result['passed'] else "❌"
            message = result.get('message', '')
            if message:
                print(f"  {icon} {result['test_name']}: {message}")
            else:
                print(f"  {icon} {result['test_name']}")
        
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="秒杀系统 API 自动化测试")
    parser.add_argument('--base-url', default='http://localhost:5000',
                       help='API 基础地址（默认: http://localhost:5000）')
    parser.add_argument('--disable-self-healing', action='store_true',
                       help='禁用 API 自愈功能（用于对比测试）')
    parser.add_argument('--admin-username', default=None,
                       help='商品管理前管理员登录用户名（默认: 环境变量 TEST_ADMIN_USERNAME 或 admin）')
    parser.add_argument('--admin-password', default=None,
                       help='商品管理前管理员登录密码（默认: 环境变量 TEST_ADMIN_PASSWORD 或 admin123）')
    parser.add_argument('--skip-test-init', action='store_true',
                       help='不调用 POST /api/test/init（连接非 seckill_finance_system 或不想改库时用）')
    
    args = parser.parse_args()
    
    runner = SeckillAPITestRunner(
        base_url=args.base_url,
        enable_self_healing=not args.disable_self_healing,
        admin_username=args.admin_username,
        admin_password=args.admin_password,
        skip_test_init=args.skip_test_init,
    )
    runner.run_all_tests()
    
    # 返回退出码
    failed = sum(1 for r in runner.test_results if not r['passed'])
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
