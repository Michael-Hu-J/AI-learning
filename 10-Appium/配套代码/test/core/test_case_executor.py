# test_case_executor.py - 测试用例批量执行器
"""
测试用例批量执行器
功能：
1. 从YAML文件读取测试用例
2. 自动判断主流程（接口测试）和次要流程（UI测试）
3. 批量执行测试用例
4. 记录未执行的用例，方便后续人工执行
"""
import yaml
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from utils.logger import Logger
from core.test_router import TestRouter, TestType
from core.hybrid_test_executor import HybridTestExecutor
# from utils.unexecuted_report_generator import UnexecutedReportGenerator  # 已删除
from core.data_driver import DataDriver

logger = Logger().get_logger()


class TestCaseExecutor:
    """
    测试用例执行器
    
    功能：
    1. 读取YAML测试用例
    2. 智能判断主流程和次要流程
    3. 批量执行测试用例
    4. 生成执行报告（包括未执行用例）
    """
    
    # 主流程关键词（包含这些关键词的用例认为是主流程，使用接口测试）
    MAIN_FLOW_KEYWORDS = [
        "主流程", "核心流程", "主要流程", "主", "核心",
        "登录", "注册", "支付", "下单", "结算", "提交订单",
        "创建", "删除", "更新", "修改",
        "数据准备", "数据清理", "初始化", "清理"
    ]
    
    # 次要流程关键词（包含这些关键词的用例认为是次要流程，使用UI测试）
    SUB_FLOW_KEYWORDS = [
        "次要流程", "辅助流程", "非主流程",
        "查看", "浏览", "展示", "显示", "详情",
        "界面", "UI", "页面", "跳转", "导航"
    ]
    
    def __init__(self, driver=None, api_client=None, auto_prepare: bool = True):
        """
        初始化测试用例执行器
        
        参数：
        - driver: Appium driver（UI测试需要）
        - api_client: API客户端（接口测试需要）
        - auto_prepare: 是否自动准备用例和代码（检查并生成缺失的）
        """
        self.driver = driver
        self.api_client = api_client
        self.executor = HybridTestExecutor()
        self.auto_prepare = auto_prepare
        
        # 执行统计
        self.stats = {
            "total": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "main_flow_api": 0,  # 主流程接口测试数量
            "sub_flow_ui": 0,    # 次要流程UI测试数量
        }
        
        # 未执行用例列表
        self.unexecuted_cases = []
        
        # 执行结果
        self.execution_results = []
    
    def load_test_cases(self, yaml_file: str) -> Dict[str, Any]:
        """
        从YAML文件加载测试用例
        
        参数：
        - yaml_file: YAML文件路径
        
        返回：
        - Dict: 测试套件
        """
        try:
            logger.info(f"加载测试用例文件: {yaml_file}")
            
            # 如果启用了自动准备，检查并准备用例和代码
            if self.auto_prepare:
                from core.test_case_preparer import TestCasePreparer
                preparer = TestCasePreparer()
                result = preparer.prepare_for_execution(yaml_file)
                
                if not result["yaml_exists"]:
                    logger.warning(f"YAML文件不存在: {yaml_file}")
                    logger.info("提示：可以使用 scripts/prepare_test_cases.py 准备用例")
                
                if result["page_generated"] or result["test_generated"]:
                    logger.info(" 已自动生成缺失的代码文件")
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                test_suite = yaml.safe_load(f)
            
            # 统计用例数量
            self.stats["total"] = self._count_test_cases(test_suite)
            logger.info(f"加载完成，共 {self.stats['total']} 个测试用例")
            
            return test_suite
            
        except Exception as e:
            logger.error(f"加载测试用例失败: {str(e)}")
            raise
    
    def _count_test_cases(self, suite: Dict) -> int:
        """统计测试用例数量"""
        count = 0
        for module in suite.get("test_modules", []):
            count += self._count_cases_in_module(module)
        return count
    
    def _count_cases_in_module(self, module: Dict) -> int:
        """递归统计模块中的用例数量"""
        if module.get("type") == "test_case":
            return 1
        
        count = 0
        for case in module.get("test_cases", []):
            count += self._count_cases_in_module(case)
        return count
    
    def _process_data_driven_cases(self, test_suite: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理数据驱动的测试用例
        
        参数：
        - test_suite: 测试套件
        
        返回：
        - Dict: 处理后的测试套件
        """
        processed_modules = []
        
        for module in test_suite.get("test_modules", []):
            processed_module = self._process_module_data_driven(module)
            if processed_module:
                processed_modules.append(processed_module)
        
        test_suite["test_modules"] = processed_modules
        return test_suite
    
    def _process_module_data_driven(self, module: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归处理模块中的数据驱动用例
        """
        import copy
        
        if module.get("type") == "test_case":
            # 这是测试用例，检查是否有data_file
            if "data_file" in module:
                data_file = module["data_file"]
                # 复制用例模板（移除data_file字段）
                case_template = copy.deepcopy(module)
                del case_template["data_file"]
                
                # 生成参数化用例
                try:
                    parametrized_cases = DataDriver.generate_parametrized_cases(case_template, data_file)
                    # 返回一个模块包含所有参数化用例
                    return {
                        "name": f"{module.get('name', '参数化用例')} (数据驱动)",
                        "type": "module",
                        "test_cases": parametrized_cases
                    }
                except Exception as e:
                    logger.warning(f"处理数据驱动用例失败: {str(e)}")
                    return module  # 返回原始用例
            
            return module
        else:
            # 这是模块，递归处理
            processed_module = copy.deepcopy(module)
            processed_cases = []
            
            for case in module.get("test_cases", []):
                processed_case = self._process_module_data_driven(case)
                if processed_case:
                    processed_cases.append(processed_case)
            
            processed_module["test_cases"] = processed_cases
            return processed_module
    
    def is_main_flow(self, test_case: Dict[str, Any]) -> bool:
        """
        判断是否是主流程用例
        
        参数：
        - test_case: 测试用例字典
        
        返回：
        - bool: True表示主流程，False表示次要流程
        """
        # 如果用例明确标记了test_type，优先使用
        if "test_type" in test_case:
            test_type = test_case["test_type"].lower()
            if test_type in ["api", "接口"]:
                return True
            elif test_type in ["ui", "界面"]:
                return False
        
        # 根据用例名称和描述判断
        name = test_case.get("name", "").lower()
        description = test_case.get("description", "").lower()
        text = f"{name} {description}"
        
        # 检查主流程关键词
        main_score = sum(1 for keyword in self.MAIN_FLOW_KEYWORDS if keyword in text)
        # 检查次要流程关键词
        sub_score = sum(1 for keyword in self.SUB_FLOW_KEYWORDS if keyword in text)
        
        # 如果主流程关键词多，或者是第一层用例，认为是主流程
        if main_score > sub_score:
            return True
        elif sub_score > main_score:
            return False
        else:
            # 默认：没有明确关键词的，根据层级判断
            # 第一层用例通常是主流程
            level = test_case.get("level", 0)
            return level <= 1
    
    def execute_test_suite(self, test_suite: Dict[str, Any], execute_main_flow: bool = True, execute_sub_flow: bool = True):
        """
        执行测试套件
        
        参数：
        - test_suite: 测试套件
        - execute_main_flow: 是否执行主流程（接口测试）
        - execute_sub_flow: 是否执行次要流程（UI测试）
        """
        logger.info("=" * 60)
        logger.info("开始执行测试套件")
        logger.info(f"执行主流程: {execute_main_flow}, 执行次要流程: {execute_sub_flow}")
        logger.info("=" * 60)
        
        for module in test_suite.get("test_modules", []):
            self._execute_module(module, execute_main_flow, execute_sub_flow, level=0, module_path=module.get("name", ""))
        
        # 生成执行报告
        self._generate_execution_report()
    
    def _execute_module(self, module: Dict[str, Any], execute_main_flow: bool, execute_sub_flow: bool, level: int = 0, module_path: str = ""):
        """
        递归执行模块中的测试用例
        
        参数：
        - module: 测试模块
        - execute_main_flow: 是否执行主流程
        - execute_sub_flow: 是否执行次要流程
        - level: 当前层级
        """
        if module.get("type") == "test_case":
            # 这是测试用例
            test_case = module.copy()
            test_case["level"] = level
            
            # 判断是否主流程
            is_main = self.is_main_flow(test_case)
            test_case["is_main_flow"] = is_main
            
            # 决定是否执行
            should_execute = False
            reason_not_executed = ""
            if is_main:
                if execute_main_flow:
                    should_execute = True
                    test_case["test_type"] = "api"  # 主流程用接口测试
                else:
                    reason_not_executed = "主流程用例（当前仅执行次要流程）"
            else:
                if execute_sub_flow:
                    should_execute = True
                    test_case["test_type"] = "ui"  # 次要流程用UI测试
                else:
                    reason_not_executed = "次要流程用例（当前仅执行主流程）"
            
            if should_execute:
                # 执行测试用例
                try:
                    logger.info(f"执行测试用例: {test_case.get('name')} (类型: {'主流程-接口' if is_main else '次要流程-UI'})")
                    result = self.executor.execute(test_case, self.driver, self.api_client)
                    
                    self.execution_results.append({
                        "test_case": test_case,
                        "result": result
                    })
                    
                    # 更新统计
                    self.stats["executed"] += 1
                    if result.get("status") == "passed":
                        self.stats["passed"] += 1
                    elif result.get("status") == "failed":
                        self.stats["failed"] += 1
                    else:
                        self.stats["skipped"] += 1
                    
                    if is_main:
                        self.stats["main_flow_api"] += 1
                    else:
                        self.stats["sub_flow_ui"] += 1
                        
                except Exception as e:
                    logger.error(f"执行测试用例失败: {test_case.get('name')}, 错误: {str(e)}")
                    self.execution_results.append({
                        "test_case": test_case,
                        "result": {"status": "failed", "message": str(e)}
                    })
                    self.stats["executed"] += 1
                    self.stats["failed"] += 1
            else:
                # 未执行，记录到未执行列表
                if reason_not_executed:
                    current_path = f"{module_path} > {test_case.get('name')}" if module_path else test_case.get('name')
                    self.unexecuted_cases.append({
                        "test_case": test_case,
                        "reason": reason_not_executed,
                        "suggested_type": "api" if is_main else "ui",
                        "module_path": current_path
                    })
                    self.stats["skipped"] += 1
        else:
            # 这是模块，递归处理子用例
            current_module_path = f"{module_path} > {module.get('name')}" if module_path else module.get('name', '')
            for case in module.get("test_cases", []):
                self._execute_module(case, execute_main_flow, execute_sub_flow, level + 1, current_module_path)
    
    def _generate_execution_report(self):
        """生成执行报告"""
        logger.info("=" * 60)
        logger.info("测试执行完成")
        logger.info("=" * 60)
        logger.info(f"总用例数: {self.stats['total']}")
        logger.info(f"已执行: {self.stats['executed']}")
        logger.info(f"  通过: {self.stats['passed']}")
        logger.info(f"  失败: {self.stats['failed']}")
        logger.info(f"  跳过: {self.stats['skipped']}")
        logger.info(f"主流程接口测试: {self.stats['main_flow_api']}")
        logger.info(f"次要流程UI测试: {self.stats['sub_flow_ui']}")
        logger.info(f"未执行用例数: {len(self.unexecuted_cases)}")
    
    def save_unexecuted_report(self, output_file: str = "reports/unexecuted_cases.yaml", generate_all: bool = True):
        """
        保存未执行用例报告（生成多种格式）
        
        参数：
        - output_file: 输出YAML文件路径
        - generate_all: 是否生成所有格式的报告（YAML、Markdown、Python脚本）
        """
        if not self.unexecuted_cases:
            logger.info("没有未执行的用例")
            return
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 生成YAML报告
            report = {
                "report_info": {
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_unexecuted": len(self.unexecuted_cases),
                    "total_cases": self.stats["total"],
                    "executed_cases": self.stats["executed"]
                },
                "unexecuted_cases": []
            }
            
            for item in self.unexecuted_cases:
                case_info = {
                    "name": item["test_case"].get("name"),
                    "description": item["test_case"].get("description"),
                    "reason": item["reason"],
                    "suggested_test_type": item["suggested_type"],
                    "is_main_flow": item["test_case"].get("is_main_flow", False),
                    "module_path": item.get("module_path", ""),
                    "test_case": item["test_case"]  # 完整用例信息，方便后续执行
                }
                report["unexecuted_cases"].append(case_info)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(
                    report,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            
            logger.info(f"未执行用例YAML报告已保存: {output_file}")
            
            # 生成其他格式的报告
            if generate_all:
                base_dir = os.path.dirname(output_file)
                
                # 生成Markdown报告（便于阅读）
                md_file = os.path.join(base_dir, "unexecuted_cases.md")
                UnexecutedReportGenerator.generate_markdown_report(self.unexecuted_cases, md_file)
                
                # 生成Python脚本模板（便于执行）
                py_file = os.path.join(base_dir, "unexecuted_cases_template.py")
                UnexecutedReportGenerator.generate_executable_script(self.unexecuted_cases, py_file)
            
        except Exception as e:
            logger.error(f"保存未执行用例报告失败: {str(e)}")
            raise
    
    def save_execution_report(self, output_file: str = "reports/execution_report.yaml"):
        """
        保存执行报告
        
        参数：
        - output_file: 输出文件路径
        """
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            report = {
                "report_info": {
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_cases": self.stats["total"],
                    "executed": self.stats["executed"],
                    "passed": self.stats["passed"],
                    "failed": self.stats["failed"],
                    "skipped": self.stats["skipped"],
                    "main_flow_api": self.stats["main_flow_api"],
                    "sub_flow_ui": self.stats["sub_flow_ui"]
                },
                "execution_results": []
            }
            
            for item in self.execution_results:
                result_info = {
                    "test_case_name": item["test_case"].get("name"),
                    "test_type": item["test_case"].get("test_type"),
                    "is_main_flow": item["test_case"].get("is_main_flow", False),
                    "status": item["result"].get("status"),
                    "message": item["result"].get("message", ""),
                    "test_case": item["test_case"]
                }
                report["execution_results"].append(result_info)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(
                    report,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            
            logger.info(f"执行报告已保存: {output_file}")
            
        except Exception as e:
            logger.error(f"保存执行报告失败: {str(e)}")
            raise

