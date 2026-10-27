"""
质量校验模块测试
~~~~~~~~~~~~~~~~
覆盖：图片质量检查、OCR 结果校验、转录完整性检查、发票字段检查、综合判定

作者：测试员周周（14 年测试老兵）
"""
import os
import sys
import unittest
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.quality_checker import QualityChecker


class TestQualityChecker(unittest.TestCase):
    """质量校验器测试套件"""

    @classmethod
    def setUpClass(cls):
        """类级别初始化"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.checker = QualityChecker()

        # 创建测试用图片文件
        cls.small_image_path = os.path.join(cls.temp_dir, "small.png")
        with open(cls.small_image_path, "wb") as f:
            f.write(b"0" * 500)  # 500 bytes - 非常小

        cls.normal_image_path = os.path.join(cls.temp_dir, "normal.jpg")
        with open(cls.normal_image_path, "wb") as f:
            f.write(b"0" * 100 * 1024)  # 100KB - 正常大小

    @classmethod
    def tearDownClass(cls):
        """类级别清理"""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # ---- 图片质量检查测试 ----

    def test_check_image_quality_normal(self):
        """测试正常图片的质量检查"""
        result = self.checker.check_image_quality(self.normal_image_path)
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["quality_score"], 0.0)

    def test_check_image_quality_small(self):
        """测试小图片的质量检查"""
        result = self.checker.check_image_quality(self.small_image_path)
        # 500 bytes 的文件应该触发质量问题
        self.assertGreater(len(result["issues"]), 0)

    def test_check_image_quality_not_exists(self):
        """测试不存在的文件的质量检查"""
        result = self.checker.check_image_quality("/nonexistent/file.jpg")
        self.assertFalse(result["passed"])
        self.assertIn("无法读取", result["issues"][0])

    # ---- OCR 结果校验测试 ----

    def test_check_ocr_result_valid(self):
        """测试有效的 OCR 结果"""
        result = self.checker.check_ocr_result(
            "发票号码：12345678，金额：15800元，开票日期：2024-10-15"
        )
        self.assertTrue(result["passed"])
        self.assertGreater(result["text_length"], 0)
        self.assertTrue(result["has_numbers"])

    def test_check_ocr_result_empty(self):
        """测试空 OCR 结果"""
        result = self.checker.check_ocr_result("")
        self.assertFalse(result["passed"])
        self.assertIn("空", result["issues"][0])

    def test_check_ocr_result_with_expected_fields(self):
        """测试带期望字段的 OCR 校验"""
        result = self.checker.check_ocr_result(
            "发票号码：12345678，金额：15800元，开票日期：2024-10-15",
            expected_fields=["发票", "号码", "金额", "日期"]
        )
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["found_fields"]), 4)
        self.assertEqual(result["coverage_rate"], 1.0)

    def test_check_ocr_result_missing_fields(self):
        """测试缺少关键字段的 OCR 校验"""
        result = self.checker.check_ocr_result(
            "这是一段普通的文字描述",
            expected_fields=["发票", "金额"]
        )
        self.assertFalse(result["passed"])
        self.assertIn("缺少关键字段", " ".join(result["issues"]))

    def test_check_ocr_result_no_numbers(self):
        """测试 OCR 结果中没有数字"""
        result = self.checker.check_ocr_result("这是一段纯中文文字描述")
        self.assertFalse(result["passed"])
        self.assertIn("未检测到数字", " ".join(result["issues"]))

    # ---- 发票字段检查测试 ----

    def test_check_invoice_fields_valid(self):
        """测试有效发票文本的字段检查"""
        result = self.checker.check_invoice_fields(
            "发票号码：12345678，金额：15800元，开票日期：2024-10-15"
        )
        self.assertIsNotNone(result["extracted_amount"])
        self.assertIsNotNone(result["invoice_no"])
        self.assertEqual(result["invoice_no"], "12345678")

    def test_check_invoice_fields_no_match(self):
        """测试非发票文本的字段检查"""
        result = self.checker.check_invoice_fields("这是一段普通文字")
        self.assertIsNone(result["extracted_amount"])
        self.assertIsNone(result["invoice_no"])

    def test_check_invoice_fields_missing_all(self):
        """测试完全不相干的文本"""
        result = self.checker.check_invoice_fields("hello world 123")
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["missing_fields"]), 0)

    # ---- 转录完整性检查测试 ----

    def test_check_transcription_completeness_normal(self):
        """测试正常转录结果"""
        transcription = {
            "success": True,
            "text": "今天天气不错，适合外出活动。",
            "duration_sec": 30,
        }
        result = self.checker.check_transcription_completeness(
            transcription, original_duration_sec=35
        )
        self.assertTrue(result["passed"])

    def test_check_transcription_completeness_empty(self):
        """测试空转录结果"""
        transcription = {
            "success": True,
            "text": "",
            "duration_sec": 0,
        }
        result = self.checker.check_transcription_completeness(
            transcription, original_duration_sec=60
        )
        self.assertFalse(result["passed"])
        self.assertTrue(len(result["issues"]) > 0)

    def test_check_transcription_completeness_incomplete(self):
        """测试时长不匹配的转录"""
        transcription = {
            "success": True,
            "text": "短文本",
            "duration_sec": 10,
        }
        result = self.checker.check_transcription_completeness(
            transcription, original_duration_sec=60
        )
        self.assertFalse(result["passed"])
        # 时长差距超过 30%，应该警告
        duration_issue = any("转录时长" in issue for issue in result["issues"])
        self.assertTrue(duration_issue)

    def test_check_transcription_completeness_with_warning(self):
        """测试带警告的转录"""
        transcription = {
            "success": True,
            "text": "测试文本",
            "duration_sec": 30,
            "warning": "检测到较强背景噪音",
        }
        result = self.checker.check_transcription_completeness(
            transcription, original_duration_sec=35
        )
        self.assertFalse(result["passed"])
        self.assertIn("背景噪音", " ".join(result["issues"]))

    # ---- 综合判定测试 ----

    def test_get_overall_verdict_all_pass(self):
        """测试全部通过的综合判定"""
        results = [
            {"passed": True, "issues": []},
            {"passed": True, "issues": []},
        ]
        verdict = self.checker.get_overall_verdict(results)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["passed_checks"], 2)
        self.assertEqual(verdict["failed_checks"], 0)

    def test_get_overall_verdict_some_fail(self):
        """测试部分失败的综合判定"""
        results = [
            {"passed": True, "issues": []},
            {"passed": False, "issues": ["问题1"]},
        ]
        verdict = self.checker.get_overall_verdict(results)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["passed_checks"], 1)
        self.assertEqual(verdict["failed_checks"], 1)
        self.assertIn("问题1", verdict["all_issues"])


if __name__ == "__main__":
    unittest.main()
