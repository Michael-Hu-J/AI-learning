"""文档自动摘要系统自动化测试"""

import sys
import os
import unittest
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_parser import DocumentParser, DocumentChunk
from src.extractive_summarizer import ExtractiveSummarizer
from src.generative_summarizer import GenerativeSummarizer
from src.summary_evaluator import SummaryEvaluator


# =============================================================================
# 1. 核心功能测试 — 文档解析器
# =============================================================================

class TestDocumentParser(unittest.TestCase):
    """文档解析器测试"""

    def setUp(self):
        self.parser = DocumentParser()

    def test_clean_whitespace(self):
        text = "多    余    空    白"
        cleaned = self.parser.parse_raw_text(text)
        self.assertNotIn("  ", cleaned)

    def test_remove_page_numbers(self):
        text = "正文内容\n\n123\n\n继续正文"
        cleaned = self.parser.parse_raw_text(text)
        self.assertNotIn("\n123\n", cleaned)

    def test_split_into_chunks_basic(self):
        text = "段落一的内容。\n\n段落二的内容。\n\n段落三的内容。"
        chunks = self.parser.split_into_chunks(text, max_chunk_size=200)
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertGreater(len(chunk.content), 0)

    def test_split_into_chunks_long_paragraph(self):
        long_text = "内容。" * 500
        chunks = self.parser.split_into_chunks(long_text, max_chunk_size=200)
        self.assertGreater(len(chunks), 1)

    def test_empty_input(self):
        chunks = self.parser.split_into_chunks("", max_chunk_size=200)
        # 可能返回 0 或 1 个（含空段落）
        self.assertIsNotNone(chunks)

    def test_sentence_splitting(self):
        text = "第一句话。第二句话！第三句话？第四句话；第五句话。"
        sentences = self.parser._split_sentences(text)
        self.assertGreater(len(sentences), 1)


# =============================================================================
# 2. 核心功能测试 — 抽取式摘要
# =============================================================================

class TestExtractiveSummarizer(unittest.TestCase):
    """抽取式摘要测试"""

    def setUp(self):
        self.extractor = ExtractiveSummarizer()
        self.sample = """人工智能（Artificial Intelligence，简称 AI）是计算机科学的一个分支，
用于开发能够模拟人类智能行为的系统。自 1956 年达特茅斯会议首次提出"人工智能"概念以来，
该领域经历了多次发展浪潮。

机器学习是人工智能的核心技术之一。2012 年，深度学习在图像识别领域取得突破性进展，
AlexNet 在 ImageNet 竞赛中将错误率从 26% 降低到 15%。此后，深度学习在语音识别、
自然语言处理、机器翻译等领域相继取得重大突破。

2017 年，Google 提出了 Transformer 架构，彻底改变了自然语言处理领域。
基于 Transformer 的 BERT、GPT 等模型在多项 NLP 任务上刷新了记录。"""

    def test_summary_not_empty(self):
        summary = self.extractor.summarize(self.sample, summary_ratio=0.2)
        self.assertGreater(len(summary), 0)

    def test_compression_ratio(self):
        summary = self.extractor.summarize(self.sample, summary_ratio=0.2)
        ratio = len(summary) / len(self.sample)
        self.assertLess(ratio, 0.4)
        self.assertGreater(ratio, 0.02)

    def test_short_input(self):
        short = "人工智能是未来。"
        result = self.extractor.summarize(short)
        self.assertEqual(result, short)

    def test_empty_input(self):
        result = self.extractor.summarize("")
        self.assertEqual(result, "")


# =============================================================================
# 3. 核心功能测试 — 摘要评估器
# =============================================================================

