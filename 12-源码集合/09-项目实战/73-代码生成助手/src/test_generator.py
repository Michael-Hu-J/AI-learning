"""单元测试生成器"""

import os
import sys
import tempfile
import subprocess
import logging
from typing import Dict, Optional, Callable

logger = logging.getLogger(__name__)


class TestGenerator:
    """单元测试生成器"""

    def __init__(self, llm_call_func: Optional[Callable] = None):
        self.llm = llm_call_func

    def generate_tests(self, code: str, language: str = "python") -> str:
        """为生成的代码生成单元测试"""
        if not self.llm:
            return "# LLM 未配置，无法生成测试"

        prompt = (
            f"请为以下 {language} 代码生成单元测试。\n\n"
            f"代码：\n{code}\n\n"
            f"要求：\n"
            f"- 覆盖正常流程和异常流程\n"
            f"- 使用标准测试框架（Python 用 unittest）\n"
            f"- 包含边界条件测试\n"
            f"- 只输出测试代码，不要解释\n"
        )
        return self.llm(prompt)

    def run_tests(self, code: str, tests: str) -> Dict:
        """运行测试并返回结果"""
        combined = f"{code}\n\n{tests}"

        with tempfile.NamedTemporaryFile(mode='w', suffix='_test.py', delete=False, encoding='utf-8') as f:
            f.write(combined)
            test_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True, text=True, timeout=30
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout + result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "output": "测试执行超时", "returncode": -1}
        finally:
            try:
                os.unlink(test_file)
            except OSError:
                pass
