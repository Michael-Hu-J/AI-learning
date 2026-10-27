"""
OCR 识别引擎模块
~~~~~~~~~~~~~~~
负责文字识别、置信度估算、图表数据提取等 OCR 核心逻辑。

作者：测试员周周（14 年测试老兵）
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR 识别结果"""
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # x1, y1, x2, y2


class OCREngine:
    """
    OCR 识别引擎
    负责文字识别、置信度评估、图表数据提取。
    支持三种任务类型：通用描述(general)、文字识别(ocr)、图表分析(chart)。

    注意：OCR 识别不是"看到什么输出什么"，模型有时会"脑补"模糊区域的内容。
    置信度评估就是为了发现这种"自信的错误"。
    """

    def __init__(self, config=None):
        """
        初始化 OCR 引擎
        :param config: 配置对象
        """
        self.config = config
        self._init_thresholds()

    def _init_thresholds(self):
        """从配置初始化阈值参数"""
        if self.config:
            self.confidence_threshold = self.config.get(
                "ocr", "confidence_threshold", default=0.6
            )
            self.min_chinese_ratio = self.config.get(
                "ocr", "min_chinese_ratio", default=0.3
            )
            self.max_chinese_ratio = self.config.get(
                "ocr", "max_chinese_ratio", default=0.9
            )
            self.high_confidence = self.config.get("ocr", "high_confidence", default=0.85)
            self.medium_confidence = self.config.get("ocr", "medium_confidence", default=0.7)
            self.low_confidence = self.config.get("ocr", "low_confidence", default=0.6)
            self.no_text_confidence = self.config.get("ocr", "no_text_confidence", default=0.0)
        else:
            self.confidence_threshold = 0.6
            self.min_chinese_ratio = 0.3
            self.max_chinese_ratio = 0.9
            self.high_confidence = 0.85
            self.medium_confidence = 0.7
            self.low_confidence = 0.6
            self.no_text_confidence = 0.0

    def estimate_confidence(self, text: str) -> float:
        """
        估算 OCR 置信度（基于文本合理性的启发式方法）
        :param text: OCR 识别的文本
        :return: 置信度 0.0 - 1.0

        思路：
        - 如果文本为空或"未检测到文字"，置信度为 0
        - 中文字符比例在合理范围内(30%-90%)认为置信度较高
        - 纯英文或纯中文（无标点）的文本可能有问题
        """
        if not text or not text.strip():
            logger.debug("文本为空，置信度: 0.0")
            return self.no_text_confidence

        text_stripped = text.strip()
        if text_stripped in ("未检测到文字", "未检测到文字。", "未检测到文字！"):
            logger.debug("检测到'未检测到文字'标记，置信度: 0.0")
            return self.no_text_confidence

        # 计算中文字符比例
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text_stripped))
        # 计算英文字符
        english_chars = len(re.findall(r"[a-zA-Z]", text_stripped))
        # 计算数字
        digit_chars = len(re.findall(r"[0-9]", text_stripped))
        total_chars = len(text_stripped)

        if total_chars == 0:
            return self.no_text_confidence

        chinese_ratio = chinese_chars / total_chars

        logger.debug(
            "置信度估算: 总字符=%d, 中文=%d(%.2f), 英文=%d, 数字=%d",
            total_chars, chinese_chars, chinese_ratio, english_chars, digit_chars
        )

        # 有中文字符的情况
        if chinese_chars > 0:
            if self.min_chinese_ratio <= chinese_ratio <= self.max_chinese_ratio:
                # 有合理比例的中文 + 一些英文/数字，这是最正常的场景
                confidence = self.high_confidence
            elif chinese_ratio > self.max_chinese_ratio:
                # 几乎全是中文，缺少标点和数字，可能识别不全
                confidence = self.medium_confidence
            else:
                # 中文比例偏低，可能是识别错误
                confidence = self.low_confidence
        elif english_chars > 0 or digit_chars > 0:
            # 纯英文或纯数字文本
            confidence = self.high_confidence
        else:
            # 特殊字符或其他
            confidence = self.low_confidence

        logger.debug("估算置信度: %.2f", confidence)
        return confidence

    def extract_chart_data(self, response: str) -> Optional[Dict]:
        """
        从图表分析结果中提取结构化数据
        :param response: LLM 返回的图表分析文本
        :return: 结构化数据字典，如果无法提取则返回 None
        """
        if not response or not response.strip():
            logger.debug("图表响应为空，无法提取数据")
            return None

        # 尝试从文本中提取数字数据（支持整数、小数、千分位格式）
        # 先提取带小数的数字，再提取整数
        numbers = re.findall(r"\d+\.\d+|\d+", response)
        # 过滤掉太短的数字（可能是噪点）
        meaningful_numbers = []
        for n in numbers:
            try:
                val = float(n)
                if val > 0:
                    meaningful_numbers.append(val)
            except ValueError:
                continue

        if not meaningful_numbers:
            logger.debug("未从图表响应中提取到有效数字")
            return None

        # 尝试提取中文字符中的数值描述（如"一百二十万"）
        chinese_numbers = re.findall(
            r"[零一二三四五六七八九十百千万亿]+", response
        )

        result = {
            "raw_text": response,
            "extracted_numbers": meaningful_numbers,
            "data_points": len(meaningful_numbers),
            "has_chinese_numbers": len(chinese_numbers) > 0,
        }

        logger.info(
            "图表数据提取完成: %d 个数据点, 含中文数字: %s",
            len(meaningful_numbers), result["has_chinese_numbers"]
        )
        return result

    def parse_response(self, response: str, task: str) -> Dict:
        """
        解析多模态响应，返回结构化结果
        :param response: LLM 返回的文本
        :param task: 任务类型 (general/ocr/chart)
        :return: 解析后的字典
        """
        logger.debug("解析响应, 任务类型: %s, 响应长度: %d", task, len(response))

        result = {
            "description": response,
            "confidence": None,
            "chart_data": None,
            "text": "",
        }

        if task == "ocr":
            result["text"] = response
            result["confidence"] = self.estimate_confidence(response)
            logger.info(
                "OCR 解析完成, 文本长度: %d, 置信度: %.2f",
                len(response), result["confidence"]
            )

        elif task == "chart":
            result["chart_data"] = self.extract_chart_data(response)
            if result["chart_data"]:
                logger.info(
                    "图表解析完成, 提取到 %d 个数据点",
                    result["chart_data"]["data_points"]
                )
            else:
                logger.warning("图表解析完成, 但未提取到结构化数据")

        elif task == "general":
            result["text"] = response
            logger.info("通用描述解析完成, 描述长度: %d", len(response))

        return result

    def meets_confidence_threshold(self, text: str) -> bool:
        """
        判断 OCR 结果是否达到置信度阈值
        :param text: OCR 识别的文本
        :return: True 表示可信，False 表示需要标记或重新识别
        """
        confidence = self.estimate_confidence(text)
        meets = confidence >= self.confidence_threshold
        if not meets:
            logger.warning(
                "OCR 结果置信度 %.2f 低于阈值 %.2f", confidence, self.confidence_threshold
            )
        return meets