class TestSummaryEvaluator(unittest.TestCase):
    """摘要质量评估测试"""

    def setUp(self):
        self.evaluator = SummaryEvaluator()
        self.original = """人工智能是计算机科学的一个分支，用于开发能够模拟人类智能行为的系统。
2012年，深度学习在图像识别领域取得突破，AlexNet将错误率从26%降低到15%。
2017年，Google提出Transformer架构，彻底改变了自然语言处理领域。"""
        self.summary = """人工智能用于模拟人类智能。2012年深度学习取得突破，
错误率从26%降到15%。2017年Transformer架构改变了NLP领域。"""

    def test_rouge_1_non_zero(self):
        results = self.evaluator.evaluate(self.original, self.summary)
        self.assertGreater(results["rouge_1"]["f1"], 0.0)

    def test_rouge_l_non_zero(self):
        results = self.evaluator.evaluate(self.original, self.summary)
        self.assertGreater(results["rouge_l"]["f1"], 0.0)

    def test_compression_ratio(self):
        results = self.evaluator.evaluate(self.original, self.summary)
        self.assertGreater(results["compression_ratio"], 0.0)
        self.assertLess(results["compression_ratio"], 1.0)

    def test_factual_consistency(self):
        results = self.evaluator.evaluate(self.original, self.summary)
        self.assertGreaterEqual(results["factual_consistency"]["score"], 0.0)

    def test_readability(self):
        results = self.evaluator.evaluate(self.original, self.summary)
        self.assertGreater(results["readability"]["score"], 0.0)


# =============================================================================
# 4. 核心功能测试 — 生成式摘要
# =============================================================================

class TestGenerativeSummarizer(unittest.TestCase):
    """生成式摘要测试"""

    def setUp(self):
        self.mock_llm_calls = 0

        def mock_llm(prompt):
            self.mock_llm_calls += 1
            return "人工智能是计算机科学的分支，用于模拟人类智能。"

        self.generator = GenerativeSummarizer(mock_llm)

    def test_summary_not_empty(self):
        text = "人工智能（AI）是计算机科学的分支。用于模拟人类智能。"
        result = self.generator.summarize(text)
        self.assertGreater(len(result), 0)

    def test_long_document_splitting(self):
        """测试长文档分段摘要"""
        # 创建超过一个 chunk 的长文档
        long_text = "内容。" * 1500
        result = self.generator.summarize(long_text)
        self.assertGreater(len(result), 0)
        # 应该调用了多次 LLM
        self.assertGreater(self.mock_llm_calls, 1)

    def test_no_llm_mode(self):
        """测试无 LLM 模式"""
        generator = GenerativeSummarizer()
        result = generator.summarize("一些文本内容。")
        self.assertIn("LLM 未配置", result)


# =============================================================================
# 5. 核心功能测试 — 端到端
# =============================================================================

class TestEndToEnd(unittest.TestCase):
    """端到端测试"""

    def setUp(self):
        self.parser = DocumentParser()
        self.extractor = ExtractiveSummarizer()
        self.evaluator = SummaryEvaluator()
        self.sample = """人工智能是计算机科学的一个分支，用于开发能够模拟人类智能行为的系统。
2012年，深度学习在图像识别领域取得突破，AlexNet将错误率从26%降低到15%。
2017年，Google提出Transformer架构，彻底改变了自然语言处理领域。
基于Transformer的BERT和GPT等模型在多项任务上刷新记录。"""

    def test_full_pipeline(self):
        """测试完整流程：解析 → 摘要 → 评估"""
        chunks = self.parser.split_into_chunks(self.sample)
        self.assertGreater(len(chunks), 0)

        summary = self.extractor.summarize(self.sample, summary_ratio=0.3)
        self.assertGreater(len(summary), 0)

        results = self.evaluator.evaluate(self.sample, summary)
        self.assertIn("rouge_1", results)
        self.assertIn("rouge_l", results)
        self.assertIn("factual_consistency", results)


# =============================================================================
# 6. 边界条件测试 — 文档解析器
# =============================================================================

