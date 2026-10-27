# retry.py - 重试工具类
"""
重试工具类
功能：对失败的测试用例或操作进行重试
通俗理解：就像考试没考好可以补考，测试失败了可以再试一次，避免偶发性错误影响测试结果
"""
import time
from functools import wraps
from utils.logger import Logger

logger = Logger().get_logger()


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    重试装饰器
    
    参数说明：
    - max_attempts: 最大重试次数（包括首次尝试），默认3次
    - delay: 每次重试之间的延迟时间（秒），默认1秒
    - exceptions: 需要重试的异常类型，默认所有异常
    
    使用示例：
    @retry_on_failure(max_attempts=3, delay=2.0)
    def test_login():
        # 测试代码
        pass
    
    通俗理解：给函数加一个"保护罩"，如果执行失败了，会自动再试几次
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"执行 {func.__name__} - 尝试 {attempt}/{max_attempts}")
                    result = func(*args, **kwargs)
                    
                    if attempt > 1:
                        logger.info(f"{func.__name__} 在第 {attempt} 次尝试时成功")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"{func.__name__} 第 {attempt} 次尝试失败: {str(e)}"
                    )
                    
                    if attempt < max_attempts:
                        logger.info(f"等待 {delay} 秒后进行第 {attempt + 1} 次尝试...")
                        time.sleep(delay)
            
            # 所有尝试都失败
            logger.error(
                f"{func.__name__} 在 {max_attempts} 次尝试后仍然失败"
            )
            raise last_exception
        
        return wrapper
    return decorator


class RetryHelper:
    """
    重试辅助类
    
    作用：提供更灵活的重试方式，可以在代码中手动控制重试逻辑
    """
    
    @staticmethod
    def retry_operation(operation, max_attempts: int = 3, delay: float = 1.0, 
                       exceptions: tuple = (Exception,), *args, **kwargs):
        """
        重试执行某个操作
        
        参数说明：
        - operation: 要执行的操作（函数）
        - max_attempts: 最大重试次数
        - delay: 重试延迟
        - exceptions: 需要重试的异常类型
        - *args, **kwargs: 传递给operation的参数
        
        返回：
        - result: operation的执行结果
        
        使用示例：
        result = RetryHelper.retry_operation(
            self.click, 
            max_attempts=3,
            locator_type="id",
            locator_value="button"
        )
        """
        last_exception = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(f"执行操作 {operation.__name__} - 尝试 {attempt}/{max_attempts}")
                result = operation(*args, **kwargs)
                return result
                
            except exceptions as e:
                last_exception = e
                logger.warning(
                    f"操作 {operation.__name__} 第 {attempt} 次尝试失败: {str(e)}"
                )
                
                if attempt < max_attempts:
                    time.sleep(delay)
        
        logger.error(
            f"操作 {operation.__name__} 在 {max_attempts} 次尝试后仍然失败"
        )
        raise last_exception
    
    @staticmethod
    def retry_until_success(operation, max_attempts: int = 10, delay: float = 0.5,
                           success_condition=None, *args, **kwargs):
        """
        重试直到满足成功条件
        
        参数说明：
        - operation: 要执行的操作
        - max_attempts: 最大重试次数
        - delay: 重试延迟
        - success_condition: 成功条件（函数），如果返回True则认为成功
        - *args, **kwargs: 传递给operation的参数
        
        使用示例：
        # 重试点击直到元素出现
        RetryHelper.retry_until_success(
            self.click,
            success_condition=lambda: self.is_element_displayed("id", "result"),
            locator_type="id",
            locator_value="button"
        )
        """
        for attempt in range(1, max_attempts + 1):
            try:
                result = operation(*args, **kwargs)
                
                # 如果提供了成功条件，检查是否满足
                if success_condition:
                    if success_condition():
                        logger.info(f"操作 {operation.__name__} 在第 {attempt} 次尝试时成功")
                        return result
                else:
                    # 没有异常就认为成功
                    return result
                    
            except Exception as e:
                logger.debug(f"操作 {operation.__name__} 第 {attempt} 次尝试: {str(e)}")
            
            if attempt < max_attempts:
                time.sleep(delay)
        
        raise Exception(f"操作 {operation.__name__} 在 {max_attempts} 次尝试后仍未成功")

