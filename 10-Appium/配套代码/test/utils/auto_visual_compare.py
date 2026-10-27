# auto_visual_compare.py - 自动视觉对比工具
"""
自动视觉对比工具
功能：在测试过程中自动截图并对比UI设计稿
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any
from utils.logger import Logger
from utils.visual_comparison import VisualComparison
from utils.bug_reporter import get_bug_reporter

logger = Logger().get_logger()


class AutoVisualCompare:
    """自动视觉对比工具类"""
    
    def __init__(self, design_dir: str = "testcases/ui_designs/figma_exports"):
        """
        初始化自动视觉对比工具
        
        参数：
        - design_dir: 设计稿目录
        """
        self.comparison = VisualComparison(design_dir)
        self.results: list[Dict[str, Any]] = []
        self.enabled = True  # 默认启用
    
    def compare_screenshot(
        self,
        screenshot_path: str,
        threshold: float = 0.95
    ) -> Optional[Dict[str, Any]]:
        """
        对比截图与设计稿
        
        参数：
        - screenshot_path: 截图路径
        - threshold: 相似度阈值（默认0.95，即95%）
        
        返回：
        - Dict: 对比结果，如果未找到设计稿返回None
        """
        if not self.enabled:
            return None
        
        if not screenshot_path or not os.path.exists(screenshot_path):
            logger.warning(f"截图文件不存在: {screenshot_path}")
            return None
        
        try:
            # 对比截图与设计稿
            result = self.comparison.compare_images(screenshot_path, threshold=threshold)
            
            # 记录结果
            if result.get("status") == "compared":
                self.results.append(result)
                logger.info(f"视觉对比完成: {Path(screenshot_path).name}, 相似度: {result.get('similarity_percent', 0):.2f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"视觉对比失败: {str(e)}")
            return None
    
    def enable(self):
        """启用自动视觉对比"""
        self.enabled = True
        logger.info("自动视觉对比已启用")
    
    def disable(self):
        """禁用自动视觉对比"""
        self.enabled = False
        logger.info("自动视觉对比已禁用")
    
    def get_all_results(self) -> list[Dict[str, Any]]:
        """获取所有对比结果"""
        return self.results
    
    def clear_results(self):
        """清空对比结果"""
        self.results.clear()


# 全局实例
_auto_visual_compare_instance: Optional[AutoVisualCompare] = None


def get_auto_visual_compare() -> AutoVisualCompare:
    """获取自动视觉对比工具实例（单例）"""
    global _auto_visual_compare_instance
    if _auto_visual_compare_instance is None:
        _auto_visual_compare_instance = AutoVisualCompare()
    return _auto_visual_compare_instance

