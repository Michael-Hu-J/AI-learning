#!/usr/bin/env python3
# test_data_generator.py - 测试数据生成工具
"""
测试数据生成工具
功能：生成测试所需的各种数据（用户名、邮箱、密码、商品名等）
适用于电商系统 API 自动化测试
"""
import random
import string
import datetime
from typing import Dict, Any, Optional


class TestDataGenerator:
    """测试数据生成器"""
    
    _context: Dict[str, Any] = {}  # 用于存储上下文数据
    
    @staticmethod
    def reset_context():
        """重置上下文数据"""
        TestDataGenerator._context = {}
    
    @staticmethod
    def set_context(key: str, value: Any):
        """设置上下文数据（用于存储从前一个响应中提取的值）"""
        TestDataGenerator._context[key] = value
    
    @staticmethod
    def get_context(key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return TestDataGenerator._context.get(key, default)
    
    @staticmethod
    def generate_username(length: int = 8) -> str:
        """
        生成用户名
        格式：test + 随机字母数字
        
        返回：
        - str: 用户名
        """
        prefix = "test"
        suffix_length = max(1, length - len(prefix))
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=suffix_length))
        username = f"{prefix}{suffix}"
        return username
    
    @staticmethod
    def generate_email() -> str:
        """
        生成邮箱地址
        格式：随机字符 + @example.com
        
        返回：
        - str: 邮箱地址
        """
        domains = ["@example.com", "@test.com", "@demo.com"]
        domain = random.choice(domains)
        
        prefix_length = random.randint(5, 12)
        prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=prefix_length))
        
        email = f"{prefix}{domain}"
        return email
    
    @staticmethod
    def generate_password(length: int = 12) -> str:
        """
        生成密码
        规则：8-32位，包含大小写字母+数字+符号
        
        参数：
        - length: 密码长度（默认12，范围8-32）
        
        返回：
        - str: 密码
        """
        if length < 8:
            length = 8
        elif length > 32:
            length = 32
        
        lowercase = random.choice(string.ascii_lowercase)
        uppercase = random.choice(string.ascii_uppercase)
        digit = random.choice(string.digits)
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        symbol = random.choice(symbols)
        
        all_chars = string.ascii_letters + string.digits + symbols
        remaining = ''.join(random.choices(all_chars, k=length - 4))
        
        password_chars = list(lowercase + uppercase + digit + symbol + remaining)
        random.shuffle(password_chars)
        password = ''.join(password_chars)
        
        return password
    
    @staticmethod
    def generate_product_name() -> str:
        """
        生成商品名称
        格式：品牌 + 品类 + 随机后缀
        
        返回：
        - str: 商品名称
        """
        brands = ["TechPro", "SmartLife", "EcoPlus", "UltraMax", "GreenWay"]
        categories = ["耳机", "充电宝", "智能手表", "键盘", "鼠标", "摄像头", "音箱", "路由器"]
        suffixes = ["Pro", "Max", "Plus", "Ultra", "Lite", ""]
        
        brand = random.choice(brands)
        category = random.choice(categories)
        suffix = random.choice(suffixes)
        
        if suffix:
            return f"{brand} {category} {suffix}"
        return f"{brand} {category}"
    
    @staticmethod
    def generate_price(min_price: float = 10.0, max_price: float = 9999.0) -> float:
        """
        生成价格
        
        参数：
        - min_price: 最低价格
        - max_price: 最高价格
        
        返回：
        - float: 价格（保留2位小数）
        """
        price = round(random.uniform(min_price, max_price), 2)
        return price
    
    @staticmethod
    def generate_seckill_price(regular_price: float) -> float:
        """
        生成秒杀价格（通常为原价的3-7折）
        
        参数：
        - regular_price: 原价
        
        返回：
        - float: 秒杀价格
        """
        discount = random.uniform(0.3, 0.7)
        seckill_price = round(regular_price * discount, 2)
        return seckill_price
    
    @staticmethod
    def generate_stock(min_stock: int = 10, max_stock: int = 1000) -> int:
        """
        生成库存数量
        
        参数：
        - min_stock: 最小库存
        - max_stock: 最大库存
        
        返回：
        - int: 库存数量
        """
        return random.randint(min_stock, max_stock)
    
    @staticmethod
    def generate_order_id() -> str:
        """
        生成订单号
        格式：ORD + 时间戳 + 随机后缀
        
        返回：
        - str: 订单号
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD{timestamp}{suffix}"
    
    @staticmethod
    def generate_seckill_order_id() -> str:
        """
        生成秒杀订单号
        格式：SK + 时间戳 + 随机后缀
        
        返回：
        - str: 秒杀订单号
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"SK{timestamp}{suffix}"
    
    @staticmethod
    def generate_date(days_ahead: int = None) -> str:
        """
        生成日期字符串
        
        参数：
        - days_ahead: 从今天起多少天后（None 表示今天）
        
        返回：
        - str: ISO格式日期
        """
        if days_ahead is None:
            days_ahead = random.randint(1, 30)
        
        target_date = datetime.datetime.now() + datetime.timedelta(days=days_ahead)
        return target_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    @staticmethod
    def resolve_value(value: Any, previous_responses: Dict[str, Any] = None) -> Any:
        """
        解析值，支持动态生成和从响应中提取
        
        支持的占位符：
        - {generate_username}: 生成用户名
        - {generate_email}: 生成邮箱
        - {generate_password}: 生成密码
        - {generate_product_name}: 生成商品名
        - {generate_price}: 生成价格
        - {generate_stock}: 生成库存
        - {generate_order_id}: 生成订单号
        - {generate_seckill_order_id}: 生成秒杀订单号
        - {context:key}: 从上下文获取值
        
        参数：
        - value: 原始值（可能是字符串占位符）
        - previous_responses: 之前的响应数据字典
        
        返回：
        - Any: 解析后的值
        """
        if not isinstance(value, str):
            return value
        
        # 检查是否是占位符
        if not (value.startswith('{') and value.endswith('}')):
            return value
        
        placeholder = value[1:-1]  # 去掉花括号
        
        # 生成用户名
        if placeholder == "generate_username":
            return TestDataGenerator.generate_username()
        
        # 生成邮箱
        elif placeholder == "generate_email":
            return TestDataGenerator.generate_email()
        
        # 生成密码
        elif placeholder == "generate_password":
            return TestDataGenerator.generate_password()
        
        # 生成商品名
        elif placeholder == "generate_product_name":
            return TestDataGenerator.generate_product_name()
        
        # 生成价格
        elif placeholder == "generate_price":
            return TestDataGenerator.generate_price()
        
        # 生成库存
        elif placeholder == "generate_stock":
            return TestDataGenerator.generate_stock()
        
        # 生成订单号
        elif placeholder == "generate_order_id":
            return TestDataGenerator.generate_order_id()
        
        # 生成秒杀订单号
        elif placeholder == "generate_seckill_order_id":
            return TestDataGenerator.generate_seckill_order_id()
        
        # 从上下文获取
        elif placeholder.startswith("context:"):
            key = placeholder[8:]  # 去掉"context:"前缀
            context_value = TestDataGenerator.get_context(key)
            return context_value
        
        # 未知的占位符，返回原值
        return value
    
    @staticmethod
    def process_request_data(data: Any, previous_responses: Dict[str, Any] = None) -> Any:
        """
        处理请求数据，替换所有占位符
        
        参数：
        - data: 请求数据（可能是dict、list或字符串）
        - previous_responses: 之前的响应数据
        
        返回：
        - Any: 处理后的数据
        """
        if isinstance(data, dict):
            processed = {}
            for key, value in data.items():
                processed[key] = TestDataGenerator.process_request_data(value, previous_responses)
            return processed
        elif isinstance(data, list):
            return [TestDataGenerator.process_request_data(item, previous_responses) for item in data]
        elif isinstance(data, str):
            return TestDataGenerator.resolve_value(data, previous_responses)
        else:
            return data
