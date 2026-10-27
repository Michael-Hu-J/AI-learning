"""
多模态应用主流程
~~~~~~~~~~~~~~~~
整合图片处理、OCR 识别、音频处理、质量校验等模块，
提供完整的端到端多模态处理流水线。

作者：测试员周周（14 年测试老兵）
"""
import os
import logging
from typing import Dict, List, Optional, Any

from src.image_processor import ImageProcessor, MediaType, MediaFile
from src.ocr_engine import OCREngine
from src.audio_processor import AudioProcessor
from src.quality_checker import QualityChecker
from src.config import Config

logger = logging.getLogger(__name__)


class MultimodalApp:
    """
    多模态应用主类
    整合所有模块，提供统一的多模态文件处理入口。

    处理流程：
    1. 文件预处理（格式校验、大小限制、质量评估）
    2. 根据媒体类型分流
       - 图片: 图像理解 + OCR + 图表分析
       - 音频: 语音转文本
    3. 多模态融合（整合多种模态的理解结果）
    4. 质量校验（关键信息验证、置信度评估）
    5. 返回结果
    """

    def __init__(self, config_path: str = None, llm_call_func: callable = None):
        """
        初始化多模态应用
        :param config_path: 配置文件路径
        :param llm_call_func: LLM 调用函数，接收 messages 列表，返回文本响应
        """
        # 初始化配置
        self.config = Config(config_path) if config_path else Config()

        # 初始化各模块
        self.image_processor = ImageProcessor(self.config)
        self.ocr_engine = OCREngine(self.config)
        self.audio_processor = AudioProcessor(self.config)
        self.quality_checker = QualityChecker(self.config)

        # LLM 调用函数（实际项目中连接大模型 API）
        self.llm = llm_call_func or self._default_llm_call

        # 设置日志级别
        log_level = self.config.get("logging", "level", default="INFO")
        log_format = self.config.get(
            "logging", "format",
            default="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        logging.basicConfig(level=getattr(logging, log_level), format=log_format)

        logger.info("多模态应用初始化完成，版本: %s", self.config.get("app", "version", default="1.0.0"))

    @staticmethod
    def _default_llm_call(messages: List[Dict]) -> str:
        """
        默认 LLM 调用函数（模拟实现）
        实际项目中应替换为真实的 API 调用。
        """
        logger.warning("使用默认 LLM 调用函数（模拟），应替换为真实 API 调用")
        return "这是一个模拟的多模态分析结果。"

    def process_file(self, file_path: str, task: str = "general") -> Dict:
        """
        处理单个媒体文件的主入口
        :param file_path: 媒体文件路径
        :param task: 任务类型 (general/ocr/chart/audio)
        :return: 处理结果字典

        这是整个系统的核心方法，串联了预处理 -> 识别 -> 校验的全流程。
        """
        logger.info("=" * 60)
        logger.info("开始处理文件: %s (任务: %s)", file_path, task)
        logger.info("=" * 60)

        result = {
            "success": False,
            "file_path": file_path,
            "task": task,
            "media_type": None,
            "processing_steps": [],
            "data": {},
            "quality_check": None,
            "error": None,
        }

        # 第一步：文件存在性检查
        if not file_path or not os.path.exists(file_path):
            error_msg = f"文件不存在: {file_path}"
            logger.error(error_msg)
            result["error"] = error_msg
            return result
        result["processing_steps"].append("文件存在性检查通过")

        # 第二步：判断媒体类型
        media_type = self.image_processor.get_media_type(file_path)
        result["media_type"] = media_type.value
        result["processing_steps"].append(f"媒体类型识别: {media_type.value}")
        logger.info("媒体类型: %s", media_type.value)

        # 第三步：根据媒体类型分流处理
        if media_type == MediaType.IMAGE:
            result = self._process_image(file_path, task, result)
        elif media_type == MediaType.AUDIO:
            result = self._process_audio(file_path, result)
        else:
            error_msg = f"不支持的媒体类型: {file_path}"
            logger.error(error_msg)
            result["error"] = error_msg
            return result

        # 第四步：质量校验
        quality_result = self._run_quality_checks(result)
        result["quality_check"] = quality_result
        result["processing_steps"].append(
            f"质量校验: {'通过' if quality_result.get('passed', False) else '发现问题'}"
        )

        # 总体成功标记
        result["success"] = result.get("error") is None
        logger.info("文件处理完成: success=%s", result["success"])
        return result

    def _process_image(self, file_path: str, task: str, result: Dict) -> Dict:
        """
        处理图片文件
        """
        # 校验图片
        valid, msg = self.image_processor.validate_image(file_path)
        if not valid:
            logger.error("图片校验失败: %s", msg)
            result["error"] = msg
            return result
        result["processing_steps"].append(f"图片校验通过: {msg}")

        # 评估图片质量
        quality_score = self.image_processor.estimate_image_quality(file_path)
        result["data"]["image_quality"] = quality_score
        result["processing_steps"].append(f"图片质量评分: {quality_score:.2f}")

        # 如果图片质量低于阈值，直接返回提示，不调用多模态模型
        quality_threshold = self.image_processor.quality_threshold
        if quality_score < quality_threshold:
            warning_msg = (
                f"图片质量不足（评分: {quality_score:.2f}，阈值: {quality_threshold}），"
                f"请重新拍摄"
            )
            logger.warning(warning_msg)
            result["data"]["description"] = warning_msg
            result["data"]["quality_warning"] = True
            result["processing_steps"].append("图片质量不足，跳过多模态分析")
            return result

        # 构建多模态请求并调用 LLM
        b64_image = self.image_processor.encode_image_to_base64(file_path)
        response = self._call_llm_for_image(b64_image, task)
        result["processing_steps"].append(f"LLM 多模态分析完成 (task: {task})")

        # 解析响应
        parsed = self.ocr_engine.parse_response(response, task)
        result["data"]["description"] = parsed["description"]
        result["data"]["text"] = parsed.get("text", "")
        result["data"]["confidence"] = parsed.get("confidence")
        result["data"]["chart_data"] = parsed.get("chart_data")

        if task == "ocr" and parsed.get("confidence") is not None:
            result["processing_steps"].append(
                f"OCR 置信度: {parsed['confidence']:.2f}"
            )

        return result

    def _process_audio(self, file_path: str, result: Dict) -> Dict:
        """
        处理音频文件
        """
        # 转录音频
        transcription = self.audio_processor.transcribe(file_path)
        result["processing_steps"].append("音频转录完成")

        if not transcription.get("success", False):
            result["error"] = transcription.get("error", "音频转录失败")
            return result

        result["data"]["transcription"] = transcription
        result["data"]["text"] = transcription.get("text", "")

        # 也生成带时间戳的版本
        try:
            segments = self.audio_processor.transcribe_with_timestamps(file_path)
            result["data"]["segments"] = segments
            result["processing_steps"].append(
                f"时间戳转录完成: {len(segments)} 个片段"
            )
        except Exception as e:
            logger.warning("时间戳转录失败（非关键错误）: %s", e)

        return result

    def _call_llm_for_image(self, b64_image: str, task: str) -> str:
        """
        调用 LLM 进行图片多模态分析
        :param b64_image: base64 编码的图片
        :param task: 任务类型
        :return: LLM 响应文本
        """
        task_prompts = {
            "general": "请详细描述这张图片的内容，包括场景、人物、物体和文字信息。",
            "ocr": "请识别图片中的所有文字内容，按阅读顺序输出。如果图片中没有文字，请回答'未检测到文字'。",
            "chart": "请分析这张图表，提取其中的数据信息，包括标题、坐标轴标签、数据系列和关键数据点。",
        }

        prompt = task_prompts.get(task, task_prompts["general"])

        message = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_image}"
                    },
                },
            ],
        }

        return self.llm([message])

    def _run_quality_checks(self, result: Dict) -> Dict:
        """
        对处理结果执行质量校验
        """
        data = result.get("data", {})
        task = result.get("task", "general")
        check_results = []

        # 1. OCR 文本检查（如果是 OCR 任务）
        if task == "ocr":
            ocr_text = data.get("text", "")
            field_map = {
                "invoice": ["发票", "号码", "金额", "日期"],
                "receipt": ["金额", "日期", "项目"],
            }
            # 根据文本内容选择期望字段
            if "发票" in ocr_text:
                expected = field_map["invoice"]
            elif "收据" in ocr_text or "明细" in ocr_text:
                expected = field_map["receipt"]
            else:
                expected = None

            ocr_check = self.quality_checker.check_ocr_result(
                ocr_text, expected
            )
            ocr_check["check_name"] = "OCR 结果检查"
            check_results.append(ocr_check)

        # 2. 转录完整性检查（如果是音频任务）
        if result.get("media_type") == "audio":
            transcription = data.get("transcription", {})
            trans_check = self.quality_checker.check_transcription_completeness(
                transcription
            )
            trans_check["check_name"] = "转录完整性检查"
            check_results.append(trans_check)

        # 3. 图片质量检查（如果是图片任务）
        if result.get("media_type") == "image":
            file_path = result.get("file_path", "")
            if file_path and os.path.exists(file_path):
                quality_check = self.quality_checker.check_image_quality(file_path)
                quality_check["check_name"] = "图片质量检查"
                check_results.append(quality_check)

        # 综合判定
        if check_results:
            verdict = self.quality_checker.get_overall_verdict(check_results)
            verdict["checks"] = check_results
            return verdict

        return {"passed": True, "checks": [], "verdict": "无检查项"}
