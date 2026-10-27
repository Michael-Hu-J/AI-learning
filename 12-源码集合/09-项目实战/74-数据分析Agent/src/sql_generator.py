"""SQL 生成器"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Callable

logger = logging.getLogger(__name__)


class SQLGenerator:
    """SQL 生成器"""

    def __init__(self, schema_manager, llm_call_func: Optional[Callable] = None):
        self.schema = schema_manager
        self.llm = llm_call_func

    def generate(self, question: str) -> Tuple[str, List[str]]:
        """
        根据自然语言问题生成 SQL
        返回 (SQL语句, 使用的表名列表)
        """
        schema_text = self.schema.get_schema_text()

        prompt = (
            f"你是一名数据分析师。根据用户问题生成 SQL 查询语句。\n\n"
            f"数据库表结构：\n{schema_text}\n\n"
            f"用户问题：{question}\n\n"
            f"要求：\n"
            f"1. 只输出 SQL 语句，不要其他解释\n"
            f"2. SQL 使用标准 MySQL 语法\n"
            f"3. 注意聚合函数和 GROUP BY 的正确使用\n"
            f"4. 涉及金额的计算要准确（如销售额 = 单价 * 数量）\n"
            f"5. 只使用上述表中存在的字段\n"
        )

        if self.llm:
            sql = self.llm(prompt)
        else:
            sql = self._fallback_generate(question)

        # 清理 SQL
        sql = self._clean_sql(sql)

        # 提取使用的表名
        used_tables = self._extract_tables(sql)

        logger.info(f"SQL 生成: {len(sql)} 字符, 使用表: {used_tables}")
        return sql, used_tables

    @staticmethod
    def _clean_sql(sql: str) -> str:
        """清理 SQL 语句"""
        # 去除 markdown 代码块标记
        sql = re.sub(r"^```(?:sql)?\s*", "", sql.strip())
        sql = re.sub(r"\s*```$", "", sql.strip())
        # 去除首尾空白
        sql = sql.strip()
        # 保证以分号结尾
        if sql and not sql.endswith(";"):
            sql += ";"
        return sql

    @staticmethod
    def _fallback_generate(question: str) -> str:
        """无 LLM 时的降级 SQL 生成"""
        if "用户数" in question or "统计用户" in question:
            return "SELECT COUNT(*) AS user_count FROM users;"
        elif "销售额" in question:
            return "SELECT SUM(price * quantity) AS total_sales FROM orders;"
        return "SELECT 1;"

    @staticmethod
    def _extract_tables(sql: str) -> List[str]:
        """从 SQL 中提取使用的表名"""
        tables = []
        patterns = [
            r"FROM\s+(\w+)",
            r"JOIN\s+(\w+)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)
        return list(set(tables))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.schema_manager import SchemaManager, TableSchema, Column

    schema_mgr = SchemaManager()
    schema_mgr.add_table(TableSchema(
        table_name="users",
        description="用户表",
        aliases=["用户", "用户信息"],
        columns=[
            Column("id", "INT", "用户ID", is_primary_key=True),
            Column("name", "VARCHAR(100)", "用户姓名"),
            Column("age", "INT", "年龄"),
            Column("city", "VARCHAR(50)", "所在城市"),
            Column("created_at", "DATETIME", "注册时间"),
        ],
    ))
    schema_mgr.add_table(TableSchema(
        table_name="orders",
        description="订单表",
        aliases=["订单", "订单信息"],
        columns=[
            Column("id", "INT", "订单ID", is_primary_key=True),
            Column("user_id", "INT", "用户ID", is_foreign_key=True, references="users.id"),
            Column("product_id", "INT", "商品ID"),
            Column("price", "DECIMAL(10,2)", "单价"),
            Column("quantity", "INT", "数量"),
            Column("amount", "DECIMAL(10,2)", "总金额"),
            Column("created_at", "DATETIME", "下单时间"),
        ],
    ))

    def mock_llm(prompt):
        return "SELECT name, SUM(amount) AS total FROM orders JOIN users ON orders.user_id = users.id GROUP BY name ORDER BY total DESC LIMIT 10;"

    generator = SQLGenerator(schema_mgr, mock_llm)
    sql, tables = generator.generate("销售额最高的十个用户")
    print(f"\n生成 SQL: {sql}")
    print(f"使用表: {tables}")
