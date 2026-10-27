# scene_collector.py - 失败现场收集器
"""
失败现场收集器

功能：
1. 测试失败时自动收集证据：截图、日志、请求/响应体
2. 附加到 Allure 报告
3. 按用例维度存储，方便后续排查
"""
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SceneCollector:
    """
    失败现场收集器。
    
    使用方式（在 conftest.py 中集成）：
        collector = SceneCollector(report_dir="reports/scenes")
        
        # 在 pytest_runtest_makereport 中：
        if report.failed:
            collector.collect(item.nodeid, driver=driver)
    """

    def __init__(self, report_dir: str = "reports/scenes"):
        self.report_dir = report_dir

    def collect(self, nodeid: str, driver=None, response: str = "", 
                extra_logs: str = "", category: str = "unknown") -> dict:
        """
        收集失败现场。
        
        参数：
        - nodeid: 测试用例 ID
        - driver: 浏览器/Appium driver（用于截图）
        - response: 请求/响应体信息
        - extra_logs: 额外日志
        - category: 失败分类（environment/code_bug/timeout 等）
        
        返回收集的文件信息字典。
        """
        scene_id = self._generate_scene_id(nodeid)
        scene_dir = Path(self.report_dir) / scene_id
        scene_dir.mkdir(parents=True, exist_ok=True)

        collected = {
            "scene_id": scene_id,
            "nodeid": nodeid,
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "files": [],
        }

        # 收集截图
        if driver is not None:
            screenshot_path = self._take_screenshot(driver, scene_dir, nodeid)
            if screenshot_path:
                collected["files"].append(("screenshot", screenshot_path))

        # 收集响应体
        if response:
            response_path = self._save_response(response, scene_dir)
            if response_path:
                collected["files"].append(("response", response_path))

        # 收集日志
        if extra_logs:
            log_path = self._save_logs(extra_logs, scene_dir)
            if log_path:
                collected["files"].append(("log", log_path))

        return collected

    def _generate_scene_id(self, nodeid: str) -> str:
        """生成场景标识（用例名_时间戳）"""
        safe_name = (
            nodeid.replace("/", "_")
                  .replace("::", "_")
                  .replace(".py", "")
                  .replace("[", "_")
                  .replace("]", "")
        )
        timestamp = datetime.now().strftime("%H%M%S")
        return f"{safe_name}_{timestamp}"

    def _take_screenshot(self, driver, scene_dir: Path, nodeid: str) -> Optional[str]:
        """截图"""
        try:
            screenshot_path = str(scene_dir / "failure.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"失败截图已保存: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.warning(f"截图失败: {e}")
            return None

    def _save_response(self, response: str, scene_dir: Path) -> Optional[str]:
        """保存响应体"""
        try:
            response_path = scene_dir / "response.txt"
            response_path.write_text(response, encoding="utf-8")
            return str(response_path)
        except Exception as e:
            logger.warning(f"保存响应体失败: {e}")
            return None

    def _save_logs(self, logs: str, scene_dir: Path) -> Optional[str]:
        """保存日志"""
        try:
            log_path = scene_dir / "debug.log"
            log_path.write_text(logs, encoding="utf-8")
            return str(log_path)
        except Exception as e:
            logger.warning(f"保存日志失败: {e}")
            return None

    def attach_to_allure(self, collected: dict, nodeid: str):
        """将收集的证据附加到 Allure 报告（如果安装了 allure-pytest）"""
        try:
            import allure
            for file_type, file_path in collected.get("files", []):
                if file_type == "screenshot" and os.path.exists(file_path):
                    allure.attach.file(
                        file_path,
                        name=f"失败截图 - {nodeid}",
                        attachment_type=allure.attachment_type.PNG,
                    )
                elif file_type == "response" and os.path.exists(file_path):
                    content = Path(file_path).read_text(encoding="utf-8")
                    allure.attach(
                        content,
                        name=f"响应体 - {nodeid}",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                elif file_type == "log" and os.path.exists(file_path):
                    content = Path(file_path).read_text(encoding="utf-8")
                    allure.attach(
                        content,
                        name=f"调试日志 - {nodeid}",
                        attachment_type=allure.attachment_type.TEXT,
                    )
        except ImportError:
            logger.debug("未安装 allure-pytest，跳过 Allure 附件")
        except Exception as e:
            logger.warning(f"Allure 附件失败: {e}")


# 全局场景收集器
scene_collector = SceneCollector()
