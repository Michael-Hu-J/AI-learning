"""数据分析Agent 自动化测试"""

import sys
import os
import unittest
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schema_manager import SchemaManager, TableSchema, Column
from src.sql_generator import SQLGenerator
from src.sql_validator import SQLValidator, SQLValidationResult
from src.sql_executor import SQLExecutor
from src.data_analyzer import DataAnalyzer, AnalysisResult
from src.pipeline import DataAnalysisAgent, AgentResult
from src.config import Config, load_config, DEFAULT_CONFIG


# =============================================================================
# Schema 管理器测试
# =============================================================================

class TestSchemaManager(unittest.TestCase):
    """Schema 管理器测试"""

    def setUp(self):
        self.mgr = SchemaManager()
        self.mgr.add_table(TableSchema(
            table_name="users",
            description="用户表",
            aliases=["用户"],
            columns=[
                Column("id", "INT", "用户ID", is_primary_key=True),
                Column("name", "VARCHAR(100)", "姓名"),
                Column("city", "VARCHAR(50)", "城市"),
            ],
        ))
        self.mgr.add_table(TableSchema(
            table_name="orders",
            description="订单表",
            aliases=["订单"],
            columns=[
                Column("id", "INT", "订单ID", is_primary_key=True),
                Column("user_id", "INT", "用户ID"),
                Column("price", "DECIMAL(10,2)", "单价"),
                Column("quantity", "INT", "数量"),
                Column("amount", "DECIMAL(10,2)", "金额"),
            ],
        ))

    def test_add_table(self):
        self.assertEqual(len(self.mgr.tables), 2)

    def test_get_schema_text(self):
        text = self.mgr.get_schema_text()
        self.assertIn("users", text)
        self.assertIn("orders", text)
        self.assertIn("用户ID", text)

    def test_resolve_table_by_name(self):
        table = self.mgr.resolve_table("users")
        self.assertIsNotNone(table)
        self.assertEqual(table.table_name, "users")

    def test_resolve_table_by_alias(self):
        table = self.mgr.resolve_table("用户")
        self.assertIsNotNone(table)
        self.assertEqual(table.table_name, "users")

    def test_resolve_unknown_table(self):
        table = self.mgr.resolve_table("nonexistent")
        self.assertIsNone(table)

    def test_get_stats(self):
        stats = self.mgr.get_stats()
        self.assertEqual(stats["total_tables"], 2)
        self.assertEqual(stats["total_columns"], 8)

    def test_load_from_json(self):
        schema_data = {
            "tables": [
                {
                    "table_name": "products",
                    "description": "商品表",
                    "columns": [
                        {"name": "id", "data_type": "INT", "description": "商品ID"},
                        {"name": "name", "data_type": "VARCHAR(200)", "description": "商品名"},
                    ],
                    "aliases": ["商品"],
                }
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(schema_data, f)
            f.flush()
            count = self.mgr.load_from_json(f.name)
        os.unlink(f.name)
        self.assertEqual(count, 1)
        self.assertIn("products", self.mgr.tables)

    def test_load_from_nonexistent_file(self):
        count = self.mgr.load_from_json("/nonexistent/path/schema.json")
        self.assertEqual(count, 0)

    def test_empty_schema_text(self):
        empty_mgr = SchemaManager()
        text = empty_mgr.get_schema_text()
        self.assertEqual(text, "")

    def test_column_to_dict(self):
        col = Column("id", "INT", "ID", is_primary_key=True)
        d = col.to_dict()
        self.assertEqual(d["name"], "id")
        self.assertTrue(d["is_primary_key"])

    def test_table_schema_to_dict(self):
        schema = TableSchema(
            table_name="test",
            description="测试表",
            columns=[Column("id", "INT")],
            aliases=["测试"],
        )
        d = schema.to_dict()
        self.assertEqual(d["table_name"], "test")
        self.assertEqual(len(d["columns"]), 1)
        self.assertIn("测试", d["aliases"])


# =============================================================================
# SQL 生成器测试
# =============================================================================

class TestSQLGenerator(unittest.TestCase):
    """SQL 生成器测试"""

    def setUp(self):
        self.schema_mgr = SchemaManager()
        self.schema_mgr.add_table(TableSchema(
            table_name="users",
            description="用户表",
            aliases=["用户"],
            columns=[
                Column("id", "INT", "用户ID", is_primary_key=True),
                Column("name", "VARCHAR(100)", "姓名"),
                Column("city", "VARCHAR(50)", "城市"),
            ],
        ))
        self.schema_mgr.add_table(TableSchema(
            table_name="orders",
            description="订单表",
            aliases=["订单"],
            columns=[
                Column("id", "INT", "订单ID", is_primary_key=True),
                Column("user_id", "INT", "用户ID"),
                Column("price", "DECIMAL(10,2)", "单价"),
                Column("quantity", "INT", "数量"),
                Column("amount", "DECIMAL(10,2)", "金额"),
            ],
        ))

        def mock_llm(prompt):
            return "SELECT name, SUM(amount) AS total FROM orders JOIN users ON orders.user_id = users.id GROUP BY name ORDER BY total DESC LIMIT 10;"

        self.generator = SQLGenerator(self.schema_mgr, mock_llm)

    def test_sql_generation(self):
        sql, tables = self.generator.generate("销售额最高的十个用户")
        self.assertIn("SELECT", sql.upper())
        self.assertIn("FROM", sql.upper())
        self.assertGreater(len(tables), 0)

    def test_sql_cleaning(self):
        raw_sql = "```sql\nSELECT * FROM users;\n```"
        cleaned = SQLGenerator._clean_sql(raw_sql)
        self.assertNotIn("```", cleaned)
        self.assertTrue(cleaned.endswith(";"))

    def test_table_extraction(self):
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id;"
        tables = SQLGenerator._extract_tables(sql)
        self.assertIn("users", tables)
        self.assertIn("orders", tables)

    def test_fallback_generation(self):
        sql = SQLGenerator._fallback_generate("统计用户数")
        self.assertIn("COUNT", sql.upper())
        self.assertIn("users", sql.lower())

    def test_fallback_sales(self):
        sql = SQLGenerator._fallback_generate("销售额统计")
        self.assertIn("SUM", sql.upper())
        self.assertIn("price", sql.lower())
        self.assertIn("quantity", sql.lower())

    def test_clean_sql_adds_semicolon(self):
        raw = "SELECT * FROM users"
        cleaned = SQLGenerator._clean_sql(raw)
        self.assertTrue(cleaned.endswith(";"))

    def test_clean_sql_strips_markdown(self):
        raw = "```SELECT * FROM users;```"
        cleaned = SQLGenerator._clean_sql(raw)
        self.assertNotIn("```", cleaned)
        self.assertEqual(cleaned, "SELECT * FROM users;")

    def test_extract_tables_no_match(self):
        tables = SQLGenerator._extract_tables("SELECT 1;")
        self.assertEqual(tables, [])

    def test_fallback_unknown(self):
        sql = SQLGenerator._fallback_generate("未知问题")
        self.assertIn("SELECT", sql.upper())


# =============================================================================
# SQL 校验器测试
# =============================================================================

class TestSQLValidator(unittest.TestCase):
    """SQL 校验器测试"""

    def setUp(self):
        self.schema_mgr = SchemaManager()
        self.schema_mgr.add_table(TableSchema(
            table_name="users",
            columns=[Column("id", "INT"), Column("name", "VARCHAR(100)")],
        ))
        self.validator = SQLValidator()

    def test_valid_select(self):
        result = self.validator.validate("SELECT * FROM users;", self.schema_mgr)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.risk_level, "low")

    def test_dangerous_operation(self):
        result = self.validator.validate("DROP TABLE users;", self.schema_mgr)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.risk_level, "high")
        self.assertTrue(any("DROP" in err for err in result.errors))

    def test_missing_from(self):
        result = self.validator.validate("SELECT *;", self.schema_mgr)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("FROM" in err for err in result.errors))

    def test_unknown_table(self):
        result = self.validator.validate("SELECT * FROM nonexistent;", self.schema_mgr)
        self.assertTrue(result.is_valid)
        self.assertGreater(len(result.warnings), 0)

    def test_bracket_mismatch(self):
        result = self.validator.validate("SELECT * FROM users WHERE id IN (1, 2, 3;", self.schema_mgr)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("括号" in err for err in result.errors))

    def test_comment_injection(self):
        result = self.validator.validate("SELECT * FROM users; -- comment", self.schema_mgr)
        self.assertTrue(result.is_valid)
        self.assertTrue(any("注释" in w for w in result.warnings))

    def test_delete_operation(self):
        result = self.validator.validate("DELETE FROM users;", self.schema_mgr)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("DELETE" in err for err in result.errors))

    def test_truncate_operation(self):
        result = self.validator.validate("TRUNCATE TABLE users;", self.schema_mgr)
        self.assertFalse(result.is_valid)

    def test_insert_operation(self):
        result = self.validator.validate("INSERT INTO users VALUES (1);", self.schema_mgr)
        self.assertFalse(result.is_valid)

    def test_update_operation(self):
        result = self.validator.validate("UPDATE users SET name='test';", self.schema_mgr)
        self.assertFalse(result.is_valid)

    def test_alter_operation(self):
        result = self.validator.validate("ALTER TABLE users ADD COLUMN age INT;", self.schema_mgr)
        self.assertFalse(result.is_valid)

    def test_create_operation(self):
        result = self.validator.validate("CREATE TABLE test (id INT);", self.schema_mgr)
        self.assertFalse(result.is_valid)

    def test_validation_result_defaults(self):
        vr = SQLValidationResult()
        self.assertTrue(vr.is_valid)
        self.assertEqual(vr.errors, [])
        self.assertEqual(vr.warnings, [])
        self.assertEqual(vr.risk_level, "low")

    def test_block_comment_injection(self):
        result = self.validator.validate("SELECT /* comment */ * FROM users;", self.schema_mgr)
        self.assertTrue(any("注释" in w for w in result.warnings))


