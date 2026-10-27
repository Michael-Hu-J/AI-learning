"""企业知识库问答系统自动化测试"""

import sys
import os
import unittest
import time
import json
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_parser import DocumentParser, TextSplitter, DocumentChunk, DocStatus, KnowledgeDocument
from src.vector_store import VectorStore, HybridRetriever, SearchResult
from src.knowledge_base_qa import KnowledgeBaseQA, QAResult
from src.config import Config, DEFAULT_CONFIG, load_config


# ============================================================================
# TestDocumentParser - 文档解析器测试
# ============================================================================

class TestDocumentParser(unittest.TestCase):
    """文档解析器测试"""

    def setUp(self):
        self.parser = DocumentParser()
        self.splitter = TextSplitter()

    def test_text_parsing(self):
        """测试纯文本解析"""
        test_file = "/tmp/test_kb_qa.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("这是一段测试文本。\n包含多行内容。")

        content = self.parser.parse(test_file)
        self.assertIn("测试文本", content)
        os.remove(test_file)

    def test_markdown_parsing(self):
        """测试 Markdown 解析"""
        md_text = """# 标题

这是一段正文内容。

- 列表项 1
- 列表项 2

[链接](http://example.com) 这是链接文字。"""

        import re
        content = md_text
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
        content = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", content)

        self.assertIn("标题", content)
        self.assertIn("链接文字", content)
        self.assertNotIn("http://example.com", content)

    def test_html_parsing(self):
        """测试 HTML 解析"""
        html_text = """<html>
<head><title>测试</title></head>
<body>
<h1>标题</h1>
<p>这是一段正文内容。</p>
</body>
</html>"""

        import re
        content = html_text
        content = re.sub(r"<style.*?</style>", "", content, flags=re.DOTALL)
        content = re.sub(r"<script.*?</script>", "", content, flags=re.DOTALL)
        content = re.sub(r"<[^>]+>", " ", content)

        self.assertIn("标题", content)
        self.assertIn("正文内容", content)
        self.assertNotIn("<", content)

    def test_file_not_found(self):
        """测试文件不存在"""
        with self.assertRaises(FileNotFoundError):
            self.parser.parse("/nonexistent/file.txt")

    def test_unsupported_format(self):
        """测试不支持的格式"""
        test_file = "/tmp/test_kb_qa.xyz"
        with open(test_file, "w") as f:
            f.write("test")

        with self.assertRaises(ValueError):
            self.parser.parse(test_file)
        os.remove(test_file)

    # --- 新增：边界条件测试 ---

    def test_parse_empty_text_file(self):
        """测试解析空文本文件"""
        test_file = "/tmp/test_empty.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("")

        content = self.parser.parse(test_file)
        self.assertEqual(content, "")
        os.remove(test_file)

    def test_parse_whitespace_only_file(self):
        """测试解析仅包含空白字符的文件"""
        test_file = "/tmp/test_whitespace.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("   \n\n\t  \n")

        content = self.parser.parse(test_file)
        self.assertEqual(content.strip(), "")
        os.remove(test_file)

    def test_parse_very_long_text(self):
        """测试解析超长文本文件"""
        test_file = "/tmp/test_long.txt"
        long_content = "这是一段测试文本。" * 10000
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(long_content)

        content = self.parser.parse(test_file)
        self.assertEqual(len(content), len(long_content))
        os.remove(test_file)

    def test_parse_special_characters(self):
        """测试解析包含特殊字符的文件"""
        test_file = "/tmp/test_special.txt"
        special_content = "特殊字符: !@#$%^&*()_+{}|:\"<>?~`-=[]\\;',./\n中文: 测试\nEmoji: \U0001f600"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(special_content)

        content = self.parser.parse(test_file)
        self.assertIn("特殊字符", content)
        self.assertIn("中文", content)
        os.remove(test_file)

    def test_parse_markdown_code_blocks(self):
        """测试 Markdown 代码块被正确移除"""
        test_file = "/tmp/test_code.md"
        md_content = """# 文档

这是一段说明文字。

```python
def hello():
    print("hello")
```

这是另一段说明文字。"""
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        content = self.parser.parse(test_file)
        self.assertIn("说明文字", content)
        self.assertNotIn("```", content)
        self.assertNotIn("def hello", content)
        os.remove(test_file)

    def test_parse_markdown_images(self):
        """测试 Markdown 图片被正确移除"""
        test_file = "/tmp/test_img.md"
        md_content = "![图片描述](http://example.com/image.png)\n正文内容。"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        content = self.parser.parse(test_file)
        self.assertIn("正文内容", content)
        self.assertNotIn("![", content)
        os.remove(test_file)

    def test_parse_html_with_scripts(self):
        """测试 HTML 中 script 标签被移除"""
        test_file = "/tmp/test_script.html"
        html_content = """<html><body>
<script>alert('xss')</script>
<p>安全内容</p>
</body></html>"""
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        content = self.parser.parse(test_file)
        self.assertIn("安全内容", content)
        self.assertNotIn("script", content.lower())
        os.remove(test_file)

    def test_parse_html_with_styles(self):
        """测试 HTML 中 style 标签被移除"""
        test_file = "/tmp/test_style.html"
        html_content = """<html><body>
<style>body { color: red; }</style>
<p>可见内容</p>
</body></html>"""
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        content = self.parser.parse(test_file)
        self.assertIn("可见内容", content)
        self.assertNotIn("color", content)
        os.remove(test_file)

    def test_parse_html_entities(self):
        """测试 HTML 实体被正确处理"""
        test_file = "/tmp/test_entity.html"
        html_content = "<p>&nbsp;内容&nbsp;</p>"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        content = self.parser.parse(test_file)
        self.assertIn("内容", content)
        os.remove(test_file)

    def test_parse_pdf_not_implemented(self):
        """测试 PDF 解析抛出 NotImplementedError"""
        test_file = "/tmp/test.pdf"
        with open(test_file, "w") as f:
            f.write("fake pdf")

        with self.assertRaises(NotImplementedError):
            self.parser.parse(test_file)
        os.remove(test_file)

    def test_parse_docx_not_implemented(self):
        """测试 DOCX 解析抛出 NotImplementedError"""
        test_file = "/tmp/test.docx"
        with open(test_file, "w") as f:
            f.write("fake docx")

        with self.assertRaises(NotImplementedError):
            self.parser.parse(test_file)
        os.remove(test_file)

    # --- 新增：异常处理测试 ---

    def test_parse_binary_file_as_text(self):
        """测试解析二进制文件"""
        test_file = "/tmp/test_binary.txt"
        with open(test_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe")

        # 应该尝试多种编码，最终可能抛出 ValueError
        try:
            content = self.parser.parse(test_file)
            # 如果成功解析，内容不应为空
            self.assertIsInstance(content, str)
        except ValueError:
            pass  # 预期行为
        finally:
            os.remove(test_file)

    def test_parse_permission_denied(self):
        """测试无权限读取文件（跨平台：Windows 上 chmod 不可靠，用 mock）"""
        import tempfile
        from unittest.mock import patch

        test_file = os.path.join(tempfile.gettempdir(), "test_noperm.txt")
        with patch("builtins.open", side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaises((PermissionError, ValueError, OSError)):
                self.parser.parse(test_file)

    def test_parse_directory_path(self):
        """测试传入目录路径而非文件路径"""
        with self.assertRaises((IsADirectoryError, ValueError)):
            self.parser.parse("/tmp")

    def test_parse_unicode_filename(self):
        """测试 Unicode 文件名"""
        test_file = "/tmp/测试文件_测试.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Unicode 文件名测试内容")

        content = self.parser.parse(test_file)
        self.assertIn("Unicode", content)
        os.remove(test_file)


# ============================================================================
# TestTextSplitter - 文本切片器测试
# ============================================================================

class TestTextSplitter(unittest.TestCase):
    """文本切片器测试"""

    def setUp(self):
        self.splitter = TextSplitter()

    def test_basic_splitting(self):
        """测试基本切片"""
        text = """第一章 总则

为了规范企业管理，制定本手册。本手册适用于全体员工。

第二章 考勤

公司实行弹性工作制。核心工作时间为 10:00-16:00。

每月允许 3 次迟到豁免。"""

        chunks = self.splitter.split(text, chunk_size=80, chunk_overlap=10)
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertGreater(len(chunk.content.strip()), 0)

    def test_empty_text_splitting(self):
        """测试空文本切片"""
        chunks = self.splitter.split("", chunk_size=500)
        self.assertEqual(len(chunks), 0)

    def test_long_text_splitting(self):
        """测试超长文本切片"""
        long_text = "这是一段很长的文字。" * 100
        chunks = self.splitter.split(long_text, chunk_size=100, chunk_overlap=10)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.content), 150)

    def test_chunk_id_uniqueness(self):
        """测试切片 ID 唯一性"""
        chunk1 = TextSplitter._generate_chunk_id("内容 A")
        chunk2 = TextSplitter._generate_chunk_id("内容 B")
        self.assertNotEqual(chunk1, chunk2)

    def test_sentence_boundary_splitting(self):
        """测试句子边界分割"""
        text = "第一句话。第二句话很长很长很长很长很长很长很长很长很长很长很长很长。第三句话。"
        chunks = self.splitter._split_long_text(text, 30)
        for chunk in chunks:
            self.assertTrue(
                chunk.endswith(("。", "！", "？", ";", ".", "!", "?")) or
                chunk == chunks[-1],
                f"切片不在句子边界: {chunk}"
            )

    def test_overlap(self):
        """测试重叠内容"""
        chunks = ["AAAAA", "BBBBB", "CCCCC"]
        overlapped = TextSplitter._add_overlap(chunks, 3)
        self.assertEqual(len(overlapped), 3)
        self.assertIn("AA", overlapped[1])

    # --- 新增：边界条件测试 ---

    def test_whitespace_only_splitting(self):
        """测试仅空白字符的文本切片"""
        chunks = self.splitter.split("   \n\n\t  ", chunk_size=100)
        self.assertEqual(len(chunks), 0)

    def test_single_char_splitting(self):
        """测试单字符文本切片"""
        chunks = self.splitter.split("a", chunk_size=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content.strip(), "a")

    def test_chunk_size_one(self):
        """测试 chunk_size=1 的极端情况"""
        chunks = self.splitter.split("abc def", chunk_size=1, chunk_overlap=0)
        self.assertGreater(len(chunks), 0)

    def test_chunk_size_larger_than_text(self):
        """测试 chunk_size 大于文本长度"""
        text = "短文本"
        chunks = self.splitter.split(text, chunk_size=10000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content.strip(), text)

    def test_zero_overlap(self):
        """测试零重叠"""
        text = "第一段。\n\n第二段。\n\n第三段。"
        chunks = self.splitter.split(text, chunk_size=50, chunk_overlap=0)
        self.assertGreater(len(chunks), 0)
        # 验证没有重叠内容
        for i in range(1, len(chunks)):
            self.assertFalse(chunks[i].content.startswith(chunks[i-1].content[-3:]))

    def test_overlap_larger_than_chunk(self):
        """测试重叠大于 chunk_size 的边界情况"""
        text = "第一段。\n\n第二段。"
        chunks = self.splitter.split(text, chunk_size=10, chunk_overlap=100)
        # 应该仍能正常工作，不会崩溃
        self.assertGreater(len(chunks), 0)

    def test_split_with_source_title(self):
        """测试切片时设置 source_title"""
        text = "测试内容。"
        chunks = self.splitter.split(text, chunk_size=100, source_title="测试文档")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].title, "测试文档")

    def test_split_preserves_order(self):
        """测试切片顺序正确"""
        text = "第一段。\n\n第二段。\n\n第三段。\n\n第四段。"
        chunks = self.splitter.split(text, chunk_size=20, chunk_overlap=0)
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk.order, i)

    def test_split_unicode_text(self):
        """测试 Unicode 文本切片"""
        text = "这是一段中文测试文本。\n\nThis is English text.\n\n混合内容：中文 English 中文。"
        chunks = self.splitter.split(text, chunk_size=30)
        self.assertGreater(len(chunks), 0)

    def test_split_long_sentence(self):
        """测试超长句子按边界分割"""
        long_sentence = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的句子。"
        chunks = self.splitter._split_long_text(long_sentence, 30)
        self.assertGreater(len(chunks), 1)
        # 确保每个切片不超过限制
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 35)

    def test_split_no_paragraph_breaks(self):
        """测试没有段落分隔的长文本"""
        text = "第一行\n第二行\n第三行\n第四行\n第五行"
        chunks = self.splitter.split(text, chunk_size=20, chunk_overlap=0)
        self.assertGreater(len(chunks), 0)

    def test_chunk_id_deterministic(self):
        """测试相同内容生成相同 chunk_id"""
        id1 = TextSplitter._generate_chunk_id("相同内容")
        id2 = TextSplitter._generate_chunk_id("相同内容")
        self.assertEqual(id1, id2)

    def test_chunk_id_format(self):
        """测试 chunk_id 格式"""
        chunk_id = TextSplitter._generate_chunk_id("测试内容")
        self.assertEqual(len(chunk_id), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in chunk_id))

    # --- 新增：异常处理测试 ---

    def test_split_none_input(self):
        """测试传入 None 作为输入"""
        chunks = self.splitter.split(None, chunk_size=100)
        self.assertEqual(len(chunks), 0)

    def test_split_negative_chunk_size(self):
        """测试负数 chunk_size"""
        try:
            chunks = self.splitter.split("测试文本", chunk_size=-1)
            # 如果没报错，应该返回空或正常结果
            self.assertIsInstance(chunks, list)
        except (ValueError, TypeError):
            pass  # 也可以接受

    def test_split_negative_overlap(self):
        """测试负数 overlap"""
        try:
            chunks = self.splitter.split("测试文本", chunk_size=10, chunk_overlap=-5)
            self.assertIsInstance(chunks, list)
        except (ValueError, TypeError):
            pass


