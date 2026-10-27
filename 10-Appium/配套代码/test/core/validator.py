# validator.py - 测试结果验证器
"""
测试结果验证器
功能：提供详细的验证逻辑，包括字段值验证、文本内容验证等
"""
import re
from typing import Dict, Any, Optional, List
from utils.logger import Logger

logger = Logger().get_logger()


class Validator:
    """
    测试结果验证器
    
    功能：
    1. API响应验证（字段值、状态码、内容等）
    2. UI元素验证（文本内容、属性值、存在性等）
    3. 复杂断言表达式
    """
    
    @staticmethod
    def validate_api_response(response_data: Any, expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证API响应
        
        参数：
        - response_data: 响应数据（dict或str）
        - expected: 预期结果字典，支持以下格式：
            {
                "status_code": 200,  # 状态码
                "contains": "success",  # 包含文本
                "fields": {  # 字段验证
                    "code": 0,  # 精确匹配
                    "message": {"contains": "成功"},  # 包含匹配
                    "data.id": {"exists": True},  # 字段存在
                    "data.count": {"gt": 0},  # 大于
                    "data.count": {"gte": 1},  # 大于等于
                    "data.count": {"lt": 100},  # 小于
                    "data.count": {"lte": 50},  # 小于等于
                    "data.name": {"regex": "^test.*"}  # 正则匹配
                }
            }
        
        返回：
        - (bool, str): (是否通过, 错误信息)
        """
        try:
            # 如果是字符串，尝试解析为JSON
            if isinstance(response_data, str):
                try:
                    import json
                    response_data = json.loads(response_data)
                except:
                    pass  # 保持为字符串
            
            # 验证状态码
            if "status_code" in expected:
                status_code = response_data.get("status_code") if isinstance(response_data, dict) else None
                if status_code != expected["status_code"]:
                    return False, f"状态码不匹配: 期望 {expected['status_code']}, 实际 {status_code}"
            
            # 获取实际响应数据（如果response_data是包含status_code的字典，提取data）
            actual_data = response_data
            if isinstance(response_data, dict) and "response" in response_data:
                actual_data = response_data["response"]
            
            # 验证包含文本
            if "contains" in expected:
                expected_text = str(expected["contains"]).lower()
                actual_text = str(actual_data).lower()
                if expected_text not in actual_text:
                    return False, f"响应中不包含预期文本: {expected['contains']}"
            
            # 验证字段
            if "fields" in expected and isinstance(actual_data, dict):
                fields = expected["fields"]
                for field_path, field_expected in fields.items():
                    # 支持嵌套字段，如 "data.id"
                    field_value = Validator._get_nested_field(actual_data, field_path)
                    
                    # 验证字段
                    is_valid, error_msg = Validator._validate_field(field_value, field_expected, field_path)
                    if not is_valid:
                        return False, error_msg
            
            return True, "验证通过"
            
        except Exception as e:
            logger.error(f"验证API响应时出错: {str(e)}")
            return False, f"验证失败: {str(e)}"
    
    @staticmethod
    def _get_nested_field(data: Dict, field_path: str) -> Any:
        """
        获取嵌套字段值
        
        参数：
        - data: 数据字典
        - field_path: 字段路径，如 "data.id" 或 "data.items[0].name"
        
        返回：
        - 字段值
        """
        keys = field_path.split(".")
        value = data
        
        for key in keys:
            # 处理数组索引，如 items[0]
            if "[" in key and "]" in key:
                array_key = key[:key.index("[")]
                index = int(key[key.index("[")+1:key.index("]")])
                value = value.get(array_key, [])
                if isinstance(value, list) and 0 <= index < len(value):
                    value = value[index]
                else:
                    return None
            else:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            
            if value is None:
                return None
        
        return value
    
    @staticmethod
    def _validate_field(actual_value: Any, expected: Any, field_path: str) -> tuple[bool, str]:
        """
        验证单个字段
        
        参数：
        - actual_value: 实际值
        - expected: 预期值或验证规则
        - field_path: 字段路径（用于错误信息）
        
        返回：
        - (bool, str): (是否通过, 错误信息)
        """
        # 如果是字典，说明是验证规则
        if isinstance(expected, dict):
            # 存在性验证
            if "exists" in expected:
                should_exist = expected["exists"]
                actually_exists = actual_value is not None
                if should_exist != actually_exists:
                    return False, f"字段 {field_path} 存在性不匹配: 期望 {'存在' if should_exist else '不存在'}, 实际 {'存在' if actually_exists else '不存在'}"
                return True, ""
            
            # 如果字段不存在且期望存在，返回失败
            if actual_value is None:
                return False, f"字段 {field_path} 不存在"
            
            # 包含验证
            if "contains" in expected:
                expected_text = str(expected["contains"]).lower()
                actual_text = str(actual_value).lower()
                if expected_text not in actual_text:
                    return False, f"字段 {field_path} 不包含预期文本: {expected['contains']}, 实际值: {actual_value}"
            
            # 大于
            if "gt" in expected:
                try:
                    if float(actual_value) <= float(expected["gt"]):
                        return False, f"字段 {field_path} 不大于 {expected['gt']}, 实际值: {actual_value}"
                except (ValueError, TypeError):
                    return False, f"字段 {field_path} 无法比较大小, 实际值: {actual_value}"
            
            # 大于等于
            if "gte" in expected:
                try:
                    if float(actual_value) < float(expected["gte"]):
                        return False, f"字段 {field_path} 小于 {expected['gte']}, 实际值: {actual_value}"
                except (ValueError, TypeError):
                    return False, f"字段 {field_path} 无法比较大小, 实际值: {actual_value}"
            
            # 小于
            if "lt" in expected:
                try:
                    if float(actual_value) >= float(expected["lt"]):
                        return False, f"字段 {field_path} 不小于 {expected['lt']}, 实际值: {actual_value}"
                except (ValueError, TypeError):
                    return False, f"字段 {field_path} 无法比较大小, 实际值: {actual_value}"
            
            # 小于等于
            if "lte" in expected:
                try:
                    if float(actual_value) > float(expected["lte"]):
                        return False, f"字段 {field_path} 大于 {expected['lte']}, 实际值: {actual_value}"
                except (ValueError, TypeError):
                    return False, f"字段 {field_path} 无法比较大小, 实际值: {actual_value}"
            
            # 正则匹配
            if "regex" in expected:
                pattern = expected["regex"]
                actual_str = str(actual_value)
                if not re.match(pattern, actual_str):
                    return False, f"字段 {field_path} 不匹配正则表达式 {pattern}, 实际值: {actual_value}"
            
            # 类型验证
            if "type" in expected:
                expected_type = expected["type"]
                actual_type = type(actual_value).__name__
                if actual_type != expected_type:
                    return False, f"字段 {field_path} 类型不匹配: 期望 {expected_type}, 实际 {actual_type}"
        
        # 简单相等验证
        else:
            if actual_value != expected:
                return False, f"字段 {field_path} 值不匹配: 期望 {expected}, 实际 {actual_value}"
        
        return True, ""
    
    @staticmethod
    def validate_ui_element(driver, element_locator: Dict[str, str], expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证UI元素
        
        参数：
        - driver: Appium driver
        - element_locator: 元素定位器 {"type": "id", "value": "element_id"}
        - expected: 预期结果字典，支持以下格式：
            {
                "exists": True,  # 元素存在
                "text": "登录",  # 文本内容
                "text_contains": "登录",  # 文本包含
                "enabled": True,  # 是否启用
                "displayed": True,  # 是否显示
                "attribute": {  # 属性验证
                    "name": "value"
                }
            }
        
        返回：
        - (bool, str): (是否通过, 错误信息)
        """
        try:
            from base.base_page import BasePage
            page = BasePage(driver)
            
            locator_type = element_locator.get("type", "id")
            locator_value = element_locator.get("value", element_locator.get("id", ""))
            
            # 验证元素存在
            if "exists" in expected:
                should_exist = expected["exists"]
                try:
                    element = page.find_element(locator_type, locator_value, timeout=3)
                    actually_exists = element is not None
                except:
                    actually_exists = False
                
                if should_exist != actually_exists:
                    return False, f"元素存在性不匹配: 期望 {'存在' if should_exist else '不存在'}, 实际 {'存在' if actually_exists else '不存在'}"
                
                if not should_exist:
                    return True, ""  # 如果期望不存在且确实不存在，验证通过
            
            # 如果期望存在，获取元素
            try:
                element = page.find_element(locator_type, locator_value, timeout=5)
            except:
                return False, f"元素不存在: {locator_type}={locator_value}"
            
            # 验证文本内容
            if "text" in expected:
                actual_text = element.text
                if actual_text != expected["text"]:
                    return False, f"元素文本不匹配: 期望 '{expected['text']}', 实际 '{actual_text}'"
            
            # 验证文本包含
            if "text_contains" in expected:
                actual_text = element.text
                expected_text = expected["text_contains"]
                if expected_text not in actual_text:
                    return False, f"元素文本不包含预期内容: 期望包含 '{expected_text}', 实际文本 '{actual_text}'"
            
            # 验证是否启用
            if "enabled" in expected:
                is_enabled = element.is_enabled()
                if is_enabled != expected["enabled"]:
                    return False, f"元素启用状态不匹配: 期望 {expected['enabled']}, 实际 {is_enabled}"
            
            # 验证是否显示
            if "displayed" in expected:
                is_displayed = element.is_displayed()
                if is_displayed != expected["displayed"]:
                    return False, f"元素显示状态不匹配: 期望 {expected['displayed']}, 实际 {is_displayed}"
            
            # 验证属性
            if "attribute" in expected:
                for attr_name, attr_expected in expected["attribute"].items():
                    try:
                        attr_value = element.get_attribute(attr_name)
                        if attr_value != attr_expected:
                            return False, f"元素属性 {attr_name} 不匹配: 期望 '{attr_expected}', 实际 '{attr_value}'"
                    except:
                        return False, f"无法获取元素属性 {attr_name}"
            
            return True, "验证通过"
            
        except Exception as e:
            logger.error(f"验证UI元素时出错: {str(e)}")
            return False, f"验证失败: {str(e)}"
    
    @staticmethod
    def parse_expected(expected: Any) -> Dict[str, Any]:
        """
        解析预期结果（支持多种格式）
        
        参数：
        - expected: 预期结果，可以是字符串或字典
        
        返回：
        - Dict: 解析后的预期结果字典
        """
        if isinstance(expected, dict):
            return expected
        elif isinstance(expected, str):
            # 简单字符串，转换为包含验证
            return {"contains": expected}
        else:
            return {"equals": expected}