# =============================================================================
# SQL 执行器测试
# =============================================================================

class TestSQLExecutor(unittest.TestCase):
    """SQL 执行器测试"""

    def setUp(self):
        self.executor = SQLExecutor()

    def test_count_query(self):
        result = self.executor.execute("SELECT COUNT(*) FROM users;")
        self.assertTrue(result["success"])
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["rows"][0]["user_count"], 1523)

    def test_sum_query(self):
        result = self.executor.execute("SELECT SUM(price * quantity) AS total_sales FROM orders;")
        self.assertTrue(result["success"])
        self.assertEqual(result["rows"][0]["total_sales"], 2400000.00)

    def test_limit_query(self):
        result = self.executor.execute("SELECT * FROM users LIMIT 5;")
        self.assertTrue(result["success"])
        self.assertEqual(result["row_count"], 5)

    def test_group_by_query(self):
        result = self.executor.execute("SELECT name, SUM(amount) FROM orders GROUP BY name;")
        self.assertTrue(result["success"])
        self.assertGreater(result["row_count"], 0)

    def test_default_result(self):
        result = self.executor.execute("SELECT 1;")
        self.assertTrue(result["success"])
        self.assertEqual(result["rows"][0]["result"], "无数据")

    def test_execution_metadata(self):
        result = self.executor.execute("SELECT * FROM users;")
        self.assertIn("sql", result)
        self.assertIn("execution_time_ms", result)
        self.assertIn("rows", result)
        self.assertIn("row_count", result)

    def test_limit_zero(self):
        result = self.executor.execute("SELECT * FROM users LIMIT 0;")
        self.assertEqual(result["row_count"], 0)

    def test_limit_large(self):
        result = self.executor.execute("SELECT * FROM users LIMIT 999;")
        self.assertEqual(result["row_count"], 10)  # capped at 10