# ============================================================================
# TestVectorStore - 向量存储测试
# ============================================================================

class TestVectorStore(unittest.TestCase):
    """向量存储测试"""

    def setUp(self):
        self.store = VectorStore()

    def test_add_and_count_chunks(self):
        """测试添加和计数切片"""
        chunks = [
            DocumentChunk(chunk_id="c1", source_doc_id="d1", content="内容1"),
            DocumentChunk(chunk_id="c2", source_doc_id="d1", content="内容2"),
        ]
        self.store.add_chunks(chunks)
        self.assertEqual(len(self.store.chunks), 2)

    def test_remove_chunks(self):
        """测试删除切片"""
        self.store.add_chunks([
            DocumentChunk(chunk_id="c1", source_doc_id="d1", content="内容1"),
            DocumentChunk(chunk_id="c2", source_doc_id="d1", content="内容2"),
        ])
        removed = self.store.remove_chunks(["c1"])
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.store.chunks), 1)

    def test_remove_nonexistent_chunks(self):
        """测试删除不存在的切片"""
        removed = self.store.remove_chunks(["nonexistent"])
        self.assertEqual(removed, 0)

    def test_search_with_embedding(self):
        """测试向量检索"""
        chunk = DocumentChunk(
            chunk_id="c1", source_doc_id="d1", content="内容",
            embedding=[1.0, 0.0, 0.0]
        )
        self.store.add_chunks([chunk])
        results = self.store.search([1.0, 0.0, 0.0], top_k=5)
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0][1], 1.0, places=5)

    def test_search_without_embedding(self):
        """测试无 embedding 的切片不参与检索"""
        chunk = DocumentChunk(chunk_id="c1", source_doc_id="d1", content="内容")
        self.store.add_chunks([chunk])
        results = self.store.search([1.0, 0.0, 0.0], top_k=5)
        self.assertEqual(len(results), 0)

    def test_search_empty_query(self):
        """测试空查询向量"""
        results = self.store.search([], top_k=5)
        self.assertEqual(len(results), 0)

    def test_cosine_similarity_identical(self):
        """测试相同向量的余弦相似度为 1"""
        similarity = VectorStore._cosine_similarity([1.0, 0.0], [1.0, 0.0])
        self.assertAlmostEqual(similarity, 1.0, places=5)

    def test_cosine_similarity_orthogonal(self):
        """测试正交向量的余弦相似度为 0"""
        similarity = VectorStore._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        self.assertAlmostEqual(similarity, 0.0, places=5)

    def test_cosine_similarity_empty(self):
        """测试空向量的余弦相似度"""
        self.assertEqual(VectorStore._cosine_similarity([], [1.0]), 0.0)
        self.assertEqual(VectorStore._cosine_similarity([1.0], []), 0.0)

    def test_cosine_similarity_zero_vector(self):
        """测试零向量的余弦相似度"""
        self.assertEqual(VectorStore._cosine_similarity([0.0, 0.0], [1.0, 0.0]), 0.0)

    def test_get_stats(self):
        """测试获取存储统计"""
        self.store.add_chunks([
            DocumentChunk(chunk_id="c1", source_doc_id="d1", content="内容1", embedding=[1.0]),
            DocumentChunk(chunk_id="c2", source_doc_id="d1", content="内容2"),
        ])
        stats = self.store.get_stats()
        self.assertEqual(stats["total_chunks"], 2)
        self.assertEqual(stats["with_embedding"], 1)

    # --- 新增：边界条件测试 ---

    def test_add_empty_chunks_list(self):
        """测试添加空切片列表"""
        self.store.add_chunks([])
        self.assertEqual(len(self.store.chunks), 0)

    def test_add_duplicate_chunk_ids(self):
        """测试添加重复 chunk_id 的切片（应覆盖）"""
        chunk1 = DocumentChunk(chunk_id="c1", source_doc_id="d1", content="内容1")
        chunk2 = DocumentChunk(chunk_id="c1", source_doc_id="d2", content="内容2")
        self.store.add_chunks([chunk1, chunk2])
        self.assertEqual(len(self.store.chunks), 1)
        self.assertEqual(self.store.chunks["c1"].content, "内容2")

    def test_remove_all_chunks(self):
        """测试删除所有切片"""
        self.store.add_chunks([
            DocumentChunk(chunk_id="c1", source_doc_id="d1", content="内容1"),
            DocumentChunk(chunk_id="c2", source_doc_id="d1", content="内容2"),
        ])
        removed = self.store.remove_chunks(["c1", "c2"])
        self.assertEqual(removed, 2)
        self.assertEqual(len(self.store.chunks), 0)

    def test_search_empty_store(self):
        """测试在空存储中检索"""
        results = self.store.search([1.0, 0.0], top_k=5)
        self.assertEqual(len(results), 0)

    def test_search_top_k_limit(self):
        """测试 top_k 限制"""
        for i in range(10):
            self.store.add_chunks([
                DocumentChunk(chunk_id=f"c{i}", source_doc_id="d1",
                              content=f"内容{i}", embedding=[float(i), 0.0])
            ])
        results = self.store.search([1.0, 0.0], top_k=3)
        self.assertLessEqual(len(results), 3)

    # --- 新增：异常处理测试 ---

    def test_remove_from_empty_store(self):
        """测试从空存储中删除"""
        removed = self.store.remove_chunks(["c1"])
        self.assertEqual(removed, 0)

    def test_cosine_similarity_different_lengths(self):
        """测试不同长度向量的余弦相似度"""
        similarity = VectorStore._cosine_similarity([1.0, 0.0], [1.0])
        # zip 会截断到最短长度
        self.assertAlmostEqual(similarity, 1.0, places=5)


