"""
图片处理与 OCR 模块
~~~~~~~~~~~~~~~~~~
负责图片格式校验、质量评估、base64 编码、媒体类型识别等预处理逻辑。

作者：测试员周周（14 年测试老兵）
"""
import os
import base64
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class MediaType(Enum):
    """媒体类型枚举"""
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"


@dataclass
class MediaFile:
    """媒体文件描述"""
    file_path: str
    media_type: MediaType
    file_size: int = 0
    width: int = 0
    height: int = 0
    quality_score: float = 1.0  # 质量评分 0-1


class ImageProcessor:
    """
    图片预处理器
    负责格式校验、质量评估、编码等预处理工作。
    这是多模态管线的第一道关卡——质量不合格的图片直接拒掉，
    避免让模型产生"自信的错误答案"。
    """

    def __init__(self, config=None):
        """
        初始化图片处理器
        :param config: 配置对象，包含图片处理的各项参数
        """
        self.config = config
        self._init_limits()

    def _init_limits(self):
        """从配置初始化限制参数"""
        if self.config:
            self.max_size_mb = self.config.get("image", "max_size_mb", default=20)
            self.supported_formats = self.config.get(
                "image", "supported_formats",
                default=[".jpg", ".jpeg", ".png", ".webp", ".bmp"]
            )
            self.min_resolution = tuple(
                self.config.get("image", "min_resolution", default=[100, 100])
            )
            self.quality_threshold = self.config.get(
                "image", "quality_threshold", default=0.5
            )
        else:
            self.max_size_mb = 20
            self.supported_formats = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]
            self.min_resolution = (100, 100)
            self.quality_threshold = 0.5

    def validate_image(self, file_path: str) -> Tuple[bool, str]:
        """
        校验图片文件是否合法
        :param file_path: 图片文件路径
        :return: (是否合法, 提示信息)
        """
        logger.debug("校验图片文件: %s", file_path)

        # 1. 检查文件是否存在
        if not file_path or not os.path.exists(file_path):
            return False, "文件不存在"

        # 2. 检查文件大小
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            logger.error("读取文件大小失败: %s, 错误: %s", file_path, e)
            return False, f"无法读取文件: {e}"

        max_size_bytes = self.max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"文件过大（{file_size / 1024 / 1024:.1f}MB），限制 {self.max_size_mb}MB"

        # 3. 检查文件格式
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_formats:
            return False, f"不支持的图片格式: {ext}，支持: {', '.join(self.supported_formats)}"

        # 4. 检查文件是否为空
        if file_size == 0:
            return False, "文件为空"

        logger.info("图片校验通过: %s (大小: %d, 格式: %s)", file_path, file_size, ext)
        return True, "校验通过"

    def validate_audio(self, file_path: str) -> Tuple[bool, str]:
        """
        校验音频文件是否合法
        :param file_path: 音频文件路径
        :return: (是否合法, 提示信息)
        """
        logger.debug("校验音频文件: %s", file_path)

        if not file_path or not os.path.exists(file_path):
            return False, "文件不存在"

        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return False, f"无法读取文件: {e}"

        # 检查文件是否为空
        if file_size == 0:
            return False, "文件为空"

        # 检查大小
        if self.config:
            max_size_mb = self.config.get("audio", "max_size_mb", default=50)
        else:
            max_size_mb = 50
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"文件过大（{file_size / 1024 / 1024:.1f}MB），限制 {max_size_mb}MB"

        # 检查格式
        ext = os.path.splitext(file_path)[1].lower()
        if self.config:
            supported = self.config.get(
                "audio", "supported_formats",
                default=[".mp3", ".wav", ".m4a", ".ogg", ".flac"]
            )
        else:
            supported = [".mp3", ".wav", ".m4a", ".ogg", ".flac"]
        if ext not in supported:
            return False, f"不支持的音频格式: {ext}，支持: {', '.join(supported)}"

        logger.info("音频校验通过: %s (大小: %d, 格式: %s)", file_path, file_size, ext)
        return True, "校验通过"

    def encode_image_to_base64(self, file_path: str) -> str:
        """
        将图片编码为 base64，用于 API 调用
        :param file_path: 图片文件路径
        :return: base64 编码字符串
        """
        logger.debug("编码图片为 base64: %s", file_path)
        try:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            logger.info("图片 base64 编码完成，长度: %d", len(encoded))
            return encoded
        except Exception as e:
            logger.error("图片 base64 编码失败: %s", e)
            raise

    def get_media_type(self, file_path: str) -> MediaType:
        """
        根据文件扩展名判断媒体类型
        :param file_path: 文件路径
        :return: MediaType 枚举值
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self.supported_formats:
            return MediaType.IMAGE
        if self.config:
            audio_formats = self.config.get(
                "audio", "supported_formats",
                default=[".mp3", ".wav", ".m4a", ".ogg", ".flac"]
            )
        else:
            audio_formats = [".mp3", ".wav", ".m4a", ".ogg", ".flac"]
        if ext in audio_formats:
            return MediaType.AUDIO
        return MediaType.DOCUMENT

    def estimate_image_quality(self, file_path: str) -> float:
        """
        估算图片质量（基于文件大小和格式的启发式方法）
        真实项目中应使用 OpenCV/PIL 计算清晰度、亮度、对比度等指标。
        :param file_path: 图片文件路径
        :return: 质量评分 0.0 - 1.0
        """
        logger.debug("估算图片质量: %s", file_path)
        try:
            file_size = os.path.getsize(file_path)
            ext = os.path.splitext(file_path)[1].lower()
        except Exception as e:
            logger.error("估算图片质量失败: %s", e)
            return 0.0

        # 文件大小太小可能质量不佳
        if file_size < 1024:  # 小于 1KB
            return 0.1
        elif file_size < 10 * 1024:  # 小于 10KB
            return 0.3
        elif file_size < 50 * 1024:  # 小于 50KB
            return 0.6
        elif file_size > 10 * 1024 * 1024:  # 大于 10MB，可能有问题
            return 0.7

        # 格式加分：PNG 通常比 JPG 质量高（无损压缩）
        format_bonus = 0.1 if ext in [".png", ".webp"] else 0.0
        score = min(1.0, 0.8 + format_bonus)
        logger.info("图片 %s 质量评分: %.2f", file_path, score)
        return score

    def create_media_file(self, file_path: str) -> Optional[MediaFile]:
        """
        根据文件路径创建 MediaFile 对象
        :param file_path: 文件路径
        :return: MediaFile 对象，如果文件无效则返回 None
        """
        if not os.path.exists(file_path):
            logger.warning("文件不存在: %s", file_path)
            return None

        media_type = self.get_media_type(file_path)
        file_size = os.path.getsize(file_path)
        quality_score = 1.0

        if media_type == MediaType.IMAGE:
            quality_score = self.estimate_image_quality(file_path)

        return MediaFile(
            file_path=file_path,
            media_type=media_type,
            file_size=file_size,
            quality_score=quality_score,
        )