# =============================================================================
# 数据分析器测试
# =============================================================================

class TestDataAnalyzer(unittest.TestCase):
    """数据分析器测试"""

    def setUp(self):
        self.analyzer = DataAnalyzer()

    def test_summary_generation(self):
        data = [
            {"name": "A", "sales": 100},
            {"name": "B", "sales": 200},
            {"name": "C", "sales": 150},
        ]
        result = self.analyzer.analyze("销售数据", "SELECT ...", data)
        self.assertIn("3", result.summary)
        self.assertIn("100", result.summary)
        self.assertIn("200", result.summary)

    def test_chart_recommendation(self):
        data = [{"name": "A", "sales": 100}, {"name": "B", "sales": 200}]
        result = self.analyzer.analyze("销售数据", "SELECT ...", data)
        self.assertEqual(result.chart_type, "bar")

    def test_empty_data(self):
        result = self.analyzer.analyze("无数据", "SELECT ...", [])
        self.assertIn("空", result.summary)
        self.assertGreater(len(result.anomalies), 0)

    def test_anomaly_detection(self):
        data = [
            {"value": 100}, {"value": 102}, {"value": 98},
            {"value": 101}, {"value": 99}, {"value": 103},
            {"value": 97}, {"value": 100}, {"value": 102},
            {"value": 98}, {"value": 10000},
        ]
        result = self.analyzer.analyze("数据", "SELECT ...", data)
        self.assertGreater(len(result.anomalies), 0)

    def test_table_chart_type(self):
        data = [{"value": 100}, {"value": 200}]
        result = self.analyzer.analyze("数据", "SELECT ...", data)
        self.assertEqual(result.chart_type, "table")

    def test_chart_data_extraction(self):
        data = [{"name": "A", "sales": 100}, {"name": "B", "sales": 200}]
        result = self.analyzer.analyze("销售数据", "SELECT ...", data)
        self.assertIsNotNone(result.chart_data)
        self.assertEqual(result.chart_data["type"], "bar")
        self.assertEqual(len(result.chart_data["labels"]), 2)
        self.assertEqual(len(result.chart_data["values"]), 2)

    def test_analysis_result_to_dict(self):
        data = [{"name": "A", "sales": 100}]
        result = self.analyzer.analyze("测试", "SELECT ...", data)
        d = result.to_dict()
        self.assertEqual(d["question"], "测试")
        self.assertEqual(d["sql"], "SELECT ...")
        self.assertIn("summary", d)
        self.assertIn("chart_type", d)
        self.assertIn("anomalies", d)

    def test_summary_single_value(self):
        data = [{"value": 42}]
        result = self.analyzer.analyze("单值", "SELECT ...", data)
        self.assertIn("42", result.summary)
        self.assertIn("42.0", result.summary)

    def test_no_anomaly_uniform_data(self):
        data = [{"value": 100} for _ in range(20)]
        result = self.analyzer.analyze("均匀数据", "SELECT ...", data)
        self.assertEqual(len(result.anomalies), 0)

    def test_chart_data_title(self):
        data = [{"name": "A", "sales": 100}, {"name": "B", "sales": 200}]
        result = self.analyzer.analyze("销售", "SELECT ...", data)
        self.assertIn("sales", result.chart_data["title"])


