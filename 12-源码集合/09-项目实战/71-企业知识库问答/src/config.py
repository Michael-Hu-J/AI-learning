"""配置加载模块"""

import os
import copy
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "app": {
        "name": "企业知识库问答系统",
        "version": "1.0.0",
        "debug": False,
    },
    "parsing": {
        "chunk_size": 300,
        "chunk_overlap": 50,
        "supported_formats": [".md", ".txt", ".html", ".htm"],
    },
    "retrieval": {
        "top_k": 5,
        "min_score": 0.3,
        "docs_path": "docs",
        "index_path": "data/index.json",
    },
    "llm": {
        "enabled": False,
        "provider": "dashscope",
        "model": "qwen-plus",
        "api_key": "",
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    },
}


class Config:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self._config = copy.deepcopy(DEFAULT_CONFIG)
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
        if os.environ.get("KB_QA_DEBUG"):
            self._config["app"]["debug"] = os.environ["KB_QA_DEBUG"].lower() == "true"

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
    print(f"\nchunk_size: {config.get('parsing.chunk_size')}")
    print(f"top_k: {config.get('retrieval.top_k')}")
    print(f"LLM 启用: {config.get('llm.enabled')}")
