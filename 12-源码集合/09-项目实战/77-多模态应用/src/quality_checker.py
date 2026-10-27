"""
质量校验模块
~~~~~~~~~~~
负责图片质量评估、OCR 结果校验、完整性检查等质量保障逻辑。

作者：测试员周周（14 年测试老兵）
"""
import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class QualityChecker:
    """
    质量校验器
    负责多维度质量检查：
    1. 图片质量评估（清晰度、亮度、对比度）
    2. OCR 结果校验（关键字段提取、合理性检查）
    3. 完整性校验（转录时长 vs 音频时长）

    这是多模态管线的最后一道质量门禁。
    所有结果在返回用户之前，必须经过质量校验。
    """

    def __init__(self, config=None):
        """
        初始化质量校验器
        :param config: 配置对象
        """
        self.config = config
        self._init_thresholds()

    def _init_thresholds(self):
        """从配置初始化阈值参数"""
        if self.config:
            self.blur_threshold = self.config.get(
                "quality_check", "blur_threshold", default=100.0
            )
            self.brightness_min = self.config.get(
                "quality_check", "brightness_min", default=30
            )
            self.brightness_max = self.config.get(
                "quality_check", "brightness_max", default=240
            )
            self.contrast_min = self.config.get(
                "quality_check", "contrast_min", default=20
            )
            self.min_text_length = self.config.get(
                "quality_check", "min_text_length", default=5
            )
        else:
            self.blur_threshold = 100.0
            self.brightness_min = 30
            self.brightness_max = 240
            self.contrast_min = 20
            self.min_text_length = 5

    def check_image_quality(self, file_path: str) -> Dict:
        """
        综合检查图片质量
        真实项目中应使用 OpenCV/PIL 计算实际的清晰度、亮度、对比度。
        这里使用基于文件大小的启发式方法演示。

        :param file_path: 图片文件路径
        :return: 质量检查结果字典
        """
        logger.debug("检查图片质量: %s", file_path)

        import os
        try:
            file_size = os.path.getsize(file_path)
        except Exception as e:
            logger.error("读取文件失败: %s", e)
            return {
                "passed": False,
                "quality_score": 0.0,
                "issues": [f"无法读取文件: {e}"],
                "details": {},
            }

        issues = []
        quality_score = 1.0
        details = {}

        # 基于文件大小估算质量
        if file_size < 1024:
            quality_score = 0.1
            issues.append("文件过小（< 1KB），可能已损坏")
        elif file_size < 10 * 1024:
            quality_score = 0.3
            issues.append("文件较小（< 10KB），可能分辨率不足")
        elif file_size > 10 * 1024 * 1024:
            quality_score = 0.7
            issues.append("文件较大（> 10MB），可能包含冗余数据")

        details["file_size_bytes"] = file_size
        details["estimated_quality"] = quality_score

        passed = quality_score >= 0.3  # 动态阈值：低于 0.3 才拒掉
        result = {
            "passed": passed,
            "quality_score": quality_score,
            "issues": issues,
            "details": details,
        }

        if passed:
            logger.info("图片质量检查通过: score=%.2f", quality_score)
        else:
            logger.warning("图片质量检查不通过: score=%.2f, issues=%s", quality_score, issues)

        return result

    def check_ocr_result(self, ocr_text: str, expected_fields: List[str] = None) -> Dict:
        """
        检查 OCR 识别结果的完整性
        :param ocr_text: OCR 识别出的文本
        :param expected_fields: 期望包含的关键字段列表
        :return: 校验结果字典
        """
        logger.debug("检查 OCR 结果")

        if not ocr_text or not ocr_text.strip():
            return {
                "passed": False,
                "issues": ["OCR 结果为空"],
                "field_coverage": {},
            }

        issues = []
        field_coverage = {}

        # 检查文本长度
        text_length = len(ocr_text.strip())
        if text_length < self.min_text_length:
            issues.append(f"文本过短（{text_length} 字符），可能识别不完整")

        # 检查关键字段
        if expected_fields:
            found_fields = []
            missing_fields = []
            for field in expected_fields:
                if field in ocr_text:
                    found_fields.append(field)
                    field_coverage[field] = True
                else:
                    missing_fields.append(field)
                    field_coverage[field] = False

            if missing_fields:
                issues.append(f"缺少关键字段: {', '.join(missing_fields)}")

            coverage_rate = len(found_fields) / len(expected_fields) if expected_fields else 1.0
        else:
            found_fields = []
            missing_fields = []
            coverage_rate = 1.0

        # 检查是否包含数字（发票金额、号码等关键信息通常包含数字）
        has_numbers = bool(re.search(r"\d+", ocr_text))
        if not has_numbers and text_length > 0:
            issues.append("未检测到数字信息，可能缺少金额/日期等关键数据")

        result = {
            "passed": len(issues) == 0,
            "issues": issues,
            "field_coverage": field_coverage,
            "coverage_rate": coverage_rate,
            "found_fields": found_fields,
            "missing_fields": missing_fields,
            "text_length": text_length,
            "has_numbers": has_numbers,
        }

        if result["passed"]:
            logger.info("OCR 结果检查通过: 字段覆盖率=%.0f%%", coverage_rate * 100)
        else:
            logger.warning("OCR 结果检查发现问题: %s", issues)

        return result

    def check_transcription_completeness(
        self, transcription: Dict, original_duration_sec: float = None
    ) -> Dict:
        """
        检查音频转录的完整性
        如果转录时长和音频时长差距超过 30%，标记为"可能不完整"。

        :param transcription: 转录结果字典
        :param original_duration_sec: 原始音频时长（秒）
        :return: 完整性检查结果
        """
        logger.debug("检查转录完整性")

        issues = []
        transcript_duration = transcription.get("duration_sec", 0)
        transcript_text = transcription.get("text", "")

        # 检查转录文本是否为空
        if not transcript_text or not transcript_text.strip():
            issues.append("转录结果为空")

        # 检查时长一致性
        if original_duration_sec and original_duration_sec > 0:
            if transcript_duration > 0:
                duration_ratio = transcript_duration / original_duration_sec
                if duration_ratio < 0.7:
                    issues.append(
                        f"转录时长（{transcript_duration:.0f}s）远小于音频时长"
                        f"（{original_duration_sec:.0f}s），可能不完整"
                    )
            else:
                issues.append("转录未返回时长信息")

        # 检查警告
        warning = transcription.get("warning", "")
        if warning:
            issues.append(warning)

        result = {
            "passed": len(issues) == 0,
            "issues": issues,
            "transcript_duration_sec": transcript_duration,
            "original_duration_sec": original_duration_sec,
            "text_length": len(transcript_text),
        }

        if result["passed"]:
            logger.info("转录完整性检查通过")
        else:
            logger.warning("转录完整性检查发现问题: %s", issues)

        return result

    def check_invoice_fields(self, ocr_text: str) -> Dict:
        """
        专门检查发票 OCR 结果中的关键字段
        :param ocr_text: OCR 识别出的发票文本
        :return: 发票字段检查结果
        """
        logger.debug("检查发票字段")

        expected_fields = ["发票", "号码", "金额", "日期"]
        base_result = self.check_ocr_result(ocr_text, expected_fields)

        # 额外检查：提取金额
        amount_patterns = [
            r"金额[：:\s]*([\d,]+\.?\d*)",
            r"合计[：:\s]*([\d,]+\.?\d*)",
            r"总计[：:\s]*([\d,]+\.?\d*)",
            r"¥\s*([\d,]+\.?\d*)",
        ]
        extracted_amount = None
        for pattern in amount_patterns:
            match = re.search(pattern, ocr_text)
            if match:
                extracted_amount = match.group(1)
                break

        # 额外检查：提取发票号码
        invoice_no_pattern = r"发票号码[：:\s]*([\d]+)"
        invoice_no_match = re.search(invoice_no_pattern, ocr_text)
        invoice_no = invoice_no_match.group(1) if invoice_no_match else None

        base_result["extracted_amount"] = extracted_amount
        base_result["invoice_no"] = invoice_no

        if extracted_amount:
            logger.info("提取到发票金额: %s", extracted_amount)
        if invoice_no:
            logger.info("提取到发票号码: %s", invoice_no)

        return base_result

    def get_overall_verdict(self, check_results: List[Dict]) -> Dict:
        """
        综合多个检查结果，给出总体判定
        :param check_results: 检查结果字典列表
        :return: 总体判定结果
        """
        total_checks = len(check_results)
        passed_checks = sum(1 for r in check_results if r.get("passed", False))
        all_issues = []
        for r in check_results:
            all_issues.extend(r.get("issues", []))

        overall_passed = passed_checks == total_checks

        result = {
            "passed": overall_passed,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "all_issues": all_issues,
            "verdict": "通过" if overall_passed else "不通过",
        }

        logger.info(
            "总体判定: %s (%d/%d 检查通过)",
            result["verdict"], passed_checks, total_checks
        )
        if all_issues:
            logger.warning("问题列表: %s", all_issues)

        return result
