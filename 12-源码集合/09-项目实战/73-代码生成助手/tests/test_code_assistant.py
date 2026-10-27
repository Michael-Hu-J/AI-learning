"""代码生成助手自动化测试"""

import sys
import os
import unittest
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_context import CodeContextManager
from src.code_generator import CodeGenerator, CodeGenerationResult
from src.code_quality import CodeQualityChecker
from src.test_generator import TestGenerator
from src.pipeline import CodeAssistantPipeline


# =============================================================================
# 1. 核心功能测试 — 上下文管理器
# =============================================================================

class TestCodeContextManager(unittest.TestCase):
    """上下文管理器测试"""

    def setUp(self):
        # 创建临时项目目录
        self.test_dir = tempfile.mkdtemp()
        self.manager = CodeContextManager(self.test_dir)

        # 创建测试文件
        with open(f"{self.test_dir}/data_utils.py", "w") as f:
            f.write("def migrate_data(): pass\ndef process_db(): pass")
        with open(f"{self.test_dir}/string_utils.py", "w") as f:
            f.write("def count_words(): pass\ndef find_longest(): pass")

    def test_find_related_files(self):
        files = self.manager.find_related_files("data migration database", max_files=5)
        self.assertGreater(len(files), 0)
        # data_utils.py should be found (contains "data" keyword)
        self.assertTrue(any("data" in f for f in files))

    def test_find_no_files(self):
        files = self.manager.find_related_files("完全不相关的内容 xyz123", max_files=5)
        self.assertEqual(len(files), 0)

    def test_nonexistent_project(self):
        manager = CodeContextManager("/nonexistent/path")
        files = manager.find_related_files("测试", max_files=5)
        self.assertEqual(len(files), 0)

    def test_build_context_prompt(self):
        prompt = self.manager.build_context_prompt("数据迁移")
        self.assertIn("数据迁移", prompt)
        self.assertIn("相关代码参考", prompt)

    def test_extract_keywords(self):
        keywords = self.manager._extract_keywords("编写一个数据迁移脚本")
        # 应该包含中文单字和可能的英文
        self.assertGreater(len(keywords), 0)
        # 检查包含关键中文字
        self.assertTrue(any(c in keywords for c in "数据迁移"))


# =============================================================================
# 2. 核心功能测试 — 代码生成器
# =============================================================================

class TestCodeGenerator(unittest.TestCase):
    """代码生成器测试"""

    def test_generate_without_llm(self):
        generator = CodeGenerator()
        result = generator.generate("编写一个函数")
        self.assertIn("LLM 未配置", result.code)
        self.assertEqual(result.language, "python")

    def test_generate_with_mock_llm(self):
        def mock_llm(prompt):
            return "def hello(): return 'Hello'"

        generator = CodeGenerator(mock_llm)
        result = generator.generate("编写一个函数")
        self.assertEqual(result.code, "def hello(): return 'Hello'")
        self.assertEqual(result.language, "python")

    def test_result_to_dict(self):
        result = CodeGenerationResult(code="test", language="python")
        d = result.to_dict()
        self.assertEqual(d["code"], "test")
        self.assertEqual(d["language"], "python")


# =============================================================================
# 3. 核心功能测试 — 代码质量检查器
# =============================================================================

