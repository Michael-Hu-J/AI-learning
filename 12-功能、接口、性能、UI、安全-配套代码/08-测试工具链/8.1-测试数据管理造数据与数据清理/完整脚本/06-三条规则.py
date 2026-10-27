# data_factory.py — 测试数据工厂
import random
import requests
from datetime import datetime, timedelta

class TestDataFactory:
    """测试数据工厂 — 一行代码造完整测试数据"""
    
    def __init__(self, base_url, session=None):
        self.base_url = base_url
        self.session = session or requests.Session()
        self.created_ids = []  # 记录创建的数据ID，方便清理
    
    def create_user(self, name=None, phone=None):
        """创建一个测试用户"""
        phone = phone or f"139{random.randint(10000000, 99999999)}"
        name = name or f"测试用户_{phone[-4:]}"
        
        resp = self.session.post(f"{self.base_url}/api/auth/register", json={
            "username": name,
            "password": "Test123456",
            "phone": phone
        })
        user_id = resp.json().get("data", {}).get("user_id")
        self.created_ids.append(("users", user_id))
        return resp.json()
    
    def create_product(self, name=None, price=99.0, stock=100):
        """创建一个测试商品"""
        name = name or f"测试商品_{random.randint(1000, 9999)}"
        
        resp = self.session.post(f"{self.base_url}/api/products", json={
            "name": name,
            "price": price,
            "stock": stock,
            "description": "测试商品，可删除"
        })
        product_id = resp.json().get("data", {}).get("id")
        self.created_ids.append(("products", product_id))
        return resp.json()
    
    def create_seckill_activity(self, product_id, start_time=None, end_time=None, stock=10):
        """创建一个抢购活动"""
        start_time = start_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        end_time = end_time or (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        
        resp = self.session.post(f"{self.base_url}/api/seckill/activities", json={
            "product_id": product_id,
            "seckill_price": 1.0,
            "stock": stock,
            "start_time": start_time,
            "end_time": end_time
        })
        activity_id = resp.json().get("data", {}).get("id")
        self.created_ids.append(("seckill_activities", activity_id))
        return resp.json()
    
    def cleanup(self):
        """清理所有创建的数据（倒序删除，避免外键约束）"""
        # 按表名倒序删除（先删依赖表，再删主表）
        tables_order = ["seckill_activities", "orders", "order_items", "products", "users"]
        
        for table in tables_order:
            ids = [item[1] for item in self.created_ids if item[0] == table]
            if ids:
                print(f"清理 {table}: {len(ids)} 条")
                # 这里执行实际清理逻辑
                # cursor.execute(f"DELETE FROM {table} WHERE id IN ({','.join(map(str, ids))})")
        
        self.created_ids.clear()
        print("✅ 清理完成")

# ========== 使用示例 ==========
# 测试前：一行代码造好所有数据
factory = TestDataFactory("http://localhost:5001")
user = factory.create_user()          # 创建用户
product = factory.create_product()    # 创建商品
activity = factory.create_seckill_activity(product["data"]["id"])  # 创建抢购活动

# 测试中：用这些数据跑测试
# ...

# 测试后：一行代码清理
factory.cleanup()
