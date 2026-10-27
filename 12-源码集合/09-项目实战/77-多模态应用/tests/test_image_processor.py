"""
图片处理模块测试
~~~~~~~~~~~~~~~
覆盖：图片校验、音频校验、base64 编码、媒体类型识别、质量估算

作者：测试员周周（14 年测试老兵）
"""
import os
import sys
import unittest
import tempfile

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.image_processor import ImageProcessor, MediaType


class TestImageProcessor(unittest.TestCase):
    """图片处理器测试套件"""

    @classmethod
    def setUpClass(cls):
        """类级别初始化：创建测试用临时文件"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.processor = ImageProcessor()

        # 创建一个有效的测试图片文件（1x1 像素的 PNG）
        cls.valid_image_path = os.path.join(cls.temp_dir, "test_image.png")
        # 最小的有效 PNG 文件
        with open(cls.valid_image_path, "wb") as f:
            f.write(
                b'\x89PNG\r\n\x1a\n'  # PNG 文件头
                b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx'
                b'\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00'
                b'\x00\x00\x00IEND\xaeB`\x82'
            )

        # 创建一个有效的测试音频文件
        cls.valid_audio_path = os.path.join(cls.temp_dir, "test_audio.mp3")
        with open(cls.valid_audio_path, "wb") as f:
            f.write(b'\xff\xfb\x90\x00' * 100)  # MP3 帧模拟

        # 创建一个空文件
        cls.empty_file_path = os.path.join(cls.temp_dir, "empty.png")
        with open(cls.empty_file_path, "wb") as f:
            f.write(b"")

        # 一个大文件（超过限制）
        cls.large_file_path = os.path.join(cls.temp_dir, "large.jpg")
        with open(cls.large_file_path, "wb") as f:
            f.write(b"0" * (21 * 1024 * 1024))  # 21MB

    @classmethod
    def tearDownClass(cls):
        """类级别清理：删除临时文件"""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # ---- 图片校验测试 ----

    def test_validate_image_valid(self):
        """测试有效图片的校验"""
        valid, msg = self.processor.validate_image(self.valid_image_path)
        self.assertTrue(valid, f"有效图片应通过校验，但返回: {msg}")

    def test_validate_image_not_exists(self):
        """测试不存在的图片文件"""
        valid, msg = self.processor.validate_image("/nonexistent/file.jpg")
        self.assertFalse(valid)
        self.assertIn("不存在", msg)

    def test_validate_image_empty(self):
        """测试空文件"""
        valid, msg = self.processor.validate_image(self.empty_file_path)
        self.assertFalse(valid)
        self.assertIn("空", msg)

    def test_validate_image_large(self):
        """测试超大文件"""
        valid, msg = self.processor.validate_image(self.large_file_path)
        self.assertFalse(valid)
        self.assertIn("过大", msg)

    def test_validate_image_unsupported_format(self):
        """测试不支持的格式"""
        unsupported_path = os.path.join(self.temp_dir, "test.pdf")
        with open(unsupported_path, "wb") as f:
            f.write(b"%PDF-1.4")
        valid, msg = self.processor.validate_image(unsupported_path)
        self.assertFalse(valid)
        self.assertIn("不支持", msg)

    def test_validate_image_none_path(self):
        """测试传入 None 路径"""
        valid, msg = self.processor.validate_image(None)
        self.assertFalse(valid)
        self.assertIn("不存在", msg)

    # ---- 音频校验测试 ----

    def test_validate_audio_valid(self):
        """测试有效音频的校验"""
        valid, msg = self.processor.validate_audio(self.valid_audio_path)
        self.assertTrue(valid, f"有效音频应通过校验，但返回: {msg}")

    def test_validate_audio_not_exists(self):
        """测试不存在的音频文件"""
        valid, msg = self.processor.validate_audio("/nonexistent/audio.mp3")
        self.assertFalse(valid)
        self.assertIn("不存在", msg)

    def test_validate_audio_empty(self):
        """测试空音频文件"""
        empty_audio = os.path.join(self.temp_dir, "empty.mp3")
        with open(empty_audio, "wb") as f:
            f.write(b"")
        valid, msg = self.processor.validate_audio(empty_audio)
        self.assertFalse(valid)
        self.assertIn("空", msg)

    def test_validate_audio_unsupported_format(self):
        """测试不支持的音频格式"""
        unsupported_path = os.path.join(self.temp_dir, "test_audio_unsupported.wma")
        with open(unsupported_path, "wb") as f:
            f.write(b"test data")
        valid, msg = self.processor.validate_audio(unsupported_path)
        self.assertFalse(valid)
        self.assertIn("不支持", msg)

    # ---- Base64 编码测试 ----

    def test_encode_image_to_base64(self):
        """测试 base64 编码"""
        encoded = self.processor.encode_image_to_base64(self.valid_image_path)
        self.assertIsInstance(encoded, str)
        self.assertGreater(len(encoded), 0)
        # 验证是有效的 base64 编码
        import base64
        decoded = base64.b64decode(encoded)
        self.assertGreater(len(decoded), 0)

    def test_encode_image_not_exists(self):
        """测试对不存在的文件进行 base64 编码"""
        with self.assertRaises(Exception):
            self.processor.encode_image_to_base64("/nonexistent/file.jpg")

    # ---- 媒体类型识别测试 ----

    def test_get_media_type_image(self):
        """测试图片类型识别"""
        self.assertEqual(
            self.processor.get_media_type("photo.jpg"),
            MediaType.IMAGE
        )
        self.assertEqual(
            self.processor.get_media_type("photo.png"),
            MediaType.IMAGE
        )
        self.assertEqual(
            self.processor.get_media_type("photo.jpeg"),
            MediaType.IMAGE
        )

    def test_get_media_type_audio(self):
        """测试音频类型识别"""
        self.assertEqual(
            self.processor.get_media_type("audio.mp3"),
            MediaType.AUDIO
        )
        self.assertEqual(
            self.processor.get_media_type("audio.wav"),
            MediaType.AUDIO
        )

    def test_get_media_type_document(self):
        """测试文档类型识别"""
        self.assertEqual(
            self.processor.get_media_type("document.pdf"),
            MediaType.DOCUMENT
        )
        self.assertEqual(
            self.processor.get_media_type("data.csv"),
            MediaType.DOCUMENT
        )

    # ---- 图片质量估算测试 ----

    def test_estimate_quality_small_file(self):
        """测试小文件的质量评分"""
        score = self.processor.estimate_image_quality(self.valid_image_path)
        # 我们的测试 PNG 文件很小，但有效
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_estimate_quality_not_exists(self):
        """测试不存在的文件的质量评分"""
        score = self.processor.estimate_image_quality("/nonexistent/file.jpg")
        self.assertEqual(score, 0.0)

    # ---- MediaFile 对象创建测试 ----

    def test_create_media_file_image(self):
        """测试创建图片 MediaFile"""
        mf = self.processor.create_media_file(self.valid_image_path)
        self.assertIsNotNone(mf)
        self.assertEqual(mf.media_type, MediaType.IMAGE)
        self.assertGreater(mf.file_size, 0)
        self.assertGreaterEqual(mf.quality_score, 0.0)

    def test_create_media_file_not_exists(self):
        """测试创建不存在的文件的 MediaFile"""
        mf = self.processor.create_media_file("/nonexistent/file.jpg")
        self.assertIsNone(mf)


if __name__ == "__main__":
    unittest.main()
