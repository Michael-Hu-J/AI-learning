# bug_allure_helper.py - Bug信息附加到Allure报告的辅助工具
"""
Bug信息附加到Allure报告的辅助工具
功能：在测试失败时，将Bug信息（截图、API信息等）附加到Allure报告
"""
import allure
import os
from typing import Optional, Dict, Any, List
from utils.logger import Logger

logger = Logger().get_logger()


class BugAllureHelper:
    """Bug信息Allure辅助类"""
    
    @staticmethod
    def attach_bug_info(
        error_message: str,
        screenshot_path: Optional[str] = None,
        api_request: Optional[Dict] = None,
        api_response: Optional[Dict] = None,
        test_steps: Optional[List[Dict]] = None
    ):
        """
        将Bug信息附加到Allure报告
        
        参数：
        - error_message: 错误信息
        - screenshot_path: 截图路径
        - api_request: API请求信息
        - api_response: API响应信息
        - test_steps: 测试步骤列表
        """
        try:
            # 附加错误信息
            allure.attach(
                error_message,
                name=" Bug描述",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # 附加截图
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    with open(screenshot_path, 'rb') as f:
                        allure.attach(
                            f.read(),
                            name=" 失败截图",
                            attachment_type=allure.attachment_type.PNG
                        )
                    logger.info(f"已附加截图到Allure报告: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"附加截图失败: {e}")
            
            # 附加API请求/响应信息
            if api_request or api_response:
                api_info = {
                    "request": api_request,
                    "response": api_response
                }
                import json
                allure.attach(
                    json.dumps(api_info, indent=2, ensure_ascii=False),
                    name=" API请求/响应",
                    attachment_type=allure.attachment_type.JSON
                )
                logger.info("已附加API信息到Allure报告")
            
            # 附加测试步骤
            if test_steps:
                # 处理test_steps可能是字符串列表或字典列表的情况
                steps_list = []
                for idx, step in enumerate(test_steps):
                    if isinstance(step, dict):
                        step_text = f"{idx + 1}. {step.get('action', '')} {step.get('element', '')}"
                        if step.get('value'):
                            step_text += f": {step.get('value', '')}"
                        steps_list.append(step_text)
                    else:
                        steps_list.append(f"{idx + 1}. {step}")
                
                steps_text = "\n".join(steps_list)
                allure.attach(
                    steps_text,
                    name=" 测试步骤",
                    attachment_type=allure.attachment_type.TEXT
                )
                logger.info("已附加测试步骤到Allure报告")
            
        except Exception as e:
            logger.error(f"附加Bug信息到Allure报告失败: {str(e)}")
    
    @staticmethod
    def attach_bug_summary(bug_summary: Dict[str, Any]):
        """
        附加Bug摘要信息到Allure报告
        
        参数：
        - bug_summary: Bug摘要字典
        """
        try:
            summary_text = f"""
Bug ID: {bug_summary.get('bug_id', 'N/A')}
测试用例: {bug_summary.get('test_name', 'N/A')}
错误信息: {bug_summary.get('error_message', 'N/A')}
失败时间: {bug_summary.get('timestamp', 'N/A')}
"""
            allure.attach(
                summary_text,
                name=" Bug摘要",
                attachment_type=allure.attachment_type.TEXT
            )
        except Exception as e:
            logger.error(f"附加Bug摘要失败: {str(e)}")

