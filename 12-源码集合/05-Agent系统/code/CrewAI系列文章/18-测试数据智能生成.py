# app/agents/data_generator.py
from crewai import Agent, LLM
from app.core.config import settings

def create_data_generator_agent():
    """创建测试数据生成专家 Agent"""
    
    llm = LLM(
        model=settings.OPENAI_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL
    )
    
    return Agent(
        role="测试数据生成专家 (Test Data Generator Expert)",
        goal="根据测试用例自动生成高质量的测试数据",
        backstory="""你是测试数据生成专家，擅长：
        1. 理解测试用例的数据需求
        2. 设计合理的数据规则
        3. 生成符合业务逻辑的测试数据
        4. 覆盖边界值和异常场景
        5. 保证数据可清理（幂等性）
        
        你有 10 年测试数据准备经验，生成过 100 万 + 测试数据。
        你相信：好的测试数据是测试成功的一半。
        
        你的数据生成原则：
        - 真实：符合业务逻辑
        - 全面：覆盖各种场景
        - 可清理：测试后能彻底清理
        - 可追溯：每个数据都有标记""",
        llm=llm,
        verbose=False
    )

# app/tasks/data_generation.py
from crewai import Task

def create_data_generation_task(test_cases: str, data_rules: str, agent):
    """创建数据生成任务"""
    
    return Task(
        description=f"""请根据以下测试用例和数据规则，生成测试数据：

## 测试用例
{test_cases}

## 数据规则
{data_rules}

请完成以下任务：

1. **数据需求分析**
   - 识别需要的数据类型
   - 确定每种数据的数量
   - 识别边界值和特殊场景

2. **数据规则设计**
   - 定义数据字段和格式
   - 设置数据约束
   - 设计数据关联关系

3. **数据生成**
   - 生成符合规则的测试数据
   - 覆盖正常场景和异常场景
   - 包含边界值数据

4. **数据验证**
   - 验证数据格式正确
   - 验证数据关联正确
   - 验证数据可清理

请按以下 JSON 格式输出：
{{
  "data_requirements": [
    {{
      "type": "数据类型",
      "count": 数量，
      "fields": ["字段 1", "字段 2"],
      "constraints": ["约束 1", "约束 2"]
    }}
  ],
  "generated_data": {{
    "users": [...],
    "products": [...],
    "orders": [...]
  }},
  "boundary_cases": [...],
  "cleanup_script": "清理 SQL 或脚本"
}}
""",
        expected_output="JSON 格式的测试数据",
        agent=agent
    )

# app/tools/data_generator.py
from crewai_tools import BaseTool
from faker import Faker
import random
from datetime import datetime, timedelta
from typing import List, Dict

