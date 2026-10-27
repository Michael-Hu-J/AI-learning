"""
=============================================================================
 config.py — 配置管理模块
 作者: 测试员周周 (14年测试老兵)
 描述: 集中管理问答机器人的全部配置参数，支持 YAML 文件加载与环境变量覆盖
 用法:
   config = load_config("config.yaml")
   # 或使用默认路径
   config = load_config()
=============================================================================
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("qa_bot.config")


def _merge_env_overrides(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    环境变量覆盖规则：
      QA_BOT_KNOWLEDGE_BASE_PATH       → cfg["knowledge_base"]["path"]
      QA_BOT_RETRIEVAL_TOP_K            → cfg["retrieval"]["top_k"]
      QA_BOT_RETRIEVAL_THRESHOLD        → cfg["retrieval"]["threshold"]
      QA_BOT_GENERATION_MAX_LENGTH      → cfg["generation"]["max_length"]
      QA_BOT_QUALITY_PASS_THRESHOLD     → cfg["quality"]["pass_threshold"]
    """
    env_map = {
        "QA_BOT_KNOWLEDGE_BASE_PATH": ("knowledge_base", "path"),
        "QA_BOT_RETRIEVAL_TOP_K": ("retrieval", "top_k"),
        "QA_BOT_RETRIEVAL_THRESHOLD": ("retrieval", "threshold"),
        "QA_BOT_GENERATION_MAX_LENGTH": ("generation", "max_length"),
        "QA_BOT_QUALITY_PASS_THRESHOLD": ("quality", "pass_threshold"),
    }
    for env_key, keys in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            # 尝试转成数值类型
            try:
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
            except ValueError:
                pass  # 保留字符串
            # 逐级深入到 dict 中
            target = cfg
            for k in keys[:-1]:
                target = target.setdefault(k, {})
            target[keys[-1]] = val
            logger.info("环境变量 %s 覆盖配置: %s = %s", env_key, ".".join(keys), val)
    return cfg


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件，支持环境变量覆盖。
    默认搜索路径：
      1. 当前目录下的 config.yaml
      2. 项目根目录下的 config.yaml
      3. ../config.yaml
    """
    if config_path is None:
        search_paths = [
            Path.cwd() / "config.yaml",
            Path(__file__).resolve().parent.parent / "config.yaml",
            Path(__file__).resolve().parent.parent.parent / "config.yaml",
        ]
        for sp in search_paths:
            if sp.exists():
                config_path = str(sp)
                break

    if config_path is None or not os.path.exists(config_path):
        logger.warning("未找到配置文件，使用默认配置")
        return get_default_config()

    logger.info("加载配置文件: %s", config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg = _merge_env_overrides(cfg)
    return cfg


def get_default_config() -> Dict[str, Any]:
    """返回硬编码的默认配置（当配置文件不存在时使用）"""
    return {
        "app": {
            "name": "智能问答机器人",
            "version": "1.0.0",
            "debug": False,
        },
        "knowledge_base": {
            "path": "data/knowledge",
            "auto_load": True,
            "index_refresh_interval": 300,  # 秒
        },
        "retrieval": {
            "top_k": 5,
            "threshold": 0.15,
            "keyword_weight": 0.4,
            "semantic_weight": 0.4,
            "freshness_weight": 0.2,
            "enable_synonym_expansion": True,
        },
        "generation": {
            "max_length": 200,
            "temperature": 0.3,
            "enable_fallback": True,
        },
        "quality": {
            "pass_threshold": 0.7,
            "factual_weight": 0.35,
            "relevance_weight": 0.25,
            "safety_weight": 0.25,
            "completeness_weight": 0.15,
        },
        "rejection": {
            "message": "抱歉，我暂时没有找到相关信息。建议您联系人工客服。",
            "fallback_message": "抱歉，我暂时没有找到相关信息。",
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "file": "logs/qa_bot.log",
        },
    }


def validate_config(cfg: Dict[str, Any]) -> bool:
    """校验配置参数的合法性"""
    errors = []

    # retrieval 校验
    retrieval = cfg.get("retrieval", {})
    top_k = retrieval.get("top_k", 5)
    if not isinstance(top_k, int) or top_k < 1:
        errors.append("retrieval.top_k 必须为正整数")

    threshold = retrieval.get("threshold", 0.15)
    if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 1):
        errors.append("retrieval.threshold 必须在 [0, 1] 范围内")

    # quality 校验
    quality = cfg.get("quality", {})
    pass_threshold = quality.get("pass_threshold", 0.7)
    if not isinstance(pass_threshold, (int, float)) or not (0 <= pass_threshold <= 1):
        errors.append("quality.pass_threshold 必须在 [0, 1] 范围内")

    if errors:
        for e in errors:
            logger.error("配置校验失败: %s", e)
        return False
    return True


# ---------- 快捷导出 ----------
__all__ = [
    "load_config",
    "get_default_config",
    "validate_config",
]
