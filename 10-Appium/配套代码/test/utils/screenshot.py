# screenshot.py - 截图工具类
"""
截图工具类
功能：在测试过程中自动截图，特别是失败时
通俗理解：就像拍照，把手机屏幕拍下来，出问题时看看当时屏幕上是什么样
"""
import os
from datetime import datetime
from pathlib import Path
from utils.logger import Logger

logger = Logger().get_logger()

# 延迟导入，避免循环依赖
_auto_visual_compare = None


def _get_auto_visual_compare():
    """延迟导入自动视觉对比工具"""
    global _auto_visual_compare
    if _auto_visual_compare is None:
        try:
            from utils.auto_visual_compare import get_auto_visual_compare
            _auto_visual_compare = get_auto_visual_compare()
        except ImportError:
            pass
    return _auto_visual_compare


class ScreenshotHelper:
    """
    截图工具类
    
    作用：
    1. 统一截图保存路径和命名规则
    2. 自动创建截图目录（按设备-类型-时间命名）
    3. 截图文件名包含时间戳，便于查找
    """
    
    def __init__(self, driver, screenshot_dir=None):
        """
        初始化截图工具
        
        参数说明：
        - driver: Appium WebDriver实例
        - screenshot_dir: 截图保存目录，如果为None则从环境变量或会话管理器获取
        """
        self.driver = driver
        
        # 确定截图目录
        if screenshot_dir is None:
            # 优先从环境变量获取（由test_session_manager设置）
            screenshot_dir = os.getenv("SCREENSHOT_DIR", "screenshots")
        
        self.screenshot_dir = screenshot_dir
        
        # 创建截图目录
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
            logger.info(f"创建截图目录: {self.screenshot_dir}")
    
    def take_screenshot(self, screenshot_name: str = None):
        """
        截图
        
        参数说明：
        - screenshot_name: 截图名称（不含扩展名），如果为None则使用时间戳
        
        返回：
        - screenshot_path: 截图文件路径
        
        通俗理解：给手机屏幕拍一张照片，保存在指定的文件夹里
        """
        try:
            # 生成截图文件名
            if screenshot_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{screenshot_name}_{timestamp}.png"
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"screenshot_{timestamp}.png"
            
            # 完整的截图路径
            screenshot_path = os.path.join(self.screenshot_dir, filename)
            
            # 执行截图
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"截图已保存: {screenshot_path}")
            
            # 自动视觉对比（如果启用）
            try:
                auto_compare = _get_auto_visual_compare()
                if auto_compare and auto_compare.enabled:
                    compare_result = auto_compare.compare_screenshot(screenshot_path)
                    if compare_result and compare_result.get("status") == "compared":
                        similarity = compare_result.get("similarity_percent", 0)
                        passed = compare_result.get("passed", False)
                        status_icon = "" if passed else ""
                        logger.info(f"{status_icon} 视觉对比: {Path(screenshot_path).name}, 相似度: {similarity:.2f}%")
                        
                        # 如果对比失败，记录到Bug报告
                        if not passed:
                            try:
                                from utils.bug_reporter import get_bug_reporter
                                bug_reporter = get_bug_reporter()
                                bug_reporter.record_failure(
                                    test_name=f"visual_compare_{Path(screenshot_path).stem}",
                                    error_message=f"视觉对比失败: 相似度 {similarity:.2f}% < 阈值 {compare_result.get('threshold', 0.95) * 100:.0f}%",
                                    screenshot_path=screenshot_path,
                                    test_steps=[{
                                        "action": "视觉对比",
                                        "screenshot": screenshot_path,
                                        "design": compare_result.get("design_path"),
                                        "similarity": similarity
                                    }]
                                )
                            except Exception as e:
                                logger.warning(f"记录视觉对比失败到Bug报告时出错: {str(e)}")
            except Exception as e:
                logger.debug(f"自动视觉对比失败（不影响截图）: {str(e)}")
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return None
    
    def take_screenshot_on_failure(self, test_name: str):
        """
        测试失败时截图（带测试名称）
        
        参数：
        - test_name: 测试用例名称
        
        通俗理解：测试出问题时，自动拍一张照片，文件名包含测试名称，方便知道是哪个测试失败了
        """
        screenshot_name = f"failure_{test_name}"
        return self.take_screenshot(screenshot_name)
    
    def take_screenshot_on_success(self, test_name: str):
        """
        测试成功时截图（可选，用于关键步骤记录）
        
        参数：
        - test_name: 测试用例名称
        """
        screenshot_name = f"success_{test_name}"
        return self.take_screenshot(screenshot_name)