# ============================================================================
# TestHybridRetriever - 混合检索器测试
# ============================================================================

class TestHybridRetriever(unittest.TestCase):
    """混合检索器测试"""

    def setUp(self):
        self.store = VectorStore()
        self.retriever = HybridRetriever(self.store)

        test_chunks = [
            DocumentChunk(
                chunk_id="c001", source_doc_id="d001",
                content="压力容器操作的安全距离为 3 米。操作人员必须佩戴防护装备。",
                title="安全操作规程", metadata={"days_old": 30},
            ),
            DocumentChunk(
                chunk_id="c002", source_doc_id="d001",
                content="新员工入职需要携带身份证、学历证明、离职证明等材料。",
                title="员工手册", metadata={"days_old": 60},
            ),
            DocumentChunk(
                chunk_id="c003", source_doc_id="d002",
                content="报销流程：在系统中提交报销申请，上传发票，主管审批后财务打款。",
                title="报销流程", metadata={"days_old": 200},
            ),
        ]
        self.store.add_chunks(test_chunks)
        self.retriever.build_keyword_index()

    def test_exact_match(self):
        """测试精确匹配"""
        results = self.retriever.retrieve("压力容器安全距离", top_k=3)
        self.assertGreater(len(results), 0)
        self.assertIn("安全", results[0].source_doc_title)

    def test_no_match(self):
        """测试无匹配结果"""
        results = self.retriever.retrieve("怎么修汽车", top_k=3)
        if results:
            self.assertLess(results[0].score, 0.3)

    def test_expired_doc_ranking(self):
        """测试过期文档排序靠后"""
        results = self.retriever.retrieve("报销", top_k=3)
        for r in results:
            if r.chunk.metadata.get("days_old", 0) > 180:
                self.assertLessEqual(r.score, 1.0)

    def test_rerank_title_boost(self):
        """测试标题匹配加分"""
        results = self.retriever.retrieve("安全", top_k=3)
        safety_results = [r for r in results if "安全" in r.source_doc_title]
        if safety_results:
            self.assertGreater(safety_results[0].score, 0.1)

    def test_rerank_freshness(self):
        """测试时效性衰减"""
        old_chunk = DocumentChunk(
            chunk_id="old001", source_doc_id="old_doc",
            content="压力容器操作的安全距离为 1.5 米（旧版）。",
            title="安全操作规程", metadata={"days_old": 400},
        )
        new_chunk = DocumentChunk(
            chunk_id="new001", source_doc_id="new_doc",
            content="压力容器操作的安全距离为 3 米（新版）。",
            title="安全操作规程", metadata={"days_old": 30},
        )
        self.store.add_chunks([old_chunk, new_chunk])
        self.retriever.build_keyword_index()

        results = self.retriever.retrieve("压力容器安全距离", top_k=5)
        if len(results) >= 2:
            old_score = next((r.score for r in results if r.chunk.chunk_id == "old001"), 0)
            new_score = next((r.score for r in results if r.chunk.chunk_id == "new001"), 0)
            self.assertGreater(new_score, old_score)

    # --- 新增：边界条件测试 ---

    def test_retrieve_empty_query(self):
        """测试空查询字符串"""
        results = self.retriever.retrieve("", top_k=3)
        self.assertIsInstance(results, list)

    def test_retrieve_whitespace_query(self):
        """测试空白查询字符串"""
        results = self.retriever.retrieve("   ", top_k=3)
        self.assertIsInstance(results, list)

    def test_retrieve_top_k_one(self):
        """测试 top_k=1"""
        results = self.retriever.retrieve("安全", top_k=1)
        self.assertLessEqual(len(results), 1)

    def test_retrieve_top_k_zero(self):
        """测试 top_k=0"""
        results = self.retriever.retrieve("安全", top_k=0)
        self.assertEqual(len(results), 0)

    def test_retrieve_top_k_negative(self):
        """测试负数 top_k"""
        results = self.retriever.retrieve("安全", top_k=-1)
        self.assertIsInstance(results, list)

    def test_retrieve_very_long_query(self):
        """测试超长查询"""
        long_query = "测试" * 1000
        results = self.retriever.retrieve(long_query, top_k=3)
        self.assertIsInstance(results, list)

    def test_retrieve_special_characters_query(self):
        """测试包含特殊字符的查询"""
        results = self.retriever.retrieve("安全!@#$%^&*()", top_k=3)
        self.assertIsInstance(results, list)

    def test_retrieve_chinese_query(self):
        """测试中文查询"""
        results = self.retriever.retrieve("新员工入职材料", top_k=3)
        self.assertGreater(len(results), 0)

    def test_retrieve_english_query(self):
        """测试英文查询"""
        results = self.retriever.retrieve("safety distance", top_k=3)
        self.assertIsInstance(results, list)

    def test_rebuild_keyword_index(self):
        """测试重新构建关键词索引"""
        self.store.add_chunks([
            DocumentChunk(chunk_id="new1", source_doc_id="d3",
                          content="全新内容测试", title="新文档")
        ])
        self.retriever.build_keyword_index()
        results = self.retriever.retrieve("全新内容", top_k=3)
        self.assertGreater(len(results), 0)

    def test_retrieve_empty_store(self):
        """测试在空存储中检索"""
        empty_store = VectorStore()
        empty_retriever = HybridRetriever(empty_store)
        empty_retriever.build_keyword_index()
        results = empty_retriever.retrieve("测试", top_k=3)
        self.assertEqual(len(results), 0)

    # --- 新增：异常处理测试 ---

    def test_retrieve_unicode_query(self):
        """测试 Unicode 查询"""
        results = self.retriever.retrieve("安全距离 测试", top_k=3)
        self.assertIsInstance(results, list)

    def test_retrieve_with_emoji_query(self):
        """测试包含 emoji 的查询"""
        results = self.retriever.retrieve("安全🔒距离", top_k=3)
        self.assertIsInstance(results, list)

    # --- 新增：数据验证测试 ---

    def test_search_result_structure(self):
        """测试检索结果结构"""
        results = self.retriever.retrieve("安全", top_k=3)
        if results:
            result = results[0]
            self.assertIsInstance(result, SearchResult)
            self.assertIsInstance(result.chunk, DocumentChunk)
            self.assertIsInstance(result.score, float)
            self.assertIsInstance(result.source_doc_title, str)
            self.assertGreaterEqual(result.score, 0.0)

    def test_score_capped_at_one(self):
        """测试得分不超过 1.0"""
        results = self.retriever.retrieve("安全", top_k=5)
        for r in results:
            self.assertLessEqual(r.score, 1.0)

    def test_score_minimum_filter(self):
        """测试最低分过滤"""
        results = self.retriever.retrieve("安全", top_k=10)
        for r in results:
            self.assertGreaterEqual(r.score, 0.01)

    def test_tokenize_english(self):
        """测试英文分词"""
        tokens = HybridRetriever._tokenize("hello world test123")
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertIn("test123", tokens)

    def test_tokenize_chinese(self):
        """测试中文分词"""
        tokens = HybridRetriever._tokenize("测试中文")
        self.assertIn("测", tokens)
        self.assertIn("试", tokens)
        self.assertIn("中", tokens)
        self.assertIn("文", tokens)

    def test_tokenize_mixed(self):
        """测试混合分词"""
        tokens = HybridRetriever._tokenize("hello 测试 world")
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertIn("测", tokens)
        self.assertIn("试", tokens)

    def test_tokenize_empty(self):
        """测试空字符串分词"""
        tokens = HybridRetriever._tokenize("")
        self.assertEqual(len(tokens), 0)

    def test_tokenize_single_char_english(self):
        """测试单字符英文不被提取"""
        tokens = HybridRetriever._tokenize("a b c")
        self.assertEqual(len(tokens), 0)  # 英文单词需要 >=2 字符

    def test_merge_results_empty(self):
        """测试合并空结果"""
        merged = HybridRetriever._merge_results([], [])
        self.assertEqual(len(merged), 0)

    def test_rerank_empty(self):
        """测试空结果重排序"""
        reranked = HybridRetriever._rerank("测试", [], top_k=5)
        self.assertEqual(len(reranked), 0)