class TestDocumentParserBoundary(unittest.TestCase):
    """文档解析器边界条件测试"""

    def setUp(self):
        self.parser = DocumentParser()

    def test_only_whitespace(self):
        text = "   \t\n  \t  "
        cleaned = self.parser.parse_raw_text(text)
        self.assertEqual(cleaned.strip(), "")

    def test_only_newlines(self):
        text = "\n\n\n\n\n"
        cleaned = self.parser.parse_raw_text(text)
        self.assertEqual(cleaned.strip(), "")

    def test_single_char(self):
        text = "A"
        cleaned = self.parser.parse_raw_text(text)
        self.assertEqual(cleaned, "A")

    def test_multiple_page_numbers(self):
        text = "正文\n\n1\n\n正文2\n\n2\n\n正文3\n\n9999\n\n正文4"
        cleaned = self.parser.parse_raw_text(text)
        self.assertNotIn("\n1\n", cleaned)
        self.assertNotIn("\n2\n", cleaned)
        self.assertNotIn("\n9999\n", cleaned)

    def test_page_number_with_text(self):
        """页码行包含文字不应被移除"""
        text = "正文\n\n第123页\n\n继续"
        cleaned = self.parser.parse_raw_text(text)
        self.assertIn("第123页", cleaned)

    def test_chunk_with_overlap(self):
        long_text = "句子一。句子二。句子三。句子四。句子五。" * 100
        chunks = self.parser.split_into_chunks(long_text, max_chunk_size=100, overlap=20)
        self.assertGreater(len(chunks), 1)
        # 检查重叠：前一个 chunk 的结尾应与后一个 chunk 的开头有重叠
        if len(chunks) >= 2:
            # 由于重叠机制，内容应该连贯
            self.assertGreater(len(chunks[0].content), 0)
            self.assertGreater(len(chunks[1].content), 0)

    def test_chunk_id_uniqueness(self):
        text = "段落一。\n\n段落二。\n\n段落三。"
        chunks = self.parser.split_into_chunks(text, max_chunk_size=200)
        chunk_ids = [c.chunk_id for c in chunks]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))

    def test_chunk_order(self):
        text = "段落一。\n\n段落二。\n\n段落三。"
        chunks = self.parser.split_into_chunks(text, max_chunk_size=200)
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk.order, i)

    def test_chunk_word_count(self):
        text = "段落一的内容。"
        chunks = self.parser.split_into_chunks(text, max_chunk_size=200)
        self.assertGreater(chunks[0].word_count, 0)

    def test_max_chunk_size_one(self):
        """测试极小的 max_chunk_size"""
        text = "ABC。DEF。"
        chunks = self.parser.split_into_chunks(text, max_chunk_size=1)
        self.assertGreater(len(chunks), 0)

    def test_very_long_single_paragraph(self):
        text = "A" * 100000
        chunks = self.parser.split_into_chunks(text, max_chunk_size=1000)
        # 没有句子分隔符时，整个文本作为一个 chunk 返回
        self.assertGreater(len(chunks), 0)
        total_chars = sum(c.word_count for c in chunks)
        self.assertGreater(total_chars, 0)

    def test_mixed_languages(self):
        text = "Hello world. 你好世界。こんにちは世界。"
        chunks = self.parser.split_into_chunks(text, max_chunk_size=200)
        self.assertGreater(len(chunks), 0)

    def test_special_characters(self):
        text = "特殊字符：@#$%^&*()_+{}|:\"<>?\n\n继续内容。"
        cleaned = self.parser.parse_raw_text(text)
        self.assertIn("@#$%^&*()", cleaned)

    def test_html_tags_in_text(self):
        text = "<p>段落内容</p>\n\n<div>更多</div>"
        cleaned = self.parser.parse_raw_text(text)
        self.assertIn("<p>", cleaned)


# =============================================================================
# 7. 边界条件测试 — 抽取式摘要
# =============================================================================

