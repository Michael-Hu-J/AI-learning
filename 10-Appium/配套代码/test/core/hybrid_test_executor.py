# hybrid_test_executor.py - 混合测试执行器
"""
混合测试执行器
功能：支持接口测试和UI测试的协同执行
"""
from typing import Dict, Any, Optional, Callable
from utils.logger import Logger
from core.test_router import TestRouter, TestType
from core.validator import Validator

logger = Logger().get_logger()


class HybridTestExecutor:
    """
    混合测试执行器
    
    功能：
    1. 根据测试用例类型，选择合适的执行方式
    2. 支持接口准备数据 + UI验证的混合模式
    3. 统一管理测试执行流程
    """
    
    def __init__(self, api_executor: Optional[Callable] = None, ui_executor: Optional[Callable] = None):
        """
        初始化混合测试执行器
        
        参数：
        - api_executor: API测试执行函数
        - ui_executor: UI测试执行函数
        """
        self.api_executor = api_executor
        self.ui_executor = ui_executor
    
    def execute(self, test_case: Dict[str, Any], driver=None, api_client=None) -> Dict[str, Any]:
        """
        执行测试用例（自动选择接口或UI）
        
        参数：
        - test_case: 测试用例字典
        - driver: Appium driver（UI测试需要）
        - api_client: API客户端（接口测试需要）
        
        返回：
        - Dict: 测试结果
        """
        test_type = TestRouter.determine_test_type(test_case)
        
        result = {
            "test_case": test_case.get("name"),
            "test_type": test_type.value,
            "status": "unknown",
            "message": "",
            "data": {}
        }
        
        try:
            if test_type == TestType.API:
                result = self._execute_api_test(test_case, api_client)
            elif test_type == TestType.UI:
                result = self._execute_ui_test(test_case, driver)
            elif test_type == TestType.HYBRID:
                result = self._execute_hybrid_test(test_case, driver, api_client)
            else:
                raise ValueError(f"未知的测试类型: {test_type}")
            
        except Exception as e:
            logger.error(f"执行测试用例失败: {test_case.get('name')}, 错误: {str(e)}")
            result["status"] = "failed"
            result["message"] = str(e)
        
        return result
    
    def _execute_api_test(self, test_case: Dict[str, Any], api_client) -> Dict[str, Any]:
        """
        执行接口测试
        
        参数：
        - test_case: 测试用例
        - api_client: API客户端
        
        返回：
        - Dict: 测试结果
        """
        logger.info(f"执行接口测试: {test_case.get('name')}")
        
        if self.api_executor:
            return self.api_executor(test_case, api_client)
        
        # 默认实现：解析steps并执行
        if not api_client:
            return {
                "test_case": test_case.get("name"),
                "test_type": "api",
                "status": "skipped",
                "message": "未提供API客户端"
            }
        
        return self._execute_api_steps(test_case, api_client)
    
    def _execute_ui_test(self, test_case: Dict[str, Any], driver) -> Dict[str, Any]:
        """
        执行UI测试
        
        参数：
        - test_case: 测试用例
        - driver: Appium driver
        
        返回：
        - Dict: 测试结果
        """
        logger.info(f"执行UI测试: {test_case.get('name')}")
        
        if self.ui_executor:
            return self.ui_executor(test_case, driver)
        
        # 默认实现：解析steps并执行
        if not driver:
            return {
                "test_case": test_case.get("name"),
                "test_type": "ui",
                "status": "skipped",
                "message": "未提供driver"
            }
        
        return self._execute_ui_steps(test_case, driver, case_name=test_case.get("name", ""))
    
    def _execute_hybrid_test(
        self,
        test_case: Dict[str, Any],
        driver,
        api_client
    ) -> Dict[str, Any]:
        """
        执行混合测试（先接口后UI）
        
        参数：
        - test_case: 测试用例
        - driver: Appium driver
        - api_client: API客户端
        
        返回：
        - Dict: 测试结果
        """
        logger.info(f"执行混合测试: {test_case.get('name')}")
        
        result = {
            "test_case": test_case.get("name"),
            "test_type": "hybrid",
            "status": "unknown",
            "api_result": {},
            "ui_result": {}
        }
        
        try:
            # 第一步：接口准备数据
            api_steps = test_case.get("api_steps", [])
            if api_steps and api_client:
                logger.info("步骤1: 通过接口准备测试数据")
                api_result = self._execute_api_test({"name": "数据准备", "steps": api_steps}, api_client)
                result["api_result"] = api_result
                
                if api_result.get("status") == "failed":
                    result["status"] = "failed"
                    result["message"] = "接口数据准备失败"
                    return result
            
            # 第二步：UI验证
            ui_steps = test_case.get("steps", test_case.get("ui_steps", []))
            if ui_steps and driver:
                logger.info("步骤2: 通过UI验证功能")
                ui_result = self._execute_ui_test({"name": test_case.get("name"), "steps": ui_steps}, driver)
                result["ui_result"] = ui_result
                
                if ui_result.get("status") == "failed":
                    result["status"] = "failed"
                    result["message"] = "UI验证失败"
                    return result
            
            # 如果都成功
            if result.get("api_result", {}).get("status") != "failed" and \
               result.get("ui_result", {}).get("status") != "failed":
                result["status"] = "passed"
                result["message"] = "混合测试通过"
            
        except Exception as e:
            logger.error(f"混合测试执行失败: {str(e)}")
            result["status"] = "failed"
            result["message"] = str(e)
        
        return result
    
    def _execute_api_steps(self, test_case: Dict[str, Any], api_client) -> Dict[str, Any]:
        """
        执行API测试步骤（实际实现）
        
        参数：
        - test_case: 测试用例，包含steps列表
        - api_client: API客户端
        
        返回：
        - Dict: 测试结果
        """
        result = {
            "test_case": test_case.get("name"),
            "test_type": "api",
            "status": "passed",
            "message": "",
            "data": {}
        }
        
        try:
            steps = test_case.get("steps", [])
            if not steps:
                logger.warning(f"用例 {test_case.get('name')} 没有steps，跳过执行")
                result["status"] = "skipped"
                result["message"] = "用例没有steps"
                return result
            
            logger.info(f"开始执行 {len(steps)} 个API步骤")
            
            # 重置数据生成器上下文
            from utils.test_data_generator import TestDataGenerator
            TestDataGenerator.reset_context()
            
            # 执行每个步骤
            for idx, step in enumerate(steps, 1):
                step_action = step.get("action", "").lower()
                logger.info(f"步骤 {idx}/{len(steps)}: {step_action}")
                
                # 根据action执行不同的操作
                if "post" in step_action or "发送POST" in step.get("action", ""):
                    endpoint = step.get("endpoint", "")
                    method = step.get("method", "POST").upper()
                    body = step.get("body") or step.get("data") or step.get("json")
                    
                    if not endpoint:
                        raise ValueError(f"步骤 {idx} 缺少endpoint参数")
                    
                    # 处理请求数据，生成动态值
                    if body:
                        body = TestDataGenerator.process_request_data(body, result["data"])
                        logger.debug(f"处理后的请求体: {body}")
                    
                    # 处理headers
                    headers = step.get("headers", {})
                    if headers:
                        headers = TestDataGenerator.process_request_data(headers, result["data"])
                        logger.debug(f"处理后的请求头: {headers}")
                    
                    response = api_client.post(endpoint, json_data=body, headers=headers)
                    
                    # 解析响应内容
                    try:
                        if response.content:
                            response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '').lower() else response.text
                        else:
                            response_data = None
                    except Exception:
                        response_data = response.text
                    
                    result["data"][f"step_{idx}"] = {
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response": response_data,
                        "headers": dict(response.headers) if response.headers else {}
                    }
                    
                    # 自动提取常用字段到上下文（如果响应成功）
                    if response.status_code < 400 and isinstance(response_data, dict):
                        # 提取 otpSessionId
                        otp_session_id = TestDataGenerator.extract_from_response(response_data, "data.otpSessionId") or \
                                       TestDataGenerator.extract_from_response(response_data, "data.extra.ivsSession.sessionId")
                        if otp_session_id:
                            TestDataGenerator.set_context("otpSessionId", otp_session_id)
                            logger.info(f"自动提取并保存 otpSessionId: {otp_session_id}")
                    
                    # 验证响应状态码
                    if response.status_code >= 400:
                        result["status"] = "failed"
                        error_detail = response_data if isinstance(response_data, str) else str(response_data)[:200]
                        result["message"] = f"步骤 {idx} 请求失败，状态码: {response.status_code}, 错误: {error_detail}"
                        return result
                
                elif "get" in step_action or "发送GET" in step.get("action", ""):
                    endpoint = step.get("endpoint", "")
                    params = step.get("params") or step.get("query")
                    
                    if not endpoint:
                        raise ValueError(f"步骤 {idx} 缺少endpoint参数")
                    
                    # 处理请求参数，生成动态值
                    if params:
                        params = TestDataGenerator.process_request_data(params, result["data"])
                        logger.debug(f"处理后的请求参数: {params}")
                    
                    # 处理headers
                    headers = step.get("headers", {})
                    if headers:
                        headers = TestDataGenerator.process_request_data(headers, result["data"])
                        logger.debug(f"处理后的请求头: {headers}")
                    
                    response = api_client.get(endpoint, params=params, headers=headers)
                    
                    # 解析响应内容
                    try:
                        if response.content:
                            response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '').lower() else response.text
                        else:
                            response_data = None
                    except Exception:
                        response_data = response.text
                    
                    result["data"][f"step_{idx}"] = {
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response": response_data
                    }
                    
                    if response.status_code >= 400:
                        result["status"] = "failed"
                        error_detail = response_data if isinstance(response_data, str) else str(response_data)[:200]
                        result["message"] = f"步骤 {idx} 请求失败，状态码: {response.status_code}, 错误: {error_detail}"
                        return result
                
                elif "put" in step_action or "发送PUT" in step.get("action", ""):
                    endpoint = step.get("endpoint", "")
                    body = step.get("body") or step.get("data") or step.get("json")
                    
                    if not endpoint:
                        raise ValueError(f"步骤 {idx} 缺少endpoint参数")
                    
                    # 处理请求数据，生成动态值
                    if body:
                        body = TestDataGenerator.process_request_data(body, result["data"])
                        logger.debug(f"处理后的请求体: {body}")
                    
                    response = api_client.put(endpoint, json_data=body)
                    
                    # 解析响应内容
                    try:
                        if response.content:
                            response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '').lower() else response.text
                        else:
                            response_data = None
                    except Exception:
                        response_data = response.text
                    
                    result["data"][f"step_{idx}"] = {
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response": response_data
                    }
                    
                    # 自动提取常用字段到上下文
                    if response.status_code < 400 and isinstance(response_data, dict):
                        otp_session_id = TestDataGenerator.extract_from_response(response_data, "data.otpSessionId") or \
                                       TestDataGenerator.extract_from_response(response_data, "data.extra.ivsSession.sessionId")
                        if otp_session_id:
                            TestDataGenerator.set_context("otpSessionId", otp_session_id)
                    
                    if response.status_code >= 400:
                        result["status"] = "failed"
                        error_detail = response_data if isinstance(response_data, str) else str(response_data)[:200]
                        result["message"] = f"步骤 {idx} 请求失败，状态码: {response.status_code}, 错误: {error_detail}"
                        return result
                
                elif "delete" in step_action or "发送DELETE" in step.get("action", ""):
                    endpoint = step.get("endpoint", "")
                    
                    if not endpoint:
                        raise ValueError(f"步骤 {idx} 缺少endpoint参数")
                    
                    response = api_client.delete(endpoint)
                    
                    # 解析响应内容
                    try:
                        if response.content:
                            response_data = response.json() if 'application/json' in response.headers.get('Content-Type', '').lower() else response.text
                        else:
                            response_data = None
                    except Exception:
                        response_data = response.text
                    
                    result["data"][f"step_{idx}"] = {
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response": response_data
                    }
                    
                    if response.status_code >= 400:
                        result["status"] = "failed"
                        error_detail = response_data if isinstance(response_data, str) else str(response_data)[:200]
                        result["message"] = f"步骤 {idx} 请求失败，状态码: {response.status_code}, 错误: {error_detail}"
                        return result
                
                else:
                    logger.warning(f"未知的API操作: {step_action}，跳过")
                    continue
            
            # 验证预期结果（使用Validator进行详细验证）
            expected = test_case.get("expected", {})
            if expected:
                logger.info(f"预期结果: {expected}")
                
                # 解析预期结果
                expected_dict = Validator.parse_expected(expected)
                
                # 验证响应内容（如果最后一步有响应）
                if result["data"]:
                    last_step_key = max(result["data"].keys(), key=lambda k: int(k.split("_")[1]) if "_" in k else 0)
                    last_step_data = result["data"][last_step_key]
                    last_response = last_step_data.get("response")
                    
                    if last_response or "status_code" in expected_dict:
                        # 构建完整的响应数据（包含status_code）
                        response_data = {
                            "status_code": last_step_data.get("status_code"),
                            "response": last_response
                        }
                        
                        # 使用Validator验证
                        is_valid, error_msg = Validator.validate_api_response(response_data, expected_dict)
                        if not is_valid:
                            result["status"] = "failed"
                            result["message"] = f"验证失败: {error_msg}"
                            logger.error(f" API验证失败: {error_msg}")
                            return result
                        else:
                            logger.info(f" API验证通过")
            
            if result["status"] == "passed":
                result["message"] = "所有API步骤执行成功"
                logger.info(f" API测试通过: {test_case.get('name')}")
            
        except Exception as e:
            logger.error(f"API测试执行失败: {str(e)}")
            result["status"] = "failed"
            result["message"] = str(e)
        
        return result
    
    def _execute_ui_steps(self, test_case: Dict[str, Any], driver, case_name: str = "") -> Dict[str, Any]:
        """
        执行UI测试步骤（实际实现）
        
        参数：
        - test_case: 测试用例，包含steps列表
        - driver: Appium driver
        
        返回：
        - Dict: 测试结果
        """
        result = {
            "test_case": test_case.get("name"),
            "test_type": "ui",
            "status": "passed",
            "message": "",
            "data": {}
        }
        
        try:
            from base.base_page import BasePage
            
            # 创建BasePage实例（用于UI操作）
            page = BasePage(driver)
            
            steps = test_case.get("steps", [])
            if not steps:
                logger.warning(f"用例 {test_case.get('name')} 没有steps，跳过执行")
                result["status"] = "skipped"
                result["message"] = "用例没有steps"
                return result
            
            logger.info(f"开始执行 {len(steps)} 个UI步骤")
            
            # 执行每个步骤
            for idx, step in enumerate(steps, 1):
                step_action = step.get("action", "").lower()
                logger.info(f"步骤 {idx}/{len(steps)}: {step_action}")
                
                # 根据action执行不同的操作
                if "点击" in step.get("action", "") or "click" in step_action:
                    element = step.get("element", "")
                    
                    if not element:
                        raise ValueError(f"步骤 {idx} 缺少element参数")
                    
                    # 特殊处理：如果element是"元素"（占位符）且用例名称包含"logout"，使用Logout按钮查找逻辑
                    element_str = str(element).lower()
                    case_name_lower = case_name.lower() if case_name else ""
                    is_logout_action = ("logout" in element_str or "退出" in element_str or 
                                       "logout" in case_name_lower or "退出" in case_name_lower or
                                       element_str == "元素" and ("logout" in case_name_lower or "退出" in case_name_lower))
                    
                    if is_logout_action:
                        # 使用滚动查找Logout按钮的逻辑（与注册流程一致）
                        logger.info("检测到Logout操作，使用滚动查找Logout按钮")
                        try:
                            from selenium.webdriver.common.by import By
                            import time
                            
                            # 等待页面加载完成
                            time.sleep(3)
                            
                            # 先检查是否有生物识别页面需要关闭
                            try:
                                biometrics_indicators = [
                                    "//*[contains(@text, 'Enable Biometrics') or contains(@text, 'Enable biometrics')]",
                                    "//*[contains(@text, 'faster log') or contains(@text, 'faster log in')]",
                                    "//*[@text='Enable now' or contains(@text, 'Enable now')]"
                                ]
                                
                                is_biometrics_page = False
                                for indicator in biometrics_indicators:
                                    try:
                                        bio_elements = driver.find_elements(By.XPATH, indicator)
                                        if bio_elements and len(bio_elements) > 0:
                                            visible_bio = [e for e in bio_elements if e.is_displayed()]
                                            if visible_bio:
                                                is_biometrics_page = True
                                                break
                                    except:
                                        continue
                                
                                # 如果检测到生物识别页面，点击右上角的关闭按钮
                                if is_biometrics_page:
                                    logger.info(" 检测到生物识别页面，先关闭生物识别页面...")
                                    close_button_found = False
                                    close_selectors = [
                                        "//*[@content-desc='Close' or @content-desc='close' or @content-desc='×' or @content-desc='X']",
                                        "//*[contains(@content-desc, 'Close') or contains(@content-desc, 'close')]",
                                        "//*[@class='android.widget.ImageButton' and contains(@content-desc, 'Close')]",
                                        "//*[@class='android.widget.ImageButton'][last()]",
                                    ]
                                    
                                    for close_selector in close_selectors:
                                        try:
                                            close_buttons = driver.find_elements(By.XPATH, close_selector)
                                            if close_buttons and len(close_buttons) > 0:
                                                size_info = driver.get_window_size()
                                                for btn in close_buttons:
                                                    if btn.is_displayed():
                                                        location = btn.location
                                                        if location['y'] < size_info['height'] * 0.2:
                                                            btn.click()
                                                            logger.info(" 已点击生物识别页面的关闭按钮")
                                                            close_button_found = True
                                                            time.sleep(2)
                                                            break
                                                if close_button_found:
                                                    break
                                        except:
                                            continue
                                    
                                    if not close_button_found:
                                        try:
                                            # 方式1：查找所有ImageButton和ImageView
                                            all_buttons = driver.find_elements(By.XPATH, 
                                                "//*[@clickable='true' and (@class='android.widget.ImageButton' or @class='android.widget.ImageView')]")
                                            size_info = driver.get_window_size()
                                            for btn in all_buttons:
                                                if btn.is_displayed():
                                                    location = btn.location
                                                    size_btn = btn.size
                                                    # 检查是否在右上角区域（右侧70%宽度，顶部20%高度）
                                                    if location['x'] + size_btn['width'] > size_info['width'] * 0.7 and location['y'] < size_info['height'] * 0.2:
                                                        btn.click()
                                                        logger.info(" 已点击右上角按钮（可能是关闭按钮）")
                                                        close_button_found = True
                                                        time.sleep(2)
                                                        break
                                            
                                            # 方式2：如果仍然找不到，尝试坐标点击右上角
                                            if not close_button_found:
                                                size_info = driver.get_window_size()
                                                # 点击右上角区域（右侧5%宽度，顶部8%高度）
                                                x_coord = int(size_info['width'] * 0.95)
                                                y_coord = int(size_info['height'] * 0.08)
                                                driver.tap([(x_coord, y_coord)], 100)
                                                logger.info(" 已通过坐标点击右上角（可能是关闭按钮）")
                                                close_button_found = True
                                                time.sleep(2)
                                        except Exception as coord_e:
                                            logger.debug(f"坐标点击失败: {str(coord_e)}")
                                            pass
                            except Exception as bio_check_e:
                                logger.debug(f"检查生物识别页面失败: {str(bio_check_e)}")
                                # 如果检查失败，不影响主流程，继续执行Logout查找
                            
                            # 获取屏幕尺寸
                            size = driver.get_window_size()
                            start_x = size['width'] // 2
                            start_y = int(size['height'] * 0.7)
                            end_y = int(size['height'] * 0.3)
                            
                            # 尝试多次滑动并查找Logout按钮
                            max_scrolls = 10  # 最多滑动10次
                            logout_clicked = False
                            
                            # Logout按钮的多种定位方式
                            logout_selectors = [
                                "//*[@text='Logout' or @content-desc='Logout']",
                                "//*[contains(@text, 'Logout') or contains(@content-desc, 'Logout')]",
                                "//*[@text='登出' or @content-desc='登出']",
                                "//*[contains(@text, '登出') or contains(@content-desc, '登出')]",
                                "//*[contains(@text, 'Log out') or contains(@content-desc, 'Log out')]",
                                "//*[contains(@text, 'log out') or contains(@content-desc, 'log out')]"
                            ]
                            
                            for scroll_attempt in range(max_scrolls):
                                # 每次滑动前先检查是否能找到Logout按钮
                                for selector in logout_selectors:
                                    try:
                                        logout_elements = driver.find_elements(By.XPATH, selector)
                                        if logout_elements and len(logout_elements) > 0:
                                            # 找到Logout按钮，点击
                                            logout_elements[0].click()
                                            logger.info(f" 已找到并点击Logout按钮（尝试 {scroll_attempt + 1} 次滑动后）")
                                            logout_clicked = True
                                            time.sleep(2)
                                            break
                                    except Exception as e:
                                        logger.debug(f"定位方式失败: {selector}, 错误: {str(e)}")
                                        continue
                                
                                if logout_clicked:
                                    break
                                
                                # 如果没找到，继续向下滑动
                                if scroll_attempt < max_scrolls - 1:
                                    # 向下滑动
                                    driver.swipe(start_x, start_y, start_x, end_y, 500)
                                    time.sleep(1)  # 等待滑动完成
                                    logger.debug(f" 向下滑动查找Logout按钮（第 {scroll_attempt + 1} 次）...")
                            
                            if not logout_clicked:
                                raise Exception(f"未能找到Logout按钮（已尝试滑动 {max_scrolls} 次）")
                            
                            result["data"][f"step_{idx}"] = {
                                "action": "click",
                                "element": "Logout按钮",
                                "method": "滚动查找"
                            }
                        except Exception as e:
                            logger.error(f"滚动查找Logout按钮失败: {str(e)}")
                            # 如果滚动查找失败，尝试普通的点击方式作为备选
                            logger.info("尝试普通点击方式作为备选...")
                            # 继续执行普通点击逻辑
                            is_logout_action = False  # 重置标志，使用普通点击
                    
                    if not is_logout_action:
                        # 普通点击逻辑
                        # 尝试解析element（可能是字符串，也可能是字典）
                        if isinstance(element, dict):
                            locator_type = element.get("type", "id")
                            locator_value = element.get("value", element.get("id", ""))
                        else:
                            # 默认使用id定位
                            locator_type = "id"
                            locator_value = str(element)
                        
                        page.click(locator_type, locator_value)
                        result["data"][f"step_{idx}"] = {
                            "action": "click",
                            "element": element
                        }
                
                elif "输入" in step.get("action", "") or "input" in step_action or "输入文本" in step.get("action", ""):
                    element = step.get("element", "")
                    value = step.get("value", "") or step.get("text", "")
                    length = step.get("length")  # 获取length参数（用于生成指定长度的字符串）
                    
                    if not element:
                        raise ValueError(f"步骤 {idx} 缺少element参数")
                    if not value and not length:
                        raise ValueError(f"步骤 {idx} 缺少value参数")
                    
                    # 处理生成指定长度的字符串
                    if length and isinstance(length, (int, str)):
                        try:
                            import string
                            from utils.test_data_generator import TestDataGenerator
                            
                            length_int = int(length)
                            # 检查value中是否包含"生成XX个字符"的描述，或者有length参数
                            # 如果有length参数，就生成指定长度的数据
                            should_generate = False
                            if isinstance(value, str) and ("生成" in value or "个字符" in value):
                                should_generate = True
                            elif length_int > 0:
                                should_generate = True
                            
                            if should_generate:
                                value_str = str(value).lower()
                                # 判断是邮箱、手机号还是普通字符串
                                # 从用例名称、element描述、或value描述中判断类型
                                element_str = str(element).lower()
                                case_name_lower = case_name.lower() if case_name else ""
                                
                                # 判断是否是邮箱输入（优先检查用例名称）
                                is_email_input = ("邮箱" in case_name_lower or "email" in case_name_lower or
                                                "邮箱" in value_str or "email" in value_str or
                                                "邮箱" in element_str or "email" in element_str)
                                
                                if is_email_input:
                                    # 生成邮箱格式的长字符串（前缀 + @example.com）
                                    suffix = "@example.com"
                                    prefix_length = max(0, length_int - len(suffix))
                                    if prefix_length > 0:
                                        prefix = TestDataGenerator.generate_string_with_length(
                                            prefix_length, charset=string.ascii_lowercase + string.digits
                                        )
                                        value = prefix + suffix
                                    else:
                                        value = suffix[:length_int]
                                    logger.info(f"生成 {length_int} 个字符的邮箱（实际长度: {len(value)}）: {value[:50]}...")
                                elif "手机" in value_str or "mobile" in value_str or "phone" in value_str:
                                    # 生成手机号格式的长字符串（纯数字）
                                    value = TestDataGenerator.generate_string_with_length(
                                        length_int, charset=string.digits
                                    )
                                    logger.info(f"生成 {length_int} 个字符的手机号")
                                else:
                                    # 生成普通字符串（字母+数字）
                                    value = TestDataGenerator.generate_string_with_length(
                                        length_int, charset=string.ascii_letters + string.digits
                                    )
                                    logger.info(f"生成 {length_int} 个字符的字符串")
                        except (ValueError, TypeError) as e:
                            logger.warning(f"解析length参数失败: {length}, 错误: {str(e)}")
                            # 如果解析失败，继续使用原始value
                        except ImportError as e:
                            logger.warning(f"导入TestDataGenerator失败: {str(e)}")
                            # 如果导入失败，继续使用原始value
                    
                    # 解析element
                    if isinstance(element, dict):
                        locator_type = element.get("type", "id")
                        locator_value = element.get("value", element.get("id", ""))
                    else:
                        # 如果是字符串，尝试智能推断定位方式
                        element_str = str(element)
                        
                        # 如果包含xpath、resource-id等关键词，提取定位类型
                        if element_str.startswith("//") or element_str.startswith("/"):
                            locator_type = "xpath"
                            locator_value = element_str
                        elif ":" in element_str and "/" in element_str:
                            # 类似 "com.app:id/email" 的resource-id
                            locator_type = "resource-id"
                            locator_value = element_str
                        elif element_str.startswith("@") or element_str.startswith("#"):
                            locator_type = "id"
                            locator_value = element_str.lstrip("@#")
                        else:
                            # 通用描述，尝试多种定位方式
                            # 先尝试xpath查找包含关键词的输入框
                            if "输入框" in element_str or "input" in element_str.lower():
                                # 尝试查找邮箱输入框（React Native使用TextView作为输入框）
                                if "邮箱" in element_str or "email" in element_str.lower():
                                    locator_type = "xpath"
                                    # React Native应用可能使用TextView作为输入框
                                    locator_value = "//android.widget.TextView[@hint='your email address' or contains(@hint,'email') or contains(@hint,'邮箱') or contains(@text,'your email')] | //android.widget.EditText[contains(@resource-id,'email') or contains(@hint,'email') or contains(@hint,'邮箱')]"
                                else:
                                    # 通用输入框，尝试TextView（React Native）或EditText
                                    locator_type = "xpath"
                                    locator_value = "//android.widget.TextView[@hint and @clickable='true'][1] | //android.widget.EditText[1]"
                            else:
                                # 默认使用id定位
                                locator_type = "id"
                                locator_value = element_str
                    
                    # 判断是否是验证码输入，使用专门的验证码输入方法
                    is_otp_input = False
                    if isinstance(value, str):
                        value_str = str(value).lower()
                        element_str = str(element).lower()
                        case_name_lower = case_name.lower() if case_name else ""
                        
                        # 判断是否是验证码输入
                        is_otp_input = ("验证码" in value_str or "otp" in value_str or 
                                       "验证码" in element_str or "otp" in element_str or "code" in element_str or
                                       "验证码" in case_name_lower or "otp" in case_name_lower or "code" in case_name_lower)
                    
                    if is_otp_input and len(str(value)) >= 4:
                        # 使用专门的验证码输入方法
                        logger.info(f"检测到验证码输入，使用专门的验证码输入方法")
                        page.input_otp_code(str(value))
                    else:
                        # 普通输入
                        page.input_text(locator_type, locator_value, str(value))
                    result["data"][f"step_{idx}"] = {
                        "action": "input",
                        "element": element,
                        "value": value
                    }
                
                elif "滑动" in step.get("action", "") or "swipe" in step_action:
                    direction = step.get("direction", "down").lower()
                    
                    if direction == "up" or direction == "向上":
                        page.swipe_up()
                    elif direction == "down" or direction == "向下":
                        page.swipe_down()
                    elif direction == "left" or direction == "向左":
                        page.swipe_left()
                    elif direction == "right" or direction == "向右":
                        page.swipe_right()
                    else:
                        logger.warning(f"未知的滑动方向: {direction}，使用向下滑动")
                        page.swipe_down()
                    
                    result["data"][f"step_{idx}"] = {
                        "action": "swipe",
                        "direction": direction
                    }
                
                elif "等待" in step.get("action", "") or "wait" in step_action:
                    seconds = step.get("seconds", step.get("time", 1))
                    import time
                    time.sleep(float(seconds))
                    result["data"][f"step_{idx}"] = {
                        "action": "wait",
                        "seconds": seconds
                    }
                
                elif "验证" in step.get("action", "") or "verify" in step_action or "检查" in step.get("action", ""):
                    element = step.get("element", "")
                    expected = step.get("expected", step.get("value", ""))
                    
                    if element:
                        # 验证元素是否存在
                        if isinstance(element, dict):
                            locator_type = element.get("type", "id")
                            locator_value = element.get("value", element.get("id", ""))
                        else:
                            locator_type = "id"
                            locator_value = str(element)
                        
                        try:
                            page.find_element(locator_type, locator_value, timeout=5)
                            result["data"][f"step_{idx}"] = {
                                "action": "verify",
                                "element": element,
                                "result": "元素存在"
                            }
                        except Exception:
                            result["status"] = "failed"
                            result["message"] = f"步骤 {idx} 验证失败：元素不存在"
                            return result
                    else:
                        logger.warning(f"步骤 {idx} 验证操作缺少element参数")
                
                else:
                    logger.warning(f"未知的UI操作: {step_action}，跳过")
                    continue
            
            # 验证预期结果（使用Validator进行详细验证）
            expected = test_case.get("expected", {})
            if expected:
                logger.info(f"预期结果: {expected}")
                
                # 解析预期结果
                expected_dict = Validator.parse_expected(expected)
                
                # 如果预期结果包含元素验证信息
                if "element" in expected_dict or "exists" in expected_dict or "text" in expected_dict:
                    # 需要验证特定元素
                    element_locator = expected_dict.get("element", {})
                    if not element_locator:
                        # 如果steps中最后一个操作有element，使用它
                        if steps:
                            last_step = steps[-1]
                            element = last_step.get("element", "")
                            if element:
                                if isinstance(element, dict):
                                    element_locator = element
                                else:
                                    element_locator = {"type": "id", "value": str(element)}
                    
                    if element_locator:
                        # 使用Validator验证UI元素
                        is_valid, error_msg = Validator.validate_ui_element(driver, element_locator, expected_dict)
                        if not is_valid:
                            result["status"] = "failed"
                            result["message"] = f"UI验证失败: {error_msg}"
                            logger.error(f" UI验证失败: {error_msg}")
                            return result
                        else:
                            logger.info(f" UI验证通过")
                else:
                    # 简单验证：如果所有步骤都执行成功，认为验证通过
                    logger.info(" UI验证通过（所有步骤执行成功）")
            
            result["message"] = "所有UI步骤执行成功"
            logger.info(f" UI测试通过: {test_case.get('name')}")
            
        except Exception as e:
            logger.error(f"UI测试执行失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            result["status"] = "failed"
            result["message"] = str(e)
        
        return result

