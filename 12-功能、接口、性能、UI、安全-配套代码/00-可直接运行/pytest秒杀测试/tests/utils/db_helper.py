"""数据库验证工具"""
import pymysql


class DbHelper:
    """连接数据库，用于验证数据落库是否正确"""

    def __init__(self, host, port, user, password, database):
        self.conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
        )

    def query_one(self, sql):
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchone()

    def query_all(self, sql):
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def execute(self, sql):
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
        self.conn.commit()

    def close(self):
        self.conn.close()
