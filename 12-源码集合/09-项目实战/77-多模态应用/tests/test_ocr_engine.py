"""
OCR 引擎测试
~~~~~~~~~~~~
覆盖：置信度估算、图表数据提取、响应解析、置信度阈值判断

作者：测试员周周（14 年测试老兵）
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ocr_engine import OCREngine


class TestOCREngine(unittest.TestCase):
    """OCR 引擎测试套件"""

    @classmethod
    def setUpClass(cls):
        """类级别初始化"""
        cls.engine = OCREngine()

    # ---- 置信度估算测试 ----

    def test_confidence_empty_text(self):
        """测试空文本的置信度"""
        conf = self.engine.estimate_confidence("")
        self.assertEqual(conf, 0.0)

    def test_confidence_no_text_marker(self):
        """测试"未检测到文字"标记的置信度"""
        conf = self.engine.estimate_confidence("未检测到文字")
        self.assertEqual(conf, 0.0)

    def test_confidence_normal_chinese(self):
        """测试正常中文文本的置信度"""
        conf = self.engine.estimate_confidence("发票号码：12345678，金额：15800元")
        self.assertGreater(conf, 0.7)

    def test_confidence_mixed_language(self):
        """测试中英文混合文本的置信度"""
        # "Hello 世界，测试 123" -> 中文4/总15=0.267 < 0.3, 所以置信度 0.6
        conf = self.engine.estimate_confidence("Hello 世界，测试 123")
        self.assertEqual(conf, 0.6)

    def test_confidence_pure_english(self):
        """测试纯英文文本的置信度"""
        conf = self.engine.estimate_confidence("Hello World, this is a test.")
        self.assertGreater(conf, 0.7)

    def test_confidence_pure_digits(self):
        """测试纯数字文本的置信度"""
        conf = self.engine.estimate_confidence("1234567890")
        self.assertGreater(conf, 0.7)

    def test_confidence_all_chinese_no_punctuation(self):
        """测试几乎全是中文字符（缺少标点）的置信度"""
        conf = self.engine.estimate_confidence(
            "这是一张发票照片发票号码为一二三四五六七八金额为一五八零零元开票日期为二零二四年十月十五日"
        )
        # 中文字符比例 > 90%，应返回中等置信度
        self.assertLess(conf, 0.8)

    def test_confidence_low_chinese_ratio(self):
        """测试中文比例偏低的情况"""
        conf = self.engine.estimate_confidence("abc123!@#$%^中文")
        self.assertLess(conf, 0.7)

    def test_confidence_whitespace_only(self):
        """测试纯空白字符"""
        conf = self.engine.estimate_confidence("   \n  \t  ")
        self.assertEqual(conf, 0.0)

    # ---- 图表数据提取测试 ----

    def test_extract_chart_data_normal(self):
        """测试正常图表数据提取"""
        response = "柱状图显示：一季度销售额 120万，二季度 150万，三季度 180万，四季度 200万。"
        data = self.engine.extract_chart_data(response)
        self.assertIsNotNone(data)
        self.assertEqual(data["data_points"], 4)
        # 验证提取到了数值
        numbers = data["extracted_numbers"]
        self.assertTrue(any(n == 120 for n in numbers))
        self.assertTrue(any(n == 150 for n in numbers))

    def test_extract_chart_data_empty(self):
        """测试空响应"""
        data = self.engine.extract_chart_data("")
        self.assertIsNone(data)

    def test_extract_chart_data_no_numbers(self):
        """测试没有数字的响应"""
        data = self.engine.extract_chart_data("该图表没有显示任何数据。")
        self.assertIsNone(data)

    def test_extract_chart_data_with_decimals(self):
        """测试带小数的数据提取"""
        response = "数据点：A=12.5, B=23.7, C=45.9"
        data = self.engine.extract_chart_data(response)
        self.assertIsNotNone(data)
        self.assertEqual(len(data["extracted_numbers"]), 3)
        self.assertIn(12.5, data["extracted_numbers"])
        self.assertIn(23.7, data["extracted_numbers"])
        self.assertIn(45.9, data["extracted_numbers"])

    def test_extract_chart_data_with_chinese_numbers(self):
        """测试含中文数字的数据"""
        response = "一月份销售额120万，二月份150万"
        data = self.engine.extract_chart_data(response)
        self.assertIsNotNone(data)
        self.assertTrue(data["has_chinese_numbers"])
        self.assertGreater(data["data_points"], 0)

    # ---- 响应解析测试 ----

    def test_parse_response_general(self):
        """测试通用描述解析"""
        result = self.engine.parse_response(
            "这是一张办公室的照片，桌上有一台笔记本电脑和一杯咖啡。",
            "general"
        )
        self.assertIn("办公室", result["description"])
        self.assertIsNone(result["confidence"])
        self.assertIsNone(result["chart_data"])

    def test_parse_response_ocr(self):
        """测试 OCR 任务解析"""
        result = self.engine.parse_response(
            "发票号码：12345678，金额：15800元，日期：2024-10-15",
            "ocr"
        )
        self.assertIn("发票号码", result["text"])
        self.assertIsNotNone(result["confidence"])
        # 文本中中文比例 9/37=0.24 < 0.3，置信度为 0.6
        self.assertEqual(result["confidence"], 0.6)

    def test_parse_response_chart(self):
        """测试图表任务解析"""
        result = self.engine.parse_response(
            "一季度 120万，二季度 150万，三季度 180万",
            "chart"
        )
        self.assertIsNotNone(result["chart_data"])
        self.assertEqual(result["chart_data"]["data_points"], 3)

    # ---- 置信度阈值测试 ----

    def test_meets_confidence_threshold_pass(self):
        """测试达到置信度阈值"""
        self.assertTrue(
            self.engine.meets_confidence_threshold("正常的发票文字内容")
        )

    def test_meets_confidence_threshold_fail(self):
        """测试未达到置信度阈值"""
        self.assertFalse(
            self.engine.meets_confidence_threshold("")
        )
        self.assertFalse(
            self.engine.meets_confidence_threshold("未检测到文字")
        )


if __name__ == "__main__":
    unittest.main()
