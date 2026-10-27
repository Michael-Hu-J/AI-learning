"""合规检查模块"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import re


@dataclass
class ComplianceIssue:
    """合规问题"""
    word: str = ""
    position: int = 0
    rule: str = ""
    severity: str = "warning"
    suggestion: str = ""
    
    def __str__(self):
        return f"[{self.severity.upper()}] 第{self.position}位: '{self.word}' - {self.rule}"


class ComplianceChecker:
    """合规检查器"""
    
    BANNED_WORDS = [
        "最", "第一", "唯一", "绝对", "100%", "无效退款",
        "有效率", "治愈率", "三天见效", "永不", "顶级", "国家级",
    ]
    
    def __init__(self, banned_words=None, industry_rules=None):
        self.banned_words = banned_words or self.BANNED_WORDS
        self.industry_rules = industry_rules or {}
    
    def check(self, text, industry=""):
        """检查文案合规性"""
        issues = []
        
        for word in self.banned_words:
            pos = text.find(word)
            while pos != -1:
                issues.append(ComplianceIssue(
                    word=word, position=pos,
                    rule=f"广告法禁用词：'{word}'",
                    severity="critical",
                    suggestion="替换为中性表述",
                ))
                pos = text.find(word, pos + 1)
        
        if industry and industry in self.industry_rules:
            rule_config = self.industry_rules[industry]
            if isinstance(rule_config, dict):
                for pattern in rule_config.get("banned_patterns", []):
                    for match in re.finditer(pattern, text):
                        issues.append(ComplianceIssue(
                            word=match.group(),
                            position=match.start(),
                            rule=f"行业限制",
                            severity="error",
                            suggestion="修改为合规表述",
                        ))
        
        issues.sort(key=lambda x: x.position)
        return issues
    
    def is_compliant(self, text, industry=""):
        issues = self.check(text, industry)
        critical = [i for i in issues if i.severity == "critical"]
        errors = [i for i in issues if i.severity == "error"]
        return len(critical) == 0 and len(errors) == 0, issues
    
    def get_compliance_score(self, text, industry=""):
        issues = self.check(text, industry)
        if not issues:
            return 100.0
        penalty = sum(
            30 if i.severity == "critical" else
            15 if i.severity == "error" else 5
            for i in issues
        )
        return max(0, 100 - penalty)
