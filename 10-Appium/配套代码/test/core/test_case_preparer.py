# test_case_preparer.py - 测试用例准备器
"""
测试用例准备器
功能：在执行测试前，检查并准备所有必需的用例和代码
保证可以全量回归执行
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from utils.logger import Logger
# from utils.test_case_registry import get_registry  # 已删除

logger = Logger().get_logger()


class TestCasePreparer:
    """
    测试用例准备器
    
    功能：
    1. 检查YAML用例文件是否存在
    2. 检查对应的Page Object代码是否存在
    3. 检查对应的测试代码是否存在
    4. 如果不存在，自动生成
    """
    
    def __init__(self, yaml_dir: str = "testcases/yaml", 
                 pages_dir: str = "pages",
                 tests_dir: str = "tests"):
        """
        初始化准备器
        
        参数：
        - yaml_dir: YAML用例文件目录
        - pages_dir: Page Object代码目录
        - tests_dir: 测试代码目录
        """
        self.yaml_dir = Path(yaml_dir)
        self.pages_dir = Path(pages_dir)
        self.tests_dir = Path(tests_dir)
        self.registry = get_registry()
    
    def prepare_for_execution(self, yaml_file: str, force_regenerate: bool = False) -> Dict[str, bool]:
        """
        准备测试用例以便执行
        
        参数：
        - yaml_file: YAML用例文件路径
        - force_regenerate: 是否强制重新生成（即使已存在）
        
        返回：
        - Dict: {
            "yaml_exists": bool,
            "page_exists": bool,
            "test_exists": bool,
            "page_generated": bool,
            "test_generated": bool
        }
        """
        yaml_path = Path(yaml_file)
        if not yaml_path.exists():
            logger.warning(f"YAML文件不存在: {yaml_file}")
            return {
                "yaml_exists": False,
                "page_exists": False,
                "test_exists": False,
                "page_generated": False,
                "test_generated": False
            }
        
        result = {
            "yaml_exists": True,
            "page_exists": False,
            "test_exists": False,
            "page_generated": False,
            "test_generated": False
        }
        
        # 从YAML文件名推断页面名称
        page_name = self._extract_page_name_from_yaml(yaml_path)
        
        # 检查Page Object是否存在
        page_file = self.pages_dir / f"{page_name}_page.py"
        if page_file.exists() and not force_regenerate:
            logger.debug(f" Page Object已存在: {page_file}")
            result["page_exists"] = True
            result["page_file"] = str(page_file)
        else:
            # Page Object不存在，需要生成
            logger.info(f" Page Object不存在: {page_file}")
            result["page_generated"] = True
        
        # 检查测试代码是否存在
        test_file = self._find_test_file(page_name)
        if test_file and not force_regenerate:
            logger.debug(f" 测试代码已存在: {test_file}")
            result["test_exists"] = True
            result["test_file"] = test_file
        else:
            # 测试代码不存在，需要生成
            logger.info(f" 测试代码不存在，需要生成")
            result["test_generated"] = True
        
        # 如果需要生成代码，调用生成器
        if result["test_generated"]:
            try:
                from scripts.generate_python_test_from_yaml import PythonTestGenerator
                logger.info(f" 开始生成测试代码...")
                generator = PythonTestGenerator(str(yaml_path))
                output_file = generator.generate_complete_test_file(
                    output_file=f"tests/test_{page_name}_generated.py"
                )
                logger.info(f" 代码已生成: {output_file}")
                result["test_file"] = output_file
                result["test_exists"] = True
                
                # 注册到注册表
                case_key = f"{yaml_path.stem}-generated"
                self.registry.register_test_case(
                    case_key=case_key,
                    yaml_file=str(yaml_path),
                    test_file=output_file
                )
            except Exception as e:
                logger.error(f"生成代码失败: {e}")
                import traceback
                traceback.print_exc()
        
        return result
    
    def _extract_page_name_from_yaml(self, yaml_path: Path) -> str:
        """从YAML文件名提取页面名称"""
        stem = yaml_path.stem
        
        # 移除常见的后缀（按长度从长到短排序）
        suffixes = ["_page_test", "page_test_", "_test", "test_", "_case", "case_", "_page", "page_"]
        for suffix in sorted(suffixes, key=len, reverse=True):
            if stem.endswith(suffix):
                stem = stem[:-len(suffix)]
            if stem.startswith(suffix):
                stem = stem[len(suffix):]
        
        # 如果还有_page后缀，移除它（避免重复）
        if stem.endswith("_page"):
            stem = stem[:-5]
        
        return stem
    
    def _find_test_file(self, page_name: str) -> Optional[str]:
        """查找测试文件"""
        possible_names = [
            f"test_{page_name}.py",
            f"test_{page_name}_page.py",
            f"{page_name}_test.py"
        ]
        
        for name in possible_names:
            test_file = self.tests_dir / name
            if test_file.exists():
                return str(test_file)
        
        return None
    
    def check_all_cases_ready(self, yaml_files: Optional[List[str]] = None) -> Dict[str, any]:
        """
        检查所有用例是否准备就绪
        
        参数：
        - yaml_files: YAML文件列表，如果为None则扫描yaml_dir
        
        返回：
        - Dict: {
            "total": int,
            "ready": int,
            "missing_page": List[str],
            "missing_test": List[str]
        }
        """
        if yaml_files is None:
            yaml_files = [str(f) for f in self.yaml_dir.rglob("*.yaml")]
        
        stats = {
            "total": len(yaml_files),
            "ready": 0,
            "missing_page": [],
            "missing_test": []
        }
        
        for yaml_file in yaml_files:
            result = self.prepare_for_execution(yaml_file)
            if result["page_exists"] and result["test_exists"]:
                stats["ready"] += 1
            else:
                if not result["page_exists"]:
                    stats["missing_page"].append(yaml_file)
                if not result["test_exists"]:
                    stats["missing_test"].append(yaml_file)
        
        return stats