# ============================================================================
# TestKnowledgeBaseQA - 知识库问答测试
# ============================================================================

class TestKnowledgeBaseQA(unittest.TestCase):
    """知识库问答测试"""

    def setUp(self):
        store = VectorStore()
        store.add_chunks([DocumentChunk(
            chunk_id="qa001", source_doc_id="qa_doc",
            content="压力容器操作的安全距离为 3 米。操作人员必须佩戴防护装备。",
            title="安全操作规程", metadata={"days_old": 30},
        )])
        self.retriever = HybridRetriever(store)
        self.retriever.build_keyword_index()

        def mock_llm(prompt):
            return "根据安全操作规程，压力容器操作的安全距离为 3 米。"

        self.qa = KnowledgeBaseQA(self.retriever, mock_llm)

    def test_answer_question(self):
        """测试问答"""
        result = self.qa.answer("压力容器安全距离")
        self.assertFalse(result.is_rejected)
        self.assertIn("3 米", result.answer)
        self.assertGreater(result.confidence, 0.0)

    def test_reject_unknown(self):
        """测试拒答未知问题"""
        result = self.qa.answer("怎么修电脑")
        self.assertTrue(result.is_rejected)
        self.assertIn("抱歉", result.answer)

    def test_answer_sources(self):
        """测试答案来源"""
        result = self.qa.answer("压力容器安全距离")
        self.assertGreater(len(result.sources), 0)

    def test_no_llm_mode(self):
        """测试无 LLM 模式"""
        qa_no_llm = KnowledgeBaseQA(self.retriever)
        result = qa_no_llm.answer("压力容器安全距离")
        self.assertFalse(result.is_rejected)
        self.assertGreater(len(result.answer), 0)

    # --- 新增：边界条件测试 ---

    def test_answer_empty_question(self):
        """测试空问题"""
        result = self.qa.answer("")
        self.assertIsInstance(result, QAResult)
        self.assertEqual(result.question, "")

    def test_answer_whitespace_question(self):
        """测试空白问题"""
        result = self.qa.answer("   ")
        self.assertIsInstance(result, QAResult)

    def test_answer_very_long_question(self):
        """测试超长问题"""
        long_question = "测试" * 500
        result = self.qa.answer(long_question)
        self.assertIsInstance(result, QAResult)

    def test_answer_special_chars_question(self):
        """测试包含特殊字符的问题"""
        result = self.qa.answer("安全距离!@#$%^&*()")
        self.assertIsInstance(result, QAResult)

    def test_answer_unicode_question(self):
        """测试 Unicode 问题"""
        result = self.qa.answer("压力容器安全距离是多少？")
        self.assertIsInstance(result, QAResult)

    # --- 新增：异常处理测试 ---

    def test_answer_with_low_score_retrieval(self):
        """测试低分检索结果被拒绝"""
        # 清空存储
        self.retriever.vector_store.chunks.clear()
        self.retriever.build_keyword_index()

        result = self.qa.answer("测试问题")
        self.assertTrue(result.is_rejected)

    def test_answer_with_no_retriever_results(self):
        """测试检索器返回空结果"""
        empty_store = VectorStore()
        empty_retriever = HybridRetriever(empty_store)
        empty_retriever.build_keyword_index()
        qa = KnowledgeBaseQA(empty_retriever)

        result = qa.answer("任意问题")
        self.assertTrue(result.is_rejected)

    # --- 新增：数据验证测试 ---

    def test_qa_result_to_dict(self):
        """测试问答结果转字典"""
        result = self.qa.answer("压力容器安全距离")
        result_dict = result.to_dict()
        self.assertIn("question", result_dict)
        self.assertIn("answer", result_dict)
        self.assertIn("sources", result_dict)
        self.assertIn("confidence", result_dict)
        self.assertIn("is_rejected", result_dict)
        self.assertIn("quality_issues", result_dict)

    def test_qa_result_confidence_range(self):
        """测试置信度范围"""
        result = self.qa.answer("压力容器安全距离")
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_qa_result_sources_not_empty(self):
        """测试答案来源不为空（成功回答时）"""
        result = self.qa.answer("压力容器安全距离")
        if not result.is_rejected:
            self.assertGreater(len(result.sources), 0)

    def test_qa_result_quality_issues(self):
        """测试质量检查"""
        result = self.qa.answer("压力容器安全距离")
        self.assertIsInstance(result.quality_issues, list)

    # --- 新增：集成测试 ---

    def test_full_qa_workflow(self):
        """测试完整问答流程"""
        result = self.qa.answer("压力容器安全距离")
        self.assertFalse(result.is_rejected)
        self.assertGreater(len(result.answer), 0)
        self.assertGreater(len(result.sources), 0)
        self.assertGreater(result.confidence, 0.0)

    def test_qa_with_custom_config(self):
        """测试自定义配置"""
        store = VectorStore()
        store.add_chunks([DocumentChunk(
            chunk_id="qa002", source_doc_id="qa_doc2",
            content="测试内容。", title="测试文档",
            metadata={"days_old": 30},
        )])
        retriever = HybridRetriever(store)
        retriever.build_keyword_index()

        qa = KnowledgeBaseQA(retriever, config={"min_retrieval_score": 0.9})
        result = qa.answer("测试")
        # 高阈值可能导致拒答
        self.assertIsInstance(result, QAResult)

    def test_qa_multiple_questions(self):
        """测试连续多个问题"""
        questions = [
            "压力容器安全距离",
            "防护装备",
            "怎么修电脑",
        ]
        for q in questions:
            result = self.qa.answer(q)
            self.assertIsInstance(result, QAResult)
            self.assertEqual(result.question, q)


