"""代码质量检查器"""

import ast
import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class CodeQualityChecker:
    """代码质量检查器：语法、安全、复杂度"""

    def check_syntax(self, code: str, language: str) -> Tuple[bool, List[str]]:
        """检查语法正确性"""
        errors = []

        if language == "python":
            try:
                ast.parse(code)
                return True, []
            except SyntaxError as e:
                errors.append(f"语法错误：第{e.lineno}行 {e.msg}")
                return False, errors
        else:
            return True, [f"暂不支持 {language} 的语法检查"]

    def check_security(self, code: str, language: str) -> List[str]:
        """安全检查：检测常见安全问题"""
        issues = []

        if language == "python":
            security_patterns = [
                (r'eval\s*\(', "使用 eval()，存在代码注入风险"),
                (r'exec\s*\(', "使用 exec()，存在代码注入风险"),
                (r'os\.system\s*\(', "使用 os.system()，存在命令注入风险"),
                (r'subprocess\.call\s*\(.*shell\s*=\s*True', "subprocess 启用 shell，存在命令注入风险"),
                (r'pickle\.loads?\s*\(', "使用 pickle，存在反序列化风险"),
                (r'password\s*=\s*[\'"]', "硬编码密码"),
                (r'api_key\s*=\s*[\'"]', "硬编码 API Key"),
                (r'cursor\.execute\s*\(.*%\s*', "SQL 拼接，存在 SQL 注入风险"),
                (r'cursor\.execute\s*\(.*\.format\s*\(', "SQL 拼接，存在 SQL 注入风险"),
                (r'cursor\.execute\s*\(.*f["\']', "SQL f-string 拼接，存在 SQL 注入风险"),
            ]
        elif language == "javascript":
            security_patterns = [
                (r'eval\s*\(', "使用 eval()，存在代码注入风险"),
                (r'innerHTML\s*=', "使用 innerHTML，存在 XSS 风险"),
                (r'document\.write\s*\(', "使用 document.write，存在 XSS 风险"),
            ]
        else:
            return [f"暂不支持 {language} 的安全检查"]

        for pattern, message in security_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(message)

        if issues:
            logger.warning(f"发现 {len(issues)} 个安全问题")
        return issues

    def check_complexity(self, code: str) -> Dict[str, int]:
        """检查代码复杂度"""
        lines = [line for line in code.split('\n') if line.strip() and not line.strip().startswith('#')]
        total_lines = len(lines)

        max_depth = 0
        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            depth = indent // 4
            max_depth = max(max_depth, depth)

        func_count = len(re.findall(r'def\s+\w+\s*\(', code))

        return {
            "total_lines": total_lines,
            "max_nesting_depth": max_depth,
            "function_count": func_count,
        }

    def calculate_quality_score(self, code: str, language: str) -> float:
        """计算综合质量分数（0-100）"""
        score = 100.0

        syntax_ok, syntax_errors = self.check_syntax(code, language)
        if not syntax_ok:
            score -= 30

        security_issues = self.check_security(code, language)
        score -= len(security_issues) * 10

        complexity = self.check_complexity(code)
        if complexity["max_nesting_depth"] > 5:
            score -= 10
        if complexity["total_lines"] > 200:
            score -= 5

        return max(0, score)
