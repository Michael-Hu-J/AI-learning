# config_reader.py - 配置文件读取工具
"""
配置文件读取工具
功能：读取yaml配置文件和.env环境变量
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class ConfigReader:
    """
    配置读取类
    """
    
    def __init__(self, config_file="config.yaml"):
        """
        初始化配置读取器
        
        参数：
        - config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """
        加载YAML配置文件
        """
        config_path = Path(__file__).parent.parent / self.config_file
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def get(self, key_path: str, default=None):
        """
        获取配置值（支持点号分隔的路径）
        
        参数：
        - key_path: 配置键路径，如 "appium.server_url"
        - default: 默认值
        
        示例：
        config.get("appium.server_url")
        config.get("test.default_timeout", 10)
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                # 如果配置文件中没有，尝试从环境变量读取
                env_key = key_path.upper().replace('.', '_')
                env_value = os.getenv(env_key)
                if env_value is not None:
                    return env_value
                return default
        
        return value if value is not None else default
    
    def get_appium_config(self):
        """
        获取Appium配置
        """
        return {
            "server_url": self.get("appium.server_url", "http://localhost:4723"),
            "timeout": self.get("appium.timeout", 300)
        }
    
    def get_android_config(self):
        """
        获取Android配置
        """
        return {
            "platform_version": os.getenv("ANDROID_PLATFORM_VERSION") or 
                              self.get("android.platform_version", "11.0"),
            "device_name": os.getenv("ANDROID_DEVICE_NAME") or 
                          self.get("android.device_name", "Android Emulator"),
            "app_package": os.getenv("APP_PACKAGE") or 
                          self.get("android.app_package", ""),
            "app_activity": os.getenv("APP_ACTIVITY") or 
                           self.get("android.app_activity", ""),
            "automation_name": self.get("android.automation_name", "UiAutomator2"),
            "no_reset": self.get("android.no_reset", True),
            "full_reset": self.get("android.full_reset", False),
            "auto_grant_permissions": self.get("android.auto_grant_permissions", True)
        }
    
    def get_ios_config(self):
        """
        获取iOS配置
        """
        return {
            "platform_version": os.getenv("IOS_PLATFORM_VERSION") or 
                              self.get("ios.platform_version", "15.0"),
            "device_name": os.getenv("IOS_DEVICE_NAME") or 
                          self.get("ios.device_name", "iPhone 13"),
            "bundle_id": os.getenv("BUNDLE_ID") or 
                        self.get("ios.bundle_id", ""),
            "automation_name": self.get("ios.automation_name", "XCUITest"),
            "no_reset": self.get("ios.no_reset", True),
            "full_reset": self.get("ios.full_reset", False)
        }
    
    def get_test_config(self):
        """
        获取测试配置
        """
        return {
            "default_timeout": self.get("test.default_timeout", 10),
            "implicit_wait": self.get("test.implicit_wait", 5),
            "screenshot_on_failure": self.get("test.screenshot_on_failure", True),
            "screenshot_dir": self.get("test.screenshot_dir", "screenshots"),
            "retry_count": self.get("test.retry_count", 3),
            "retry_delay": self.get("test.retry_delay", 1.0)
        }

