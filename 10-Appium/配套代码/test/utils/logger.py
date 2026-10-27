# logger.py - 日志工具类
"""
日志工具类
功能：统一管理测试过程中的日志输出
通俗理解：就像写日记，记录测试过程中发生的所有事情，方便出问题时查看
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


class Logger:
    """
    日志工具类
    
    作用：
    1. 统一日志格式
    2. 同时输出到控制台和文件
    3. 自动按日期创建日志文件
    4. 支持日志轮转（文件太大时自动创建新文件）
    """
    
    def __init__(self, name="mobile_test", log_dir="logs"):
        """
        初始化日志器
        
        参数说明：
        - name: 日志器名称
        - log_dir: 日志文件存放目录
        """
        self.name = name
        self.log_dir = log_dir
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """
        配置日志器
        """
        # 创建日志目录
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # 创建logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if self.logger.handlers:
            return
        
        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台handler（输出到终端）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件handler（输出到文件）
        log_file = os.path.join(
            self.log_dir, 
            f"test_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # 保留5个备份文件
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def get_logger(self):
        """
        获取logger实例
        
        返回：
        - logger: logging.Logger实例
        """
        return self.logger
    
    def debug(self, message):
        """记录DEBUG级别日志"""
        self.logger.debug(message)
    
    def info(self, message):
        """记录INFO级别日志"""
        self.logger.info(message)
    
    def warning(self, message):
        """记录WARNING级别日志"""
        self.logger.warning(message)
    
    def error(self, message):
        """记录ERROR级别日志"""
        self.logger.error(message)
    
    def critical(self, message):
        """记录CRITICAL级别日志"""
        self.logger.critical(message)

