"""SQL 执行器（模拟）"""

import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class SQLExecutor:
    """SQL 执行器（模拟）"""

    def __init__(self, mock_data: Dict[str, List[Dict]] = None):
        self.mock_data = mock_data or {}

    def execute(self, sql: str) -> Dict:
        """执行 SQL 查询"""
        rows = self._mock_execute(sql)
        result = {
            "success": True,
            "sql": sql,
            "rows": rows,
            "row_count": len(rows),
            "execution_time_ms": 50,
        }
        logger.info(f"SQL 执行: {len(rows)} 行")
        return result

    def _mock_execute(self, sql: str) -> List[Dict]:
        """模拟 SQL 执行"""
        sql_upper = sql.upper()

        if "COUNT" in sql_upper:
            return [{"user_count": 1523}]
        elif "SUM" in sql_upper and "sales" in sql.lower():
            return [{"total_sales": 2400000.00}]
        elif "LIMIT" in sql_upper:
            limit_match = re.search(r"LIMIT\s+(\d+)", sql, re.IGNORECASE)
            limit = int(limit_match.group(1)) if limit_match else 10
            return [
                {"name": f"用户{i}", "total": 100000 - i * 5000}
                for i in range(min(limit, 10))
            ]
        elif "GROUP BY" in sql_upper:
            return [
                {"name": "用户A", "total": 95000},
                {"name": "用户B", "total": 120000},
                {"name": "用户C", "total": 88000},
            ]
        return [{"result": "无数据"}]
