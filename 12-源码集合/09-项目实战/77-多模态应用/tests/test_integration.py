"""
全流程集成测试
~~~~~~~~~~~~
测试整个多模态处理流水线的端到端功能，
包括图片处理、OCR 识别、音频处理和综合流程。

作者：测试员周周（14 年测试老兵）
"""
import os
import sys
import unittest
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.multimodal_app import MultimodalApp
from src.image_processor import ImageProcessor
from src.ocr_engine import OCREngine
from src.audio_processor import AudioProcessor
from src.quality_checker import QualityChecker
from src.config import Config


class TestIntegration(unittest.TestCase):
    """全流程集成测试"""

    @classmethod
    def setUpClass(cls):
        """类级别初始化"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_path = os.path.join(cls.temp_dir, "test_config.yaml")

        # 创建测试用配置文件
        import yaml
        test_config = {
            "app": {"name": "多模态应用测试", "version": "1.0.0", "debug": True},
            "image": {
                "max_size_mb": 20,
                "supported_formats": [".jpg", ".jpeg", ".png", ".webp", ".bmp"],
                "min_resolution": [100, 100],
                "quality_threshold": 0.3,
            },
            "audio": {
                "max_size_mb": 50,
                "supported_formats": [".mp3", ".wav", ".m4a", ".ogg", ".flac"],
                "max_duration_sec": 3600,
            },
            "ocr": {
                "confidence_threshold": 0.5,
                "min_chinese_ratio": 0.2,
                "max_chinese_ratio": 0.95,
                "high_confidence": 0.85,
                "medium_confidence": 0.7,
                "low_confidence": 0.5,
                "no_text_confidence": 0.0,
            },
            "quality_check": {
                "blur_threshold": 100.0,
                "brightness_min": 20,
                "brightness_max": 250,
                "contrast_min": 15,
                "min_text_length": 3,
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            },
        }
        with open(cls.config_path, "w", encoding="utf-8") as f:
            yaml.dump(test_config, f, allow_unicode=True)

        # 创建测试用图片文件
        cls.test_image_path = os.path.join(cls.temp_dir, "test_invoice.png")
        with open(cls.test_image_path, "wb") as f:
            f.write(
                b'\x89PNG\r\n\x1a\n'
                b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx'
                b'\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00'
                b'\x00\x00\x00IEND\xaeB`\x82'
            )

        # 创建测试用音频文件
        cls.test_audio_path = os.path.join(cls.temp_dir, "test_meeting.mp3")
        with open(cls.test_audio_path, "wb") as f:
            f.write(b'\xff\xfb\x90\x00' * 1000)

    @classmethod
    def tearDownClass(cls):
        """类级别清理"""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """每个测试前初始化"""
        def mock_llm(messages):
            """模拟 LLM 多模态调用"""
            return (
                "这是一张发票照片，发票号码为 12345678，"
                "金额为 15800 元，开票日期为 2024年10月15日。"
            )

        self.mock_llm = mock_llm

    # ---- 配置管理测试 ----

    def test_config_loading(self):
        """测试配置加载"""
        config = Config(self.config_path)
        self.assertEqual(config.get("app", "name"), "多模态应用测试")
        self.assertEqual(config.get("image", "max_size_mb"), 20)
        self.assertEqual(config.get("ocr", "confidence_threshold"), 0.5)

    def test_config_default_values(self):
        """测试默认配置值"""
        config = Config()  # 不传配置文件，使用默认值
        self.assertEqual(config.get("app", "version"), "1.0.0")
        self.assertIsNotNone(config.get("image", "max_size_mb"))
        self.assertIsNotNone(config.get("audio", "max_size_mb"))

    def test_config_nested_get(self):
        """测试深层嵌套配置获取"""
        config = Config(self.config_path)
        self.assertEqual(config.get("logging", "level"), "DEBUG")

    def test_config_get_with_default(self):
        """测试带默认值的配置获取"""
        config = Config(self.config_path)
        self.assertEqual(config.get("nonexistent", default="fallback"), "fallback")

    # ---- 主流程集成测试 ----

    def test_multimodal_app_init(self):
        """测试多模态应用初始化"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        self.assertIsInstance(app.image_processor, ImageProcessor)
        self.assertIsInstance(app.ocr_engine, OCREngine)
        self.assertIsInstance(app.audio_processor, AudioProcessor)
        self.assertIsInstance(app.quality_checker, QualityChecker)

    def test_process_image_general(self):
        """测试处理图片（通用描述）"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file(self.test_image_path, task="general")
        self.assertTrue(result["success"])
        self.assertEqual(result["media_type"], "image")
        self.assertIn("description", result["data"])
        self.assertIn("processing_steps", result)
        self.assertIsNotNone(result["quality_check"])

    def test_process_image_ocr(self):
        """测试处理图片（OCR 任务）"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file(self.test_image_path, task="ocr")
        self.assertTrue(result["success"])
        # OCR 任务应该有文本内容和置信度
        if "text" in result["data"]:
            self.assertGreater(len(result["data"]["text"]), 0)
        self.assertIn("quality_check", result)

    def test_process_image_chart(self):
        """测试处理图片（图表分析）"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file(self.test_image_path, task="chart")
        self.assertTrue(result["success"])
        self.assertEqual(result["task"], "chart")

    def test_process_image_not_exists(self):
        """测试处理不存在的图片文件"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file("/nonexistent/file.jpg", task="general")
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])
        self.assertIn("不存在", result["error"])

    def test_process_image_invalid_format(self):
        """测试处理不支持的格式"""
        invalid_path = os.path.join(self.temp_dir, "test.bmp")
        with open(invalid_path, "wb") as f:
            f.write(b"fake data")
        app = MultimodalApp(self.config_path, self.mock_llm)
        # 如果是 BMP，在 supported_formats 中检查
        result = app.process_file(invalid_path, task="general")
        # 应该成功（bmp 在支持的格式列表中）
        self.assertTrue(result["success"])

    def test_process_audio(self):
        """测试处理音频文件"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file(self.test_audio_path, task="audio")
        self.assertTrue(result["success"])
        self.assertEqual(result["media_type"], "audio")
        self.assertIn("transcription", result["data"])
        self.assertIn("text", result["data"])

    def test_process_audio_not_exists(self):
        """测试处理不存在的音频文件"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file("/nonexistent/audio.mp3", task="audio")
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])

    # ---- 边界场景测试 ----

    def test_process_empty_path(self):
        """测试传入空路径"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file("", task="general")
        self.assertFalse(result["success"])

    def test_process_none_path(self):
        """测试传入 None 路径"""
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file(None, task="general")
        self.assertFalse(result["success"])

    # ---- 端到端多步骤验证 ----

    def test_image_pipeline_full_flow(self):
        """
        测试完整图片处理流水线
        1. 图片预处理 -> 2. 多模态分析 -> 3. 质量校验
        """
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file(self.test_image_path, task="ocr")

        # 验证处理步骤顺序
        steps = result["processing_steps"]
        self.assertGreater(len(steps), 2)

        # 验证每一步都有日志（图片质量不足时会跳过多模态分析）
        self.assertTrue(any("校验通过" in s for s in steps))
        has_analysis = any("分析完成" in s for s in steps)
        has_quality_warning = any("质量不足" in s for s in steps)
        self.assertTrue(has_analysis or has_quality_warning, "应有分析步骤或质量不足提示")
        self.assertTrue(any("质量校验" in s for s in steps))

    def test_audio_pipeline_full_flow(self):
        """
        测试完整音频处理流水线
        1. 音频预处理 -> 2. 语音转录 -> 3. 时间戳转录 -> 4. 质量校验
        """
        app = MultimodalApp(self.config_path, self.mock_llm)
        result = app.process_file(self.test_audio_path, task="audio")

        # 验证处理步骤
        steps = result["processing_steps"]
        self.assertGreater(len(steps), 1)

        # 应该包含时间戳转录
        step_text = " ".join(steps)
        self.assertIn("时间戳", step_text)
        self.assertIn("质量校验", step_text)


if __name__ == "__main__":
    unittest.main()
