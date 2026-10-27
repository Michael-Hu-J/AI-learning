#!/usr/bin/env python3
# demo_self_healing.py - API 自愈演示脚本
"""
API 自愈演示脚本
功能：模拟网络故障，展示 API 自愈能力

演示场景：
1. 场景1：500 错误自动重试 → 最终成功
2. 场景2：网络超时自动重试 → 最终成功
3. 场景3：连续失败 → 重试耗尽后返回最后响应
4. 场景4：404 错误 → 不重试（直接返回）
5. 场景5：限流 429 → 自动重试

使用方式：
python scripts/demo_self_healing.py
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.api_self_healing import SelfHealingAPIClient, APIRetryConfig


class MockResponse:
    """模拟 HTTP 响应"""
    
    def __init__(self, status_code: int, json_data: dict = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
    
    def json(self):
        return self._json_data


class MockAPIClient:
    """模拟 API 客户端"""
    
    def __init__(self):
        self.call_count = 0
        self.fail_count = 2  # 前 N 次调用失败
        self.base_url = "http://mock-server:5000"
    
    def get(self, endpoint: str, **kwargs):
        """模拟 GET 请求"""
        self.call_count += 1
        return self._simulate_request(endpoint)
    
    def post(self, endpoint: str, **kwargs):
        """模拟 POST 请求"""
        self.call_count += 1
        return self._simulate_request(endpoint)
    
    def put(self, endpoint: str, **kwargs):
        """模拟 PUT 请求"""
        self.call_count += 1
        return self._simulate_request(endpoint)
    
    def delete(self, endpoint: str, **kwargs):
        """模拟 DELETE 请求"""
        self.call_count += 1
        return self._simulate_request(endpoint)
    
    def _simulate_request(self, endpoint: str):
        """模拟请求（根据 fail_count 决定返回成功还是失败）"""
        if self.call_count <= self.fail_count:
            # 前 N 次返回 500 错误
            print(f"    📡 请求 #{self.call_count}: 模拟 500 错误")
            return MockResponse(500, {"error": "Internal Server Error"})
        else:
            # 之后返回成功
            print(f"    📡 请求 #{self.call_count}: 返回 200 成功")
            return MockResponse(200, {
                "id": 123,
                "name": "测试商品",
                "price": 99.99,
                "stock": 100
            })
    
    def reset(self):
        """重置计数器"""
        self.call_count = 0


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(label: str, passed: bool, details: str = ""):
    """打印结果"""
    icon = "✅" if passed else "❌"
    print(f"  {icon} {label}")
    if details:
        print(f"     {details}")


def demo_scenario_1():
    """场景1：500 错误自动重试 → 最终成功"""
    print_section("场景 1：500 错误自动重试")
    print("  说明：服务器返回 500 错误，自愈客户端自动重试，最终成功")
    print()
    
    # 创建模拟客户端
    mock_client = MockAPIClient()
    mock_client.fail_count = 2  # 前 2 次失败
    
    # 创建自愈客户端
    retry_config = APIRetryConfig(
        max_retries=3,
        base_delay=0.1,  # 演示用短延迟
        max_delay=0.5,
        backoff_factor=2.0
    )
    healing_client = SelfHealingAPIClient(mock_client, retry_config)
    
    # 发送请求
    print("  开始请求...")
    response = healing_client.get('/api/products/1')
    
    # 检查结果
    print()
    print_result("请求成功", response.status_code == 200, 
                f"状态码: {response.status_code}")
    print_result("数据正确", response.json().get('name') == "测试商品",
                f"商品名: {response.json().get('name')}")
    
    # 打印自愈统计
    stats = healing_client.get_stats()
    print(f"\n  🛡️ 自愈统计:")
    print(f"    总请求数: {stats['total_requests']}")
    print(f"    重试次数: {stats['total_retries']}")
    print(f"    重试率: {stats['retry_rate']}")
    print(f"    自愈成功: {stats['saved_by_retry']} 次")
    
    return response.status_code == 200


def demo_scenario_2():
    """场景2：网络超时自动重试 → 最终成功"""
    print_section("场景 2：网络超时自动重试")
    print("  说明：网络超时抛出异常，自愈客户端自动重试，最终成功")
    print()
    
    # 创建模拟客户端（抛出异常）
    mock_client = MockAPIClient()
    mock_client.fail_count = 0  # 不模拟失败
    
    # 修改模拟行为：第一次抛出 ConnectionError
    original_simulate = mock_client._simulate_request
    
    def simulate_with_exception(endpoint: str):
        if mock_client.call_count == 1:
            print(f"    📡 请求 #1: 模拟 ConnectionError")
            raise ConnectionError("Connection refused")
        else:
            print(f"    📡 请求 #{mock_client.call_count}: 返回 200 成功")
            return MockResponse(200, {"id": 456, "name": "超时恢复商品", "price": 199.99})
    
    mock_client._simulate_request = simulate_with_exception
    
    # 创建自愈客户端
    retry_config = APIRetryConfig(
        max_retries=3,
        base_delay=0.1,
        max_delay=0.5,
        backoff_factor=2.0
    )
    healing_client = SelfHealingAPIClient(mock_client, retry_config)
    
    # 发送请求
    print("  开始请求...")
    response = healing_client.get('/api/products/2')
    
    # 检查结果
    print()
    print_result("请求成功", response.status_code == 200,
                f"状态码: {response.status_code}")
    print_result("数据正确", response.json().get('name') == "超时恢复商品",
                f"商品名: {response.json().get('name')}")
    
    # 打印自愈统计
    stats = healing_client.get_stats()
    print(f"\n  🛡️ 自愈统计:")
    print(f"    总请求数: {stats['total_requests']}")
    print(f"    重试次数: {stats['total_retries']}")
    print(f"    自愈成功: {stats['saved_by_retry']} 次")
    
    return response.status_code == 200


def demo_scenario_3():
    """场景3：连续失败 → 重试耗尽后返回最后响应"""
    print_section("场景 3：连续失败（重试耗尽）")
    print("  说明：服务器持续返回 500 错误，重试 3 次后返回最后响应")
    print()
    
    # 创建模拟客户端（持续失败）
    mock_client = MockAPIClient()
    mock_client.fail_count = 10  # 所有请求都失败
    
    # 创建自愈客户端
    retry_config = APIRetryConfig(
        max_retries=3,
        base_delay=0.1,
        max_delay=0.5,
        backoff_factor=2.0
    )
    healing_client = SelfHealingAPIClient(mock_client, retry_config)
    
    # 发送请求
    print("  开始请求...")
    response = healing_client.get('/api/products/3')
    
    # 检查结果
    print()
    print_result("返回最后响应", response.status_code == 500,
                f"状态码: {response.status_code}（重试耗尽）")
    
    # 打印自愈统计
    stats = healing_client.get_stats()
    print(f"\n  🛡️ 自愈统计:")
    print(f"    总请求数: {stats['total_requests']}")
    print(f"    重试次数: {stats['total_retries']}")
    print(f"    自愈失败: {stats['failed_after_retry']} 次")
    
    return response.status_code == 500


def demo_scenario_4():
    """场景4：404 错误 → 不重试（直接返回）"""
    print_section("场景 4：404 错误（不重试）")
    print("  说明：404 是业务错误，自愈客户端不会重试，直接返回")
    print()
    
    # 创建模拟客户端（返回 404）
    mock_client = MockAPIClient()
    mock_client.fail_count = 0  # 不模拟失败
    
    # 修改模拟行为：返回 404
    def simulate_404(endpoint: str):
        print(f"    📡 请求 #1: 返回 404 Not Found")
        return MockResponse(404, {"error": "Product not found"})
    
    mock_client._simulate_request = simulate_404
    
    # 创建自愈客户端
    retry_config = APIRetryConfig(
        max_retries=3,
        base_delay=0.1,
        max_delay=0.5,
        backoff_factor=2.0
    )
    healing_client = SelfHealingAPIClient(mock_client, retry_config)
    
    # 发送请求
    print("  开始请求...")
    response = healing_client.get('/api/products/999')
    
    # 检查结果
    print()
    print_result("直接返回 404", response.status_code == 404,
                f"状态码: {response.status_code}（未重试）")
    
    # 打印自愈统计
    stats = healing_client.get_stats()
    print(f"\n  🛡️ 自愈统计:")
    print(f"    总请求数: {stats['total_requests']}")
    print(f"    重试次数: {stats['total_retries']}（404 不重试）")
    
    return response.status_code == 404


def demo_scenario_5():
    """场景5：限流 429 → 自动重试"""
    print_section("场景 5：限流 429（自动重试）")
    print("  说明：429 限流错误属于可重试错误，自愈客户端会自动重试")
    print()
    
    # 创建模拟客户端
    mock_client = MockAPIClient()
    mock_client.fail_count = 0  # 不模拟失败
    
    # 修改模拟行为：第一次返回 429，第二次成功
    def simulate_429_then_success(endpoint: str):
        if mock_client.call_count == 1:
            print(f"    📡 请求 #1: 返回 429 Too Many Requests")
            return MockResponse(429, {"error": "Too Many Requests"})
        else:
            print(f"    📡 请求 #{mock_client.call_count}: 返回 200 成功")
            return MockResponse(200, {"id": 789, "name": "限流恢复商品", "price": 299.99})
    
    mock_client._simulate_request = simulate_429_then_success
    
    # 创建自愈客户端
    retry_config = APIRetryConfig(
        max_retries=3,
        base_delay=0.1,
        max_delay=0.5,
        backoff_factor=2.0
    )
    healing_client = SelfHealingAPIClient(mock_client, retry_config)
    
    # 发送请求
    print("  开始请求...")
    response = healing_client.get('/api/products/4')
    
    # 检查结果
    print()
    print_result("限流后成功", response.status_code == 200,
                f"状态码: {response.status_code}")
    print_result("数据正确", response.json().get('name') == "限流恢复商品",
                f"商品名: {response.json().get('name')}")
    
    # 打印自愈统计
    stats = healing_client.get_stats()
    print(f"\n  🛡️ 自愈统计:")
    print(f"    总请求数: {stats['total_requests']}")
    print(f"    重试次数: {stats['total_retries']}")
    print(f"    自愈成功: {stats['saved_by_retry']} 次")
    
    return response.status_code == 200


def print_final_report(results: list):
    """打印最终报告"""
    print_section("演示报告")
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    
    print(f"\n  总计: {total} 个场景")
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print()
    
    for result in results:
        icon = "✅" if result['passed'] else "❌"
        print(f"  {icon} {result['name']}")
    
    print()


def main():
    """主函数"""
    print("="*60)
    print(" 🛡️ API 自愈演示")
    print("="*60)
    print(f"  演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  演示场景: 5 个")
    print("="*60)
    
    results = []
    
    # 运行演示场景
    results.append({
        'name': '场景1: 500 错误自动重试',
        'passed': demo_scenario_1()
    })
    
    results.append({
        'name': '场景2: 网络超时自动重试',
        'passed': demo_scenario_2()
    })
    
    results.append({
        'name': '场景3: 连续失败（重试耗尽）',
        'passed': demo_scenario_3()
    })
    
    results.append({
        'name': '场景4: 404 错误（不重试）',
        'passed': demo_scenario_4()
    })
    
    results.append({
        'name': '场景5: 限流 429（自动重试）',
        'passed': demo_scenario_5()
    })
    
    # 打印最终报告
    print_final_report(results)
    
    # 返回退出码
    failed = sum(1 for r in results if not r['passed'])
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