class TestExtractiveSummarizerBoundary(unittest.TestCase):
    """抽取式摘要边界条件测试"""

    def setUp(self):
        self.extractor = ExtractiveSummarizer()

    def test_ratio_zero(self):
        text = "句子一。句子二。句子三。句子四。句子五。"
        result = self.extractor.summarize(text, summary_ratio=0.0)
        # ratio=0 时 k = max(1, int(n*0)) = 1
        self.assertGreater(len(result), 0)

    def test_ratio_one(self):
        text = "句子一。句子二。句子三。句子四。句子五。"
        result = self.extractor.summarize(text, summary_ratio=1.0)
        self.assertGreater(len(result), 0)

    def test_ratio_greater_than_one(self):
        text = "句子一。句子二。句子三。句子四。句子五。"
        result = self.extractor.summarize(text, summary_ratio=2.0)
        self.assertGreater(len(result), 0)

    def test_two_sentences(self):
        text = "句子一。句子二。"
        result = self.extractor.summarize(text)
        # <=3 句返回原文
        self.assertEqual(result, text)

    def test_three_sentences(self):
        text = "句子一。句子二。句子三。"
        result = self.extractor.summarize(text)
        # <=3 句返回原文
        self.assertEqual(result, text)

    def test_four_sentences(self):
        text = "句子一。句子二。句子三。句子四。"
        result = self.extractor.summarize(text)
        # >3 句进行摘要
        self.assertGreater(len(result), 0)

    def test_all_same_sentences(self):
        text = "相同内容。相同内容。相同内容。相同内容。相同内容。"
        result = self.extractor.summarize(text, summary_ratio=0.2)
        self.assertGreater(len(result), 0)

    def test_no_punctuation(self):
        text = "没有标点符号的文本内容"
        result = self.extractor.summarize(text)
        self.assertEqual(result, text)

    def test_only_punctuation(self):
        text = "。！?；"
        result = self.extractor.summarize(text)
        self.assertGreater(len(result), 0)

    def test_english_sentences(self):
        text = "This is the first sentence. This is the second sentence. " \
               "This is the third sentence. This is the fourth sentence. " \
               "This is the fifth sentence."
        result = self.extractor.summarize(text, summary_ratio=0.3)
        self.assertGreater(len(result), 0)

    def test_mixed_punctuation(self):
        text = "第一句！第二句？第三句；第四句。第五句。"
        result = self.extractor.summarize(text, summary_ratio=0.3)
        self.assertGreater(len(result), 0)

    def test_single_long_sentence(self):
        text = "这是一个很长的句子，包含了很多内容，" * 50
        result = self.extractor.summarize(text)
        # 只有一句，返回原文
        self.assertEqual(result, text)

    def test_whitespace_text(self):
        text = "   "
        result = self.extractor.summarize(text)
        self.assertEqual(result, "")

    def test_newline_only(self):
        text = "\n\n\n"
        result = self.extractor.summarize(text)
        self.assertEqual(result, "")


# =============================================================================
# 8. 边界条件测试 — 摘要评估器
# =============================================================================

class TestSummaryEvaluatorBoundary(unittest.TestCase):
    """摘要评估器边界条件测试"""

    def setUp(self):
        self.evaluator = SummaryEvaluator()

    def test_empty_original(self):
        results = self.evaluator.evaluate("", "摘要内容")
        self.assertIn("error", results)

    def test_empty_summary(self):
        results = self.evaluator.evaluate("原文内容", "")
        self.assertIn("error", results)

    def test_both_empty(self):
        results = self.evaluator.evaluate("", "")
        self.assertIn("error", results)

    def test_identical_texts(self):
        text = "完全相同的文本内容。"
        results = self.evaluator.evaluate(text, text)
        self.assertEqual(results["rouge_1"]["f1"], 1.0)
        self.assertEqual(results["compression_ratio"], 1.0)

    def test_completely_different_texts(self):
        original = "人工智能是未来。"
        summary = "今天天气很好。"
        results = self.evaluator.evaluate(original, summary)
        self.assertGreaterEqual(results["rouge_1"]["f1"], 0.0)

    def test_rouge_2_non_zero(self):
        original = "人工智能是计算机科学的一个分支。"
        summary = "人工智能是计算机科学。"
        results = self.evaluator.evaluate(original, summary)
        self.assertIn("rouge_2", results)

    def test_rouge_n_zero_for_large_n(self):
        original = "短文本。"
        summary = "摘要。"
        results = self.evaluator.rouge_n(original, summary, n=10)
        self.assertEqual(results["f1"], 0.0)

    def test_rouge_n_empty_inputs(self):
        results = self.evaluator.rouge_n("", "", n=1)
        self.assertEqual(results["f1"], 0.0)

    def test_rouge_l_empty_inputs(self):
        results = self.evaluator.rouge_l("", "")
        self.assertEqual(results["f1"], 0.0)

    def test_lcs_edge_case(self):
        result = SummaryEvaluator._lcs_length([], [])
        self.assertEqual(result, 0)

    def test_lcs_identical(self):
        result = SummaryEvaluator._lcs_length([1, 2, 3], [1, 2, 3])
        self.assertEqual(result, 3)

    def test_lcs_no_match(self):
        result = SummaryEvaluator._lcs_length([1, 2], [3, 4])
        self.assertEqual(result, 0)

    def test_information_coverage_empty_keypoints(self):
        # 没有关键信息点时返回 1.0
        original = "aaaa"
        summary = "aaaa"
        coverage = self.evaluator._information_coverage(original, summary)
        self.assertGreaterEqual(coverage, 0.0)

    def test_factual_consistency_no_numbers(self):
        original = "没有数字的文本。"
        summary = "也没有数字。"
        result = self.evaluator._factual_consistency(original, summary)
        self.assertEqual(result["score"], 1.0)

    def test_factual_consistency_hallucinated(self):
        original = "原文有数字 100。"
        summary = "摘要有数字 200。"
        result = self.evaluator._factual_consistency(original, summary)
        self.assertLess(result["score"], 1.0)

    def test_readability_short_sentences(self):
        summary = "短。句。短。句。"
        result = SummaryEvaluator._readability(summary)
        self.assertGreater(result["score"], 0.0)

    def test_readability_long_sentences(self):
        summary = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常长的句子。" * 5
        result = SummaryEvaluator._readability(summary)
        self.assertGreater(result["score"], 0.0)

    def test_readability_empty(self):
        result = SummaryEvaluator._readability("")
        self.assertEqual(result["score"], 0)

    def test_readability_no_punctuation(self):
        summary = "没有标点符号的文本内容"
        result = SummaryEvaluator._readability(summary)
        self.assertGreater(result["score"], 0.0)

    def test_evaluate_result_keys(self):
        results = self.evaluator.evaluate("原文内容。", "摘要内容。")
        expected_keys = {"rouge_1", "rouge_2", "rouge_l", "compression_ratio",
                         "information_coverage", "factual_consistency", "readability"}
        self.assertEqual(set(results.keys()), expected_keys)


