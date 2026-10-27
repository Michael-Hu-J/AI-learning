"""
配置管理模块
~~~~~~~~~~~~
读取 YAML 配置，提供全局配置对象供各模块使用。

作者：测试员周周（14 年测试老兵）
"""
import os
import yaml
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 默认配置（当 config.yaml 加载失败时使用）
DEFAULT_CONFIG = {
    "app": {
        "name": "多模态应用",
        "version": "1.0.0",
        "debug": False,
    },
    "image": {
        "max_size_mb": 20,
        "supported_formats": [".jpg", ".jpeg", ".png", ".webp", ".bmp"],
        "min_resolution": [100, 100],
        "quality_threshold": 0.5,
    },
    "audio": {
        "max_size_mb": 50,
        "supported_formats": [".mp3", ".wav", ".m4a", ".ogg", ".flac"],
        "max_duration_sec": 3600,
    },
    "ocr": {
        "confidence_threshold": 0.6,
        "min_chinese_ratio": 0.3,
        "max_chinese_ratio": 0.9,
        "high_confidence": 0.85,
        "medium_confidence": 0.7,
        "low_confidence": 0.6,
        "no_text_confidence": 0.0,
    },
    "quality_check": {
        "blur_threshold": 100.0,
        "brightness_min": 30,
        "brightness_max": 240,
        "contrast_min": 20,
        "min_text_length": 5,
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    },
}


class Config:
    """配置管理类 - 单例模式，全局只加载一次配置"""

    _instance = None
    _data: Dict[str, Any] = None

    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self, config_path: str = None):
        if self._loaded:
            return
        self._data = dict(DEFAULT_CONFIG)  # 深拷贝默认配置
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
        self._loaded = True
        logger.info("配置加载完成")

    def _load_from_file(self, config_path: str):
        """从 YAML 文件加载配置"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
            if file_config and isinstance(file_config, dict):
                self._deep_merge(self._data, file_config)
                logger.info("从 %s 加载配置成功", config_path)
            else:
                logger.warning("配置文件 %s 为空或格式错误，使用默认配置", config_path)
        except Exception as e:
            logger.error("加载配置文件 %s 失败: %s，使用默认配置", config_path, e)

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """深度合并字典，override 覆盖 base"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, *keys: str, default=None):
        """按层级获取配置值，例如 config.get('image', 'max_size_mb')"""
        current = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @property
    def data(self) -> Dict[str, Any]:
        """获取完整配置数据"""
        return self._data

    def reload(self, config_path: str):
        """重新加载配置（测试用）"""
        self._data = dict(DEFAULT_CONFIG)
        if os.path.exists(config_path):
            self._load_from_file(config_path)
        logger.info("配置已重新加载")
