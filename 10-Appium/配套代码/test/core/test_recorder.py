# test_recorder.py - 测试用例录制器
"""
测试用例录制器
功能：在手动操作过程中自动识别接口和UI操作，生成可执行的测试用例
"""
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import Logger

logger = Logger().get_logger()


class TestRecorder:
    """
    测试用例录制器
    
    功能：
    1. 记录UI操作（点击、输入、滑动等）
    2. 记录API请求（通过抓包或监控）
    3. 智能识别操作类型（API/UI）
    4. 生成YAML格式的测试用例
    """
    
    def __init__(self, test_case_name: str = "录制的测试用例"):
        """
        初始化录制器
        
        参数：
        - test_case_name: 测试用例名称
        """
        self.test_case_name = test_case_name
        self.ui_actions: List[Dict[str, Any]] = []
        self.api_requests: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.is_recording = False
    
    def start_recording(self):
        """开始录制"""
        self.is_recording = True
        self.ui_actions.clear()
        self.api_requests.clear()
        self.start_time = datetime.now()
        logger.info(f"开始录制测试用例: {self.test_case_name}")
    
    def stop_recording(self):
        """停止录制"""
        self.is_recording = False
        logger.info(f"停止录制，共录制 {len(self.ui_actions)} 个UI操作，{len(self.api_requests)} 个API请求")
    
    def record_ui_action(self, action_type: str, element: Optional[str] = None, 
                        value: Optional[str] = None, locator_type: str = "id", **kwargs):
        """
        记录UI操作
        
        参数：
        - action_type: 操作类型（click, input, swipe, wait等）
        - element: 元素定位值
        - value: 输入的值（如果是input操作）
        - locator_type: 定位方式（id, xpath等）
        - **kwargs: 其他参数（如direction用于swipe）
        """
        if not self.is_recording:
            return
        
        action = {
            "action": action_type,
            "timestamp": datetime.now().isoformat(),
            "element": element,
            "locator_type": locator_type,
            **kwargs
        }
        
        if value is not None:
            action["value"] = value
        
        self.ui_actions.append(action)
        logger.debug(f"录制UI操作: {action_type}, element: {element}")
    
    def record_api_request(self, method: str, url: str, headers: Optional[Dict] = None,
                          params: Optional[Dict] = None, body: Optional[Any] = None,
                          response_status: Optional[int] = None, response_body: Optional[Any] = None):
        """
        记录API请求
        
        参数：
        - method: HTTP方法（GET, POST等）
        - url: 请求URL
        - headers: 请求头
        - params: URL参数
        - body: 请求体
        - response_status: 响应状态码
        - response_body: 响应体
        """
        if not self.is_recording:
            return
        
        # 提取endpoint（去掉base_url）
        endpoint = url.split("?")[0]  # 去掉查询参数
        
        request = {
            "method": method.upper(),
            "url": url,
            "endpoint": endpoint,
            "headers": headers or {},
            "params": params,
            "body": body,
            "response_status": response_status,
            "response_body": response_body,
            "timestamp": datetime.now().isoformat()
        }
        
        self.api_requests.append(request)
        logger.debug(f"录制API请求: {method} {endpoint}")
    
    def generate_test_case(self, test_type: Optional[str] = None) -> Dict[str, Any]:
        """
        生成测试用例
        
        参数：
        - test_type: 测试类型（api, ui, hybrid），如果为None则自动判断
        
        返回：
        - Dict: 测试用例字典
        """
        # 如果没有指定类型，自动判断
        if test_type is None:
            if self.api_requests and not self.ui_actions:
                test_type = "api"
            elif self.ui_actions and not self.api_requests:
                test_type = "ui"
            elif self.api_requests and self.ui_actions:
                test_type = "hybrid"
            else:
                test_type = "ui"  # 默认
        
        test_case = {
            "name": self.test_case_name,
            "type": "test_case",
            "description": f"自动录制的测试用例，录制时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            "test_type": test_type,
            "steps": []
        }
        
        # 生成步骤
        if test_type == "api" or test_type == "hybrid":
            # API步骤
            for req in self.api_requests:
                step = {
                    "action": f"发送{req['method']}请求",
                    "endpoint": req["endpoint"],
                    "method": req["method"]
                }
                
                if req.get("params"):
                    step["params"] = req["params"]
                
                if req.get("body"):
                    step["body"] = req["body"]
                
                test_case["steps"].append(step)
        
        if test_type == "ui" or test_type == "hybrid":
            # UI步骤
            for action in self.ui_actions:
                step = {}
                
                action_type = action.get("action", "")
                
                if action_type == "click":
                    step = {
                        "action": "点击",
                        "element": action.get("element")
                    }
                elif action_type == "input":
                    step = {
                        "action": "输入",
                        "element": action.get("element"),
                        "value": action.get("value")
                    }
                elif action_type == "swipe":
                    step = {
                        "action": "滑动",
                        "direction": action.get("direction", "down")
                    }
                elif action_type == "wait":
                    step = {
                        "action": "等待",
                        "seconds": action.get("seconds", 1)
                    }
                
                if step:
                    test_case["steps"].append(step)
        
        # 添加预期结果（基于最后一个操作的响应）
        if self.api_requests:
            last_response = self.api_requests[-1]
            if last_response.get("response_status"):
                test_case["expected"] = {
                    "status_code": last_response["response_status"]
                }
        
        return test_case
    
    def generate_yaml(self, output_file: str):
        """
        生成YAML格式的测试用例文件
        
        参数：
        - output_file: 输出文件路径
        """
        import yaml
        import os
        
        test_case = self.generate_test_case()
        
        # 创建测试套件格式
        test_suite = {
            "name": "录制的测试套件",
            "description": f"自动录制于 {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            "test_modules": [
                {
                    "name": "录制的测试模块",
                    "type": "module",
                    "test_cases": [test_case]
                }
            ]
        }
        
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                test_suite,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False
            )
        
        logger.info(f"测试用例已保存到: {output_file}")
        return output_file
    
    def generate_python_code(self, output_file: str):
        """
        生成Python代码格式的测试用例
        
        参数：
        - output_file: 输出文件路径
        """
        import os
        
        test_case = self.generate_test_case()
        
        code_lines = [
            "# 自动生成的测试用例",
            f"# 录制时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "import pytest",
            "import allure",
            "from pages.login_page import LoginPage  # 根据实际页面调整",
            "from api.base_api import BaseAPI  # 根据实际API调整",
            "",
            f"@allure.epic('自动录制测试')",
            f"@allure.feature('{test_case['name']}')",
            f"class TestRecordedCase:",
            "",
            f"    @allure.title('{test_case['name']}')",
            f"    @pytest.mark.{test_case.get('test_type', 'ui')}",
            f"    def test_recorded_case(self, driver, api_client):",
            f"        \"\"\"{test_case.get('description', '')}\"\"\"",
            ""
        ]
        
        # 生成步骤代码
        for idx, step in enumerate(test_case.get("steps", []), 1):
            action = step.get("action", "")
            
            if action.startswith("发送") or "请求" in action:
                # API步骤
                method = step.get("method", "GET").upper()
                endpoint = step.get("endpoint", "")
                body = step.get("body")
                
                code_lines.append(f"        # 步骤{idx}: {action}")
                if method == "GET":
                    code_lines.append(f"        response = api_client.get('{endpoint}')")
                elif method == "POST":
                    body_str = json.dumps(body, ensure_ascii=False) if body else "{}"
                    code_lines.append(f"        response = api_client.post('{endpoint}', json_data={body_str})")
                elif method == "PUT":
                    body_str = json.dumps(body, ensure_ascii=False) if body else "{}"
                    code_lines.append(f"        response = api_client.put('{endpoint}', json_data={body_str})")
                elif method == "DELETE":
                    code_lines.append(f"        response = api_client.delete('{endpoint}')")
                code_lines.append(f"        assert response.status_code == 200")
                code_lines.append("")
            
            elif action == "点击":
                element = step.get("element", "")
                code_lines.append(f"        # 步骤{idx}: {action} {element}")
                code_lines.append(f"        # page.click('id', '{element}')  # 需要根据实际页面对象调整")
                code_lines.append("")
            
            elif action == "输入":
                element = step.get("element", "")
                value = step.get("value", "")
                code_lines.append(f"        # 步骤{idx}: {action} {element} = {value}")
                code_lines.append(f"        # page.input_text('id', '{element}', '{value}')  # 需要根据实际页面对象调整")
                code_lines.append("")
            
            elif action == "滑动":
                direction = step.get("direction", "down")
                code_lines.append(f"        # 步骤{idx}: {action} {direction}")
                code_lines.append(f"        # page.swipe_{direction}()  # 需要根据实际页面对象调整")
                code_lines.append("")
        
        code_lines.append("        assert True, '测试完成'")
        
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(code_lines))
        
        logger.info(f"Python代码已保存到: {output_file}")
        return output_file