# =============================================================================
# 9. 边界条件测试 — 生成式摘要
# =============================================================================

class TestGenerativeSummarizerBoundary(unittest.TestCase):
    """生成式摘要边界条件测试"""

    def test_empty_text_with_llm(self):
        call_count = 0
        def mock_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "摘要"
        gen = GenerativeSummarizer(mock_llm)
        result = gen.summarize("")
        self.assertEqual(result, "")
        self.assertEqual(call_count, 0)

    def test_whitespace_text_with_llm(self):
        call_count = 0
        def mock_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "摘要"
        gen = GenerativeSummarizer(mock_llm)
        result = gen.summarize("   ")
        self.assertEqual(result, "")
        self.assertEqual(call_count, 0)

    def test_short_text_single_chunk(self):
        call_count = 0
        def mock_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "摘要"
        gen = GenerativeSummarizer(mock_llm, max_chunk_size=2000)
        result = gen.summarize("短文本。")
        self.assertEqual(call_count, 1)

    def test_split_text(self):
        gen = GenerativeSummarizer(max_chunk_size=100)
        text = "A" * 250
        chunks = gen._split_text(text)
        self.assertEqual(len(chunks), 3)  # 100 + 100 + 50

    def test_split_text_exact_multiple(self):
        gen = GenerativeSummarizer(max_chunk_size=100)
        text = "A" * 300
        chunks = gen._split_text(text)
        self.assertEqual(len(chunks), 3)

    def test_merge_summaries(self):
        call_count = 0
        def mock_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "合并摘要"
        gen = GenerativeSummarizer(mock_llm)
        result = gen._merge_summaries(["摘要1", "摘要2", "摘要3"])
        self.assertEqual(result, "合并摘要")
        self.assertEqual(call_count, 1)

    def test_custom_max_chunk_size(self):
        gen = GenerativeSummarizer(max_chunk_size=50)
        self.assertEqual(gen.max_chunk_size, 50)

    def test_custom_max_summary_length(self):
        gen = GenerativeSummarizer(max_summary_length=1000)
        self.assertEqual(gen.max_summary_length, 1000)


# =============================================================================
# 10. 异常处理测试
# =============================================================================