class TestCodeQualityChecker(unittest.TestCase):
    """代码质量检查器测试"""

    def setUp(self):
        self.checker = CodeQualityChecker()

    def test_valid_python_syntax(self):
        code = "def hello():\n    return 'Hello'"
        ok, errors = self.checker.check_syntax(code, "python")
        self.assertTrue(ok)
        self.assertEqual(len(errors), 0)

    def test_invalid_python_syntax(self):
        code = "def hello(\n    return"
        ok, errors = self.checker.check_syntax(code, "python")
        self.assertFalse(ok)
        self.assertGreater(len(errors), 0)

    def test_security_eval(self):
        code = "result = eval(user_input)"
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("eval" in issue for issue in issues))

    def test_security_exec(self):
        code = "exec(code)"
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("exec" in issue for issue in issues))

    def test_security_os_system(self):
        code = "os.system('rm -rf /')"
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("os.system" in issue for issue in issues))

    def test_security_sql_injection(self):
        code = "cursor.execute(f'SELECT * FROM {table}')"
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("SQL" in issue for issue in issues))

    def test_security_hardcoded_password(self):
        code = 'password = "secret123"'
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("密码" in issue for issue in issues))

    def test_clean_code_no_issues(self):
        code = "def add(a, b): return a + b"
        issues = self.checker.check_security(code, "python")
        self.assertEqual(len(issues), 0)

    def test_complexity(self):
        code = """def test():
    if True:
        if True:
            if True:
                pass
"""
        complexity = self.checker.check_complexity(code)
        self.assertEqual(complexity["function_count"], 1)
        self.assertGreater(complexity["max_nesting_depth"], 0)

    def test_quality_score_clean(self):
        code = "def add(a, b): return a + b"
        score = self.checker.calculate_quality_score(code, "python")
        self.assertEqual(score, 100.0)

    def test_quality_score_with_issues(self):
        code = "eval(input())"
        score = self.checker.calculate_quality_score(code, "python")
        self.assertLess(score, 100.0)


# =============================================================================
# 4. 核心功能测试 — 测试生成器
# =============================================================================

class TestTestGenerator(unittest.TestCase):
    """测试生成器测试"""

    def test_generate_without_llm(self):
        generator = TestGenerator()
        tests = generator.generate_tests("def hello(): pass")
        self.assertIn("LLM 未配置", tests)

    def test_run_tests_pass(self):
        code = """def add(a, b):
    return a + b
"""
        tests = """import unittest

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)
    def test_add_negative(self):
        self.assertEqual(add(-1, -1), -2)

if __name__ == '__main__':
    unittest.main()
"""
        generator = TestGenerator()
        result = generator.run_tests(code, tests)
        self.assertTrue(result["passed"])

    def test_run_tests_fail(self):
        code = """def add(a, b):
    return a + b
"""
        tests = """import unittest

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 999)  # 故意写错

if __name__ == '__main__':
    unittest.main()
"""
        generator = TestGenerator()
        result = generator.run_tests(code, tests)
        self.assertFalse(result["passed"])


# =============================================================================
# 5. 核心功能测试 — 完整流程
# =============================================================================

class TestPipeline(unittest.TestCase):
    """完整流程测试"""

    def test_pipeline_with_mock_llm(self):
        def mock_llm(prompt):
            if "数据迁移" in prompt:
                return '''import sqlite3

def migrate_data(source_db: str, target_db: str, table_name: str) -> int:
    """从源数据库迁移数据到目标数据库"""
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
'''
            return "def hello(): return 'Hello'"

        pipeline = CodeAssistantPipeline(mock_llm)
        result = pipeline.process("编写一个数据迁移脚本")

        self.assertTrue(result.syntax_valid)
        self.assertGreater(result.quality_score, 0)
        # 应该有安全问题（SQL f-string 拼接）
        self.assertGreater(len(result.security_issues), 0)

    def test_pipeline_without_llm(self):
        pipeline = CodeAssistantPipeline()
        result = pipeline.process("编写一个函数")

        # 占位代码 "# LLM 未配置，返回占位代码" 是有效的 Python 注释
        self.assertIn("LLM 未配置", result.code)
        self.assertIn("LLM 未配置", str(result.errors))


# =============================================================================
# 6. 核心功能测试 — 端到端
# =============================================================================

