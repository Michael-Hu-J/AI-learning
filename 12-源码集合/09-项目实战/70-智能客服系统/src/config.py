"""配置加载模块"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "app": {
        "name": "智能客服系统",
        "version": "1.0.0",
        "debug": False,
    },
    "conversation": {
        "max_history": 20,
        "session_timeout": 1800,  # 30 分钟
        "max_rounds": 5,
    },
    "retrieval": {
        "top_k": 3,
        "knowledge_base_path": "data/knowledge_base.json",
    },
    "llm": {
        "enabled": False,
        "provider": "dashscope",
        "model": "qwen-plus",
        "api_key": "",
        "base_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    },
}


class Config:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self._config = DEFAULT_CONFIG.copy()
        if config_path:
            self.load_from_file(config_path)
        self._load_from_env()

    def load_from_file(self, path: str) -> None:
        """从 YAML 文件加载配置"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
            if file_config:
                self._deep_merge(self._config, file_config)
                logger.info(f"配置已从 {path} 加载")
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")

    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        if os.environ.get("DASHSCOPE_API_KEY"):
            self._config["llm"]["api_key"] = os.environ["DASHSCOPE_API_KEY"]
            self._config["llm"]["enabled"] = True
        if os.environ.get("CUSTOM_BOT_DEBUG"):
            self._config["app"]["debug"] = os.environ["CUSTOM_BOT_DEBUG"].lower() == "true"

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_section(self, section: str) -> Dict:
        """获取配置段"""
        return self._config.get(section, {})

    @property
    def config(self) -> Dict:
        """返回完整配置"""
        return self._config

    def __repr__(self) -> str:
        return f"Config({self._config})"


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置工厂函数"""
    return Config(config_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    print("默认配置:")
    print(config)
    print(f"\nmax_history: {config.get('conversation.max_history')}")
    print(f"top_k: {config.get('retrieval.top_k')}")
    print(f"LLM 启用: {config.get('llm.enabled')}")