class TestExceptionHandling(unittest.TestCase):
    """异常处理测试"""

    def test_document_chunk_to_dict(self):
        chunk = DocumentChunk(
            chunk_id="c001", title="测试标题", content="测试内容",
            section_path="/section/1", word_count=10, order=0,
        )
        d = chunk.to_dict()
        self.assertEqual(d["chunk_id"], "c001")
        self.assertEqual(d["word_count"], 10)

    def test_document_chunk_defaults(self):
        chunk = DocumentChunk(chunk_id="c002")
        self.assertEqual(chunk.title, "")
        self.assertEqual(chunk.content, "")
        self.assertEqual(chunk.section_path, "")
        self.assertEqual(chunk.word_count, 0)
        self.assertEqual(chunk.order, 0)

    def test_extractor_default_params(self):
        extractor = ExtractiveSummarizer()
        self.assertEqual(extractor.damping, 0.85)
        self.assertEqual(extractor.iterations, 50)

    def test_extractor_custom_params(self):
        extractor = ExtractiveSummarizer(damping=0.9, iterations=100)
        self.assertEqual(extractor.damping, 0.9)
        self.assertEqual(extractor.iterations, 100)

    def test_generator_default_params(self):
        gen = GenerativeSummarizer()
        self.assertEqual(gen.max_chunk_size, 2000)
        self.assertEqual(gen.max_summary_length, 500)

    def test_extract_words(self):
        words = ExtractiveSummarizer._extract_words("Hello 世界123!@#")
        self.assertIn("H", words)
        self.assertIn("世", words)
        self.assertIn("界", words)

    def test_llm_exception_handling(self):
        def failing_llm(prompt):
            raise RuntimeError("LLM 调用失败")
        gen = GenerativeSummarizer(failing_llm)
        with self.assertRaises(RuntimeError):
            gen.summarize("测试文本内容。")


# =============================================================================
# 11. 性能测试
# =============================================================================

class TestPerformance(unittest.TestCase):
    """性能测试"""

    def test_speed(self):
        long_text = "人工智能是计算机科学的分支。" * 50 \
                   + "机器学习、深度学习、自然语言处理。" * 50
        extractor = ExtractiveSummarizer()
        start = time.time()
        extractor.summarize(long_text, summary_ratio=0.2)
        elapsed = time.time() - start
        self.assertLess(elapsed, 10.0, f"摘要生成耗时过长: {elapsed:.2f}s")
        print(f"\n性能测试：长文本摘要耗时 {elapsed:.3f}s")

    def test_parsing_speed(self):
        long_text = "段落内容。" * 1000
        parser = DocumentParser()
        start = time.time()
        chunks = parser.split_into_chunks(long_text, max_chunk_size=500)
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, f"文档解析耗时过长: {elapsed:.2f}s")
        self.assertGreater(len(chunks), 0)
        print(f"\n解析性能测试: {len(chunks)} 个片段，耗时 {elapsed:.3f}s")

    def test_evaluation_speed(self):
        evaluator = SummaryEvaluator()
        original = "人工智能是计算机科学的分支。" * 100
        summary = "人工智能是计算机科学分支。" * 20
        start = time.time()
        results = evaluator.evaluate(original, summary)
        elapsed = time.time() - start
        self.assertLess(elapsed, 10.0, f"评估耗时过长: {elapsed:.2f}s")
        self.assertIn("rouge_1", results)
        print(f"\n评估性能测试: 耗时 {elapsed:.3f}s")

    def test_generator_long_doc_speed(self):
        gen = GenerativeSummarizer(max_chunk_size=500)
        call_count = 0
        def mock_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "摘要结果"
        gen.llm = mock_llm
        long_text = "内容。" * 3000
        start = time.time()
        result = gen.summarize(long_text)
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, f"生成式摘要耗时过长: {elapsed:.2f}s")
        self.assertGreater(call_count, 1)
        print(f"\n生成式摘要性能测试: {call_count} 次LLM调用，耗时 {elapsed:.3f}s")

    def test_textrank_scaling(self):
        """测试 TextRank 随句子数量扩展的性能"""
        extractor = ExtractiveSummarizer(iterations=20)
        # 构建不同长度的文本
        for n_sentences in [10, 20, 50]:
            text = "。".join([f"第{i}个句子的内容" for i in range(n_sentences)]) + "。"
            start = time.time()
            result = extractor.summarize(text, summary_ratio=0.3)
            elapsed = time.time() - start
            self.assertLess(elapsed, 5.0,
                            f"{n_sentences} 句摘要耗时过长: {elapsed:.2f}s")
        print(f"\nTextRank 扩展性能测试通过")