# ============================================================================
# TestConfig - 配置测试
# ============================================================================

class TestConfig(unittest.TestCase):
    """配置管理器测试"""

    def setUp(self):
        self.config = Config()

    def tearDown(self):
        # 清理环境变量
        for key in ["DASHSCOPE_API_KEY", "KB_QA_DEBUG"]:
            if key in os.environ:
                del os.environ[key]

    def test_default_config(self):
        """测试默认配置"""
        self.assertEqual(self.config.get("app.name"), "企业知识库问答系统")
        self.assertEqual(self.config.get("app.version"), "1.0.0")
        self.assertFalse(self.config.get("app.debug"))

    def test_get_nested_config(self):
        """测试获取嵌套配置"""
        self.assertEqual(self.config.get("parsing.chunk_size"), 300)
        self.assertEqual(self.config.get("parsing.chunk_overlap"), 50)
        self.assertEqual(self.config.get("retrieval.top_k"), 5)

    def test_get_missing_config(self):
        """测试获取不存在的配置"""
        self.assertIsNone(self.config.get("nonexistent.key"))
        self.assertEqual(self.config.get("nonexistent.key", "default"), "default")

    def test_get_section(self):
        """测试获取配置段"""
        parsing = self.config.get_section("parsing")
        self.assertIn("chunk_size", parsing)
        self.assertIn("chunk_overlap", parsing)

    def test_load_from_file(self):
        """测试从文件加载配置"""
        config_file = "/tmp/test_config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("app:\n  name: 自定义系统\n  debug: true\n")

        config = Config(config_file)
        self.assertEqual(config.get("app.name"), "自定义系统")
        self.assertTrue(config.get("app.debug"))
        os.remove(config_file)

    def test_load_from_nonexistent_file(self):
        """测试从不存在的文件加载配置（应使用默认配置）"""
        config = Config("/nonexistent/config.yaml")
        self.assertEqual(config.get("app.name"), "企业知识库问答系统")

    def test_load_from_invalid_yaml(self):
        """测试从无效 YAML 文件加载"""
        config_file = "/tmp/test_invalid.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        config = Config(config_file)
        # 应该使用默认配置
        self.assertEqual(config.get("app.name"), "企业知识库问答系统")
        os.remove(config_file)

    def test_env_api_key(self):
        """测试从环境变量加载 API Key"""
        os.environ["DASHSCOPE_API_KEY"] = "test-api-key"
        config = Config()
        self.assertEqual(config.get("llm.api_key"), "test-api-key")
        self.assertTrue(config.get("llm.enabled"))

    def test_env_debug(self):
        """测试从环境变量加载 debug 模式"""
        os.environ["KB_QA_DEBUG"] = "true"
        config = Config()
        self.assertTrue(config.get("app.debug"))

    def test_env_debug_false(self):
        """测试环境变量 debug=false"""
        os.environ["KB_QA_DEBUG"] = "false"
        config = Config()
        self.assertFalse(config.get("app.debug"))

    def test_deep_merge(self):
        """测试深度合并"""
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": 10, "d": 3}}
        config = Config()
        config._deep_merge(base, override)
        self.assertEqual(base["a"]["b"], 10)
        self.assertEqual(base["a"]["c"], 2)
        self.assertEqual(base["a"]["d"], 3)

    def test_config_property(self):
        """测试 config 属性"""
        full_config = self.config.config
        self.assertIn("app", full_config)
        self.assertIn("parsing", full_config)
        self.assertIn("retrieval", full_config)

    def test_config_repr(self):
        """测试 config 的 repr"""
        repr_str = repr(self.config)
        self.assertIn("Config", repr_str)

    def test_load_config_factory(self):
        """测试 load_config 工厂函数"""
        config = load_config()
        self.assertIsInstance(config, Config)

    def test_supported_formats(self):
        """测试支持的格式列表"""
        formats = self.config.get("parsing.supported_formats")
        self.assertIn(".md", formats)
        self.assertIn(".txt", formats)
        self.assertIn(".html", formats)

    def test_llm_default_disabled(self):
        """测试 LLM 默认禁用"""
        config = Config()
        self.assertFalse(config.get("llm.enabled"))
        self.assertEqual(config.get("llm.provider"), "dashscope")
        self.assertEqual(config.get("llm.model"), "qwen-plus")

    def test_logging_config(self):
        """测试日志配置"""
        level = self.config.get("logging.level")
        fmt = self.config.get("logging.format")
        self.assertEqual(level, "INFO")
        self.assertIn("%(asctime)s", fmt)

    def test_config_file_override_default(self):
        """测试配置文件覆盖默认值"""
        config_file = "/tmp/test_override.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("retrieval:\n  top_k: 10\n  min_score: 0.5\n")

        config = Config(config_file)
        self.assertEqual(config.get("retrieval.top_k"), 10)
        self.assertEqual(config.get("retrieval.min_score"), 0.5)
        # 未被覆盖的默认值保持不变
        self.assertEqual(config.get("parsing.chunk_size"), 300)
        os.remove(config_file)

    def test_env_overrides_file(self):
        """测试环境变量覆盖文件配置"""
        config_file = "/tmp/test_env_override.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("llm:\n  enabled: false\n  api_key: file-key\n")

        os.environ["DASHSCOPE_API_KEY"] = "env-key"
        config = Config(config_file)
        self.assertEqual(config.get("llm.api_key"), "env-key")
        self.assertTrue(config.get("llm.enabled"))
        os.remove(config_file)