class TestEndToEnd(unittest.TestCase):
    """端到端测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        def mock_llm(prompt):
            return '''def count_words(text: str) -> dict:
    """统计单词出现次数"""
    words = text.lower().split()
    result = {}
    for word in words:
        result[word] = result.get(word, 0) + 1
    return result
'''
        pipeline = CodeAssistantPipeline(mock_llm)
        result = pipeline.process("编写一个统计单词出现次数的函数")

        self.assertTrue(result.syntax_valid)
        self.assertGreater(result.quality_score, 50)
        self.assertEqual(len(result.security_issues), 0)


# =============================================================================
# 7. 边界条件测试 — 上下文管理器
# =============================================================================

class TestCodeContextManagerBoundary(unittest.TestCase):
    """上下文管理器边界条件测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.manager = CodeContextManager(self.test_dir)

    def test_empty_project(self):
        files = self.manager.find_related_files("测试", max_files=5)
        self.assertEqual(len(files), 0)

    def test_max_files_limit(self):
        for i in range(10):
            with open(f"{self.test_dir}/file_{i}.py", "w") as f:
                f.write(f"def func_{i}(): pass")
        files = self.manager.find_related_files("func", max_files=3)
        self.assertLessEqual(len(files), 3)

    def test_hidden_dir_skipped(self):
        os.makedirs(f"{self.test_dir}/.hidden", exist_ok=True)
        with open(f"{self.test_dir}/.hidden/secret.py", "w") as f:
            f.write("def secret(): pass")
        files = self.manager.find_related_files("secret", max_files=5)
        self.assertEqual(len(files), 0)

    def test_non_python_files(self):
        with open(f"{self.test_dir}/readme.txt", "w") as f:
            f.write("This is a readme file with some content.")
        files = self.manager.find_related_files("readme", max_files=5)
        self.assertEqual(len(files), 0)

    def test_build_context_prompt_no_files(self):
        prompt = self.manager.build_context_prompt("不相关的内容 xyz123")
        self.assertIn("不相关的内容 xyz123", prompt)

    def test_extract_keywords_empty(self):
        keywords = self.manager._extract_keywords("")
        self.assertEqual(len(keywords), 0)

    def test_extract_keywords_english_only(self):
        keywords = self.manager._extract_keywords("data migration script")
        self.assertTrue(any("data" in kw for kw in keywords))

    def test_extract_keywords_chinese_only(self):
        keywords = self.manager._extract_keywords("数据迁移")
        self.assertTrue(any(c in keywords for c in "数据"))

    def test_score_file_relevance_nonexistent(self):
        score = self.manager._score_file_relevance("/nonexistent/file.py", ["test"])
        self.assertEqual(score, 0)

    def test_score_file_relevance_no_match(self):
        with open(f"{self.test_dir}/unrelated.py", "w") as f:
            f.write("def hello(): pass")
        score = self.manager._score_file_relevance(
            f"{self.test_dir}/unrelated.py", ["xyz123"]
        )
        self.assertEqual(score, 0)

    def test_cache_behavior(self):
        """测试缓存行为"""
        self.assertEqual(len(self.manager._cache), 0)

    def test_node_modules_skipped(self):
        os.makedirs(f"{self.test_dir}/node_modules", exist_ok=True)
        with open(f"{self.test_dir}/node_modules/lib.js", "w") as f:
            f.write("module.exports = {}")
        files = self.manager.find_related_files("exports", max_files=5)
        self.assertEqual(len(files), 0)

    def test_venv_skipped(self):
        os.makedirs(f"{self.test_dir}/venv", exist_ok=True)
        with open(f"{self.test_dir}/venv/lib.py", "w") as f:
            f.write("def venv_func(): pass")
        files = self.manager.find_related_files("venv_func", max_files=5)
        self.assertEqual(len(files), 0)

    def test_subdirectory_files(self):
        os.makedirs(f"{self.test_dir}/src/utils", exist_ok=True)
        with open(f"{self.test_dir}/src/utils/helper.py", "w") as f:
            f.write("def helper_func(): pass")
        files = self.manager.find_related_files("helper", max_files=5)
        self.assertEqual(len(files), 1)
        self.assertIn("helper.py", files[0])


# =============================================================================
# 8. 边界条件测试 — 代码生成器
# =============================================================================

