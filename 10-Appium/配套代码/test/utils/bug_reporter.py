# bug_reporter.py - Bug清单报告生成器
"""
Bug清单报告生成器
功能：在测试失败时自动收集bug信息，生成bug清单报告

包含信息：
1. Bug描述（错误信息）
2. 截图
3. 接口请求/响应信息
4. 测试步骤信息
5. 环境信息
"""
import os
import json
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from utils.logger import Logger

logger = Logger().get_logger()


class BugReporter:
    """Bug清单报告生成器"""
    
    def __init__(self, output_dir: str = "reports/bug_list"):
        """
        初始化Bug报告器
        
        参数：
        - output_dir: Bug清单输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.bugs: List[Dict[str, Any]] = []
    
    def record_failure(
        self,
        test_name: str,
        error_message: str,
        screenshot_path: Optional[str] = None,
        api_request: Optional[Dict] = None,
        api_response: Optional[Dict] = None,
        test_steps: Optional[List[Dict]] = None,
        test_data: Optional[Dict] = None,
        environment: Optional[Dict] = None
    ):
        """
        记录测试失败信息
        
        参数：
        - test_name: 测试用例名称
        - error_message: 错误信息
        - screenshot_path: 截图路径
        - api_request: API请求信息（如果有）
        - api_response: API响应信息（如果有）
        - test_steps: 测试步骤列表
        - test_data: 测试数据（如果有）
        - environment: 环境信息
        """
        bug_info = {
            "bug_id": f"BUG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.bugs) + 1}",
            "test_name": test_name,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
            "screenshot": screenshot_path if screenshot_path and os.path.exists(screenshot_path) else None,
            "api_request": api_request,
            "api_response": api_response,
            "test_steps": test_steps or [],
            "test_data": test_data,
            "environment": environment or {}
        }
        
        self.bugs.append(bug_info)
        logger.info(f"记录Bug: {bug_info['bug_id']} - {test_name}")
    
    def generate_markdown_report(self, output_file: Optional[str] = None) -> str:
        """
        生成Markdown格式的Bug清单报告
        
        参数：
        - output_file: 输出文件路径，如果为None则自动生成
        
        返回：
        - str: 报告文件路径
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"bug_list_{timestamp}.md"
        else:
            output_file = Path(output_file)
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成Markdown内容
        md_content = self._generate_markdown_content()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Bug清单报告已生成: {output_file}")
        return str(output_file)
    
    def _generate_markdown_content(self) -> str:
        """生成Markdown内容"""
        lines = [
            "# Bug清单报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Bug总数: {len(self.bugs)}",
            "",
            "---",
            ""
        ]
        
        for idx, bug in enumerate(self.bugs, 1):
            lines.extend([
                f"## Bug #{idx}: {bug['bug_id']}",
                "",
                f"### 测试用例",
                f"- **用例名称**: {bug['test_name']}",
                f"- **失败时间**: {bug['timestamp']}",
                "",
                f"### Bug描述",
                f"```",
                bug['error_message'],
                f"```",
                ""
            ])
            
            # 测试步骤
            if bug.get('test_steps'):
                lines.extend([
                    "### 测试步骤",
                    ""
                ])
                for step_idx, step in enumerate(bug['test_steps'], 1):
                    action = step.get('action', '')
                    element = step.get('element', '')
                    value = step.get('value', '')
                    lines.append(f"{step_idx}. **{action}** {element}" + (f": {value}" if value else ""))
                lines.append("")
            
            # 截图
            if bug.get('screenshot') and os.path.exists(bug['screenshot']):
                screenshot_path = bug['screenshot']
                # 使用相对路径或绝对路径
                rel_path = os.path.relpath(screenshot_path, self.output_dir.parent)
                lines.extend([
                    "### 截图",
                    f"![失败截图]({rel_path})",
                    "",
                    f"截图路径: `{screenshot_path}`",
                    ""
                ])
            
            # API请求/响应
            if bug.get('api_request') or bug.get('api_response'):
                lines.extend([
                    "### API信息",
                    ""
                ])
                
                if bug.get('api_request'):
                    lines.extend([
                        "#### API请求",
                        "```json",
                        json.dumps(bug['api_request'], indent=2, ensure_ascii=False),
                        "```",
                        ""
                    ])
                
                if bug.get('api_response'):
                    lines.extend([
                        "#### API响应",
                        "```json",
                        json.dumps(bug['api_response'], indent=2, ensure_ascii=False),
                        "```",
                        ""
                    ])
            
            # 测试数据
            if bug.get('test_data'):
                lines.extend([
                    "### 测试数据",
                    "```yaml",
                    yaml.dump(bug['test_data'], allow_unicode=True, default_flow_style=False),
                    "```",
                    ""
                ])
            
            # 环境信息
            if bug.get('environment'):
                lines.extend([
                    "### 环境信息",
                    ""
                ])
                for key, value in bug['environment'].items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            
            lines.extend([
                "---",
                ""
            ])
        
        return "\n".join(lines)
    
    def generate_json_report(self, output_file: Optional[str] = None) -> str:
        """
        生成JSON格式的Bug清单报告
        
        参数：
        - output_file: 输出文件路径
        
        返回：
        - str: 报告文件路径
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"bug_list_{timestamp}.json"
        else:
            output_file = Path(output_file)
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "total_bugs": len(self.bugs),
            "bugs": self.bugs
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Bug清单JSON报告已生成: {output_file}")
        return str(output_file)
    
    def attach_to_allure(self, test_result: Dict[str, Any]):
        """
        将Bug信息附加到Allure报告（通过Allure的attachment机制）
        
        参数：
        - test_result: 测试结果字典
        """
        try:
            import allure
            
            # 如果测试失败，附加Bug信息
            if test_result.get("status") == "failed":
                bug_summary = f"Bug ID: {test_result.get('bug_id', 'N/A')}\n"
                bug_summary += f"Error: {test_result.get('error_message', 'N/A')}\n"
                
                allure.attach(
                    bug_summary,
                    name="Bug信息",
                    attachment_type=allure.attachment_type.TEXT
                )
                
                # 附加截图
                if test_result.get('screenshot'):
                    try:
                        with open(test_result['screenshot'], 'rb') as f:
                            allure.attach(
                                f.read(),
                                name="失败截图",
                                attachment_type=allure.attachment_type.PNG
                            )
                    except Exception as e:
                        logger.warning(f"附加截图失败: {e}")
                
                # 附加API信息
                if test_result.get('api_request') or test_result.get('api_response'):
                    api_info = {
                        "request": test_result.get('api_request'),
                        "response": test_result.get('api_response')
                    }
                    allure.attach(
                        json.dumps(api_info, indent=2, ensure_ascii=False),
                        name="API请求/响应",
                        attachment_type=allure.attachment_type.JSON
                    )
        except ImportError:
            logger.warning("Allure未安装，无法附加Bug信息到Allure报告")
        except Exception as e:
            logger.error(f"附加Bug信息到Allure报告失败: {e}")
    
    def clear(self):
        """清空已记录的Bug"""
        self.bugs.clear()
        logger.info("Bug清单已清空")


# 全局Bug报告器实例
_bug_reporter = None


def get_bug_reporter() -> BugReporter:
    """获取全局Bug报告器实例"""
    global _bug_reporter
    if _bug_reporter is None:
        _bug_reporter = BugReporter()
    return _bug_reporter