# =============================================================================
# 12. 集成测试
# =============================================================================

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_parser_to_summarizer_pipeline(self):
        """测试解析器 → 摘要器管道"""
        parser = DocumentParser()
        extractor = ExtractiveSummarizer()
        long_text = "段落一：人工智能是计算机科学的一个分支。\n\n" \
                    "段落二：机器学习是人工智能的核心技术。\n\n" \
                    "段落三：深度学习在图像识别领域取得突破。\n\n" \
                    "段落四：Transformer架构改变了自然语言处理。\n\n" \
                    "段落五：BERT和GPT等模型刷新了多项记录。"
        chunks = parser.split_into_chunks(long_text, max_chunk_size=200)
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            summary = extractor.summarize(chunk.content, summary_ratio=0.3)
            self.assertGreater(len(summary), 0)

    def test_summarizer_to_evaluator_pipeline(self):
        """测试摘要器 → 评估器管道"""
        extractor = ExtractiveSummarizer()
        evaluator = SummaryEvaluator()
        text = "人工智能是计算机科学的一个分支。机器学习是核心技术。" \
               "深度学习在图像识别取得突破。Transformer改变了NLP。" \
               "BERT和GPT刷新了多项记录。"
        summary = extractor.summarize(text, summary_ratio=0.3)
        results = evaluator.evaluate(text, summary)
        self.assertGreater(results["rouge_1"]["f1"], 0.0)
        self.assertLess(results["compression_ratio"], 1.0)

    def test_full_pipeline_with_generative(self):
        """测试完整管道（含生成式摘要）"""
        parser = DocumentParser()
        call_count = 0
        def mock_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "AI是计算机科学的分支，用于模拟人类智能。"
        gen = GenerativeSummarizer(mock_llm, max_chunk_size=500)
        evaluator = SummaryEvaluator()

        long_text = "段落一内容。" * 200 + "段落二内容。" * 200
        cleaned = parser.parse_raw_text(long_text)
        summary = gen.summarize(cleaned)
        self.assertGreater(len(summary), 0)
        self.assertGreater(call_count, 0)

    def test_multi_format_document(self):
        """测试多格式文档处理"""
        parser = DocumentParser()
        extractor = ExtractiveSummarizer()

        # 模拟包含页码、多余空白的文档
        raw_text = """第一章 项目概述

    本项目用于开发智能文档处理系统。


    系统采用模块化设计。

1

第二章 技术方案

    文档解析模块支持多种格式。

    文本处理模块负责清洗。

2

第三章 测试方案

    测试覆盖三个维度。"""

        cleaned = parser.parse_raw_text(raw_text)
        self.assertNotIn("\n1\n", cleaned)
        self.assertNotIn("\n2\n", cleaned)

        chunks = parser.split_into_chunks(cleaned)
        self.assertGreater(len(chunks), 0)

        summary = extractor.summarize(cleaned, summary_ratio=0.3)
        self.assertGreater(len(summary), 0)

    def test_quality_gate_pipeline(self):
        """测试质量门禁管道"""
        extractor = ExtractiveSummarizer()
        evaluator = SummaryEvaluator()
        text = "人工智能是计算机科学的一个分支。用于开发智能系统。" \
               "2012年深度学习取得突破。2017年Transformer改变NLP。"
        summary = extractor.summarize(text, summary_ratio=0.2)
        results = evaluator.evaluate(text, summary)
        # 质量门禁检查
        self.assertGreater(results["rouge_1"]["f1"], 0.0,
                           "ROUGE-1 分数过低")
        self.assertLess(results["compression_ratio"], 0.5,
                        "压缩比过高")
        self.assertGreater(results["factual_consistency"]["score"], 0.0,
                           "事实一致性过低")


# =============================================================================
# 13. 配置测试
# =============================================================================

class TestConfiguration(unittest.TestCase):
    """配置测试"""

    def test_parser_default_config(self):
        parser = DocumentParser()
        # 验证默认配置可用
        result = parser.split_into_chunks("测试内容。", max_chunk_size=200)
        self.assertIsInstance(result, list)

    def test_extractor_default_damping(self):
        extractor = ExtractiveSummarizer()
        self.assertEqual(extractor.damping, 0.85)

    def test_extractor_default_iterations(self):
        extractor = ExtractiveSummarizer()
        self.assertEqual(extractor.iterations, 50)

    def test_extractor_custom_damping(self):
        extractor = ExtractiveSummarizer(damping=0.75)
        self.assertEqual(extractor.damping, 0.75)

    def test_extractor_custom_iterations(self):
        extractor = ExtractiveSummarizer(iterations=10)
        self.assertEqual(extractor.iterations, 10)

    def test_generator_default_chunk_size(self):
        gen = GenerativeSummarizer()
        self.assertEqual(gen.max_chunk_size, 2000)

    def test_generator_default_max_summary_length(self):
        gen = GenerativeSummarizer()
        self.assertEqual(gen.max_summary_length, 500)

    def test_generator_custom_chunk_size(self):
        gen = GenerativeSummarizer(max_chunk_size=1000)
        self.assertEqual(gen.max_chunk_size, 1000)

    def test_generator_custom_max_summary_length(self):
        gen = GenerativeSummarizer(max_summary_length=300)
        self.assertEqual(gen.max_summary_length, 300)

    def test_evaluator_rouge_n_variants(self):
        evaluator = SummaryEvaluator()
        original = "人工智能是计算机科学的一个分支。"
        summary = "人工智能是计算机科学。"
        for n in [1, 2, 3]:
            result = evaluator.rouge_n(original, summary, n=n)
            self.assertIn("precision", result)
            self.assertIn("recall", result)
            self.assertIn("f1", result)


