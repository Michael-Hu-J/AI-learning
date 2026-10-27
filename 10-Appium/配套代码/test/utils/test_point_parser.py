# test_point_parser.py - 测试点智能解析器
"""
测试点智能解析器
功能：从测试点标题中自动解析出操作步骤和预期结果

支持格式：
- "输入XXX能通过校验" -> 输入操作 + 预期：通过校验
- "输入XXX显示YYY错误提示" -> 输入操作 + 预期：显示错误提示
- "点击XXX按钮正常跳转" -> 点击操作 + 预期：跳转成功
"""
import re
from typing import Dict, List, Any, Optional
from utils.logger import Logger

logger = Logger().get_logger()


class TestPointParser:
    """测试点解析器"""
    
    # 操作关键词映射
    ACTION_KEYWORDS = {
        "输入": "input",
        "点击": "click",
        "滑动": "swipe",
        "验证": "verify",
        "检查": "check",
        "选择": "select",
        "提交": "submit",
        "清除": "clear",
        "获取": "get",
    }
    
    # 预期结果关键词
    EXPECTED_KEYWORDS = {
        "通过": "通过校验",
        "失败": "验证失败",
        "显示": "显示提示",
        "跳转": "跳转成功",
        "阻止": "操作被阻止",
        "允许": "操作允许",
        "正常": "正常",
        "正确": "正确",
        "错误": "错误",
    }
    
    @staticmethod
    def parse_test_point(test_point_title: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        解析测试点标题，生成基础的steps和expected
        
        参数：
        - test_point_title: 测试点标题
        - context: 上下文信息（如父级模块名称，用于推断元素）
        
        返回：
        - Dict: 包含steps和expected的字典
        """
        title = test_point_title.strip()
        if not title:
            return {"steps": [], "expected": {}}
        
        # 尝试解析操作和预期
        steps = TestPointParser._extract_steps(title, context)
        expected = TestPointParser._extract_expected(title)
        
        return {
            "steps": steps,
            "expected": expected,
            "test_type": TestPointParser._infer_test_type(title, steps)
        }
    
    @staticmethod
    def _extract_steps(title: str, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        从标题中提取操作步骤
        
        示例：
        - "输入有效邮箱格式（如user@example.com）能通过校验" 
          -> [{"action": "输入", "element": "邮箱输入框", "value": "user@example.com"}]
        """
        steps = []
        
        # 从上下文推断元素（如父级模块名）
        element_name = None
        if context:
            module_name = context.get("module_name", "")
            # 从模块名提取元素名（如"邮箱输入框" -> "邮箱输入框"）
            if "输入框" in module_name or "框" in module_name:
                element_name = module_name
            elif "按钮" in module_name:
                element_name = module_name
        
        # 优先匹配登录流程的"点击登录，在输入框输入邮箱"模式
        login_email_input = re.search(r'点击\s*(?:登录|去登录)[，,]\s*在输入框输入邮箱(.+?)(，|$)', title)
        if login_email_input:
            email_value = login_email_input.group(1).strip()
            if email_value and '@' in email_value:
                email_val = email_value
            else:
                email_val = "{generate_email}"

            steps.append({
                "action": "点击",
                "element": "登录按钮"
            })
            steps.append({
                "action": "输入",
                "element": "邮箱输入框",
                "value": email_val
            })
            if "点击continue" in title or "点击继续" in title or "continue" in title.lower():
                steps.append({
                    "action": "点击",
                    "element": "继续按钮"
                })
            return steps

        # 匹配登录流程的"点击登录，底部点击手机号登录"
        login_phone_click = re.search(r'点击\s*(?:登录|去登录)[，,]\s*底部点击\s*(?:手机号登录|手机登录)', title)
        if login_phone_click:
            steps.append({
                "action": "点击",
                "element": "登录按钮"
            })
            steps.append({
                "action": "点击",
                "element": "手机号登录"
            })
            return steps

        # 匹配登录流程的"进入密码验证页面，输入XXX，点击下一步"
        verify_password_match = re.search(r'进入(?:密码验证|验证密码)\s*页面[，,]\s*输入(.+?)[，,]\s*点击(?:下一步|next)', title, re.IGNORECASE)
        if verify_password_match:
            password_value = verify_password_match.group(1).strip()
            steps.append({
                "action": "输入",
                "element": "密码输入框",
                "value": password_value
            })
            steps.append({
                "action": "点击",
                "element": "下一步"
            })
            return steps

        # 优先匹配复杂操作序列（如"点击注册 进入注册页面，输入邮箱"）
        # 必须在所有其他匹配之前，保证点击操作优先被识别
        complex_click_input = re.search(r'点击(.+?)(进入|到|页面)[，,](.*)', title)
        if complex_click_input:
            click_element = complex_click_input.group(1).strip()
            rest_desc = complex_click_input.group(3).strip()
            
            # 第一步：点击（提取按钮名称，如"注册"）
            words = click_element.split()
            if len(words) >= 2:
                button_name = " ".join(words[:2])
            elif len(words) == 1:
                button_name = words[0]
            else:
                button_name = click_element
            
            steps.append({
                "action": "点击",
                "element": button_name or (element_name or "按钮")
            })
            
            # 解析后续操作
            # 匹配"输入Email"（支持各种描述，如"输入符合格式的Email"）
            if "Email" in rest_desc and "输入" in rest_desc:
                # 检查是否有长度限制
                length_match = re.search(r'(\d+)\s*字符', rest_desc)
                email_value = "{generate_email}"
                steps.append({
                    "action": "输入",
                    "element": "Email输入框",
                    "value": email_value
                })
            
            # 匹配"Referral code 不输入"（跳过，不需要操作）
            
            # 检查是否有勾选框操作
            checkbox_match = re.search(r'(\d+)个勾选框均勾选', rest_desc)
            if checkbox_match:
                count = int(checkbox_match.group(1))
                for i in range(count):
                    steps.append({
                        "action": "点击",
                        "element": f"勾选框{i+1}"
                    })
            
            # 匹配"点击continue"
            if "点击continue" in rest_desc or "点击继续" in rest_desc or "continue" in rest_desc.lower():
                steps.append({
                    "action": "点击",
                    "element": "Continue"
                })
            
            return steps  # 直接返回，不再继续其他匹配
        
        # 首先尝试提取示例值（括号中的内容，优先级最高）
        example_match = re.search(r'（如(.+?)）', title)
        if example_match:
            value = example_match.group(1).strip()
            steps.append({
                "action": "输入",
                "element": element_name or "输入框",
                "value": value
            })
            return steps
        
        # 匹配输入操作 - 改进的匹配模式
        # 匹配数字+单位（如254个字符）
        length_match = re.search(r'输入(\d+)(个)?(字符|长度)', title)
        if length_match:
            num = length_match.group(1)
            # 生成对应长度的测试数据（根据上下文决定，这里先用占位符）
            steps.append({
                "action": "输入",
                "element": element_name or "输入框",
                "value": f"生成{num}个字符的测试数据",
                "length": int(num)
            })
            return steps
        
        # 匹配具体格式（如"有效邮箱格式"）
        format_match = re.search(r'输入(.+?格式)', title)
        if format_match:
            format_desc = format_match.group(1)
            # 根据格式描述生成测试数据
            if "邮箱" in format_desc or "email" in format_desc.lower():
                value = "user@example.com"
            elif "手机" in format_desc or "phone" in format_desc.lower():
                value = "13800138000"
            else:
                value = f"有效的{format_desc}"
            steps.append({
                "action": "输入",
                "element": element_name or "输入框",
                "value": value
            })
            return steps
        
        # 匹配移除/清除操作（需要先输入后清除，优先级高于通用输入）
        remove_match = re.search(r'输入后移除内容|输入后清除', title)
        if remove_match:
            # 这是一个两步骤操作：先输入，再清除
            steps.append({
                "action": "输入",
                "element": element_name or "输入框",
                "value": "测试内容"
            })
            steps.append({
                "action": "清除",
                "element": element_name or "输入框"
            })
            return steps
        
        # 匹配通用输入模式（放在移除操作之后）
        input_patterns = [
            r'输入(.+?)(能|会|显示|提示|通过|阻止|正常)',  # 输入XXX能/会/显示/提示
            r'输入(.+?)(字符|长度)',  # 输入XXX字符/长度
        ]
        
        for pattern in input_patterns:
            match = re.search(pattern, title)
            if match:
                value_part = match.group(1).strip()
                # 提取引号或括号中的具体值
                quoted_match = re.search(r'["""](.+?)["""]', value_part)
                if quoted_match:
                    value = quoted_match.group(1)
                else:
                    value = value_part
                
                steps.append({
                    "action": "输入",
                    "element": element_name or "输入框",
                    "value": value if value else "测试数据"
                })
                break
        
        # 匹配点击操作
        click_patterns = [
            r'点击(.+?)(按钮|链接|选项)',
            r'点击(.+?)(正常|跳转|显示)',
        ]
        
        for pattern in click_patterns:
            match = re.search(pattern, title)
            if match:
                click_element = match.group(1).strip()
                steps.append({
                    "action": "点击",
                    "element": click_element or (element_name or "按钮")
                })
                break
        
        
        # 匹配验证码页面输入（如"进入验证码页面,enter code 输入当前时间的验证码"）
        otp_page_match = re.search(r'进入验证码页面[，,].*?输入.*?验证码', title)
        if otp_page_match:
            # 提取验证码规则（如"当前时间的验证码，如 当前时间是15：10，验证码输入 1515"）
            time_rule_match = re.search(r'当前时间是(\d+)[：:](.+?)，验证码输入\s*(\d+)', title)
            if time_rule_match:
                # 使用动态生成
                steps.append({
                    "action": "输入",
                    "element": "验证码输入框",
                    "value": "{generate_otp_code}"
                })
            else:
                steps.append({
                    "action": "输入",
                    "element": "验证码输入框",
                    "value": "{generate_otp_code}"
                })
        
        # 匹配密码输入（包含密码生成规则）- 需要更精确的匹配，避免被之前的匹配干扰
        password_match = re.search(r'(?:your password.*?输入|输入).*?(\d+)[-到](\d+)位合规密码', title)
        if password_match:
            # 检查是否已经有密码输入步骤（避免重复）
            has_password_step = any(step.get("action") == "输入" and "密码" in str(step.get("element", "")) for step in steps)
            if not has_password_step:
                min_len = int(password_match.group(1))
                max_len = int(password_match.group(2))
                steps.append({
                    "action": "输入",
                    "element": "密码输入框",
                    "value": "{generate_password}"
                })
                
                # 如果标题中有"点击continue"，添加点击步骤
                if "点击continue" in title or "点击继续" in title:
                    steps.append({
                        "action": "点击",
                        "element": "Continue"
                    })
        
        # 匹配重新输入密码
        reenter_password_match = re.search(r'把刚才输入的密码.*?重新输入', title)
        if reenter_password_match:
            # 提取默认密码
            default_pwd_match = re.search(r'默认填([^）)）]+)', title)
            if default_pwd_match:
                default_pwd = default_pwd_match.group(1).strip()
            else:
                default_pwd = "A@123456789"
            steps.append({
                "action": "输入",
                "element": "确认密码输入框",
                "value": default_pwd
            })
            # 如果标题中有"点击continue"，添加点击步骤
            if "点击continue" in title or "点击继续" in title or "continue" in title.lower():
                steps.append({
                    "action": "点击",
                    "element": "Continue"
                })
            return steps  # 返回，不再继续其他匹配
        
        # 如果没有匹配到操作，尝试通用解析
        if not steps:
            # 检查是否包含操作关键词
            for keyword, action in TestPointParser.ACTION_KEYWORDS.items():
                if keyword in title:
                    # 提取元素和值（简单方式）
                    parts = title.split(keyword, 1)
                    if len(parts) > 1:
                        rest = parts[1]
                        # 提取值（如果有引号或括号）
                        value_match = re.search(r'["""](.+?)["""]|（(.+?)）', rest)
                        value = value_match.group(1) or value_match.group(2) if value_match else None
                        
                        steps.append({
                            "action": keyword,
                            "element": element_name or "元素",
                            "value": value
                        })
                    break
        
        # 如果还是没有步骤，至少添加一个验证步骤
        if not steps:
            steps.append({
                "action": "验证",
                "element": element_name or "元素",
                "description": title
            })
        
        return steps
    
    @staticmethod
    def _extract_expected(title: str) -> Dict[str, Any]:
        """
        从标题中提取预期结果
        
        示例：
        - "能通过校验" -> {"result": "通过校验", "status": "success"}
        - "显示XXX错误提示" -> {"message": "XXX", "status": "fail"}
        """
        expected = {}
        
        # 提取错误提示信息（支持中英文引号）
        error_patterns = [
            r'显示["""'"](.+?)["""'"]',  # 显示"XXX"
            r'提示["""'"](.+?)["""'"]',  # 提示"XXX"
            r'(.+?)错误提示',
            r'(.+?)提示',
            r'应显示["""'"](.+?)["""'"]',  # 应显示"XXX"
            r'应明确提示["""'"](.+?)["""'"]',  # 应明确提示"XXX"
        ]
        
        for pattern in error_patterns:
            match = re.search(pattern, title)
            if match:
                message = match.group(1).strip()
                expected["message"] = message
                expected["status"] = "fail"
                break
        
        # 判断成功/失败（优先级：如果有错误提示，应该是fail）
        if expected.get("message"):
            # 如果有错误提示信息，说明是失败的场景
            expected["status"] = "fail"
        elif any(keyword in title for keyword in ["失败", "错误", "阻止", "不能", "不应", "显示.*错误", "显示.*提示"]):
            expected["status"] = "fail"
        elif any(keyword in title for keyword in ["通过", "正常", "正确", "成功", "能", "允许"]):
            expected["status"] = "success"
        else:
            expected["status"] = "success"  # 默认成功
        
        # 提取其他预期信息
        if "跳转" in title:
            expected["redirect"] = True
        if "阻止" in title:
            expected["blocked"] = True
        if "允许" in title:
            expected["allowed"] = True
        
        return expected
    
    @staticmethod
    def _infer_test_type(title: str, steps: List[Dict]) -> str:
        """
        推断测试类型
        
        参数：
        - title: 测试点标题
        - steps: 解析出的步骤
        
        返回：
        - str: 测试类型（ui/api/hybrid）
        """
        # 如果标题包含API相关关键词
        if any(keyword in title.lower() for keyword in ["api", "接口", "请求", "响应"]):
            return "api"
        
        # 如果步骤中包含UI操作
        ui_actions = ["输入", "点击", "滑动", "选择"]
        if any(step.get("action") in ui_actions for step in steps):
            return "ui"
        
        # 默认UI测试
        return "ui"
    
    @staticmethod
    def enhance_test_case(test_case: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        增强测试用例，添加解析出的steps和expected
        
        参数：
        - test_case: 测试用例字典
        - context: 上下文信息
        
        返回：
        - Dict: 增强后的测试用例
        """
        title = test_case.get("name", "")
        if not title:
            return test_case
        
        # 如果已经有steps和expected，且不为空，就不替换
        if test_case.get("steps") and len(test_case.get("steps", [])) > 0:
            return test_case
        if test_case.get("expected") and test_case.get("expected") != "":
            return test_case
        
        # 解析测试点
        parsed = TestPointParser.parse_test_point(title, context)
        
        # 更新测试用例
        test_case["steps"] = parsed.get("steps", [])
        test_case["expected"] = parsed.get("expected", {})
        if not test_case.get("test_type"):
            test_case["test_type"] = parsed.get("test_type", "ui")
        
        return test_case

