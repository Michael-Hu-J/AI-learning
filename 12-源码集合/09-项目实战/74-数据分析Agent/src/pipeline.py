"""数据分析Agent 完整流程"""

import logging
from typing import Optional, Dict
from dataclasses import dataclass, field

from src.schema_manager import SchemaManager
from src.sql_generator import SQLGenerator
from src.sql_validator import SQLValidator, SQLValidationResult
from src.sql_executor import SQLExecutor
from src.data_analyzer import DataAnalyzer, AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Agent 完整结果"""
    question: str
    sql: str
    validation: SQLValidationResult
    execution: Optional[Dict] = None
    analysis: Optional[AnalysisResult] = None
    error: str = ""


class DataAnalysisAgent:
    """数据分析Agent 完整流程"""

    def __init__(self, schema_manager: SchemaManager, llm_call_func=None,
                 mock_data: Optional[dict] = None):
        self.schema = schema_manager
        self.generator = SQLGenerator(schema_manager, llm_call_func)
        self.validator = SQLValidator()
        self.executor = SQLExecutor(mock_data)
        self.analyzer = DataAnalyzer()
        logger.info("数据分析Agent 初始化完成")

    def query(self, question: str) -> AgentResult:
        """执行完整查询流程"""
        result = AgentResult(question=question, sql="", validation=SQLValidationResult())

        try:
            # 1. 生成 SQL
            sql, tables = self.generator.generate(question)
            result.sql = sql

            # 2. 校验 SQL
            validation = self.validator.validate(sql, self.schema)
            result.validation = validation

            if not validation.is_valid:
                result.error = f"SQL 校验失败: {', '.join(validation.errors)}"
                return result

            # 3. 执行查询
            execution = self.executor.execute(sql)
            result.execution = execution

            # 4. 分析结果
            data = execution.get("rows", [])
            analysis = self.analyzer.analyze(question, sql, data)
            result.analysis = analysis

            logger.info(f"查询完成: {question} -> {execution.get('row_count', 0)} 行")

        except Exception as e:
            result.error = str(e)
            logger.error(f"查询失败: {e}")

        return result