class TestDataGeneratorTool(BaseTool):
    """测试数据生成工具"""
    
    name: str = "测试数据生成器"
    description: str = "根据规则生成测试数据"
    
    def __init__(self):
        super().__init__()
        self.fake = Faker('zh_CN')  # 中文数据
    
    def _run(self, data_type: str, count: int, rules: Dict) -> List[Dict]:
        """生成测试数据"""
        
        generators = {
            "user": self._generate_users,
            "product": self._generate_products,
            "order": self._generate_orders,
            "address": self._generate_addresses
        }
        
        generator = generators.get(data_type)
        if not generator:
            raise ValueError(f"不支持的数据类型：{data_type}")
        
        return generator(count, rules)
    
    def _generate_users(self, count: int, rules: Dict) -> List[Dict]:
        """生成用户数据"""
        
        users = []
        for i in range(count):
            user = {
                "username": f"test_user_{i}_{self.fake.random_number(6)}",
                "email": self.fake.email(),
                "phone": self.fake.phone_number(),
                "password": "Test@123456",  # 统一密码，方便测试
                "status": random.choice(["active", "inactive", "locked"]),
                "created_at": (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
                "_meta": {
                    "batch_id": rules.get("batch_id", "default"),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # 应用自定义规则
            if "custom_fields" in rules:
                user.update(rules["custom_fields"])
            
            users.append(user)
        
        return users
    
    def _generate_products(self, count: int, rules: Dict) -> List[Dict]:
        """生成商品数据"""
        
        products = []
        categories = ["电子产品", "服装", "食品", "图书", "家居"]
        
        for i in range(count):
            price = round(random.uniform(10, 10000), 2)
            
            product = {
                "name": f"{self.fake.catch_phrase()}_{i}",
                "category": random.choice(categories),
                "price": price,
                "stock": random.randint(0, 1000),
                "status": random.choice(["on_sale", "out_of_stock", "discontinued"]),
                "_meta": {
                    "batch_id": rules.get("batch_id", "default"),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # 边界值数据
            if rules.get("include_boundary", False):
                if i == 0:
                    product["price"] = 0.01  # 最小价格
                elif i == 1:
                    product["price"] = 999999.99  # 最大价格
                elif i == 2:
                    product["stock"] = 0  # 零库存
                elif i == 3:
                    product["stock"] = 99999  # 最大库存
            
            products.append(product)
        
        return products
    
    def _generate_orders(self, count: int, rules: Dict) -> List[Dict]:
        """生成订单数据"""
        
        orders = []
        statuses = ["pending", "paid", "shipped", "completed", "cancelled"]
        
        for i in range(count):
            order = {
                "order_no": f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{i:06d}",
                "user_id": rules.get("user_ids", [1])[i % len(rules.get("user_ids", [1]))],
                "total_amount": round(random.uniform(10, 10000), 2),
                "status": random.choice(statuses),
                "created_at": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "_meta": {
                    "batch_id": rules.get("batch_id", "default"),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            orders.append(order)
        
        return orders
    
    def _generate_addresses(self, count: int, rules: Dict) -> List[Dict]:
        """生成地址数据"""
        
        addresses = []
        for i in range(count):
            address = {
                "province": self.fake.province(),
                "city": self.fake.city(),
                "district": self.fake.district(),
                "street": self.fake.street_address(),
                "zip_code": self.fake.postcode(),
                "_meta": {
                    "batch_id": rules.get("batch_id", "default"),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            addresses.append(address)
        
        return addresses

# app/tools/data_validator.py
from crewai_tools import BaseTool
from typing import List, Dict

class DataValidatorTool(BaseTool):
    """数据验证工具"""
    
    name: str = "数据验证器"
    description: str = "验证生成的测试数据是否符合规则"
    
    def _run(self, data: List[Dict], rules: Dict) -> Dict:
        """验证数据"""
        
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {}
        }
        
        # 检查数量
        expected_count = rules.get("expected_count", len(data))
        if len(data) != expected_count:
            result["valid"] = False
            result["errors"].append(f"数据数量不匹配：期望{expected_count}，实际{len(data)}")
        
        # 检查必填字段
        required_fields = rules.get("required_fields", [])
        for item in data:
            for field in required_fields:
                if field not in item or item[field] is None:
                    result["valid"] = False
                    result["errors"].append(f"缺少必填字段：{field}")
        
        # 检查数据格式
        if "format_rules" in rules:
            for item in data:
                format_errors = self._check_format(item, rules["format_rules"])
                result["errors"].extend(format_errors)
                if format_errors:
                    result["valid"] = False
        
        # 统计数据
        result["stats"] = {
            "total_count": len(data),
            "valid_count": sum(1 for _ in data),
            "unique_count": len({str(item) for item in data})
        }
        
        return result
    
    def _check_format(self, item: Dict, rules: Dict) -> List[str]:
        """检查数据格式"""
        errors = []
        
        for field, format_rule in rules.items():
            if field in item:
                value = item[field]
                
                # 类型检查
                if "type" in format_rule:
                    expected_type = format_rule["type"]
                    if not isinstance(value, eval(expected_type)):
                        errors.append(f"字段{field}类型错误：期望{expected_type}，实际{type(value)}")
                
                # 范围检查
                if "min" in format_rule and value < format_rule["min"]:
                    errors.append(f"字段{field}值过小：{value} < {format_rule['min']}")
                if "max" in format_rule and value > format_rule["max"]:
                    errors.append(f"字段{field}值过大：{value} > {format_rule['max']}")
        
        return errors

# app/workflows/data_generation.py
from crewai import Crew, Process
from app.agents.data_generator import create_data_generator_agent
from app.tasks.data_generation import create_data_generation_task
from app.tools.data_generator import TestDataGeneratorTool
from app.tools.data_validator import DataValidatorTool
import json

async def generate_test_data(
    test_cases: str,
    data_rules: str,
    output_format: str = "json"
):
    """生成测试数据工作流"""
    
    # 1. 创建 Agent
    generator = create_data_generator_agent()
    
    # 2. 创建 Task
    generation_task = create_data_generation_task(test_cases, data_rules, generator)
    
    # 3. 执行生成
    crew = Crew(
        agents=[generator],
        tasks=[generation_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    
    # 4. 解析结果
    generated_data = json.loads(result.raw)
    
    # 5. 验证数据
    validator = DataValidatorTool()
    for data_type, data in generated_data.get("generated_data", {}).items():
        validation_result = validator.run(data, {"expected_count": len(data)})
        if not validation_result["valid"]:
            print(f"数据验证失败：{data_type}")
            print(f"错误：{validation_result['errors']}")
    
    # 6. 保存数据
    if output_format == "json":
        with open("generated_test_data.json", "w", encoding="utf-8") as f:
            json.dump(generated_data, f, ensure_ascii=False, indent=2)
    
    return generated_data

# 使用
test_cases = """
测试用例 1: 用户登录
  - 需要正常用户
  - 需要锁定用户
  - 需要不存在用户

测试用例 2: 商品下单
  - 需要有库存商品
  - 需要零库存商品
  - 需要下架商品
"""

data_rules = """
数据规则：
- 用户数量：100 个
- 商品数量：50 个
- 订单数量：20 个
- 包含边界值：是
- 批次 ID：batch_20260420
"""

data = asyncio.run(generate_test_data(test_cases, data_rules))

# app/database/data_importer.py
import sqlite3
from typing import List, Dict

class DatabaseImporter:
    """数据库导入器"""
    
    def __init__(self, db_url: str):
        self.conn = sqlite3.connect(db_url)
        self.cursor = self.conn.cursor()
    
    def import_users(self, users: List[Dict]):
        """导入用户数据"""
        
        for user in users:
            self.cursor.execute("""
                INSERT INTO users (username, email, phone, password, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user["username"],
                user["email"],
                user["phone"],
                user["password"],
                user["status"],
                user["created_at"]
            ))
        
        self.conn.commit()
    
    def import_products(self, products: List[Dict]):
        """导入商品数据"""
        
        for product in products:
            self.cursor.execute("""
                INSERT INTO products (name, category, price, stock, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                product["name"],
                product["category"],
                product["price"],
                product["stock"],
                product["status"]
            ))
        
        self.conn.commit()
    
    def cleanup(self, batch_id: str):
        """清理指定批次的数据"""
        
        # 删除用户
        self.cursor.execute("DELETE FROM users WHERE username LIKE ?", (f"%{batch_id}%",))
        
        # 删除商品
        self.cursor.execute("DELETE FROM products WHERE name LIKE ?", (f"%{batch_id}%",))
        
        self.conn.commit()
        print(f"已清理批次 {batch_id} 的数据")

# 清理脚本示例
def cleanup_test_data(batch_id: str):
    """清理测试数据"""
    
    # 1. 删除用户
    db.execute("DELETE FROM users WHERE username LIKE ?", (f"%{batch_id}%",))
    
    # 2. 删除商品
    db.execute("DELETE FROM products WHERE name LIKE ?", (f"%{batch_id}%",))
    
    # 3. 删除订单
    db.execute("DELETE FROM orders WHERE order_no LIKE ?", (f"%{batch_id}%",))
    
    # 4. 验证清理结果
    remaining = db.query("SELECT COUNT(*) FROM users WHERE username LIKE ?", (f"%{batch_id}%",))
    assert remaining == 0, "清理不彻底"
