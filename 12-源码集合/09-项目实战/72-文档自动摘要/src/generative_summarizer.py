"""生成式摘要：基于 LLM"""

import re
import logging
from typing import List, Dict, Optional, Callable

logger = logging.getLogger(__name__)


class GenerativeSummarizer:
    """生成式摘要：基于 LLM"""

    def __init__(self, llm_call_func: Optional[Callable] = None, max_chunk_size: int = 2000,
                 max_summary_length: int = 500):
        self.llm = llm_call_func
        self.max_chunk_size = max_chunk_size
        self.max_summary_length = max_summary_length

    def summarize(self, text: str) -> str:
        """生成式摘要主流程"""
        if not self.llm:
            return "[LLM 未配置] 请设置 DASHSCOPE_API_KEY 或提供 LLM 回调函数"

        if not text or not text.strip():
            return ""

        if len(text) <= self.max_chunk_size:
            return self._summarize_chunk(text)

        # 长文档：分段摘要 + 合并
        chunks = self._split_text(text)
        chunk_summaries = []
        logger.info(f"长文档分段摘要: {len(chunks)} 段")

        for i, chunk in enumerate(chunks):
            chunk_summary = self._summarize_chunk(chunk)
            chunk_summaries.append(chunk_summary)
            logger.info(f"段 {i+1}/{len(chunks)} 摘要完成")

        if len(chunk_summaries) == 1:
            return chunk_summaries[0]

        return self._merge_summaries(chunk_summaries)

    def _summarize_chunk(self, chunk: str) -> str:
        """对单个文本片段生成摘要"""
        prompt = (
            f"请对以下文档内容进行摘要，要求：\n"
            f"1. 保留核心信息和关键数据\n"
            f"2. 不添加原文中没有的内容\n"
            f"3. 不超过 {self.max_summary_length} 字\n\n"
            f"原文：\n{chunk}\n\n"
            f"摘要：\n"
        )
        return self.llm(prompt)

    def _merge_summaries(self, summaries: List[str]) -> str:
        """合并多个摘要"""
        combined = "\n\n".join([f"片段{i+1}：{s}" for i, s in enumerate(summaries)])
        prompt = (
            f"以下是同一文档多个片段的摘要，请将它们合并为一份完整的摘要。\n"
            f"要求：\n"
            f"1. 去重，合并重复内容\n"
            f"2. 按逻辑顺序组织\n"
            f"3. 不超过 {self.max_summary_length} 字\n\n"
            f"片段摘要：\n{combined}\n\n"
            f"合并后的摘要：\n"
        )
        return self.llm(prompt)

    def _split_text(self, text: str) -> List[str]:
        """按固定大小切分文本"""
        chunks = []
        for i in range(0, len(text), self.max_chunk_size):
            chunks.append(text[i:i + self.max_chunk_size])
        return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def mock_llm(prompt: str) -> str:
        return "人工智能是计算机科学分支，用于模拟人类智能。" \
               "机器学习是核心技术，深度学习在图像识别等领域取得突破。" \
               "Transformer 架构改变了 NLP 领域。"

    generator = GenerativeSummarizer(mock_llm)
    sample = """人工智能（Artificial Intelligence，简称 AI）是计算机科学的一个分支，
用于开发能够模拟人类智能行为的系统。自 1956 年达特茅斯会议首次提出"人工智能"概念以来。

机器学习是人工智能的核心技术之一。2012 年，深度学习在图像识别领域取得突破性进展。

2017 年，Google 提出了 Transformer 架构，彻底改变了自然语言处理领域。"""

    result = generator.summarize(sample)
    print("=== 生成式摘要 ===")
    print(result)