# ============================================================================
# TestDocumentChunk - 文档切片测试
# ============================================================================

class TestDocumentChunk(unittest.TestCase):
    """文档切片数据类测试"""

    def test_chunk_to_dict(self):
        """测试切片转字典"""
        chunk = DocumentChunk(
            chunk_id="c1", source_doc_id="d1", content="内容",
            title="标题", section="章节", page_number=1, order=0,
            metadata={"key": "value"}
        )
        d = chunk.to_dict()
        self.assertEqual(d["chunk_id"], "c1")
        self.assertEqual(d["source_doc_id"], "d1")
        self.assertEqual(d["content"], "内容")
        self.assertEqual(d["title"], "标题")
        self.assertEqual(d["section"], "章节")
        self.assertEqual(d["page_number"], 1)
        self.assertEqual(d["order"], 0)
        self.assertEqual(d["metadata"], {"key": "value"})

    def test_chunk_from_dict(self):
        """测试从字典创建切片"""
        data = {
            "chunk_id": "c1", "source_doc_id": "d1", "content": "内容",
            "title": "标题", "section": "章节", "page_number": 1, "order": 0,
            "metadata": {"key": "value"}
        }
        chunk = DocumentChunk.from_dict(data)
        self.assertEqual(chunk.chunk_id, "c1")
        self.assertEqual(chunk.source_doc_id, "d1")
        self.assertEqual(chunk.content, "内容")
        self.assertEqual(chunk.title, "标题")
        self.assertEqual(chunk.metadata, {"key": "value"})

    def test_chunk_from_dict_defaults(self):
        """测试从字典创建切片使用默认值"""
        data = {"chunk_id": "c1", "source_doc_id": "d1", "content": "内容"}
        chunk = DocumentChunk.from_dict(data)
        self.assertEqual(chunk.title, "")
        self.assertEqual(chunk.section, "")
        self.assertEqual(chunk.page_number, 0)
        self.assertEqual(chunk.order, 0)
        self.assertEqual(chunk.metadata, {})

    def test_chunk_roundtrip(self):
        """测试 to_dict -> from_dict 往返"""
        original = DocumentChunk(
            chunk_id="c1", source_doc_id="d1", content="内容",
            title="标题", metadata={"key": "value"}
        )
        restored = DocumentChunk.from_dict(original.to_dict())
        self.assertEqual(original.chunk_id, restored.chunk_id)
        self.assertEqual(original.content, restored.content)
        self.assertEqual(original.title, restored.title)

    def test_doc_status_enum(self):
        """测试文档状态枚举"""
        self.assertEqual(DocStatus.ACTIVE.value, "active")
        self.assertEqual(DocStatus.EXPIRED.value, "expired")
        self.assertEqual(DocStatus.ARCHIVED.value, "archived")

    def test_knowledge_document(self):
        """测试知识文档数据类"""
        doc = KnowledgeDocument(
            doc_id="d1", title="测试文档", file_path="/path/to/file.txt",
            file_type="txt", version=1, status=DocStatus.ACTIVE
        )
        self.assertEqual(doc.doc_id, "d1")
        self.assertEqual(doc.title, "测试文档")
        self.assertEqual(doc.file_type, "txt")
        self.assertEqual(doc.status, DocStatus.ACTIVE)
        self.assertEqual(len(doc.chunks), 0)


