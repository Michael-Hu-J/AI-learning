"""配置加载模块"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "app": {"name": "代码生成助手", "version": "1.0.0", "debug": False},
    "llm": {
        "enabled": False,
        "provider": "dashscope",
        "model": "qwen-plus",
        "api_key": "",
        "max_tokens": 4096,
    },
    "quality": {
        "max_nesting_depth": 5,
        "max_lines": 200,
        "min_quality_score": 60,
    },
    "test": {
        "timeout": 30,
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    },
}


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self._config = DEFAULT_CONFIG.copy()
        if config_path:
            self.load_from_file(config_path)
        self._load_from_env()

    def load_from_file(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
            if file_config:
                self._deep_merge(self._config, file_config)
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")

    def _load_from_env(self) -> None:
        if os.environ.get("DASHSCOPE_API_KEY"):
            self._config["llm"]["api_key"] = os.environ["DASHSCOPE_API_KEY"]
            self._config["llm"]["enabled"] = True

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def config(self) -> Dict:
        return self._config


def load_config(config_path: Optional[str] = None) -> Config:
    return Config(config_path)