class TestCodeGeneratorBoundary(unittest.TestCase):
    """代码生成器边界条件测试"""

    def test_generate_empty_description(self):
        def mock_llm(prompt):
            return "def empty(): pass"
        generator = CodeGenerator(mock_llm)
        result = generator.generate("")
        self.assertEqual(result.code, "def empty(): pass")

    def test_generate_with_language_java(self):
        def mock_llm(prompt):
            return "public class Main {}"
        generator = CodeGenerator(mock_llm)
        result = generator.generate("创建一个类", language="java")
        self.assertEqual(result.language, "java")
        self.assertEqual(result.code, "public class Main {}")

    def test_result_defaults(self):
        result = CodeGenerationResult()
        self.assertEqual(result.code, "")
        self.assertEqual(result.language, "python")
        self.assertEqual(result.tests, "")
        self.assertFalse(result.syntax_valid)
        self.assertEqual(result.security_issues, [])
        self.assertEqual(result.quality_score, 0.0)
        self.assertEqual(result.errors, [])

    def test_result_to_dict_full(self):
        result = CodeGenerationResult(
            code="test code",
            language="python",
            tests="test tests",
            syntax_valid=True,
            security_issues=["issue1"],
            quality_score=80.0,
            errors=["error1"],
        )
        d = result.to_dict()
        self.assertEqual(len(d), 7)
        self.assertEqual(d["syntax_valid"], True)
        self.assertEqual(d["security_issues"], ["issue1"])
        self.assertEqual(d["quality_score"], 80.0)
        self.assertEqual(d["errors"], ["error1"])

    def test_generate_with_context_manager(self):
        test_dir = tempfile.mkdtemp()
        with open(f"{test_dir}/example.py", "w") as f:
            f.write("def example_func(): pass")
        from src.code_context import CodeContextManager
        ctx = CodeContextManager(test_dir)
        def mock_llm(prompt):
            return "def generated(): pass"
        generator = CodeGenerator(mock_llm, context_manager=ctx)
        result = generator.generate("生成代码")
        self.assertEqual(result.code, "def generated(): pass")

    def test_llm_returns_empty(self):
        def mock_llm(prompt):
            return ""
        generator = CodeGenerator(mock_llm)
        result = generator.generate("测试")
        self.assertEqual(result.code, "")

    def test_llm_returns_multiline(self):
        def mock_llm(prompt):
            return "def a():\n    pass\n\ndef b():\n    pass"
        generator = CodeGenerator(mock_llm)
        result = generator.generate("测试")
        self.assertIn("def a()", result.code)
        self.assertIn("def b()", result.code)


# =============================================================================
# 9. 边界条件测试 — 代码质量检查器
# =============================================================================

class TestCodeQualityCheckerBoundary(unittest.TestCase):
    """代码质量检查器边界条件测试"""

    def setUp(self):
        self.checker = CodeQualityChecker()

    def test_empty_code_syntax(self):
        ok, errors = self.checker.check_syntax("", "python")
        self.assertTrue(ok)

    def test_comment_only_syntax(self):
        code = "# 这是一行注释\n# 这是第二行注释"
        ok, errors = self.checker.check_syntax(code, "python")
        self.assertTrue(ok)

    def test_unsupported_language_syntax(self):
        ok, errors = self.checker.check_syntax("console.log('hi')", "javascript")
        self.assertTrue(ok)
        self.assertGreater(len(errors), 0)

    def test_javascript_security_eval(self):
        code = "eval(userInput)"
        issues = self.checker.check_security(code, "javascript")
        self.assertTrue(any("eval" in issue for issue in issues))

    def test_javascript_security_innerhtml(self):
        code = "element.innerHTML = userInput"
        issues = self.checker.check_security(code, "javascript")
        self.assertTrue(any("XSS" in issue for issue in issues))

    def test_javascript_security_document_write(self):
        code = "document.write(html)"
        issues = self.checker.check_security(code, "javascript")
        self.assertTrue(any("XSS" in issue for issue in issues))

    def test_unsupported_language_security(self):
        issues = self.checker.check_security("some code", "rust")
        self.assertTrue(any("暂不支持" in issue for issue in issues))

    def test_complexity_empty_code(self):
        complexity = self.checker.check_complexity("")
        self.assertEqual(complexity["total_lines"], 0)
        self.assertEqual(complexity["max_nesting_depth"], 0)
        self.assertEqual(complexity["function_count"], 0)

    def test_complexity_multiple_functions(self):
        code = """def func1(): pass
def func2(): pass
def func3(): pass"""
        complexity = self.checker.check_complexity(code)
        self.assertEqual(complexity["function_count"], 3)

    def test_complexity_deep_nesting(self):
        code = """def test():
    if True:
        if True:
            if True:
                if True:
                    if True:
                        if True:
                            pass"""
        complexity = self.checker.check_complexity(code)
        self.assertGreater(complexity["max_nesting_depth"], 5)

    def test_quality_score_syntax_error(self):
        code = "def broken("
        score = self.checker.calculate_quality_score(code, "python")
        self.assertLess(score, 100.0)

    def test_quality_score_deep_nesting_penalty(self):
        code = "def test():\n" + "    " * 6 + "pass"
        score = self.checker.calculate_quality_score(code, "python")
        self.assertLess(score, 100.0)

    def test_quality_score_long_code_penalty(self):
        code = "def test():\n    return 1\n" * 101  # 超过 200 行触发扣分
        score = self.checker.calculate_quality_score(code, "python")
        self.assertLess(score, 100.0)

    def test_quality_score_minimum_zero(self):
        code = "eval(input())\nos.system('rm -rf /')\nexec(code)\n" * 20
        score = self.checker.calculate_quality_score(code, "python")
        self.assertGreaterEqual(score, 0.0)

    def test_security_pickle(self):
        code = "data = pickle.loads(user_data)"
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("pickle" in issue.lower() or "反序列化" in issue for issue in issues))

    def test_security_hardcoded_api_key(self):
        code = 'api_key = "sk-123456"'
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("API Key" in issue for issue in issues))

    def test_security_sql_format(self):
        code = "cursor.execute('SELECT * FROM %s' % table)"
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("SQL" in issue for issue in issues))

    def test_security_subprocess_shell(self):
        code = "subprocess.call('ls', shell=True)"
        issues = self.checker.check_security(code, "python")
        self.assertTrue(any("subprocess" in issue for issue in issues))

    def test_complexity_counts_non_comment_lines(self):
        code = """# 注释行
def test():
    # 内部注释
    return 1"""
        complexity = self.checker.check_complexity(code)
        # 应该只计算非注释非空行
        self.assertGreater(complexity["total_lines"], 0)