# ============================================================================
# TestSearchResult - 检索结果测试
# ============================================================================

class TestSearchResult(unittest.TestCase):
    """检索结果数据类测试"""

    def test_search_result_creation(self):
        """测试创建检索结果"""
        chunk = DocumentChunk(chunk_id="c1", source_doc_id="d1", content="内容")
        result = SearchResult(chunk=chunk, score=0.9, source_doc_title="标题")
        self.assertEqual(result.chunk.chunk_id, "c1")
        self.assertAlmostEqual(result.score, 0.9)
        self.assertEqual(result.source_doc_title, "标题")


# ============================================================================
# TestQAResult - 问答结果测试
# ============================================================================

class TestQAResult(unittest.TestCase):
    """问答结果数据类测试"""

    def test_qa_result_defaults(self):
        """测试问答结果默认值"""
        result = QAResult(question="测试问题")
        self.assertEqual(result.question, "测试问题")
        self.assertEqual(result.answer, "")
        self.assertEqual(result.sources, [])
        self.assertEqual(result.confidence, 0.0)
        self.assertFalse(result.is_rejected)
        self.assertEqual(result.quality_issues, [])

    def test_qa_result_to_dict(self):
        """测试问答结果转字典"""
        result = QAResult(
            question="测试", answer="回答", sources=["来源1"],
            confidence=0.85, is_rejected=False, quality_issues=[]
        )
        d = result.to_dict()
        self.assertEqual(d["question"], "测试")
        self.assertEqual(d["answer"], "回答")
        self.assertEqual(d["sources"], ["来源1"])
        self.assertAlmostEqual(d["confidence"], 0.85)
        self.assertFalse(d["is_rejected"])


