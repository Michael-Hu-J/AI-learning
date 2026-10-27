"""
多模态应用 - 主入口
~~~~~~~~~~~~~~~~~~
提供命令行接口，支持图片理解和音频转录的多模态处理。

用法：
    python main.py <file_path> [--task general|ocr|chart|audio] [--config config.yaml]

示例：
    python main.py data/invoice.jpg --task ocr
    python main.py data/meeting.mp3 --task audio
    python main.py data/photo.png --task general

作者：测试员周周（14 年测试老兵）
"""
import os
import sys
import json
import argparse
import logging

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.multimodal_app import MultimodalApp

logger = logging.getLogger(__name__)


def setup_arg_parser() -> argparse.ArgumentParser:
    """配置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="多模态应用 - 图片理解、OCR 与图表分析的全流程测试框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s data/invoice.jpg --task ocr
  %(prog)s data/photo.png --task general
  %(prog)s data/chart.png --task chart
  %(prog)s data/meeting.mp3 --task audio
  %(prog)s data/invoice.jpg --task ocr --config custom_config.yaml
        """,
    )
    parser.add_argument(
        "file_path",
        type=str,
        help="要处理的媒体文件路径（图片或音频）",
    )
    parser.add_argument(
        "--task",
        type=str,
        choices=["general", "ocr", "chart", "audio"],
        default="general",
        help="处理任务类型（默认: general）",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="配置文件路径（默认: config.yaml）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出结果到文件（JSON 格式）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="输出详细日志",
    )
    return parser


def main():
    """主入口函数"""
    parser = setup_arg_parser()
    args = parser.parse_args()

    # 日志级别
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 默认配置文件路径
    config_path = args.config
    if config_path is None:
        default_config = os.path.join(PROJECT_ROOT, "config.yaml")
        if os.path.exists(default_config):
            config_path = default_config

    # 模拟 LLM 调用函数（实际项目中替换为真实 API）
    def mock_llm(messages):
        """模拟 LLM 多模态调用"""
        return (
            "这是一张发票照片，发票号码为 12345678，"
            "金额为 15800 元，开票日期为 2024年10月15日。"
        )

    # 初始化应用
    logger.info("初始化多模态应用...")
    app = MultimodalApp(config_path, mock_llm)

    # 处理文件
    file_path = args.file_path
    if not os.path.exists(file_path):
        logger.error("文件不存在: %s", file_path)
        sys.exit(1)

    logger.info("开始处理: %s (任务: %s)", file_path, args.task)
    result = app.process_file(file_path, task=args.task)

    # 输出结果
    output = {
        "success": result.get("success", False),
        "file_path": result.get("file_path"),
        "task": result.get("task"),
        "media_type": result.get("media_type"),
        "data": {},
        "quality_check": result.get("quality_check"),
    }

    # 提取关键的 data 字段
    data = result.get("data", {})
    if "description" in data:
        output["data"]["description"] = data["description"]
    if "text" in data:
        output["data"]["text"] = data["text"]
    if "confidence" in data:
        output["data"]["confidence"] = data["confidence"]
    if "chart_data" in data:
        output["data"]["chart_data"] = data["chart_data"]
    if "transcription" in data:
        output["data"]["transcription"] = data["transcription"]
    if "segments" in data:
        output["data"]["segments"] = data["segments"]
    if "image_quality" in data:
        output["data"]["image_quality"] = data["image_quality"]

    if result.get("error"):
        output["error"] = result["error"]

    # 输出
    output_json = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        logger.info("结果已保存到: %s", args.output)
    else:
        print(output_json)

    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())
