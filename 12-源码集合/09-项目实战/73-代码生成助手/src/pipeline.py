"""代码生成助手完整流程"""

import logging
from typing import Optional

from .code_context import CodeContextManager
from .code_generator import CodeGenerator, CodeGenerationResult
from .code_quality import CodeQualityChecker
from .test_generator import TestGenerator

logger = logging.getLogger(__name__)


class CodeAssistantPipeline:
    """代码生成助手完整流程"""

    def __init__(self, llm_call_func=None, project_root: Optional[str] = None):
        self.llm = llm_call_func
        context_mgr = CodeContextManager(project_root) if project_root else None
        self.generator = CodeGenerator(llm_call_func, context_mgr)
        self.quality_checker = CodeQualityChecker()
        self.test_generator = TestGenerator(llm_call_func)
        logger.info("代码生成助手流水线初始化完成")

    def process(self, description: str, language: str = "python") -> CodeGenerationResult:
        """执行完整的代码生成流程"""
        logger.info(f"处理需求: {description}")

        # 第一步：生成代码
        result = self.generator.generate(description, language)

        # 第二步：语法检查
        syntax_ok, syntax_errors = self.quality_checker.check_syntax(result.code, language)
        result.syntax_valid = syntax_ok
        result.errors.extend(syntax_errors)

        # 第三步：安全扫描
        result.security_issues = self.quality_checker.check_security(result.code, language)

        # 第四步：质量评分
        result.quality_score = self.quality_checker.calculate_quality_score(result.code, language)

        # 第五步：生成并运行测试
        if syntax_ok and self.llm:
            result.tests = self.test_generator.generate_tests(result.code, language)
            test_result = self.test_generator.run_tests(result.code, result.tests)
            if not test_result["passed"]:
                result.errors.append(f"测试未通过：{test_result['output'][:200]}")

        logger.info(f"处理完成: 语法={result.syntax_valid}, 安全评分={result.quality_score}")
        return result
