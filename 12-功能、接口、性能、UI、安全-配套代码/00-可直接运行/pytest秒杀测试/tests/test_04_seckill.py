"""秒杀模块测试 — 核心：防超卖验证"""
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor

class TestSeckill:
    """秒杀抢购测试"""
    
    @pytest.fixture
    def seckill_product(self, admin_api):
        """创建一个秒杀活动"""
        # 先创建一个商品
        resp = admin_api.post("/api/products",
                             json={"name": "秒杀测试商品", "price": 0.01})
        product_id = resp.json()["data"]["id"]
        
        # 创建一个秒杀活动（假设有对应接口）
        resp = admin_api.post("/api/seckill/create", json={
            "product_id": product_id,
            "stock": 10,  # 只有 10 个库存
            "start_time": "2026-06-07 00:00:00",
            "end_time": "2026-06-08 23:59:59"
        })
        seckill_id = resp.json().get("data", {}).get("id", product_id)
        
        yield {"product_id": product_id, "seckill_id": seckill_id, "stock": 10}
        
        # 清理
        admin_api.delete(f"/api/products/{product_id}")
    
    def test_seckill_single_user(self, base_url, seckill_product):
        """单用户正常秒杀"""
        # 注册一个新用户
        import requests
        resp = requests.post(f"{base_url}/api/auth/register",
                            json={"username": "seckill_test1", 
                                  "password": "test123"})
        user_token = resp.json().get("token", "")
        
        headers = {"Authorization": f"Bearer {user_token}"}
        resp = requests.post(f"{base_url}/api/seckill/{seckill_product['seckill_id']}/buy",
                            headers=headers)
        assert resp.status_code in [200, 201]
    
    def test_seckill_oversell_check(self, base_url, seckill_product):
        """并发秒杀 — 验证防超卖"""
        stock = seckill_product["stock"]
        results = []
        errors = []
        
        def seckill(user_id):
            """模拟一个用户抢购"""
            import requests
            try:
                # 注册新用户
                username = f"seckill_user_{user_id}"
                resp = requests.post(f"{base_url}/api/auth/register",
                                    json={"username": username, 
                                          "password": "test123"})
                if resp.status_code != 200:
                    errors.append(f"用户 {username} 注册失败")
                    return None
                
                token = resp.json().get("token", "")
                headers = {"Authorization": f"Bearer {token}"}
                
                # 抢购
                resp = requests.post(
                    f"{base_url}/api/seckill/{seckill_product['seckill_id']}/buy",
                    headers=headers, timeout=10
                )
                return resp.status_code
            except Exception as e:
                errors.append(f"用户 {user_id} 异常：{e}")
                return None
        
        # 50 个用户同时抢 10 个库存
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(seckill, range(stock * 5)))
        
        # 统计成功数量
        success_count = sum(1 for r in results if r in [200, 201])
        
        print(f"\n⚡ 并发测试结果：")
        print(f"   库存：{stock}")
        print(f"   抢购成功：{success_count}")
        print(f"   总请求：{len(results)}")
        
        # 关键断言：成功数不能超过库存
        assert success_count <= stock, f"❌ 防超卖失败！成功 {success_count} > 库存 {stock}"
        assert success_count > 0, "❌ 一个都没抢到，检查秒杀服务"