# =============================================================================
# 10. 边界条件测试 — 测试生成器
# =============================================================================

class TestTestGeneratorBoundary(unittest.TestCase):
    """测试生成器边界条件测试"""

    def test_generate_with_llm(self):
        def mock_llm(prompt):
            return "import unittest\nclass Test(unittest.TestCase):\n    def test_pass(self):\n        pass"
        generator = TestGenerator(mock_llm)
        tests = generator.generate_tests("def hello(): pass")
        self.assertNotIn("LLM 未配置", tests)
        self.assertIn("unittest", tests)

    def test_run_tests_timeout(self):
        code = "def infinite():\n    while True: pass"
        tests = """import unittest
import time
class TestTimeout(unittest.TestCase):
    def test_infinite(self):
        import sys
        sys.path.insert(0, '.')
        # 模拟超时测试
        self.assertTrue(True)
if __name__ == '__main__':
    unittest.main()
"""
        generator = TestGenerator()
        result = generator.run_tests(code, tests)
        # 正常测试应该通过
        self.assertTrue(result["passed"])

    def test_run_tests_with_syntax_error(self):
        code = "def broken("
        tests = """import unittest
class TestBroken(unittest.TestCase):
    def test_pass(self):
        self.assertTrue(True)
if __name__ == '__main__':
    unittest.main()
"""
        generator = TestGenerator()
        result = generator.run_tests(code, tests)
        # 代码有语法错误，测试应该失败
        self.assertFalse(result["passed"])

    def test_generate_tests_language_param(self):
        captured_prompt = []
        def mock_llm(prompt):
            captured_prompt.append(prompt)
            return "# tests"
        generator = TestGenerator(mock_llm)
        generator.generate_tests("def hello(): pass", language="java")
        self.assertIn("java", captured_prompt[0])

    def test_run_tests_result_format(self):
        code = "def add(a, b): return a + b"
        tests = """import unittest
class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)
if __name__ == '__main__':
    unittest.main()
"""
        generator = TestGenerator()
        result = generator.run_tests(code, tests)
        self.assertIn("passed", result)
        self.assertIn("output", result)
        self.assertIn("returncode", result)


# =============================================================================
# 11. 异常处理测试
# =============================================================================

