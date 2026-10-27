"""SQL 校验器"""

import re
import logging
from typing import List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SQLValidationResult:
    """SQL 校验结果"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high


class SQLValidator:
    """SQL 校验器"""

    DANGEROUS_KEYWORDS = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]

    def validate(self, sql: str, schema_mgr) -> SQLValidationResult:
        """
        校验 SQL 语句
        检查：语法、安全性、表字段存在性
        """
        result = SQLValidationResult()

        # 1. 安全检查
        self._check_safety(sql, result)

        # 2. 语法检查
        self._check_syntax(sql, result)

        # 3. 表字段存在性检查
        self._check_schema(sql, schema_mgr, result)

        # 4. 风险评估
        if result.errors:
            result.is_valid = False
        if any(kw in sql.upper() for kw in self.DANGEROUS_KEYWORDS):
            result.risk_level = "high"
        elif result.warnings:
            result.risk_level = "medium"

        logger.info(f"SQL 校验: valid={result.is_valid}, risk={result.risk_level}")
        return result

    @staticmethod
    def _check_safety(sql: str, result: SQLValidationResult) -> None:
        """安全检查"""
        sql_upper = sql.upper()
        for kw in SQLValidator.DANGEROUS_KEYWORDS:
            if kw in sql_upper:
                result.errors.append(f"包含危险操作: {kw}")

        # 检查注释
        if "--" in sql or "/*" in sql:
            result.warnings.append("SQL 中包含注释，请确认安全性")

    @staticmethod
    def _check_syntax(sql: str, result: SQLValidationResult) -> None:
        """基础语法检查"""
        sql_upper = sql.upper().strip()

        if not sql_upper.startswith("SELECT"):
            result.errors.append("SQL 必须以 SELECT 开头")

        if "SELECT" in sql_upper and "FROM" not in sql_upper:
            result.errors.append("SELECT 语句缺少 FROM 子句")

        if sql.count("(") != sql.count(")"):
            result.errors.append("括号不匹配")

    @staticmethod
    def _check_schema(sql: str, schema_mgr, result: SQLValidationResult) -> None:
        """表字段存在性检查"""
        from src.sql_generator import SQLGenerator
        table_names = SQLGenerator._extract_tables(sql)
        for table_name in table_names:
            if schema_mgr.resolve_table(table_name) is None:
                result.warnings.append(f"未知表: {table_name}")
