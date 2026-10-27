DANGEROUS_KEYWORDS = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]

class SQLValidator:
    DANGEROUS_KEYWORDS = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]

    def validate(self, sql: str, schema_mgr) -> SQLValidationResult:
        result = SQLValidationResult()
        self._check_safety(sql, result)
        self._check_syntax(sql, result)
        self._check_schema(sql, schema_mgr, result)
        if result.errors:
            result.is_valid = False
        return result

# 正常查询应该通过
validator.validate("SELECT * FROM users;", schema_mgr)  # is_valid=True

# DELETE必须拦截
validator.validate("DELETE FROM users;", schema_mgr)  # is_valid=False

# 多语句注入必须拦截
validator.validate("SELECT * FROM users; DROP TABLE users;", schema_mgr)  # is_valid=False

# 注释注入必须警告
validator.validate("SELECT * FROM users; -- DROP TABLE users", schema_mgr)  # has_warning=True

# 未知表必须警告
validator.validate("SELECT * FROM nonexistent;", schema_mgr)  # has_warning=True

# 括号不匹配必须拦截
validator.validate("SELECT * FROM users WHERE id IN (1, 2, 3;", schema_mgr)  # is_valid=False

# 按表名解析
schema_mgr.resolve_table("users")  # 返回 users 表的 Schema

# 按别名解析
schema_mgr.resolve_table("用户")   # 也返回 users 表的 Schema

# 未知表返回None
schema_mgr.resolve_table("nonexistent")  # 返回 None

@staticmethod
def _clean_sql(sql: str) -> str:
    # 去除 markdown 代码块标记
    sql = re.sub(r"^

def test_text2sql_end_to_end():
    # 初始化
    schema_mgr = SchemaManager()
    schema_mgr.load_from_json("samples/schema.json")
    agent = DataAnalysisAgent(schema_mgr, mock_llm)

    # 正常查询
    result = agent.query("销售额最高的十个用户")
    assert result.validation.is_valid
    assert result.execution is not None
    assert result.execution["row_count"] > 0

    # 危险查询应该被拦截
    result = agent.query("删除所有用户")
    assert not result.validation.is_valid
    assert "DELETE" in result.error or "危险" in result.error

analyzer = DataAnalyzer()
data = [
    {"name": "商品A", "sales": 120000},
    {"name": "商品B", "sales": 95000},
    {"name": "商品C", "sales": 110000},
]
result = analyzer.analyze("销售额最高的商品", "SELECT ...", data)
assert result.chart_type == "bar"  # 有分类+数值，推荐柱状图
assert "3" in result.summary  # 摘要里应该有记录数
assert len(result.anomalies) == 0  # 数据均匀，无异常
