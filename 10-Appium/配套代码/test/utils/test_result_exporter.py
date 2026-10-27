# test_result_exporter.py - 测试执行结果导出器
"""
测试执行结果导出器
功能：在pytest会话结束时，生成Markdown格式的执行概览报告

特性：
- 收集所有测试用例的执行结果
- 使用xmind_title作为显示名称（100%匹配原始XMind）
- 按模块/层级展示测试结果
- 生成XMind友好的格式（### 和 - 列表）
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import yaml
from utils.logger import Logger

logger = Logger().get_logger()


class TestResultExporter:
    """测试结果导出器"""
    
    def __init__(self, output_file: str = "test_results.md"):
        """
        初始化导出器
        
        参数：
        - output_file: 输出Markdown文件路径
        """
        self.output_file = output_file
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.yaml_cache: Dict[str, Dict[str, Any]] = {}  # 缓存YAML用例数据
        
    def collect_test_result(self, nodeid: str, outcome: str, duration: float, 
                           error_message: str = ""):
        """
        收集单个测试用例的结果
        
        参数：
        - nodeid: 测试用例的nodeid（如 "tests/test_login.py::test_valid_user"）
        - outcome: 执行结果（"passed", "failed", "skipped"）
        - duration: 执行耗时（秒）
        - error_message: 错误信息（如果失败）
        """
        self.test_results[nodeid] = {
            "nodeid": nodeid,
            "outcome": outcome,
            "duration": duration,
            "error_message": error_message,
            "xmind_title": self._get_xmind_title(nodeid)  # 从YAML中获取原始标题
        }
    
    def _get_xmind_title(self, nodeid: str) -> str:
        """
        从YAML文件中获取xmind_title
        
        参数：
        - nodeid: 测试用例的nodeid
        
        返回：
        - str: xmind_title，如果找不到则返回nodeid
        """
        try:
            # 从nodeid解析文件路径和测试函数名
            # 格式：tests/test_login.py::TestLogin::test_valid_user
            parts = nodeid.split("::")
            if len(parts) < 2:
                return nodeid
            
            test_file = parts[0]  # tests/test_login.py
            test_func = parts[-1]  # test_valid_user
            
            # 查找对应的YAML文件
            # 测试文件路径：tests/test_login.py -> testcases/yaml/login_test.yaml
            yaml_file = self._find_yaml_file(test_file, test_func)
            
            if not yaml_file or not os.path.exists(yaml_file):
                # 如果找不到YAML，返回nodeid作为fallback
                return test_func
            
            # 从缓存或文件加载YAML
            if yaml_file not in self.yaml_cache:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    self.yaml_cache[yaml_file] = yaml.safe_load(f)
            
            yaml_data = self.yaml_cache[yaml_file]
            
            # 查找对应的测试用例（通过函数名匹配）
            xmind_title = self._extract_xmind_title_from_yaml(yaml_data, test_func)
            
            return xmind_title or test_func
            
        except Exception as e:
            logger.debug(f"获取xmind_title失败（nodeid: {nodeid}）: {str(e)}")
            return nodeid.split("::")[-1]  # 返回函数名
    
    def _find_yaml_file(self, test_file: str, test_func: str) -> Optional[str]:
        """
        查找对应的YAML文件
        
        参数：
        - test_file: 测试文件路径（如 tests/test_login.py）
        - test_func: 测试函数名（如 test_valid_user）
        
        返回：
        - Optional[str]: YAML文件路径，如果找不到返回None
        """
        try:
            # 方法1：从测试文件路径推断YAML文件名
            # tests/test_login.py -> testcases/yaml/login_test.yaml 或 testcases/yaml/test_login.yaml
            test_file_basename = Path(test_file).stem  # test_login
            test_file_name = Path(test_file).name  # test_login.py
            
            # 可能的YAML文件名模式
            possible_names = [
                f"{test_file_basename}.yaml",
                f"{test_file_basename}.yml",
                test_file_name.replace(".py", ".yaml"),
                test_file_name.replace(".py", ".yml"),
                # 去掉test_前缀
                test_file_basename.replace("test_", "") + ".yaml",
                test_file_basename.replace("test_", "") + ".yml",
            ]
            
            yaml_dir = Path("testcases/yaml")
            for name in possible_names:
                yaml_path = yaml_dir / name
                if yaml_path.exists():
                    return str(yaml_path)
            
            # 方法2：搜索所有YAML文件，检查是否包含该测试函数名
            if yaml_dir.exists():
                for yaml_file in yaml_dir.glob("*.yaml"):
                    try:
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            yaml_data = yaml.safe_load(f)
                            if self._yaml_contains_test(yaml_data, test_func):
                                return str(yaml_file)
                    except Exception:
                        continue
                
                for yaml_file in yaml_dir.glob("*.yml"):
                    try:
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            yaml_data = yaml.safe_load(f)
                            if self._yaml_contains_test(yaml_data, test_func):
                                return str(yaml_file)
                    except Exception:
                        continue
            
            return None
            
        except Exception as e:
            logger.debug(f"查找YAML文件失败: {str(e)}")
            return None
    
    def _yaml_contains_test(self, yaml_data: Dict, test_func: str) -> bool:
        """检查YAML是否包含指定的测试用例"""
        if not yaml_data:
            return False
        
        # 递归搜索test_modules
        def search_in_module(module):
            if not isinstance(module, dict):
                return False
            
            if module.get("type") == "test_case":
                case_name = module.get("name", "")
                # 检查用例名是否匹配（忽略大小写和特殊字符）
                normalized_case_name = case_name.lower().replace(" ", "_").replace("-", "_")
                normalized_test_func = test_func.lower().replace("test_", "")
                if normalized_test_func in normalized_case_name or normalized_case_name in normalized_test_func:
                    return True
            
            # 递归搜索子模块
            for test_case in module.get("test_cases", []):
                if search_in_module(test_case):
                    return True
            
            return False
        
        for module in yaml_data.get("test_modules", []):
            if search_in_module(module):
                return True
        
        return False
    
    def _extract_xmind_title_from_yaml(self, yaml_data: Dict, test_func: str) -> Optional[str]:
        """
        从YAML数据中提取xmind_title
        
        参数：
        - yaml_data: YAML文件内容
        - test_func: 测试函数名（如 "test_normal_login"）
        
        返回：
        - Optional[str]: xmind_title，如果找不到返回None
        """
        import re
        
        def normalize_for_match(text: str) -> str:
            """标准化文本用于匹配"""
            text = text.lower().replace("test_", "")
            # 移除所有非字母数字和中文字符
            text = re.sub(r'[^\w\u4e00-\u9fa5]', '', text)
            return text
        
        normalized_test_func = normalize_for_match(test_func)
        
        # 收集所有用例及其匹配分数
        candidates = []
        
        def collect_cases(module):
            """递归收集所有测试用例"""
            if not isinstance(module, dict):
                return
            
            if module.get("type") == "test_case":
                case_name = module.get("name", "")
                xmind_title = module.get("xmind_title") or case_name
                normalized_case_name = normalize_for_match(case_name)
                
                # 计算匹配分数
                score = 0.0
                
                # 1. 完全匹配（最高分）
                if normalized_test_func == normalized_case_name:
                    score = 1.0
                # 2. 包含匹配
                elif normalized_test_func and normalized_case_name:
                    # 提取中文词和英文单词
                    case_words = set(re.findall(r'[\u4e00-\u9fa5]|[a-z]{2,}', normalized_case_name))
                    func_words = set(re.findall(r'[\u4e00-\u9fa5]|[a-z]{2,}', normalized_test_func))
                    
                    if case_words and func_words:
                        # 计算共同词汇比例
                        common = case_words & func_words
                        if common:
                            score = len(common) / max(len(case_words), len(func_words))
                    
                    # 如果test_func完全包含case_name（或反之），给予高分
                    if normalized_case_name in normalized_test_func:
                        score = max(score, 0.8)
                    elif normalized_test_func in normalized_case_name:
                        score = max(score, 0.7)
                
                candidates.append((score, xmind_title, case_name))
            
            # 递归搜索子模块
            for test_case in module.get("test_cases", []):
                collect_cases(test_case)
        
        # 收集所有用例
        for module in yaml_data.get("test_modules", []):
            collect_cases(module)
        
        if not candidates:
            return None
        
        # 按分数排序，返回得分最高的
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_title, best_name = candidates[0]
        
        # 如果得分>0.3，认为找到了匹配
        if best_score > 0.3:
            logger.debug(f"找到匹配（分数: {best_score:.2f}）: {best_title} (函数名: {test_func})")
            return best_title
        else:
            # 得分太低，返回None（将使用nodeid作为fallback）
            logger.debug(f"未找到匹配（最高分: {best_score:.2f}）: {test_func}")
            return None
    
    def generate_markdown(self) -> str:
        """
        生成Markdown格式的报告
        
        返回：
        - str: Markdown内容
        """
        if not self.test_results:
            return "# 自动化测试执行报告\n\n未执行任何测试用例。\n"
        
        # 统计信息
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results.values() if r["outcome"] == "passed")
        failed = sum(1 for r in self.test_results.values() if r["outcome"] == "failed")
        skipped = sum(1 for r in self.test_results.values() if r["outcome"] == "skipped")
        
        # 生成报告
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        markdown_lines = [
            f"# 自动化测试执行报告 - {current_time}",
            "",
            "##  执行统计",
            "",
            f"- **总用例数**: {total}",
            f"- **通过**: {passed} ",
            f"- **失败**: {failed} ",
            f"- **跳过**: {skipped} ",
            f"- **通过率**: {(passed/total*100):.1f}%" if total > 0 else "0%",
            "",
            "---",
            "",
            "##  详细结果",
            ""
        ]
        
        # 按模块分组（从nodeid推断）
        modules = self._group_by_module()
        
        # 按模块生成报告
        for module_name, test_list in sorted(modules.items()):
            # 模块标题
            markdown_lines.append(f"###  {module_name}")
            markdown_lines.append("")
            
            # 测试用例列表
            for test_info in test_list:
                status_icon = "" if test_info["outcome"] == "passed" else "" if test_info["outcome"] == "failed" else ""
                test_title = test_info["xmind_title"]
                duration = test_info["duration"]
                duration_str = f"{duration:.2f}s" if duration < 60 else f"{duration/60:.1f}m"
                
                line = f"- {status_icon} {test_title} ({duration_str})"
                markdown_lines.append(line)
                
                # 如果失败，添加错误信息（缩进显示）
                if test_info["outcome"] == "failed" and test_info["error_message"]:
                    error_preview = test_info["error_message"][:100].replace("\n", " ")
                    markdown_lines.append(f"  -  错误: {error_preview}")
            
            markdown_lines.append("")
        
        return "\n".join(markdown_lines)
    
    def _group_by_module(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        按模块分组测试用例
        
        返回：
        - Dict[str, List[Dict]]: 模块名 -> 测试用例列表
        """
        modules = defaultdict(list)
        
        for nodeid, result in self.test_results.items():
            # 从nodeid推断模块名
            # 格式：tests/test_login.py::TestLogin::test_valid_user
            parts = nodeid.split("::")
            if len(parts) >= 1:
                # 使用文件名作为模块名（去掉tests/前缀和.py后缀）
                module_name = Path(parts[0]).stem  # test_login
                module_name = module_name.replace("test_", "").replace("_", " ").title()  # Login
                
                modules[module_name].append(result)
            else:
                modules["其他"].append(result)
        
        return dict(modules)
    
    def save_to_file(self):
        """保存Markdown报告到文件"""
        try:
            markdown_content = self.generate_markdown()
            
            # 保证输出目录存在
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f" 测试执行报告已生成: {self.output_file}")
            logger.info(f"   总用例数: {len(self.test_results)}")
            
        except Exception as e:
            logger.error(f"生成Markdown报告失败: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())


# 全局导出器实例
_exporter_instance: Optional[TestResultExporter] = None


def get_exporter() -> TestResultExporter:
    """获取导出器实例（单例模式）"""
    global _exporter_instance
    if _exporter_instance is None:
        # 从环境变量或会话信息获取输出路径
        from utils.test_session_manager import get_session_info
        session_info = get_session_info()
        
        if session_info:
            report_dir = session_info.get("report_dir", "reports")
            output_file = os.path.join(report_dir, "test_results.md")
        else:
            output_file = "test_results.md"
        
        _exporter_instance = TestResultExporter(output_file)
    return _exporter_instance

