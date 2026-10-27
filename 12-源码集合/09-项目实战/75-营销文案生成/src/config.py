"""配置管理"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class GenerationConfig:
    max_versions: int = 3
    max_length: int = 500
    min_length: int = 50
    temperature_low: float = 0.3
    temperature_medium: float = 0.7
    temperature_high: float = 0.9


@dataclass
class StyleStrategy:
    name: str = ""
    description: str = ""
    keywords: List[str] = field(default_factory=list)


@dataclass
class ComplianceConfig:
    banned_words: List[str] = field(default_factory=list)
    industry_rules: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class EvaluationMetric:
    name: str = ""
    weight: float = 0.0
    description: str = ""


@dataclass
class AppConfig:
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    styles: List[StyleStrategy] = field(default_factory=list)
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)
    evaluation_metrics: List[EvaluationMetric] = field(default_factory=list)
    llm_enabled: bool = False
    llm_provider: str = ""
    llm_model: str = ""
    log_level: str = "INFO"
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """加载配置文件"""
    path = Path(config_path)
    if not path.exists():
        return AppConfig()
    
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    config = AppConfig()
    
    # 生成配置
    gen = raw.get("generation", {})
    config.generation = GenerationConfig(
        max_versions=gen.get("max_versions", 3),
        max_length=gen.get("max_length", 500),
        min_length=gen.get("min_length", 50),
        temperature_low=gen.get("temperature_range", {}).get("low", 0.3),
        temperature_medium=gen.get("temperature_range", {}).get("medium", 0.7),
        temperature_high=gen.get("temperature_range", {}).get("high", 0.9),
    )
    
    # 风格策略
    for s in raw.get("style", {}).get("strategies", []):
        config.styles.append(StyleStrategy(
            name=s.get("name", ""),
            description=s.get("description", ""),
            keywords=s.get("keywords", []),
        ))
    
    # 合规配置
    comp = raw.get("compliance", {})
    config.compliance = ComplianceConfig(
        banned_words=comp.get("banned_words", []),
        industry_rules=comp.get("industry_rules", {}),
    )
    
    # 评估指标
    for m in raw.get("evaluation", {}).get("metrics", []):
        config.evaluation_metrics.append(EvaluationMetric(
            name=m.get("name", ""),
            weight=m.get("weight", 0.0),
            description=m.get("description", ""),
        ))
    
    # LLM配置
    llm = raw.get("llm", {})
    config.llm_enabled = llm.get("enabled", False)
    config.llm_provider = llm.get("provider", "")
    config.llm_model = llm.get("model", "")
    
    # 日志配置
    log = raw.get("logging", {})
    config.log_level = log.get("level", "INFO")
    config.log_format = log.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    return config
