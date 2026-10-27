# data_driver.py - 数据驱动测试
"""
数据驱动测试模块
功能：支持参数化测试用例，从外部数据源读取测试数据
"""
import yaml
import json
import csv
from typing import Dict, Any, List, Optional
from utils.logger import Logger

logger = Logger().get_logger()


class DataDriver:
    """
    数据驱动测试类
    
    功能：
    1. 从YAML/JSON/CSV文件加载测试数据
    2. 将测试数据注入到测试用例中
    3. 生成参数化的测试用例
    """
    
    @staticmethod
    def load_data(file_path: str) -> List[Dict[str, Any]]:
        """
        从文件加载测试数据
        
        参数：
        - file_path: 数据文件路径（支持.yaml, .json, .csv）
        
        返回：
        - List[Dict]: 测试数据列表
        """
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            return DataDriver._load_yaml(file_path)
        elif file_path.endswith('.json'):
            return DataDriver._load_json(file_path)
        elif file_path.endswith('.csv'):
            return DataDriver._load_csv(file_path)
        else:
            raise ValueError(f"不支持的数据文件格式: {file_path}")
    
    @staticmethod
    def _load_yaml(file_path: str) -> List[Dict[str, Any]]:
        """加载YAML数据文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                return [data] if data else []
    
    @staticmethod
    def _load_json(file_path: str) -> List[Dict[str, Any]]:
        """加载JSON数据文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                return [data] if data else []
    
    @staticmethod
    def _load_csv(file_path: str) -> List[Dict[str, Any]]:
        """加载CSV数据文件"""
        import csv as csv_lib
        data_list = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv_lib.DictReader(f)
            for row in reader:
                data_list.append(dict(row))
        return data_list
    
    @staticmethod
    def inject_data(test_case: Dict[str, Any], test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将测试数据注入到测试用例中
        
        参数：
        - test_case: 原始测试用例
        - test_data: 测试数据字典
        
        返回：
        - Dict: 注入数据后的测试用例
        
        支持的数据注入方式：
        1. 在用例名称中使用 {variable} 占位符
        2. 在steps中使用 {variable} 占位符替换值
        3. 支持嵌套字段，如 {user.username}
        """
        import copy
        injected_case = copy.deepcopy(test_case)
        
        # 替换用例名称中的变量
        if "name" in injected_case:
            injected_case["name"] = DataDriver._replace_variables(injected_case["name"], test_data)
        
        # 替换描述中的变量
        if "description" in injected_case:
            injected_case["description"] = DataDriver._replace_variables(injected_case["description"], test_data)
        
        # 替换steps中的变量
        if "steps" in injected_case:
            for step in injected_case["steps"]:
                DataDriver._inject_step_data(step, test_data)
        
        # 替换expected中的变量
        if "expected" in injected_case:
            if isinstance(injected_case["expected"], str):
                injected_case["expected"] = DataDriver._replace_variables(injected_case["expected"], test_data)
            elif isinstance(injected_case["expected"], dict):
                DataDriver._inject_dict_data(injected_case["expected"], test_data)
        
        return injected_case
    
    @staticmethod
    def _replace_variables(text: str, data: Dict[str, Any]) -> str:
        """
        替换文本中的变量占位符
        
        参数：
        - text: 包含占位符的文本，如 "用户{username}登录"
        - data: 数据字典
        
        返回：
        - str: 替换后的文本
        """
        import re
        
        def replace_var(match):
            var_path = match.group(1)
            value = DataDriver._get_nested_value(data, var_path)
            return str(value) if value is not None else match.group(0)
        
        # 匹配 {variable} 或 {nested.field}
        pattern = r'\{([^}]+)\}'
        return re.sub(pattern, replace_var, text)
    
    @staticmethod
    def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字典的值"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            if value is None:
                return None
        return value
    
    @staticmethod
    def _inject_step_data(step: Dict[str, Any], data: Dict[str, Any]):
        """在step中注入数据"""
        # 替换字符串值
        for key, value in step.items():
            if isinstance(value, str):
                step[key] = DataDriver._replace_variables(value, data)
            elif isinstance(value, dict):
                DataDriver._inject_dict_data(value, data)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        DataDriver._inject_dict_data(item, data)
    
    @staticmethod
    def _inject_dict_data(dict_obj: Dict[str, Any], data: Dict[str, Any]):
        """在字典中注入数据"""
        for key, value in dict_obj.items():
            if isinstance(value, str):
                dict_obj[key] = DataDriver._replace_variables(value, data)
            elif isinstance(value, dict):
                DataDriver._inject_dict_data(value, data)
    
    @staticmethod
    def generate_parametrized_cases(test_case: Dict[str, Any], data_file: str) -> List[Dict[str, Any]]:
        """
        生成参数化的测试用例列表
        
        参数：
        - test_case: 模板测试用例
        - data_file: 测试数据文件路径
        
        返回：
        - List[Dict]: 参数化后的测试用例列表
        """
        test_data_list = DataDriver.load_data(data_file)
        parametrized_cases = []
        
        for idx, test_data in enumerate(test_data_list):
            injected_case = DataDriver.inject_data(test_case, test_data)
            # 为用例添加数据标识
            injected_case["_data_index"] = idx
            injected_case["_data_source"] = data_file
            parametrized_cases.append(injected_case)
        
        logger.info(f"从 {data_file} 生成了 {len(parametrized_cases)} 个参数化用例")
        return parametrized_cases