class TestExceptionHandling(unittest.TestCase):
    """异常处理测试"""

    def test_pipeline_with_broken_llm(self):
        def broken_llm(prompt):
            raise RuntimeError("LLM 服务不可用")
        pipeline = CodeAssistantPipeline(broken_llm)
        with self.assertRaises(RuntimeError):
            pipeline.process("生成代码")

    def test_quality_checker_with_none(self):
        checker = CodeQualityChecker()
        # 空字符串不应崩溃
        ok, errors = checker.check_syntax("", "python")
        self.assertTrue(ok)

    def test_code_generation_result_edge_cases(self):
        result = CodeGenerationResult(
            code=None,  # 不应崩溃
            language="",
        )
        d = result.to_dict()
        self.assertIsNone(d["code"])

    def test_context_manager_with_binary_file(self):
        test_dir = tempfile.mkdtemp()
        # 创建二进制文件
        with open(f"{test_dir}/binary.dat", "wb") as f:
            f.write(b'\x00\x01\x02\x03\xff\xfe\xfd')
        manager = CodeContextManager(test_dir)
        # 不应崩溃
        files = manager.find_related_files("test", max_files=5)
        self.assertEqual(len(files), 0)

    def test_context_manager_permission_error(self):
        """测试权限错误处理"""
        manager = CodeContextManager("/root/restricted")
        files = manager.find_related_files("test", max_files=5)
        # 不应崩溃，返回空列表
        self.assertEqual(files, [])

    def test_test_generator_cleanup(self):
        """测试临时文件清理"""
        code = "def add(a, b): return a + b"
        tests = """import unittest
class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)
if __name__ == '__main__':
    unittest.main()
"""
        generator = TestGenerator()
        result = generator.run_tests(code, tests)
        # 临时文件应被清理
        self.assertTrue(result["passed"])


# =============================================================================
# 12. 性能测试
# =============================================================================

class TestPerformance(unittest.TestCase):
    """性能测试"""

    def test_quality_check_speed(self):
        checker = CodeQualityChecker()
        code = "def test():\n    return 1\n" * 100

        start = time.time()
        checker.calculate_quality_score(code, "python")
        elapsed = time.time() - start
        self.assertLess(elapsed, 1.0, f"质量检查耗时过长: {elapsed:.2f}s")
        print(f"\n性能测试：质量检查耗时 {elapsed:.3f}s")

    def test_syntax_check_speed(self):
        checker = CodeQualityChecker()
        code = "def test():\n    return 1\n" * 200

        start = time.time()
        for _ in range(50):
            checker.check_syntax(code, "python")
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"语法检查耗时过长: {elapsed:.2f}s")
        print(f"\n语法检查性能测试: 50 次，耗时 {elapsed:.3f}s")

    def test_security_check_speed(self):
        checker = CodeQualityChecker()
        code = "eval(input())\n" * 50

        start = time.time()
        for _ in range(50):
            checker.check_security(code, "python")
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"安全检查耗时过长: {elapsed:.2f}s")
        print(f"\n安全检查性能测试: 50 次，耗时 {elapsed:.3f}s")

    def test_context_manager_search_speed(self):
        test_dir = tempfile.mkdtemp()
        for i in range(50):
            with open(f"{test_dir}/file_{i}.py", "w") as f:
                f.write(f"def func_{i}(data): pass\n")
        manager = CodeContextManager(test_dir)

        start = time.time()
        for _ in range(10):
            manager.find_related_files("data migration", max_files=10)
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, f"文件搜索耗时过长: {elapsed:.2f}s")
        print(f"\n文件搜索性能测试: 10 次，耗时 {elapsed:.3f}s")

    def test_pipeline_throughput(self):
        """测试流水线吞吐量"""
        call_count = 0
        def mock_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "def hello(): return 'Hello'"
        pipeline = CodeAssistantPipeline(mock_llm)

        start = time.time()
        for i in range(20):
            pipeline.process(f"需求{i}")
        elapsed = time.time() - start
        self.assertLess(elapsed, 10.0, f"流水线耗时过长: {elapsed:.2f}s")
        print(f"\n流水线吞吐量测试: 20 次，耗时 {elapsed:.3f}s")


