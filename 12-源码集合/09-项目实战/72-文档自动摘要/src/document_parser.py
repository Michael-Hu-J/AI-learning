"""文档解析与文本处理模块"""

import re
import os
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """文档片段"""
    chunk_id: str
    title: str = ""
    content: str = ""
    section_path: str = ""
    word_count: int = 0
    order: int = 0

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "title": self.title,
            "content": self.content,
            "section_path": self.section_path,
            "word_count": self.word_count,
            "order": self.order,
        }


class DocumentParser:
    """文档解析器：支持多种格式，包含文本清洗"""

    def parse_raw_text(self, text: str) -> str:
        """清洗原始文本"""
        # 去除多余空白
        text = re.sub(r"[ \t]+", " ", text)
        # 去除连续换行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除行首行尾空白
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # 去除纯数字行（可能是页码）
        lines = [line for line in text.split("\n") if not re.match(r"^\d{1,4}$", line.strip())]
        return "\n".join(lines)

    def split_into_chunks(self, text: str, max_chunk_size: int = 2000,
                          overlap: int = 200) -> List[DocumentChunk]:
        """
        将文本切分为片段
        策略：优先按段落切分，段落过长则按句子切分
        """
        cleaned = self.parse_raw_text(text)
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]

        chunks: List[DocumentChunk] = []
        order = 0

        for para in paragraphs:
            if len(para) <= max_chunk_size:
                chunks.append(DocumentChunk(
                    chunk_id=f"chunk_{order:04d}",
                    content=para,
                    word_count=len(para),
                    order=order,
                ))
                order += 1
            else:
                sentences = self._split_sentences(para)
                current_chunk = ""

                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                        chunks.append(DocumentChunk(
                            chunk_id=f"chunk_{order:04d}",
                            content=current_chunk.strip(),
                            word_count=len(current_chunk),
                            order=order,
                        ))
                        order += 1
                        overlap_text = current_chunk[-overlap:] if overlap > 0 else ""
                        current_chunk = overlap_text + sentence
                    else:
                        current_chunk += sentence

                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        chunk_id=f"chunk_{order:04d}",
                        content=current_chunk.strip(),
                        word_count=len(current_chunk),
                        order=order,
                    ))

        logger.info(f"文档切片完成: {len(chunks)} 个片段")
        return chunks

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """按句子切分"""
        sentences = re.split(r"([。！？；\n])", text)
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if sentence.strip():
                result.append(sentence.strip())
        if not result and text.strip():
            result = [text.strip()]
        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = DocumentParser()
    sample = """第一章 项目概述

本项目用于开发一套智能文档处理系统，支持文档的自动解析、摘要生成和质量评估。

系统采用模块化设计，包含文档解析、文本处理、摘要生成、质量评估四个核心模块。

第二章 技术方案

文档解析模块支持 PDF、Word、HTML 等多种格式的文档解析。

文本处理模块负责清洗原始文本，去除格式标记和无关内容。

第三章 测试方案

测试覆盖文档解析准确性、摘要质量、系统性能三个维度。"""

    chunks = parser.split_into_chunks(sample, max_chunk_size=300)
    print(f"切片数: {len(chunks)}")
    for chunk in chunks:
        print(f"[{chunk.chunk_id}] 字数: {chunk.word_count}")
        print(f"  内容: {chunk.content[:50]}...")
