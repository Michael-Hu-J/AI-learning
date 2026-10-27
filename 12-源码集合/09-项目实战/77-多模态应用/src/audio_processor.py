"""
音频处理模块
~~~~~~~~~~~
负责音频格式校验、语音转文本、带时间戳的转录等音频处理逻辑。

作者：测试员周周（14 年测试老兵）
"""
import os
import json
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    音频处理器
    负责音频文件的校验、语音识别（模拟）、带时间戳的转录等。
    实际项目中会调用 Whisper 或厂商语音识别 API。

    注意：语音识别的默认参数往往不是最优的。
    会议录音和电话录音的静音阈值应该不同，需要根据场景灵活调整。
    """

    # 默认支持的音频格式
    SUPPORTED_FORMATS = [".mp3", ".wav", ".m4a", ".ogg", ".flac"]
    MAX_SIZE_MB = 50

    def __init__(self, config=None):
        """
        初始化音频处理器
        :param config: 配置对象
        """
        self.config = config
        self._init_limits()

    def _init_limits(self):
        """从配置初始化限制参数"""
        if self.config:
            self.max_size_mb = self.config.get("audio", "max_size_mb", default=50)
            self.supported_formats = self.config.get(
                "audio", "supported_formats",
                default=[".mp3", ".wav", ".m4a", ".ogg", ".flac"]
            )
        else:
            self.max_size_mb = 50
            self.supported_formats = [".mp3", ".wav", ".m4a", ".ogg", ".flac"]

    def validate_audio(self, audio_path: str) -> Tuple[bool, str]:
        """
        校验音频文件是否合法
        :param audio_path: 音频文件路径
        :return: (是否合法, 提示信息)
        """
        logger.debug("校验音频文件: %s", audio_path)

        # 1. 检查文件是否存在
        if not audio_path or not os.path.exists(audio_path):
            return False, "文件不存在"

        # 2. 检查文件大小
        try:
            file_size = os.path.getsize(audio_path)
        except OSError as e:
            return False, f"无法读取文件: {e}"

        # 3. 检查文件是否为空
        if file_size == 0:
            return False, "文件为空"

        # 4. 检查文件大小限制
        max_size_bytes = self.max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"文件过大（{file_size / 1024 / 1024:.1f}MB），限制 {self.max_size_mb}MB"

        # 5. 检查文件格式
        ext = os.path.splitext(audio_path)[1].lower()
        if ext not in self.supported_formats:
            return False, f"不支持的音频格式: {ext}，支持: {', '.join(self.supported_formats)}"

        logger.info("音频校验通过: %s (大小: %d, 格式: %s)", audio_path, file_size, ext)
        return True, "校验通过"

    def transcribe(self, audio_path: str, language: str = "zh") -> Dict:
        """
        将音频文件转为文本（模拟实现）
        实际项目中应调用 Whisper 或厂商语音识别 API。

        :param audio_path: 音频文件路径
        :param language: 语言代码，默认 "zh"
        :return: 转录结果字典
        """
        logger.info("开始音频转录: %s (语言: %s)", audio_path, language)

        # 先校验
        valid, msg = self.validate_audio(audio_path)
        if not valid:
            logger.error("音频校验失败: %s", msg)
            return {"success": False, "error": msg}

        # 模拟语音识别调用
        result = self._call_speech_api(audio_path, language)
        logger.info(
            "音频转录完成: success=%s, 文本长度=%d",
            result.get("success"), len(result.get("text", ""))
        )
        return result

    def _call_speech_api(self, audio_path: str, language: str) -> Dict:
        """
        调用语音识别 API（模拟实现）
        实际项目中替换为真实的 API 调用，例如：
        - OpenAI Whisper: openai.Audio.transcribe(model="whisper-1", file=audio_file)
        - 阿里云语音识别
        - 讯飞语音识别

        :param audio_path: 音频文件路径
        :param language: 语言代码
        :return: 转录结果字典
        """
        # 模拟根据文件名返回不同的测试结果
        basename = os.path.basename(audio_path).lower()

        if "silence" in basename or "empty" in basename:
            # 模拟静音/空音频
            return {
                "success": True,
                "text": "",
                "language": language,
                "duration_sec": 0,
                "warning": "音频中未检测到语音内容",
            }

        if "noise" in basename:
            # 模拟噪音环境
            return {
                "success": True,
                "text": "今天天气不错。",
                "language": language,
                "duration_sec": 30,
                "warning": "检测到较强背景噪音，转录质量可能受影响",
            }

        # 默认模拟结果
        return {
            "success": True,
            "text": "这是一个模拟的语音识别结果，用于测试音频转文本功能。",
            "language": language,
            "duration_sec": 30,
        }

    def transcribe_with_timestamps(self, audio_path: str) -> List[Dict]:
        """
        带时间戳的语音转文本（模拟实现）
        实际项目中调用支持时间戳的语音识别 API。

        :param audio_path: 音频文件路径
        :return: 包含时间戳的文本段列表
        """
        logger.info("开始带时间戳的音频转录: %s", audio_path)

        # 模拟分段转录结果
        segments = [
            {"start": 0.0, "end": 3.5, "text": "大家好"},
            {"start": 3.5, "end": 7.2, "text": "欢迎来到今天的会议"},
            {"start": 7.2, "end": 12.0, "text": "今天我们讨论三个议题"},
        ]

        logger.info("带时间戳转录完成，共 %d 个片段", len(segments))
        return segments

    def estimate_audio_quality(self, audio_path: str) -> float:
        """
        估算音频质量（基于文件大小的启发式方法）
        真实项目中应分析音频的采样率、信噪比等指标。

        :param audio_path: 音频文件路径
        :return: 质量评分 0.0 - 1.0
        """
        try:
            file_size = os.path.getsize(audio_path)
        except Exception:
            return 0.0

        # 太小的文件可能有问题
        if file_size < 1024:  # 小于 1KB
            return 0.1
        elif file_size < 10 * 1024:  # 小于 10KB
            return 0.3

        # 合理的音频文件通常在 50KB - 50MB 之间
        if 50 * 1024 <= file_size <= 10 * 1024 * 1024:
            return 0.9
        elif file_size > 50 * 1024 * 1024:
            return 0.6  # 超大文件，可能有问题

        return 0.7