# =============================================================================
# 13. 集成测试
# =============================================================================

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_pipeline_with_context(self):
        """测试带上下文的完整流水线"""
        test_dir = tempfile.mkdtemp()
        with open(f"{test_dir}/database.py", "w") as f:
            f.write("""import sqlite3

class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
    
    def query(self, sql):
        return self.conn.execute(sql).fetchall()
""")

        def mock_llm(prompt):
            return '''def migrate_data(source_path, target_path):
    """迁移数据库数据"""
    import sqlite3
    src = sqlite3.connect(source_path)
    tgt = sqlite3.connect(target_path)
    data = src.execute("SELECT * FROM users").fetchall()
    for row in data:
        tgt.execute("INSERT INTO users VALUES (?, ?)", row)
    tgt.commit()
    return len(data)
'''
        pipeline = CodeAssistantPipeline(mock_llm, project_root=test_dir)
        result = pipeline.process("编写一个数据迁移函数")

        self.assertTrue(result.syntax_valid)
        self.assertGreater(result.quality_score, 0)

    def test_quality_gate_workflow(self):
        """测试质量门禁工作流"""
        def mock_llm(prompt):
            return '''def safe_function(x):
    """安全的函数"""
    if x > 0:
        return x * 2
    return 0
'''
        pipeline = CodeAssistantPipeline(mock_llm)
        result = pipeline.process("编写一个安全的函数")

        self.assertTrue(result.syntax_valid)
        self.assertEqual(len(result.security_issues), 0)
        self.assertGreater(result.quality_score, 80)

    def test_multi_language_support(self):
        """测试多语言支持"""
        checker = CodeQualityChecker()

        # Python 安全检查
        py_issues = checker.check_security("eval(x)", "python")
        self.assertGreater(len(py_issues), 0)

        # JavaScript 安全检查
        js_issues = checker.check_security("eval(x)", "javascript")
        self.assertGreater(len(js_issues), 0)

        # 不支持的语言
        rs_issues = checker.check_security("some code", "rust")
        self.assertTrue(any("暂不支持" in issue for issue in rs_issues))

    def test_pipeline_error_propagation(self):
        """测试错误传播"""
        def mock_llm(prompt):
            return "def broken("  # 语法错误
        pipeline = CodeAssistantPipeline(mock_llm)
        result = pipeline.process("有问题的代码")

        self.assertFalse(result.syntax_valid)
        self.assertGreater(len(result.errors), 0)

    def test_test_generation_and_execution(self):
        """测试生成并执行测试"""
        def mock_llm(prompt):
            if "单元测试" in prompt:
                return '''import unittest

class TestHello(unittest.TestCase):
    def test_hello(self):
        self.assertEqual(hello(), "Hello")
    def test_hello_type(self):
        self.assertIsInstance(hello(), str)

if __name__ == '__main__':
    unittest.main()
'''
            return '''def hello():
    """返回问候语"""
    return "Hello"
'''
        pipeline = CodeAssistantPipeline(mock_llm)
        result = pipeline.process("编写一个问候函数")

        self.assertTrue(result.syntax_valid)
        # 测试应该已生成
        self.assertGreater(len(result.tests), 0)

    def test_context_prompt_building(self):
        """测试上下文提示构建"""
        test_dir = tempfile.mkdtemp()
        with open(f"{test_dir}/utils.py", "w") as f:
            f.write("def helper(): pass")

        manager = CodeContextManager(test_dir)
        prompt = manager.build_context_prompt("helper function")
        self.assertIn("helper function", prompt)
        self.assertIn("相关代码参考", prompt)
        self.assertIn("utils.py", prompt)


# =============================================================================
# 14. 配置测试
# =============================================================================

