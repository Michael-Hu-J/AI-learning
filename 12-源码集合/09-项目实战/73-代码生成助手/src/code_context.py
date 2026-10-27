"""代码上下文管理器"""

import os
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CodeContextManager:
    """代码上下文管理器，负责收集和理解项目上下文"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self._cache: Dict[str, str] = {}
        logger.info(f"上下文管理器初始化: {project_root}")

    def find_related_files(self, description: str, max_files: int = 5) -> List[str]:
        """根据需求描述查找相关代码文件"""
        keywords = self._extract_keywords(description)
        scored_files = []

        if not os.path.exists(self.project_root):
            logger.warning(f"项目目录不存在: {self.project_root}")
            return []

        for root, _, filenames in os.walk(self.project_root):
            # 跳过隐藏目录和虚拟环境
            if any(part.startswith(".") or part in ("node_modules", "__pycache__", ".venv", "venv") for part in root.split(os.sep)):
                continue
            for filename in filenames:
                if not filename.endswith(('.py', '.java', '.js', '.ts', '.go', '.rs')):
                    continue
                filepath = os.path.join(root, filename)
                score = self._score_file_relevance(filepath, keywords)
                if score > 0:
                    scored_files.append((filepath, score))

        scored_files.sort(key=lambda x: x[1], reverse=True)
        result = [f[0] for f in scored_files[:max_files]]
        logger.info(f"找到 {len(result)} 个相关文件")
        return result

    def build_context_prompt(self, description: str) -> str:
        """构建包含上下文的 Prompt"""
        related_files = self.find_related_files(description)
        context_parts = [f"需求描述：{description}", "\n相关代码参考："]

        for filepath in related_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                context_parts.append(f"\n文件：{filepath}")
                context_parts.append(content[:2000])
            except (IOError, UnicodeDecodeError):
                continue

        return "\n".join(context_parts)

    def _extract_keywords(self, text: str) -> List[str]:
        """从需求描述中提取关键词"""
        keywords = []
        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z_]+', text)
        keywords.extend([w for w in english_words if len(w) > 1])
        # 提取中文单字（去重）
        chinese_chars = list(set(re.findall(r'[\u4e00-\u9fa5]', text)))
        keywords.extend(chinese_chars)
        return keywords

    def _score_file_relevance(self, filepath: str, keywords: List[str]) -> int:
        """计算文件与需求的相关度分数"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().lower()
        except (IOError, UnicodeDecodeError):
            return 0

        score = 0
        for kw in keywords:
            if kw.lower() in content:
                score += 1
        return score


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mgr = CodeContextManager(".")
    files = mgr.find_related_files("数据迁移数据库", max_files=3)
    print(f"找到 {len(files)} 个相关文件")
    for f in files:
        print(f"  {f}")