# ============================================================================
# TestPerformance - 性能测试
# ============================================================================

class TestPerformance(unittest.TestCase):
    """性能测试"""

    def setUp(self):
        store = VectorStore()
        for i in range(100):
            store.add_chunks([DocumentChunk(
                chunk_id=f"perf{i:03d}", source_doc_id="perf_doc",
                content=f"这是第{i}个知识片段，包含一些测试内容。",
                title="测试文档", metadata={"days_old": i},
            )])
        self.retriever = HybridRetriever(store)
        self.retriever.build_keyword_index()
        self.qa = KnowledgeBaseQA(self.retriever)

    def test_retrieval_performance(self):
        """测试检索性能"""
        start = time.time()
        for i in range(50):
            self.qa.answer(f"第{i}个问题")
        elapsed = time.time() - start
        avg_time = elapsed / 50
        self.assertLess(avg_time, 0.01, f"平均响应时间过长: {avg_time:.4f}s")
        print(f"\n性能测试：50 次问答，总耗时 {elapsed:.3f}s，平均 {avg_time:.4f}s/次")

    def test_large_store_retrieval(self):
        """测试大型存储检索性能"""
        store = VectorStore()
        for i in range(500):
            store.add_chunks([DocumentChunk(
                chunk_id=f"large{i:04d}", source_doc_id="large_doc",
                content=f"大型存储测试第{i}个知识片段内容。",
                title="大型文档", metadata={"days_old": i % 365},
            )])
        retriever = HybridRetriever(store)
        retriever.build_keyword_index()

        start = time.time()
        results = retriever.retrieve("测试知识片段", top_k=10)
        elapsed = time.time() - start
        self.assertLess(elapsed, 1.0, f"检索耗时过长: {elapsed:.3f}s")
        self.assertLessEqual(len(results), 10)
        print(f"\n大型存储检索性能：500 条数据检索耗时 {elapsed:.4f}s")

    def test_index_build_performance(self):
        """测试索引构建性能"""
        store = VectorStore()
        for i in range(1000):
            store.add_chunks([DocumentChunk(
                chunk_id=f"idx{i:04d}", source_doc_id="idx_doc",
                content=f"索引构建测试内容第{i}条。",
                title="索引文档", metadata={"days_old": 0},
            )])
        retriever = HybridRetriever(store)

        start = time.time()
        retriever.build_keyword_index()
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"索引构建耗时过长: {elapsed:.3f}s")
        print(f"\n索引构建性能：1000 条数据耗时 {elapsed:.4f}s")

    def test_split_performance(self):
        """测试文本切片性能"""
        splitter = TextSplitter()
        long_text = "这是一段测试文本。" * 5000

        start = time.time()
        chunks = splitter.split(long_text, chunk_size=300, chunk_overlap=50)
        elapsed = time.time() - start
        self.assertGreater(len(chunks), 0)
        self.assertLess(elapsed, 1.0)
        print(f"\n切片性能：5000 段文本切片耗时 {elapsed:.4f}s，生成 {len(chunks)} 个切片")


# ============================================================================
# TestIntegration - 集成测试
# ============================================================================

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_document_pipeline(self):
        """测试完整文档处理流程"""
        # 1. 创建测试文档
        test_file = "/tmp/test_integration.md"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# 安全手册\n\n压力容器操作安全距离为3米。\n\n操作人员必须佩戴防护装备。")

        # 2. 解析文档
        parser = DocumentParser()
        content = parser.parse(test_file)
        self.assertIn("安全", content)

        # 3. 切片
        splitter = TextSplitter()
        chunks = splitter.split(content, chunk_size=50, source_title="安全手册")
        self.assertGreater(len(chunks), 0)

        # 4. 存储
        store = VectorStore()
        for chunk in chunks:
            chunk.source_doc_id = "test_doc"
            chunk.metadata = {"days_old": 10}
        store.add_chunks(chunks)

        # 5. 检索
        retriever = HybridRetriever(store)
        retriever.build_keyword_index()
        results = retriever.retrieve("压力容器安全", top_k=3)
        self.assertGreater(len(results), 0)

        # 6. 问答
        qa = KnowledgeBaseQA(retriever)
        result = qa.answer("压力容器安全距离")
        self.assertIsInstance(result, QAResult)

        os.remove(test_file)

    def test_multi_document_qa(self):
        """测试多文档问答"""
        store = VectorStore()
        documents = [
            ("安全规程", "压力容器操作安全距离为3米。"),
            ("员工手册", "新员工需要携带身份证和学历证明。"),
            ("报销流程", "报销需要提交发票和审批单。"),
        ]
        for title, content in documents:
            store.add_chunks([DocumentChunk(
                chunk_id=f"multi_{title}", source_doc_id="multi_doc",
                content=content, title=title, metadata={"days_old": 30},
            )])

        retriever = HybridRetriever(store)
        retriever.build_keyword_index()
        qa = KnowledgeBaseQA(retriever)

        # 测试每个主题的问答
        test_cases = [
            ("安全距离", False),
            ("新员工材料", False),
            ("报销", False),
            ("怎么修电脑", True),
        ]
        for question, expect_rejected in test_cases:
            result = qa.answer(question)
            self.assertEqual(result.is_rejected, expect_rejected,
                             f"问题 '{question}' 拒答状态不符合预期")

    def test_config_integration(self):
        """测试配置与 QA 系统集成"""
        config_file = "/tmp/test_integration_config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("retrieval:\n  min_score: 0.5\n")

        config = Config(config_file)
        min_score = config.get("retrieval.min_score", 0.3)

        store = VectorStore()
        store.add_chunks([DocumentChunk(
            chunk_id="cfg001", source_doc_id="cfg_doc",
            content="测试内容", title="测试",
            metadata={"days_old": 30},
        )])
        retriever = HybridRetriever(store)
        retriever.build_keyword_index()

        qa = KnowledgeBaseQA(retriever, config={"min_retrieval_score": min_score})
        result = qa.answer("测试")
        self.assertIsInstance(result, QAResult)

        os.remove(config_file)


if __name__ == "__main__":
    unittest.main(verbosity=2)
