# visual_comparison.py - 视觉对比工具
"""
视觉对比工具
功能：
1. 对比测试截图与设计稿
2. 计算相似度
3. 生成差异图
4. 生成视觉测试报告
"""
import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageChops, ImageDraw, ImageFont
from utils.logger import Logger

logger = Logger().get_logger()

try:
    from skimage.metrics import structural_similarity as ssim
    SSIM_AVAILABLE = True
except ImportError:
    SSIM_AVAILABLE = False
    logger.warning("scikit-image未安装，将使用简化的相似度计算。安装方法: pip install scikit-image")


class VisualComparison:
    """视觉对比工具类"""
    
    def __init__(self, design_dir: str = "testcases/ui_designs/figma_exports"):
        """
        初始化视觉对比工具
        
        参数：
        - design_dir: 设计稿目录
        """
        self.design_dir = Path(design_dir)
        self.design_images: Dict[str, Path] = {}
        self._load_design_images()
    
    def _load_design_images(self):
        """加载设计稿图片"""
        if self.design_dir.exists():
            for img_file in self.design_dir.glob("*.png"):
                # 使用文件名（不含扩展名）作为key
                key = img_file.stem.lower()
                self.design_images[key] = img_file
                logger.debug(f"加载设计稿: {key} -> {img_file}")
        logger.info(f"已加载 {len(self.design_images)} 张设计稿")
    
    def find_design_image(self, screenshot_name: str) -> Optional[Path]:
        """
        根据截图名称查找对应的设计稿
        
        参数：
        - screenshot_name: 截图文件名（不含路径）
        
        返回：
        - Path: 设计稿路径，如果未找到返回None
        """
        # 提取截图名称的关键词
        name_lower = screenshot_name.lower().replace(".png", "").replace(".jpg", "")
        
        # 尝试直接匹配
        if name_lower in self.design_images:
            return self.design_images[name_lower]
        
        # 尝试模糊匹配
        for design_key, design_path in self.design_images.items():
            # 如果截图名称包含设计稿名称，或者设计稿名称包含截图名称
            if design_key in name_lower or name_lower in design_key:
                logger.info(f"匹配设计稿: {screenshot_name} -> {design_key}")
                return design_path
            
            # 检查常见页面类型
            page_types = {
                "login": ["登录", "login"],
                "register": ["注册", "register"],
                "home": ["首页", "home", "main"],
                "profile": ["个人", "profile", "me", "账户"],
            }
            
            for page_type, keywords in page_types.items():
                if design_key == page_type:
                    for keyword in keywords:
                        if keyword in name_lower:
                            logger.info(f"匹配设计稿（类型）: {screenshot_name} -> {design_key}")
                            return design_path
        
        logger.warning(f"未找到对应的设计稿: {screenshot_name}")
        return None
    
    def compare_images(
        self,
        screenshot_path: str,
        design_path: Optional[str] = None,
        threshold: float = 0.95
    ) -> Dict[str, Any]:
        """
        对比截图与设计稿
        
        参数：
        - screenshot_path: 截图路径
        - design_path: 设计稿路径（如果为None，自动查找）
        - threshold: 相似度阈值（默认0.95，即95%）
        
        返回：
        - Dict: 对比结果，包含相似度、差异等信息
        """
        screenshot_path = Path(screenshot_path)
        
        if not screenshot_path.exists():
            logger.error(f"截图文件不存在: {screenshot_path}")
            return {
                "status": "error",
                "error": f"截图文件不存在: {screenshot_path}",
                "similarity": 0.0
            }
        
        # 如果没有指定设计稿，自动查找
        if design_path is None:
            design_file = self.find_design_image(screenshot_path.name)
            if design_file is None:
                return {
                    "status": "no_design",
                    "message": f"未找到对应的设计稿: {screenshot_path.name}",
                    "similarity": 0.0
                }
            design_path = str(design_file)
        
        design_path = Path(design_path)
        if not design_path.exists():
            logger.error(f"设计稿文件不存在: {design_path}")
            return {
                "status": "error",
                "error": f"设计稿文件不存在: {design_path}",
                "similarity": 0.0
            }
        
        try:
            # 加载图片
            screenshot_img = Image.open(screenshot_path)
            design_img = Image.open(design_path)
            
            # 转换为RGB格式（如果必要）
            if screenshot_img.mode != 'RGB':
                screenshot_img = screenshot_img.convert('RGB')
            if design_img.mode != 'RGB':
                design_img = design_img.convert('RGB')
            
            # 调整尺寸使两个图片大小一致
            screenshot_array = np.array(screenshot_img)
            design_array = np.array(design_img)
            
            # 如果尺寸不一致，调整设计稿尺寸以匹配截图
            if screenshot_array.shape[:2] != design_array.shape[:2]:
                design_img = design_img.resize(screenshot_img.size, Image.Resampling.LANCZOS)
                design_array = np.array(design_img)
                logger.info(f"调整设计稿尺寸: {design_array.shape[:2]} -> {screenshot_array.shape[:2]}")
            
            # 计算相似度
            similarity = self._calculate_similarity(screenshot_array, design_array)
            
            # 生成差异图
            diff_image_path = self._generate_diff_image(
                screenshot_img,
                design_img,
                screenshot_path
            )
            
            # 计算差异区域
            diff_regions = self._find_diff_regions(screenshot_array, design_array)
            
            # 判断是否通过
            passed = similarity >= threshold
            
            result = {
                "status": "compared",
                "screenshot_path": str(screenshot_path),
                "design_path": str(design_path),
                "similarity": float(similarity),
                "similarity_percent": float(similarity * 100),
                "threshold": threshold,
                "passed": passed,
                "diff_image_path": diff_image_path,
                "diff_regions_count": len(diff_regions),
                "diff_regions": diff_regions,
                "screenshot_size": screenshot_img.size,
                "design_size": design_img.size,
            }
            
            logger.info(f"视觉对比完成: {screenshot_path.name}, 相似度: {similarity:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"视觉对比失败: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
                "similarity": 0.0
            }
    
    def _calculate_similarity(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        计算两张图片的相似度
        
        参数：
        - img1: 第一张图片（numpy数组）
        - img2: 第二张图片（numpy数组）
        
        返回：
        - float: 相似度（0-1之间）
        """
        try:
            # 保证尺寸一致
            if img1.shape != img2.shape:
                # 调整img2尺寸以匹配img1
                img2_resized = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            else:
                img2_resized = img2
            
            # 转换为灰度图（如果必要）
            if len(img1.shape) == 3:
                gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
            else:
                gray1 = img1
            
            if len(img2_resized.shape) == 3:
                gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_RGB2GRAY)
            else:
                gray2 = img2_resized
            
            # 使用SSIM计算相似度（如果可用）
            if SSIM_AVAILABLE:
                similarity = ssim(gray1, gray2, data_range=255)
            else:
                # 使用简化的相似度计算（像素差异）
                diff = np.abs(gray1.astype(float) - gray2.astype(float))
                similarity = 1.0 - (np.mean(diff) / 255.0)
            
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"计算相似度失败: {str(e)}")
            return 0.0
    
    def _generate_diff_image(
        self,
        screenshot_img: Image.Image,
        design_img: Image.Image,
        screenshot_path: Path
    ) -> str:
        """
        生成差异图
        
        参数：
        - screenshot_img: 截图图片
        - design_img: 设计稿图片
        - screenshot_path: 截图路径（用于生成输出路径）
        
        返回：
        - str: 差异图路径
        """
        try:
            # 保证尺寸一致
            if screenshot_img.size != design_img.size:
                design_img = design_img.resize(screenshot_img.size, Image.Resampling.LANCZOS)
            
            # 计算差异
            diff = ImageChops.difference(screenshot_img, design_img)
            
            # 转换为numpy数组以便处理
            diff_array = np.array(diff)
            
            # 创建差异图（红色高亮差异区域）
            diff_highlight = screenshot_img.copy()
            diff_array_highlight = np.array(diff_highlight)
            
            # 找出差异区域（差异大于阈值的像素）
            diff_mask = np.any(diff_array > 30, axis=2)  # 阈值可调整
            
            # 在差异区域叠加红色
            diff_array_highlight[diff_mask] = [
                np.minimum(255, diff_array_highlight[diff_mask, 0] + 100),
                diff_array_highlight[diff_mask, 1],
                diff_array_highlight[diff_mask, 2]
            ]
            
            diff_highlight = Image.fromarray(diff_array_highlight)
            
            # 保存差异图
            output_dir = Path("reports/visual_diff")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            diff_filename = f"diff_{screenshot_path.stem}.png"
            diff_path = output_dir / diff_filename
            
            diff_highlight.save(diff_path, "PNG")
            
            logger.debug(f"差异图已保存: {diff_path}")
            
            return str(diff_path)
            
        except Exception as e:
            logger.error(f"生成差异图失败: {str(e)}")
            return ""
    
    def _find_diff_regions(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
        threshold: int = 30
    ) -> List[Dict[str, Any]]:
        """
        找出差异区域
        
        参数：
        - img1: 第一张图片
        - img2: 第二张图片
        - threshold: 差异阈值
        
        返回：
        - List[Dict]: 差异区域列表，每个区域包含坐标和大小
        """
        try:
            # 保证尺寸一致
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            # 计算差异
            if len(img1.shape) == 3:
                diff = np.abs(img1.astype(float) - img2.astype(float))
                diff_gray = np.mean(diff, axis=2)
            else:
                diff_gray = np.abs(img1.astype(float) - img2.astype(float))
            
            # 找出差异区域
            diff_mask = diff_gray > threshold
            
            # 使用轮廓检测找出差异区域
            diff_mask_uint8 = (diff_mask * 255).astype(np.uint8)
            contours, _ = cv2.findContours(diff_mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # 只保留足够大的区域
                if w > 10 and h > 10:
                    regions.append({
                        "x": int(x),
                        "y": int(y),
                        "width": int(w),
                        "height": int(h),
                        "area": int(w * h)
                    })
            
            return regions
            
        except Exception as e:
            logger.error(f"查找差异区域失败: {str(e)}")
            return []
    
    def batch_compare(
        self,
        screenshot_dir: str,
        output_dir: str = "reports/visual_test"
    ) -> Dict[str, Any]:
        """
        批量对比截图与设计稿
        
        参数：
        - screenshot_dir: 截图目录
        - output_dir: 输出目录
        
        返回：
        - Dict: 批量对比结果
        """
        screenshot_dir = Path(screenshot_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not screenshot_dir.exists():
            logger.error(f"截图目录不存在: {screenshot_dir}")
            return {"status": "error", "error": f"截图目录不存在: {screenshot_dir}"}
        
        # 查找所有截图文件
        screenshot_files = list(screenshot_dir.glob("*.png")) + list(screenshot_dir.glob("*.jpg"))
        
        if not screenshot_files:
            logger.warning(f"截图目录中没有找到图片文件: {screenshot_dir}")
            return {"status": "no_screenshots", "screenshots": []}
        
        logger.info(f"开始批量对比，共 {len(screenshot_files)} 张截图")
        
        results = []
        for screenshot_file in screenshot_files:
            logger.info(f"对比截图: {screenshot_file.name}")
            result = self.compare_images(str(screenshot_file))
            result["screenshot_name"] = screenshot_file.name
            results.append(result)
        
        # 统计结果
        compared_count = sum(1 for r in results if r.get("status") == "compared")
        passed_count = sum(1 for r in results if r.get("passed", False))
        failed_count = compared_count - passed_count
        no_design_count = sum(1 for r in results if r.get("status") == "no_design")
        error_count = sum(1 for r in results if r.get("status") == "error")
        
        summary = {
            "status": "completed",
            "total_screenshots": len(screenshot_files),
            "compared": compared_count,
            "passed": passed_count,
            "failed": failed_count,
            "no_design": no_design_count,
            "errors": error_count,
            "results": results
        }
        
        logger.info(f"批量对比完成: 总计{len(screenshot_files)}，对比{compared_count}，通过{passed_count}，失败{failed_count}")
        
        return summary

