"""
音频处理模块测试
~~~~~~~~~~~~~~~~
覆盖：音频校验、音频转录、带时间戳的转录、质量估算

作者：测试员周周（14 年测试老兵）
"""
import os
import sys
import unittest
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.audio_processor import AudioProcessor


class TestAudioProcessor(unittest.TestCase):
    """音频处理器测试套件"""

    @classmethod
    def setUpClass(cls):
        """类级别初始化：创建测试用临时文件"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.processor = AudioProcessor()

        # 创建测试音频文件
        cls.valid_audio_path = os.path.join(cls.temp_dir, "test_recording.mp3")
        with open(cls.valid_audio_path, "wb") as f:
            f.write(b'\xff\xfb\x90\x00' * 1000)  # MP3 帧模拟

        # 静音音频文件
        cls.silence_audio_path = os.path.join(cls.temp_dir, "silence_recording.mp3")
        with open(cls.silence_audio_path, "wb") as f:
            f.write(b'\xff\xfb\x90\x00' * 500)

        # 噪音音频文件
        cls.noise_audio_path = os.path.join(cls.temp_dir, "noise_recording.mp3")
        with open(cls.noise_audio_path, "wb") as f:
            f.write(b'\xff\xfb\x90\x00' * 500)

        # 空文件
        cls.empty_audio_path = os.path.join(cls.temp_dir, "empty.mp3")
        with open(cls.empty_audio_path, "wb") as f:
            f.write(b"")

    @classmethod
    def tearDownClass(cls):
        """类级别清理"""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # ---- 音频校验测试 ----

    def test_validate_audio_valid(self):
        """测试有效音频的校验"""
        valid, msg = self.processor.validate_audio(self.valid_audio_path)
        self.assertTrue(valid, f"有效音频应通过校验: {msg}")

    def test_validate_audio_not_exists(self):
        """测试不存在的文件"""
        valid, msg = self.processor.validate_audio("/nonexistent/audio.mp3")
        self.assertFalse(valid)
        self.assertIn("不存在", msg)

    def test_validate_audio_empty(self):
        """测试空文件"""
        valid, msg = self.processor.validate_audio(self.empty_audio_path)
        self.assertFalse(valid)
        self.assertIn("空", msg)

    def test_validate_audio_unsupported_format(self):
        """测试不支持的格式"""
        unsupported_path = os.path.join(self.temp_dir, "audio.wma")
        with open(unsupported_path, "wb") as f:
            f.write(b"test data")
        valid, msg = self.processor.validate_audio(unsupported_path)
        self.assertFalse(valid)
        self.assertIn("不支持", msg)

    def test_validate_audio_none_path(self):
        """测试 None 路径"""
        valid, msg = self.processor.validate_audio(None)
        self.assertFalse(valid)
        self.assertIn("不存在", msg)

    # ---- 音频转录测试 ----

    def test_transcribe_success(self):
        """测试音频转录成功"""
        result = self.processor.transcribe(self.valid_audio_path)
        self.assertTrue(result["success"])
        self.assertIn("text", result)
        self.assertGreater(len(result["text"]), 0)
        self.assertEqual(result["language"], "zh")

    def test_transcribe_with_language(self):
        """测试指定语言的转录"""
        result = self.processor.transcribe(self.valid_audio_path, language="en")
        self.assertTrue(result["success"])
        self.assertEqual(result["language"], "en")

    def test_transcribe_silence_audio(self):
        """测试静音音频的转录（应返回空文本和警告）"""
        result = self.processor.transcribe(self.silence_audio_path)
        self.assertTrue(result["success"])
        self.assertIn("warning", result)

    def test_transcribe_noise_audio(self):
        """测试噪音音频的转录（应返回转录结果和警告）"""
        result = self.processor.transcribe(self.noise_audio_path)
        self.assertTrue(result["success"])
        self.assertIn("warning", result)

    def test_transcribe_not_exists(self):
        """测试不存在的文件的转录"""
        result = self.processor.transcribe("/nonexistent/audio.mp3")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    # ---- 带时间戳转录测试 ----

    def test_transcribe_with_timestamps(self):
        """测试带时间戳的转录"""
        segments = self.processor.transcribe_with_timestamps(self.valid_audio_path)
        self.assertEqual(len(segments), 3)
        # 验证时间戳顺序（相邻段的时间可能相等，即连续转录）
        self.assertGreaterEqual(segments[1]["start"], segments[0]["end"])
        self.assertGreaterEqual(segments[2]["start"], segments[1]["end"])
        # 验证文本内容
        self.assertEqual(segments[0]["text"], "大家好")
        self.assertEqual(segments[1]["text"], "欢迎来到今天的会议")

    def test_transcribe_with_timestamps_structure(self):
        """测试时间戳结构完整性"""
        segments = self.processor.transcribe_with_timestamps(self.valid_audio_path)
        for seg in segments:
            self.assertIn("start", seg)
            self.assertIn("end", seg)
            self.assertIn("text", seg)
            self.assertIsInstance(seg["start"], float)
            self.assertIsInstance(seg["end"], float)
            self.assertIsInstance(seg["text"], str)

    # ---- 音频质量估算测试 ----

    def test_estimate_quality_valid(self):
        """测试有效音频的质量估算"""
        score = self.processor.estimate_audio_quality(self.valid_audio_path)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_estimate_quality_not_exists(self):
        """测试不存在的文件的质量估算"""
        score = self.processor.estimate_audio_quality("/nonexistent/audio.mp3")
        self.assertEqual(score, 0.0)

    def test_estimate_quality_empty(self):
        """测试空文件的质量估算"""
        score = self.processor.estimate_audio_quality(self.empty_audio_path)
        self.assertLess(score, 0.5)  # 空文件质量应该很低


if __name__ == "__main__":
    unittest.main()
