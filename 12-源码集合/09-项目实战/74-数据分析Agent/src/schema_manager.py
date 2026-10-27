"""Schema 管理模块"""

import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Column:
    """数据库列定义"""
    name: str
    data_type: str  # INT, VARCHAR, DECIMAL, DATETIME 等
    description: str = ""
    is_primary_key: bool = False
    is_foreign_key: bool = False
    references: str = ""  # 外键引用的表.列

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "description": self.description,
            "is_primary_key": self.is_primary_key,
            "is_foreign_key": self.is_foreign_key,
            "references": self.references,
        }


@dataclass
class TableSchema:
    """数据库表结构"""
    table_name: str
    description: str = ""
    columns: List[Column] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)  # 业务别名

    def to_dict(self) -> Dict:
        return {
            "table_name": self.table_name,
            "description": self.description,
            "columns": [c.to_dict() for c in self.columns],
            "aliases": self.aliases,
        }


class SchemaManager:
    """数据库 Schema 管理器"""

    def __init__(self):
        self.tables: Dict[str, TableSchema] = {}
        logger.info("Schema 管理器初始化")

    def add_table(self, schema: TableSchema) -> None:
        """添加表结构"""
        self.tables[schema.table_name] = schema
        logger.info(f"添加表: {schema.table_name} ({len(schema.columns)} 列)")

    def load_from_json(self, filepath: str) -> int:
        """从 JSON 文件加载 Schema"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            tables = data.get("tables", [])
            count = 0
            for table_data in tables:
                columns = [Column(**c) for c in table_data.get("columns", [])]
                schema = TableSchema(
                    table_name=table_data["table_name"],
                    description=table_data.get("description", ""),
                    columns=columns,
                    aliases=table_data.get("aliases", []),
                )
                self.add_table(schema)
                count += 1
            logger.info(f"从 {filepath} 加载 {count} 个表")
            return count
        except Exception as e:
            logger.error(f"加载 Schema 失败: {e}")
            return 0

    def get_schema_text(self) -> str:
        """生成 Schema 描述文本，用于 Prompt"""
        parts = []
        for table_name, schema in self.tables.items():
            cols = ", ".join(
                f"{c.name}({c.data_type})" + (f" -- {c.description}" if c.description else "")
                for c in schema.columns
            )
            alias_text = ""
            if schema.aliases:
                alias_text = f" [业务别名: {', '.join(schema.aliases)}]"
            parts.append(f"- {table_name}{alias_text}: {cols}")
        return "\n".join(parts)

    def resolve_table(self, name: str) -> Optional[TableSchema]:
        """根据名称或别名解析表"""
        # 直接匹配
        if name in self.tables:
            return self.tables[name]
        # 别名匹配
        for schema in self.tables.values():
            if name in schema.aliases:
                return schema
        return None

    def get_stats(self) -> Dict:
        """获取 Schema 统计信息"""
        return {
            "total_tables": len(self.tables),
            "total_columns": sum(len(t.columns) for t in self.tables.values()),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mgr = SchemaManager()
    mgr.add_table(TableSchema(
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
    mgr.add_table(TableSchema(
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
    print("=" * 60)
    print("Schema 描述:")
    print("=" * 60)
    print(mgr.get_schema_text())
    print(f"\n统计: {mgr.get_stats()}")
