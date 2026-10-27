# allure_helper.py - Allure报告辅助工具
"""
Allure报告辅助工具
功能：提供Allure报告的配置和辅助方法，支持中文报告
通俗理解：让测试报告更好看、更详细，而且支持中文显示
"""
import allure
import os
from typing import Optional
from utils.screenshot import ScreenshotHelper


class AllureHelper:
    """
    Allure报告辅助类
    
    作用：
    1. 提供便捷的方法添加测试步骤、附件等
    2. 统一截图添加到报告的方式
    3. 支持中文显示
    """
    
    @staticmethod
    def attach_screenshot(driver, name: str = "截图", auto_compare: bool = True):
        """
        将截图添加到Allure报告，并可选择自动进行视觉对比
        
        参数说明：
        - driver: WebDriver实例
        - name: 截图在报告中的显示名称
        - auto_compare: 是否自动进行视觉对比（默认True）
        
        通俗理解：把截图放到测试报告里，让人能直接看到测试时的屏幕，并自动对比设计稿
        """
        try:
            screenshot_helper = ScreenshotHelper(driver)
            screenshot_path = screenshot_helper.take_screenshot(name)
            
            if screenshot_path and os.path.exists(screenshot_path):
                # 添加到Allure报告
                with open(screenshot_path, "rb") as f:
                    allure.attach(
                        f.read(),
                        name=name,
                        attachment_type=allure.attachment_type.PNG
                    )
                
                # 自动视觉对比（如果启用）
                if auto_compare:
                    try:
                        from utils.auto_visual_compare import get_auto_visual_compare
                        auto_visual_compare = get_auto_visual_compare()
                        if auto_visual_compare and auto_visual_compare.enabled:
                            compare_result = auto_visual_compare.compare_screenshot(screenshot_path)
                            
                            # 将对比结果附加到Allure报告
                            if compare_result and compare_result.get("status") == "compared":
                                similarity = compare_result.get("similarity_percent", 0)
                                passed = compare_result.get("passed", False)
                                design_path = compare_result.get("design_path", "")
                                diff_image_path = compare_result.get("diff_image_path", "")
                                
                                # 附加对比结果文本
                                compare_info = f"视觉对比结果:\n"
                                compare_info += f"相似度: {similarity:.2f}%\n"
                                compare_info += f"阈值: {compare_result.get('threshold', 0.95) * 100:.0f}%\n"
                                compare_info += f"状态: {'通过' if passed else '失败'}\n"
                                if design_path:
                                    compare_info += f"设计稿: {design_path}"
                                
                                allure.attach(
                                    compare_info,
                                    name=f"{name} - 视觉对比结果",
                                    attachment_type=allure.attachment_type.TEXT
                                )
                                
                                # 附加差异图（如果有）
                                if diff_image_path and os.path.exists(diff_image_path):
                                    with open(diff_image_path, "rb") as f:
                                        allure.attach(
                                            f.read(),
                                            name=f"{name} - 差异图",
                                            attachment_type=allure.attachment_type.PNG
                                        )
                    except Exception as e:
                        logger.debug(f"自动视觉对比失败（不影响截图）: {str(e)}")
                
                return True
        except Exception as e:
            print(f"添加截图到报告失败: {str(e)}")
        return False
    
    @staticmethod
    def step(step_name: str):
        """
        Allure步骤装饰器
        
        参数说明：
        - step_name: 步骤名称（会在报告中显示）
        
        使用示例：
        @AllureHelper.step("登录操作")
        def login():
            # 登录代码
            pass
        
        通俗理解：把测试步骤标记出来，在报告里能看到每个步骤做了什么
        """
        return allure.step(step_name)
    
    @staticmethod
    def description(description: str):
        """
        Allure描述装饰器
        
        参数说明：
        - description: 测试用例描述
        
        使用示例：
        @allure.description("这是一个登录测试用例")
        def test_login():
            pass
        """
        return allure.description(description)
    
    @staticmethod
    def title(title: str):
        """
        设置测试用例标题
        
        参数说明：
        - title: 测试用例标题（会在报告中显示）
        """
        return allure.title(title)
    
    @staticmethod
    def severity(severity: allure.severity_level):
        """
        设置测试用例严重程度
        
        参数说明：
        - severity: 严重程度（blocker, critical, normal, minor, trivial）
        """
        return allure.severity(severity)
    
    @staticmethod
    def attach_visual_comparison(
        similarity: float,
        status: str,
        screenshot_path: Optional[str] = None,
        design_path: Optional[str] = None,
        diff_image_path: Optional[str] = None,
        threshold: float = 0.95
    ):
        """
        附加视觉对比结果到Allure报告
        
        参数：
        - similarity: 相似度 (0-1)
        - status: 状态 (passed/failed)
        - screenshot_path: 截图路径
        - design_path: 设计稿路径
        - diff_image_path: 差异图路径
        - threshold: 阈值
        """
        
        try:
            # 附加对比结果文本
            compare_info = f"视觉对比结果:\n"
            compare_info += f"相似度: {similarity * 100:.2f}%\n"
            compare_info += f"阈值: {threshold * 100:.0f}%\n"
            compare_info += f"状态: {'通过' if status == 'passed' else '失败'}\n"
            if design_path:
                compare_info += f"设计稿: {design_path}\n"
            
            allure.attach(
                compare_info,
                name=" 视觉对比结果",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # 附加差异图（如果有）
            if diff_image_path and os.path.exists(diff_image_path):
                try:
                    with open(diff_image_path, "rb") as f:
                        allure.attach(
                            f.read(),
                            name=" 视觉差异图",
                            attachment_type=allure.attachment_type.PNG
                        )
                except Exception as e:
                    print(f"附加差异图失败: {str(e)}")
        except Exception as e:
            print(f"附加视觉对比结果失败: {str(e)}")
    
    @staticmethod
    def story(story: str):
        """
        设置测试用例所属的故事/功能
        
        参数说明：
        - story: 故事名称
        """
        return allure.story(story)
    
    @staticmethod
    def feature(feature: str):
        """
        设置测试用例所属的功能模块
        
        参数说明：
        - feature: 功能名称
        """
        return allure.feature(feature)
    
    @staticmethod
    def attach_text(content: str, name: str = "文本"):
        """
        将文本内容添加到报告
        
        参数说明：
        - content: 文本内容
        - name: 附件名称
        """
        allure.attach(content, name=name, attachment_type=allure.attachment_type.TEXT)
    
    @staticmethod
    def attach_json(content: str, name: str = "JSON"):
        """
        将JSON内容添加到报告
        
        参数说明：
        - content: JSON字符串
        - name: 附件名称
        """
        allure.attach(content, name=name, attachment_type=allure.attachment_type.JSON)

