"""示例代码文件 - 数据工具"""


def migrate_data(source_db: str, target_db: str, table_name: str) -> int:
    """从源数据库迁移数据到目标数据库"""
    import sqlite3
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)

    try:
        cursor = source_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        target_cursor = target_conn.cursor()
        migrated = 0
        for row in rows:
            target_cursor.execute(
                f"INSERT OR IGNORE INTO {table_name} VALUES ({','.join(['?'] * len(row))})", row
            )
            migrated += 1

        target_conn.commit()
        return migrated
    finally:
        source_conn.close()
        target_conn.close()


def process_records(data: list) -> list:
    """处理数据记录"""
    result = []
    for record in data:
        if record.get("status") == "active":
            result.append(record)
    return result