# =============================================================================
# 配置模块测试
# =============================================================================

class TestConfig(unittest.TestCase):
    """配置模块测试"""

    def test_default_config(self):
        saved = {
            k: os.environ[k]
            for k in ("DASHSCOPE_API_KEY", "OPENAI_API_KEY")
            if k in os.environ
        }
        try:
            for k in saved:
                del os.environ[k]
            config = Config()
            self.assertEqual(config.get("app.name"), "数据分析Agent")
            self.assertEqual(config.get("app.version"), "1.0.0")
            self.assertFalse(config.get("llm.enabled"))
        finally:
            for k in saved:
                os.environ[k] = saved[k]

    def test_get_with_default(self):
        config = Config()
        self.assertIsNone(config.get("nonexistent.key"))
        self.assertEqual(config.get("nonexistent.key", "fallback"), "fallback")

    def test_load_from_file(self):
        config_data = {"app": {"name": "CustomAgent"}, "llm": {"max_tokens": 4096}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            import yaml
            yaml.dump(config_data, f)
            f.flush()
            config = Config(f.name)
        os.unlink(f.name)
        self.assertEqual(config.get("app.name"), "CustomAgent")
        self.assertEqual(config.get("llm.max_tokens"), 4096)

    def test_load_from_nonexistent_file(self):
        config = Config("/nonexistent/config.yaml")
        # Should not crash, config should still have defaults
        self.assertIsInstance(config.config, dict)
        self.assertIn("app", config.config)

    def test_env_api_key(self):
        old_key = os.environ.get("DASHSCOPE_API_KEY")
        try:
            os.environ["DASHSCOPE_API_KEY"] = "test-key-123"
            config = Config()
            self.assertTrue(config.get("llm.enabled"))
            self.assertEqual(config.get("llm.api_key"), "test-key-123")
        finally:
            if old_key is None:
                os.environ.pop("DASHSCOPE_API_KEY", None)
            else:
                os.environ["DASHSCOPE_API_KEY"] = old_key

    def test_deep_merge(self):
        config = Config()
        override = {"app": {"debug": True}, "new_section": {"key": "value"}}
        config._deep_merge(config._config, override)
        self.assertTrue(config._config["app"]["debug"])
        self.assertEqual(config._config["new_section"]["key"], "value")

    def test_config_property(self):
        config = Config()
        self.assertIsInstance(config.config, dict)
        self.assertIn("app", config.config)
        self.assertIn("llm", config.config)


# =============================================================================
# 完整流程测试
# =============================================================================

class TestPipeline(unittest.TestCase):
    """完整流程测试"""

    def setUp(self):
        self.schema_mgr = SchemaManager()
        self.schema_mgr.add_table(TableSchema(
            table_name="users",
            columns=[Column("id", "INT"), Column("name", "VARCHAR(100)")],
        ))

    def test_successful_query(self):
        agent = DataAnalysisAgent(self.schema_mgr)
        result = agent.query("统计用户数")
        self.assertIn("SELECT", result.sql.upper())
        self.assertTrue(result.validation.is_valid)
        self.assertIsNotNone(result.execution)
        self.assertIsNotNone(result.analysis)

    def test_invalid_sql(self):
        agent = DataAnalysisAgent(self.schema_mgr)
        agent.generator.llm = lambda prompt: "DROP TABLE users;"
        result = agent.query("DROP TABLE users")
        self.assertFalse(result.validation.is_valid)
        self.assertEqual(result.validation.risk_level, "high")

    def test_missing_from(self):
        agent = DataAnalysisAgent(self.schema_mgr)
        result = agent.query("SELECT *;")
        self.assertFalse(result.validation.is_valid)

    def test_unknown_table(self):
        agent = DataAnalysisAgent(self.schema_mgr)
        agent.generator.llm = lambda prompt: "SELECT * FROM nonexistent;"
        result = agent.query("SELECT * FROM nonexistent;")
        self.assertTrue(result.validation.is_valid)
        self.assertGreater(len(result.validation.warnings), 0)

    def test_agent_result_error_field(self):
        result = AgentResult(question="test", sql="", validation=SQLValidationResult())
        self.assertEqual(result.error, "")
        result.error = "some error"
        self.assertEqual(result.error, "some error")

    def test_agent_result_to_dict_fields(self):
        result = AgentResult(question="q", sql="s", validation=SQLValidationResult())
        self.assertEqual(result.question, "q")
        self.assertEqual(result.sql, "s")
        self.assertIsNotNone(result.validation)


# =============================================================================
# 端到端测试
# =============================================================================

class TestEndToEnd(unittest.TestCase):
    """端到端测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        schema_mgr = SchemaManager()
        schema_mgr.add_table(TableSchema(
            table_name="users",
            columns=[Column("id", "INT"), Column("name", "VARCHAR(100)")],
        ))
        schema_mgr.add_table(TableSchema(
            table_name="orders",
            columns=[
                Column("id", "INT"),
                Column("user_id", "INT"),
                Column("amount", "DECIMAL(10,2)"),
            ],
        ))

        def mock_llm(prompt):
            return "SELECT name, SUM(amount) AS total FROM orders JOIN users ON orders.user_id = users.id GROUP BY name ORDER BY total DESC LIMIT 10;"

        agent = DataAnalysisAgent(schema_mgr, mock_llm)
        result = agent.query("销售额最高的十个用户")

        self.assertTrue(result.validation.is_valid)
        self.assertIsNotNone(result.execution)
        self.assertIsNotNone(result.analysis)
        self.assertEqual(result.execution["row_count"], 10)
        self.assertEqual(result.analysis.chart_type, "bar")

    def test_multi_table_join(self):
        schema_mgr = SchemaManager()
        schema_mgr.add_table(TableSchema(
            table_name="users",
            columns=[Column("id", "INT"), Column("name", "VARCHAR(100)")],
        ))
        schema_mgr.add_table(TableSchema(
            table_name="orders",
            columns=[Column("id", "INT"), Column("user_id", "INT"), Column("amount", "DECIMAL(10,2)")],
        ))

        agent = DataAnalysisAgent(schema_mgr)
        result = agent.query("统计用户数")
        self.assertTrue(result.validation.is_valid)

    def test_complex_query_with_group_by(self):
        schema_mgr = SchemaManager()
        schema_mgr.add_table(TableSchema(
            table_name="orders",
            columns=[Column("id", "INT"), Column("amount", "DECIMAL(10,2)")],
        ))

        agent = DataAnalysisAgent(schema_mgr)
        result = agent.query("各城市用户数")
        self.assertTrue(result.validation.is_valid)
        self.assertIsNotNone(result.execution)


# =============================================================================
# 边界条件测试
# =============================================================================

class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""

    def test_empty_question(self):
        schema_mgr = SchemaManager()
        schema_mgr.add_table(TableSchema(table_name="users", columns=[Column("id", "INT")]))
        agent = DataAnalysisAgent(schema_mgr)
        result = agent.query("")
        # Should not crash
        self.assertIsNotNone(result)

    def test_very_long_question(self):
        schema_mgr = SchemaManager()
        schema_mgr.add_table(TableSchema(table_name="users", columns=[Column("id", "INT")]))
        agent = DataAnalysisAgent(schema_mgr)
        long_question = "x" * 10000
        result = agent.query(long_question)
        self.assertIsNotNone(result)

    def test_special_characters(self):
        schema_mgr = SchemaManager()
        schema_mgr.add_table(TableSchema(table_name="users", columns=[Column("id", "INT")]))
        agent = DataAnalysisAgent(schema_mgr)
        result = agent.query("查询用户'; DROP TABLE users; --")
        self.assertIsNotNone(result)

    def test_unicode_question(self):
        schema_mgr = SchemaManager()
        schema_mgr.add_table(TableSchema(table_name="users", columns=[Column("id", "INT")]))
        agent = DataAnalysisAgent(schema_mgr)
        result = agent.query("查询用户 你好世界 🎉")
        self.assertIsNotNone(result)

    def test_sql_with_newlines(self):
        cleaned = SQLGenerator._clean_sql("  \n  SELECT * FROM users;  \n  ")
        self.assertEqual(cleaned, "SELECT * FROM users;")

    def test_empty_schema_manager(self):
        empty_mgr = SchemaManager()
        generator = SQLGenerator(empty_mgr)
        sql, tables = generator.generate("统计用户数")
        self.assertIn("SELECT", sql.upper())

    def test_single_row_data(self):
        analyzer = DataAnalyzer()
        data = [{"value": 42}]
        result = analyzer.analyze("单行", "SELECT ...", data)
        self.assertEqual(result.chart_type, "table")
        self.assertEqual(len(result.anomalies), 0)


# =============================================================================
# 性能测试
# =============================================================================

class TestPerformance(unittest.TestCase):
    """性能测试"""

    def test_query_speed(self):
        schema_mgr = SchemaManager()
        schema_mgr.add_table(TableSchema(
            table_name="users",
            columns=[Column("id", "INT"), Column("name", "VARCHAR(100)")],
        ))
        agent = DataAnalysisAgent(schema_mgr)

        import time
        start = time.time()
        for i in range(50):
            agent.query(f"查询用户{i}")
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, f"50次查询耗时过长: {elapsed:.2f}s")
        print(f"\n性能测试：50次查询耗时 {elapsed:.3f}s")

    def test_batch_analysis(self):
        analyzer = DataAnalyzer()
        import time
        start = time.time()
        for i in range(100):
            data = [{"value": i} for _ in range(50)]
            analyzer.analyze(f"分析{i}", "SELECT ...", data)
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, f"100次分析耗时过长: {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
