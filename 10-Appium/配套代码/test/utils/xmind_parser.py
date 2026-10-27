# xmind_parser.py - XMind文件解析工具
"""
XMind文件解析工具
功能：将XMind测试用例文件转换为YAML格式，方便后续执行自动化脚本
"""
import yaml
from typing import Dict, List, Any, Optional
from utils.logger import Logger
from utils.test_point_parser import TestPointParser

logger = Logger().get_logger()

try:
    import xmindparser
    XMIND_AVAILABLE = True
except ImportError:
    XMIND_AVAILABLE = False
    logger.warning("xmindparser未安装，无法解析XMind文件。请安装: pip install xmindparser")


class XMindParser:
    """
    XMind解析器
    
    功能：
    1. 读取XMind文件（支持三、四、五、六层结构）
    2. 转换为YAML格式的测试用例
    3. 保持原有的层级结构
    """
    
    def __init__(self):
        if not XMIND_AVAILABLE:
            raise ImportError("xmindparser未安装，请先安装: pip install xmindparser")
    
    def parse(self, xmind_file: str) -> Dict[str, Any]:
        """
        解析XMind文件
        
        参数：
        - xmind_file: XMind文件路径
        
        返回：
        - Dict: 解析后的测试用例结构
        """
        try:
            logger.info(f"开始解析XMind文件: {xmind_file}")
            
            # 使用xmindparser解析文件
            content = xmindparser.xmind_to_dict(xmind_file)
            
            if not content or len(content) == 0:
                logger.warning("XMind文件为空")
                return {}
            
            # 转换格式
            test_suite = self._convert_to_test_suite(content[0])
            
            logger.info(f"XMind文件解析完成，共 {self._count_test_cases(test_suite)} 个测试用例")
            return test_suite
            
        except Exception as e:
            logger.error(f"解析XMind文件失败: {str(e)}")
            raise
    
    def _convert_to_test_suite(self, root_topic: Dict) -> Dict[str, Any]:
        """
        将XMind主题转换为测试套件格式
        
        参数：
        - root_topic: XMind根主题
        
        返回：
        - Dict: 测试套件结构
        """
        suite = {
            "name": root_topic.get("title", "测试套件"),
            "description": root_topic.get("note", ""),
            "test_modules": []
        }
        
        # XMind文件结构可能是两种：
        # 1. 直接有topics字段: root_topic.get("topics", [])
        # 2. 有topic字段，里面包含topics: root_topic.get("topic", {}).get("topics", [])
        topics = []
        if "topics" in root_topic:
            topics = root_topic.get("topics", [])
        elif "topic" in root_topic:
            # 如果是新版本的XMind格式，实际内容在topic字段中
            topic = root_topic.get("topic", {})
            topics = topic.get("topics", [])
            # 如果topic有title，用它作为suite的name
            if topic.get("title") and topic.get("title") != "中心主题":
                suite["name"] = topic.get("title")
        
        # 处理子主题（支持多层嵌套）
        for topic in topics:
            module = self._convert_topic_to_module(topic, level=1, parent_context=None, max_level=20)
            if module:
                suite["test_modules"].append(module)
        
        return suite
    
    def _convert_topic_to_module(self, topic: Dict, level: int = 1, parent_context: Optional[Dict] = None, max_level: int = 20) -> Optional[Dict[str, Any]]:
        """
        将主题转换为测试模块或用例
        
        参数：
        - topic: XMind主题
        - level: 当前层级（从1开始）
        - parent_context: 父级上下文信息（用于推断元素）
        - max_level: 最大层级限制（默认20层，足够深）
        
        返回：
        - Dict: 测试模块或用例
        """
        if level > max_level:
            logger.warning(f"层级超过{max_level}层，跳过: {topic.get('title')}")
            return None
        
        title = topic.get("title", "").strip()
        if not title:
            return None
        
        # 构建当前上下文（用于子节点推断元素）
        current_context = {
            "module_name": title,
            "parent_name": parent_context.get("module_name") if parent_context else None
        }
        
        module = {
            "name": title,
            "description": topic.get("note", ""),
        }
        
        # 处理子主题
        sub_topics = topic.get("topics", [])
        if sub_topics:
            # 有子主题，作为模块
            module["type"] = "module"
            module["test_cases"] = []
            
            for sub_topic in sub_topics:
                test_case = self._convert_topic_to_module(sub_topic, level + 1, current_context, max_level)
                if test_case:
                    # 如果子主题还有子主题，继续递归
                    if "test_cases" in test_case:
                        module["test_cases"].append(test_case)
                    else:
                        # 这是真正的测试用例
                        module["test_cases"].append(test_case)
        else:
            # 没有子主题，作为测试用例
            # 强制添加 xmind_title 字段（原始XMind节点文本，用于后续报告显示）
            module["xmind_title"] = title
            
            # 检查是否为"前后端同时校验"场景
            if self._is_validation_test_case(title):
                # 生成双路径测试用例（UI + API）
                dual_path_module = self._generate_dual_path_test_case(title, topic, current_context)
                # 保证双路径用例也包含xmind_title
                dual_path_module["xmind_title"] = title
                # 为每个子用例也添加xmind_title
                for test_case in dual_path_module.get("test_cases", []):
                    test_case["xmind_title"] = title
                return dual_path_module
            else:
                # 普通用例，按原有逻辑处理
                module["type"] = "test_case"
                # 使用测试点解析器自动生成steps和expected
                from utils.test_point_parser import TestPointParser
                parsed = TestPointParser.parse_test_point(title, current_context)
                module["steps"] = parsed.get("steps", [])
                module["expected"] = parsed.get("expected", {})
                if not module.get("test_type"):
                    module["test_type"] = parsed.get("test_type", "ui")
                
                # 添加用例状态标记（默认draft，表示未最终版）
                # 可以通过检查标题中的关键词来设置状态
                title_lower = title.lower()
                if any(keyword in title_lower for keyword in ["一期不支持", "后续", "待开发", "待实现", "暂不支持"]):
                    module["status"] = "pending"  # 待开发/不支持
                elif any(keyword in title_lower for keyword in ["已完成", "已实现", "正式版"]):
                    module["status"] = "final"  # 已完成/最终版
                else:
                    module["status"] = "draft"  # 草稿/未最终版（默认）
        
        return module
    
    def _count_test_cases(self, suite: Dict) -> int:
        """
        统计测试用例数量
        
        参数：
        - suite: 测试套件
        
        返回：
        - int: 测试用例数量
        """
        count = 0
        for module in suite.get("test_modules", []):
            count += self._count_test_cases_in_module(module)
        return count
    
    def _count_test_cases_in_module(self, module: Dict) -> int:
        """
        统计模块中的测试用例数量（递归）
        
        参数：
        - module: 测试模块
        
        返回：
        - int: 测试用例数量
        """
        if module.get("type") == "test_case":
            return 1
        
        count = 0
        for test_case in module.get("test_cases", []):
            count += self._count_test_cases_in_module(test_case)
        return count
    
    def to_yaml(self, test_suite: Dict[str, Any], output_file: str):
        """
        将测试套件转换为YAML文件
        
        参数：
        - test_suite: 测试套件
        - output_file: 输出YAML文件路径
        """
        try:
            logger.info(f"开始生成YAML文件: {output_file}")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(
                    test_suite,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            
            logger.info(f"YAML文件生成成功: {output_file}")
            
        except Exception as e:
            logger.error(f"生成YAML文件失败: {str(e)}")
            raise
    
    def parse_to_yaml(self, xmind_file: str, output_yaml: str):
        """
        解析XMind文件并直接转换为YAML
        
        参数：
        - xmind_file: XMind文件路径
        - output_yaml: 输出YAML文件路径
        """
        test_suite = self.parse(xmind_file)
        self.to_yaml(test_suite, output_yaml)
    
    def parse_xmind_to_cases(self, xmind_file: str) -> List[Dict[str, Any]]:
        """
        解析XMind文件并返回用例列表（扁平化）
        
        参数：
        - xmind_file: XMind文件路径
        
        返回：
        - List[Dict]: 测试用例列表
        """
        test_suite = self.parse(xmind_file)
        cases = []
        
        # 递归提取所有测试用例
        for module in test_suite.get("test_modules", []):
            cases.extend(self._extract_cases_from_module(module))
        
        return cases
    
    def _extract_cases_from_module(self, module: Dict) -> List[Dict[str, Any]]:
        """
        从模块中提取测试用例（递归）
        
        参数：
        - module: 测试模块
        
        返回：
        - List[Dict]: 测试用例列表
        """
        cases = []
        
        if module.get("type") == "test_case":
            # 这就是一个用例
            cases.append(module)
        else:
            # 这是模块，递归提取子用例
            for test_case in module.get("test_cases", []):
                cases.extend(self._extract_cases_from_module(test_case))
        
        return cases

# 双路径校验生成方法的补充代码
# 需要添加到 xmind_parser.py 文件的 XMindParser 类中

    def _is_validation_test_case(self, title: str) -> bool:
        """
        判断是否为校验类测试用例（需要生成前后端双路径）
        
        参数：
        - title: 测试用例标题
        
        返回：
        - bool: 是否为校验类用例
        """
        if not title:
            return False
        
        title_lower = title.lower()
        
        # 排除明确指定单端的用例
        excludes = ["仅前端", "仅UI", "只前端", "只UI", "仅后端", "仅API", "只后端", "只API"]
        if any(exclude in title for exclude in excludes):
            return False
        
        # 校验类关键词（扩展关键词，包括更多校验相关的词）
        validation_keywords = ["长度", "格式", "必填", "非法", "校验", "验证", "检查", "字符", "位数", "合规", "限制", "位", "个字符"]
        
        # 检查是否包含校验类关键词
        has_validation_keyword = any(keyword in title for keyword in validation_keywords)
        
        # 如果包含校验关键词，进一步判断是否为验证用例
        if has_validation_keyword:
            # 排除一些明显不是验证的用例（如纯操作性的用例）
            action_only_keywords = ["点击", "选择", "滑动", "打开", "关闭"]
            # 如果只包含动作关键词，不包含校验相关内容，则不是验证用例
            has_action_only = any(kw in title for kw in action_only_keywords)
            if has_action_only and not any(kw in ["校验", "验证", "检查", "长度", "格式", "必填", "非法", "字符", "位数"] for kw in title):
                return False
            
            # 包含校验关键词，就认为是验证测试用例（不需要同时包含限制类关键词）
            # 这样可以识别更多校验用例，如"输入254个字符长度"、"密码8-32位"等
            return True
        
        # 没有校验关键词，不是验证用例
        return False
    
    def _generate_dual_path_test_case(self, title: str, topic: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """
        生成前后端双路径测试用例
        
        参数：
        - title: 测试用例标题
        - topic: XMind主题节点
        - context: 上下文信息
        
        返回：
        - Dict: 包含两个测试用例的模块结构
        """
        from utils.test_point_parser import TestPointParser
        
        # 解析原始测试点
        parsed = TestPointParser.parse_test_point(title, context)
        
        # 创建模块容器（包含两个测试用例）
        module = {
            "name": title,
            "description": topic.get("note", ""),
            "type": "module",
            "test_cases": []
        }
        
        # 生成UI路径测试用例
        ui_case = self._generate_ui_path_case(title, parsed, context)
        module["test_cases"].append(ui_case)
        
        # 生成API路径测试用例
        api_case = self._generate_api_path_case(title, parsed, context)
        module["test_cases"].append(api_case)
        
        logger.info(f"生成双路径测试用例: {title} (UI + API)")
        
        return module
    
    def _generate_ui_path_case(self, title: str, parsed: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """
        生成前端/UI路径测试用例
        
        参数：
        - title: 原始测试用例标题
        - parsed: 解析后的测试点数据
        - context: 上下文信息
        
        返回：
        - Dict: UI路径测试用例
        """
        # 生成UI用例描述（保留原始描述，或加上"前端交互"字样）
        ui_description = title
        if "前端" not in title and "UI" not in title:
            ui_description = f"{title}（前端交互）"
        
        # 复制原始步骤，调整为UI操作
        ui_steps = []
        for step in parsed.get("steps", []):
            ui_step = step.copy()
            # 保证是UI操作
            if step.get("action") in ["输入", "点击", "滑动", "选择", "清除"]:
                ui_steps.append(ui_step)
            else:
                # 如果是其他操作，转换为UI操作
                ui_step["action"] = "输入"  # 默认转换为输入
                ui_steps.append(ui_step)
        
        # 如果没有步骤，添加一个输入步骤
        if not ui_steps:
            element_name = "输入框"
            if context:
                module_name = context.get("module_name", "")
                if "输入框" in module_name or "框" in module_name:
                    element_name = module_name
            
            ui_steps.append({
                "action": "输入",
                "element": element_name,
                "value": "{generate_invalid_value}",  # 使用占位符，后续会生成
                "description": f"输入违规数据以触发前端校验"
            })
        
        # 生成UI用例的预期结果（前端提示）
        ui_expected = parsed.get("expected", {}).copy()
        if "message" not in ui_expected:
            # 如果没有明确的消息，添加默认的前端提示预期
            ui_expected["ui_validation"] = True
            ui_expected["frontend_prompt"] = "显示前端提示/弹窗"
        
        ui_case = {
            "name": ui_description,
            "description": f"前端UI交互验证：{title}",
            "type": "test_case",
            "test_type": "ui",
            "status": "draft",
            "steps": ui_steps,
            "expected": ui_expected
        }
        
        return ui_case
    
    def _generate_api_path_case(self, title: str, parsed: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """
        生成后端/API路径测试用例
        
        参数：
        - title: 原始测试用例标题
        - parsed: 解析后的测试点数据
        - context: 上下文信息
        
        返回：
        - Dict: API路径测试用例
        """
        # 生成API用例描述（加上"后端兜底"或"绕过前端"）
        api_description = title
        if "后端" not in title and "API" not in title:
            api_description = f"{title}（后端兜底）"
        
        # 从原始步骤中提取参数信息
        invalid_value = None
        for step in parsed.get("steps", []):
            if step.get("action") == "输入" and step.get("value"):
                invalid_value = step.get("value")
                break
        
        # 如果没有找到值，生成一个违规值的占位符
        if not invalid_value:
            invalid_value = "{generate_invalid_value}"
        
        # 生成API步骤（构造异常参数直接调用接口）
        api_steps = []
        
        # 推断接口端点（从上下文或标题）
        endpoint = "/api/validate"  # 默认端点，实际应该根据业务逻辑推断
        if context:
            module_name = context.get("module_name", "").lower()
            # 根据模块名推断接口（这里需要根据实际业务调整）
            if "注册" in module_name or "register" in module_name:
                endpoint = "/api/auth/register/step1"
            elif "登录" in module_name or "login" in module_name:
                endpoint = "/api/auth/login"
            elif "修改" in module_name or "update" in module_name:
                endpoint = "/api/user/update"
        
        # 构造请求体（根据上下文推断字段名）
        field_name = "value"  # 默认字段名
        if context:
            module_name = context.get("module_name", "")
            # 从模块名提取字段名（如"手机号输入框" -> "mobile"）
            if "手机" in module_name or "mobile" in module_name.lower():
                field_name = "mobile"
            elif "邮箱" in module_name or "email" in module_name.lower():
                field_name = "email"
            elif "密码" in module_name or "password" in module_name.lower():
                field_name = "password"
        
        # 生成POST请求步骤
        api_steps.append({
            "action": "POST请求",
            "endpoint": endpoint,
            "method": "POST",
            "headers": {
                "x-user-agent": "{{x-user-agent}}"
            },
            "body": {
                field_name: invalid_value,
                "description": f"构造异常参数直接调用接口，绕过前端校验"
            }
        })
        
        # 生成API用例的预期结果（接口返回错误码）
        api_expected = parsed.get("expected", {}).copy()
        api_expected["status_code"] = 400  # 默认400错误
        api_expected["error_code"] = "VALIDATION_ERROR"  # 默认错误码
        api_expected["backend_validation"] = True
        
        # 从原始预期中提取错误消息
        if "message" in api_expected:
            api_expected["error_message"] = api_expected["message"]
        
        api_case = {
            "name": api_description,
            "description": f"后端API兜底验证：{title}，绕过前端直接调用接口",
            "type": "test_case",
            "test_type": "api",
            "status": "draft",
            "steps": api_steps,
            "expected": api_expected
        }
        
        return api_case