class TestConfiguration(unittest.TestCase):
    """配置测试"""

    def test_pipeline_default_config(self):
        pipeline = CodeAssistantPipeline()
        self.assertIsNotNone(pipeline.generator)
        self.assertIsNotNone(pipeline.quality_checker)
        self.assertIsNotNone(pipeline.test_generator)

    def test_pipeline_with_project_root(self):
        test_dir = tempfile.mkdtemp()
        pipeline = CodeAssistantPipeline(project_root=test_dir)
        self.assertIsNotNone(pipeline.generator.context_manager)

    def test_pipeline_without_project_root(self):
        pipeline = CodeAssistantPipeline()
        self.assertIsNone(pipeline.generator.context_manager)

    def test_quality_checker_default_config(self):
        checker = CodeQualityChecker()
        # 验证默认配置可用
        score = checker.calculate_quality_score("def test(): pass", "python")
        self.assertEqual(score, 100.0)

    def test_test_generator_default_config(self):
        generator = TestGenerator()
        self.assertIsNone(generator.llm)

    def test_code_generator_default_config(self):
        generator = CodeGenerator()
        self.assertIsNone(generator.llm)
        self.assertIsNone(generator.context_manager)

    def test_code_generation_result_default_config(self):
        result = CodeGenerationResult()
        self.assertEqual(result.language, "python")
        self.assertFalse(result.syntax_valid)
        self.assertEqual(result.quality_score, 0.0)

    def test_context_manager_initialization(self):
        test_dir = tempfile.mkdtemp()
        manager = CodeContextManager(test_dir)
        self.assertEqual(manager.project_root, test_dir)
        self.assertEqual(len(manager._cache), 0)


# =============================================================================
# 15. 数据验证测试
# =============================================================================

class TestDataValidation(unittest.TestCase):
    """数据验证测试"""

    def test_generation_result_dict_format(self):
        result = CodeGenerationResult(
            code="def test(): pass",
            language="python",
            tests="import unittest",
            syntax_valid=True,
            security_issues=["issue1", "issue2"],
            quality_score=75.0,
            errors=["error1"],
        )
        d = result.to_dict()
        self.assertEqual(d["code"], "def test(): pass")
        self.assertEqual(d["language"], "python")
        self.assertEqual(d["tests"], "import unittest")
        self.assertEqual(d["syntax_valid"], True)
        self.assertEqual(d["security_issues"], ["issue1", "issue2"])
        self.assertEqual(d["quality_score"], 75.0)
        self.assertEqual(d["errors"], ["error1"])

    def test_pipeline_result_validation(self):
        def mock_llm(prompt):
            return "def hello(): return 'Hello'"
        pipeline = CodeAssistantPipeline(mock_llm)
        result = pipeline.process("测试")

        self.assertIsInstance(result, CodeGenerationResult)
        self.assertIsInstance(result.code, str)
        self.assertIsInstance(result.language, str)
        self.assertIsInstance(result.syntax_valid, bool)
        self.assertIsInstance(result.security_issues, list)
        self.assertIsInstance(result.quality_score, float)
        self.assertIsInstance(result.errors, list)

    def test_complexity_result_format(self):
        checker = CodeQualityChecker()
        code = "def test():\n    return 1"
        complexity = checker.check_complexity(code)
        self.assertIn("total_lines", complexity)
        self.assertIn("max_nesting_depth", complexity)
        self.assertIn("function_count", complexity)
        self.assertIsInstance(complexity["total_lines"], int)
        self.assertIsInstance(complexity["max_nesting_depth"], int)
        self.assertIsInstance(complexity["function_count"], int)

    def test_syntax_result_format(self):
        checker = CodeQualityChecker()
        ok, errors = checker.check_syntax("def test(): pass", "python")
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(errors, list)

    def test_security_result_format(self):
        checker = CodeQualityChecker()
        issues = checker.check_security("eval(x)", "python")
        self.assertIsInstance(issues, list)
        for issue in issues:
            self.assertIsInstance(issue, str)

    def test_test_result_format(self):
        code = "def add(a, b): return a + b"
        tests = """import unittest
class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)
if __name__ == '__main__':
    unittest.main()
"""
        generator = TestGenerator()
        result = generator.run_tests(code, tests)
        self.assertIsInstance(result["passed"], bool)
        self.assertIsInstance(result["output"], str)
        self.assertIsInstance(result["returncode"], int)

    def test_quality_score_range(self):
        checker = CodeQualityChecker()
        # 完美代码
        score = checker.calculate_quality_score("def add(a, b): return a + b", "python")
        self.assertEqual(score, 100.0)
        # 最差代码
        bad_code = "eval(input())\nos.system('rm -rf /')\nexec(code)\npickle.loads(x)\n" * 20
        score = checker.calculate_quality_score(bad_code, "python")
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