# =============================================================================
# 14. 数据验证测试
# =============================================================================

class TestDataValidation(unittest.TestCase):
    """数据验证测试"""

    def test_chunk_to_dict_roundtrip(self):
        chunk = DocumentChunk(
            chunk_id="rt001", title="标题", content="内容",
            section_path="/path", word_count=5, order=0,
        )
        d = chunk.to_dict()
        self.assertEqual(d["chunk_id"], "rt001")
        self.assertEqual(d["title"], "标题")
        self.assertEqual(d["content"], "内容")
        self.assertEqual(d["section_path"], "/path")
        self.assertEqual(d["word_count"], 5)
        self.assertEqual(d["order"], 0)

    def test_chunk_to_dict_defaults(self):
        chunk = DocumentChunk(chunk_id="d001")
        d = chunk.to_dict()
        self.assertEqual(d["title"], "")
        self.assertEqual(d["content"], "")
        self.assertEqual(d["section_path"], "")
        self.assertEqual(d["word_count"], 0)
        self.assertEqual(d["order"], 0)

    def test_evaluation_result_types(self):
        evaluator = SummaryEvaluator()
        results = evaluator.evaluate("原文内容。", "摘要内容。")
        self.assertIsInstance(results["rouge_1"], dict)
        self.assertIsInstance(results["rouge_1"]["precision"], float)
        self.assertIsInstance(results["rouge_1"]["recall"], float)
        self.assertIsInstance(results["rouge_1"]["f1"], float)
        self.assertIsInstance(results["compression_ratio"], float)
        self.assertIsInstance(results["information_coverage"], float)
        self.assertIsInstance(results["factual_consistency"], dict)
        self.assertIsInstance(results["readability"], dict)

    def test_rouge_score_range(self):
        evaluator = SummaryEvaluator()
        original = "人工智能是未来。"
        summary = "AI是未来。"
        result = evaluator.rouge_n(original, summary, n=1)
        for key in ["precision", "recall", "f1"]:
            self.assertGreaterEqual(result[key], 0.0)
            self.assertLessEqual(result[key], 1.0)

    def test_readability_score_range(self):
        summary = "正常长度的句子内容。" * 10
        result = SummaryEvaluator._readability(summary)
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)
        self.assertIsInstance(result["avg_sentence_length"], float)
        self.assertIsInstance(result["sentence_count"], int)

    def test_factual_consistency_result_format(self):
        evaluator = SummaryEvaluator()
        result = evaluator._factual_consistency("原文100。", "摘要200。")
        self.assertIn("score", result)
        self.assertIn("hallucinated_numbers", result)
        self.assertIn("total_numbers_in_summary", result)
        self.assertIsInstance(result["hallucinated_numbers"], list)
        self.assertIsInstance(result["total_numbers_in_summary"], int)

    def test_compression_ratio_calculation(self):
        evaluator = SummaryEvaluator()
        original = "A" * 100
        summary = "B" * 30
        results = evaluator.evaluate(original, summary)
        expected_ratio = round(30 / 100, 4)
        self.assertEqual(results["compression_ratio"], expected_ratio)

    def test_information_coverage_range(self):
        evaluator = SummaryEvaluator()
        original = "2012年深度学习突破。AlexNet错误率从26%降到15%。"
        summary = "深度学习在2012年取得突破。"
        coverage = evaluator._information_coverage(original, summary)
        self.assertGreaterEqual(coverage, 0.0)
        self.assertLessEqual(coverage, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
