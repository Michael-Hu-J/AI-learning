"""代码生成器"""

import logging
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CodeGenerationResult:
    """代码生成结果"""
    code: str = ""
    language: str = "python"
    tests: str = ""
    syntax_valid: bool = False
    security_issues: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "language": self.language,
            "tests": self.tests,
            "syntax_valid": self.syntax_valid,
            "security_issues": self.security_issues,
            "quality_score": self.quality_score,
            "errors": self.errors,
        }


class CodeGenerator:
    """代码生成器"""

    def __init__(self, llm_call_func: Optional[Callable] = None, context_manager=None):
        self.llm = llm_call_func
        self.context_manager = context_manager

    def generate(self, description: str, language: str = "python") -> CodeGenerationResult:
        """根据需求描述生成代码"""
        if not self.llm:
            return CodeGenerationResult(code="# LLM 未配置", language=language,
                                       errors=["LLM 未配置，返回占位代码"])

        if self.context_manager:
            prompt = self.context_manager.build_context_prompt(description)
            prompt += f"\n\n请用 {language} 生成完整代码，包含注释和错误处理。"
        else:
            prompt = (
                f"你是一名资深 {language} 开发者。\n"
                f"请根据以下需求生成代码：\n{description}\n\n"
                f"要求：\n"
                f"- 包含完整注释\n"
                f"- 包含错误处理\n"
                f"- 遵循 {language} 编码规范\n"
            )

        code = self.llm(prompt)
        logger.info(f"代码生成完成: {len(code)} 字符")
        return CodeGenerationResult(code=code, language=language)
