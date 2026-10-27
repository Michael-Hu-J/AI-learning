# test_data_generator.py - 测试数据生成工具
"""
测试数据生成工具
功能：生成测试所需的各种数据（手机号、邮箱、密码、OTP验证码等）
"""
import random
import string
import datetime
from typing import Dict, Any, Optional
from utils.logger import Logger

logger = Logger().get_logger()


class TestDataGenerator:
    """测试数据生成器"""
    
    _context: Dict[str, Any] = {}  # 用于存储上下文数据，如从前一个响应中提取的值
    
    @staticmethod
    def reset_context():
        """重置上下文数据"""
        TestDataGenerator._context = {}
        logger.debug("测试数据上下文已重置")
    
    @staticmethod
    def set_context(key: str, value: Any):
        """设置上下文数据（用于存储从前一个响应中提取的值）"""
        TestDataGenerator._context[key] = value
        logger.debug(f"设置上下文数据: {key} = {value}")
    
    @staticmethod
    def get_context(key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return TestDataGenerator._context.get(key, default)
    
    @staticmethod
    def generate_mobile() -> str:
        """
        生成手机号（随机，最多20个字符）
        
        返回：
        - str: 手机号
        """
        # 生成10-20位数字
        length = random.randint(10, 20)
        mobile = ''.join(random.choices(string.digits, k=length))
        logger.debug(f"生成手机号: {mobile}")
        return mobile
    
    @staticmethod
    def get_area_code() -> str:
        """
        获取手机区号（默认+84）
        
        返回：
        - str: 手机区号，如"+84"
        """
        return "+84"
    
    @staticmethod
    def generate_email() -> str:
        """
        生成邮箱地址
        格式：随机字符或数字 + @qq.com 或 @163.com
        
        返回：
        - str: 邮箱地址
        """
        # 随机选择邮箱域名
        domains = ["@qq.com", "@163.com"]
        domain = random.choice(domains)
        
        # 生成前缀（数字或字符，长度5-15）
        prefix_length = random.randint(5, 15)
        # 使用字母和数字
        prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=prefix_length))
        
        email = f"{prefix}{domain}"
        logger.debug(f"生成邮箱: {email}")
        return email
    
    @staticmethod
    def generate_otp_code() -> str:
        """
        生成OTP验证码
        规则：当前时间的小时重复2遍，小时必须为2位数
        如 16:00 -> "1616"，18:19 -> "1818"，07:30 -> "0707"
        
        返回：
        - str: OTP验证码（4位数）
        """
        now = datetime.datetime.now()
        hour_str = str(now.hour).zfill(2)  # 保证是2位数，如16 -> "16", 7 -> "07"
        otp_code = hour_str * 2  # 重复2遍，如"1616", "0707"
        logger.debug(f"生成OTP验证码（当前时间 {now.strftime('%H:%M')}，小时 {now.hour} -> {hour_str}，OTP: {otp_code}）")
        return otp_code
    
    @staticmethod
    def generate_string_with_length(length: int, prefix: str = "", suffix: str = "", 
                                   charset: str = None) -> str:
        """
        生成指定长度的字符串
        
        参数：
        - length: 字符串长度
        - prefix: 前缀（如果指定，前缀不计入长度）
        - suffix: 后缀（如果指定，后缀不计入长度）
        - charset: 字符集（默认使用字母和数字）
        
        返回：
        - str: 指定长度的字符串
        """
        if charset is None:
            charset = string.ascii_letters + string.digits
        
        # 计算需要生成的中间部分长度
        middle_length = max(0, length - len(prefix) - len(suffix))
        
        # 生成中间随机字符
        middle = ''.join(random.choices(charset, k=middle_length))
        
        result = f"{prefix}{middle}{suffix}"
        logger.debug(f"生成 {length} 个字符的字符串（实际长度: {len(result)}）")
        return result
    
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
        
        # 保证包含各种字符类型
        lowercase = random.choice(string.ascii_lowercase)
        uppercase = random.choice(string.ascii_uppercase)
        digit = random.choice(string.digits)
        # 符号集合
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        symbol = random.choice(symbols)
        
        # 生成剩余字符（混合使用所有类型）
        all_chars = string.ascii_letters + string.digits + symbols
        remaining = ''.join(random.choices(all_chars, k=length - 4))
        
        # 组合并随机打乱
        password_chars = list(lowercase + uppercase + digit + symbol + remaining)
        random.shuffle(password_chars)
        password = ''.join(password_chars)
        
        logger.debug(f"生成密码（长度 {len(password)}）: {'*' * len(password)}")
        return password
    
    @staticmethod
    def extract_from_response(response_data: Any, path: str) -> Optional[Any]:
        """
        从响应数据中提取值
        
        参数：
        - response_data: 响应数据（dict或嵌套dict）
        - path: 数据路径，支持点号分隔，如 "data.otpSessionId" 或 "data.extra.ivsSession.sessionId"
        
        返回：
        - Any: 提取的值，如果不存在返回None
        """
        if not isinstance(response_data, dict):
            logger.warning(f"响应数据不是字典类型，无法提取路径: {path}")
            return None
        
        keys = path.split('.')
        value = response_data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    logger.debug(f"路径 {path} 中的键 {key} 不存在")
                    return None
            else:
                logger.debug(f"路径 {path} 中的键 {key} 对应的值不是字典类型")
                return None
        
        logger.debug(f"从响应中提取到值: {path} = {value}")
        return value
    
    @staticmethod
    def resolve_value(value: Any, previous_responses: Dict[str, Any] = None) -> Any:
        """
        解析值，支持动态生成和从响应中提取
        
        参数：
        - value: 原始值（可能是字符串占位符）
        - previous_responses: 之前的响应数据字典，格式：{"step_1": {...}, "step_2": {...}}
        
        返回：
        - Any: 解析后的值
        
        支持的占位符：
        - {generate_mobile}: 生成手机号
        - {generate_email}: 生成邮箱
        - {generate_password}: 生成密码
        - {generate_otp_code}: 生成OTP验证码
        - {area_code}: 获取区号（+84）
        - {context:key}: 从上下文获取值
        - {response:step_N.path}: 从之前的响应中提取值，如 {response:step_1.data.otpSessionId}
        """
        if not isinstance(value, str):
            return value
        
        # 检查是否是占位符
        if not (value.startswith('{') and value.endswith('}')):
            return value
        
        placeholder = value[1:-1]  # 去掉花括号
        
        # 生成手机号
        if placeholder == "generate_mobile":
            return TestDataGenerator.generate_mobile()
        
        # 生成邮箱
        elif placeholder == "generate_email":
            return TestDataGenerator.generate_email()
        
        # 生成密码
        elif placeholder == "generate_password":
            return TestDataGenerator.generate_password()
        
        # 生成OTP验证码
        elif placeholder == "generate_otp_code":
            # 优先使用mobile_change的OTP发送小时（修改手机号流程）
            # 否则使用注册流程的OTP发送小时
            # 如果都没有，使用当前小时
            mobile_change_otp_send_hour = TestDataGenerator.get_context('mobile_change_otp_send_hour')
            otp_send_hour = TestDataGenerator.get_context('otp_send_hour')
            
            if mobile_change_otp_send_hour is not None:
                # 使用修改手机号OTP发送时的小时
                hour_str = str(mobile_change_otp_send_hour).zfill(2)
                otp_code = hour_str * 2
                logger.debug(f"使用修改手机号OTP发送时的小时 {mobile_change_otp_send_hour} 生成OTP验证码: {otp_code}")
                return otp_code
            elif otp_send_hour is not None:
                # 使用注册流程OTP发送时的小时
                hour_str = str(otp_send_hour).zfill(2)
                otp_code = hour_str * 2
                logger.debug(f"使用注册流程OTP发送时的小时 {otp_send_hour} 生成OTP验证码: {otp_code}")
                return otp_code
            else:
                # 使用当前小时
                return TestDataGenerator.generate_otp_code()
        
        # 获取区号
        elif placeholder == "area_code":
            return TestDataGenerator.get_area_code()
        
        # 从上下文获取
        elif placeholder.startswith("context:"):
            key = placeholder[8:]  # 去掉"context:"前缀
            context_value = TestDataGenerator.get_context(key)
            if context_value is None:
                logger.warning(f"上下文中不存在键: {key}")
            return context_value
        
        # 从之前的响应中提取
        elif placeholder.startswith("response:") and previous_responses:
            # 格式：response:step_N.path.to.value
            path_part = placeholder[9:]  # 去掉"response:"前缀
            
            # 分离step名称和数据路径
            parts = path_part.split('.', 1)
            if len(parts) != 2:
                logger.warning(f"无效的响应路径格式: {path_part}")
                return value
            
            step_key, data_path = parts
            step_response = previous_responses.get(step_key)
            
            if step_response is None:
                logger.warning(f"未找到步骤响应: {step_key}")
                return value
            
            # 从响应中提取
            response_data = step_response.get("response", {})
            extracted_value = TestDataGenerator.extract_from_response(response_data, data_path)
            
            if extracted_value is None:
                logger.warning(f"无法从响应中提取路径: {data_path}")
                return value
            
            return extracted_value
        
        # 未知的占位符，返回原值
        logger.warning(f"未知的占位符: {placeholder}")
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

