"""文档解析与切片模块"""

import re
import os
import hashlib
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DocStatus(Enum):
    """文档状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


@dataclass
class DocumentChunk:
    """文档切片"""
    chunk_id: str
    source_doc_id: str
    content: str
    title: str = ""
    section: str = ""  # 所属章节
    page_number: int = 0
    order: int = 0  # 在文档中的顺序
    embedding: Optional[List[float]] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "source_doc_id": self.source_doc_id,
            "content": self.content,
            "title": self.title,
            "section": self.section,
            "page_number": self.page_number,
            "order": self.order,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DocumentChunk":
        return cls(
            chunk_id=data["chunk_id"],
            source_doc_id=data["source_doc_id"],
            content=data["content"],
            title=data.get("title", ""),
            section=data.get("section", ""),
            page_number=data.get("page_number", 0),
            order=data.get("order", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class KnowledgeDocument:
    """知识文档"""
    doc_id: str
    title: str
    file_path: str
    file_type: str  # pdf, docx, md, html, txt
    version: int = 1
    status: DocStatus = DocStatus.ACTIVE
    replaced_by: str = ""  # 被哪个版本的文档替代
    created_at: float = 0.0
    updated_at: float = 0.0
    chunks: List[DocumentChunk] = field(default_factory=list)


class DocumentParser:
    """文档解析器：支持多种格式"""

    def parse(self, file_path: str) -> str:
        """解析文档，返回文本内容"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        parsers = {
            ".md": self._parse_markdown,
            ".txt": self._parse_text,
            ".html": self._parse_html,
            ".htm": self._parse_html,
            ".pdf": self._parse_pdf,
            ".docx": self._parse_docx,
        }

        parser = parsers.get(ext)
        if not parser:
            raise ValueError(f"不支持的文件格式: {ext}")

        logger.info(f"解析文档: {file_path} (格式: {ext})")
        return parser(file_path)

    @staticmethod
    def _parse_text(file_path: str) -> str:
        """解析纯文本文件"""
        # 尝试多种编码
        for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法解码文件: {file_path}")

    @staticmethod
    def _parse_markdown(file_path: str) -> str:
        """解析 Markdown 文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 去除 Markdown 标记，保留文本
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)  # 代码块
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)  # 图片
        content = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", content)  # 链接
        content = re.sub(r"[#*_>~-]", "", content)  # 标记符号
        return content.strip()

    @staticmethod
    def _parse_html(file_path: str) -> str:
        """解析 HTML 文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 去除 HTML 标签
        content = re.sub(r"<style.*?</style>", "", content, flags=re.DOTALL)
        content = re.sub(r"<script.*?</script>", "", content, flags=re.DOTALL)
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"&\w+;", " ", content)  # HTML 实体
        return content.strip()

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        """解析 PDF 文件（简化版，生产环境用 PyPDF2 或 pdfplumber）"""
        # 生产环境应使用专业的 PDF 解析库
        # from pdfplumber import pdfplumber
        # with pdfplumber.open(file_path) as pdf:
        #     text = "".join(page.extract_text() or "" for page in pdf.pages)
        # return text
        raise NotImplementedError("PDF 解析需要安装 pdfplumber 库")

    @staticmethod
    def _parse_docx(file_path: str) -> str:
        """解析 Word 文档（简化版，生产环境用 python-docx）"""
        # 生产环境应使用 python-docx
        # from docx import Document
        # doc = Document(file_path)
        # return "\n".join(para.text for para in doc.paragraphs)
        raise NotImplementedError("DOCX 解析需要安装 python-docx 库")


class TextSplitter:
    """文本切片器"""

    def split(self, text: str, chunk_size: int = 300,
              chunk_overlap: int = 50, source_title: str = "") -> List[DocumentChunk]:
        """
        将文本切分为多个片段
        策略：按段落分割 -> 合并小段落 -> 截断大段落
        """
        if not text or not text.strip():
            return []

        # 第一步：按段落分割
        paragraphs = self._split_by_paragraphs(text)

        # 第二步：合并小段落，不超过 chunk_size
        chunks_text = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks_text.append(current_chunk.strip())
                # 如果单个段落超过 chunk_size，按句子截断
                if len(para) > chunk_size:
                    sub_chunks = self._split_long_text(para, chunk_size)
                    chunks_text.extend(sub_chunks)
                else:
                    current_chunk = para + "\n"

        if current_chunk.strip():
            chunks_text.append(current_chunk.strip())

        # 第三步：添加重叠（保留上下文连续性）
        if chunk_overlap > 0 and len(chunks_text) > 1:
            chunks_text = self._add_overlap(chunks_text, chunk_overlap)

        # 第四步：生成 DocumentChunk
        chunks = []
        for i, content in enumerate(chunks_text):
            chunk = DocumentChunk(
                chunk_id=self._generate_chunk_id(content),
                source_doc_id="",  # 由调用方设置
                content=content,
                title=source_title,
                order=i,
            )
            chunks.append(chunk)

        logger.info(f"文本切片完成: {len(chunks)} 个切片")
        return chunks

    @staticmethod
    def _split_by_paragraphs(text: str) -> List[str]:
        """按段落分割"""
        # 按空行分割
        paragraphs = re.split(r"\n\s*\n", text)
        # 对没有空行的长文本，按换行符分割
        if len(paragraphs) <= 1:
            paragraphs = text.split("\n")
        return paragraphs

    @staticmethod
    def _split_long_text(text: str, max_length: int) -> List[str]:
        """截断超长文本（按句子边界）"""
        chunks = []
        sentences = re.split(r"([。！？；.!?;])", text)
        current = ""

        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            if i + 1 < len(sentences) and sentences[i + 1] in "。！？；.!?;":
                sentence += sentences[i + 1]
                i += 2
            else:
                i += 1

            if len(current) + len(sentence) <= max_length:
                current += sentence
            else:
                if current:
                    chunks.append(current.strip())
                if len(sentence) > max_length:
                    for i in range(0, len(sentence), max_length):
                        chunks.append(sentence[i:i + max_length])
                    current = ""
                else:
                    current = sentence

        if current.strip():
            if len(current) > max_length:
                for i in range(0, len(current), max_length):
                    chunks.append(current[i:i + max_length])
            else:
                chunks.append(current.strip())

        return chunks

    @staticmethod
    def _add_overlap(chunks: List[str], overlap_size: int) -> List[str]:
        """添加重叠内容"""
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                # 从前一个 chunk 末尾取 overlap_size 个字符作为前缀
                prev_tail = chunks[i - 1][-overlap_size:]
                chunk = prev_tail + "\n" + chunk
            overlapped.append(chunk)
        return overlapped

    @staticmethod
    def _generate_chunk_id(content: str) -> str:
        """生成切片 ID"""
        return hashlib.md5(content.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    splitter = TextSplitter()
    text = """# 员工手册

## 第一章 入职须知

新员工入职需要携带身份证、学历证明、离职证明等材料。
入职当天需要完成以下事项：签署劳动合同、办理工牌、开通系统账号。

## 第二章 考勤制度

公司实行弹性工作制，核心工作时间为 10:00-16:00。
迟到超过 30 分钟需要向主管请假。

每月允许 3 次迟到豁免，超过后每次扣减 50 元。"""

    chunks = splitter.split(text, chunk_size=100, chunk_overlap=20)
    print("=" * 60)
    print("文本切片测试")
    print("=" * 60)
    for i, chunk in enumerate(chunks):
        print(f"\n--- 切片 {i+1} ---")
        print(f"ID: {chunk.chunk_id}")
        print(f"内容: {chunk.content[:80]}...")
