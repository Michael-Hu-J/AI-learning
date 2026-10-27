"""
步骤适配器 — 将 step_parser_service 的 skill/params 格式
转换为 ui_worker 期望的 action/target/value 格式

对应文章：第2篇-执行引擎
"""
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page


class StepAdapter:
    """步骤格式适配器"""
    
    # skill → action 映射
    SKILL_TO_ACTION = {
        'navigate': '打开页面',
        'input': '输入文本',
        'fill': '输入文本',
        'click': '点击元素',
        'select': '点击元素',
        'verify': '验证文本',
        'wait': '等待元素',
    }
    
    def __init__(self, page: Page):
        """
        参数：
        - page: Playwright Page 对象（用于元素定位）
        """
        self.page = page
    
    def adapt_steps(self, parsed_steps: List[Dict[str, Any]], base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        将解析后的步骤列表转换为 ui_worker 格式
        
        参数：
        - parsed_steps: step_parser_service.parse_description() 的返回值
        - base_url: 基础URL（用于补充缺失的导航步骤）
        
        返回：
        - ui_worker 格式的步骤列表
        """
        adapted = []
        
        for step in parsed_steps:
            skill = step.get('skill', '')
            params = step.get('params', {})
            
            # 转换单个步骤
            worker_step = self._adapt_step(skill, params, base_url)
            if worker_step:
                adapted.append(worker_step)
        
        return adapted
    
    def _adapt_step(self, skill: str, params: Dict[str, Any], base_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """转换单个步骤"""
        
        if skill == 'navigate':
            url = params.get('url', '')
            if not url and base_url:
                url = base_url
            if url:
                return {
                    'action': '打开页面',
                    'target': url,
                    'value': None,
                    'description': f'导航到 {url}'
                }
        
        elif skill == 'input':
            placeholder = params.get('placeholder', '')
            value = params.get('value', '')
            
            # 通过 placeholder 定位元素
            selector = self._find_input_by_placeholder(placeholder)
            if selector:
                return {
                    'action': '输入文本',
                    'target': selector,
                    'value': value,
                    'description': f'输入{placeholder}: {value}'
                }
            # 降级：用通用选择器
            return {
                'action': '输入文本',
                'target': f'[placeholder="{placeholder}"]',
                'value': value,
                'description': f'输入{placeholder}: {value}'
            }
        
        elif skill == 'fill':
            label = params.get('label', '')
            value = params.get('value', '')
            
            # 通过 label 定位
            selector = self._find_input_by_label(label)
            if selector:
                return {
                    'action': '输入文本',
                    'target': selector,
                    'value': value,
                    'description': f'填写{label}: {value}'
                }
            return {
                'action': '输入文本',
                'target': f'input[name="{label}"], input[placeholder="{label}"]',
                'value': value,
                'description': f'填写{label}: {value}'
            }
        
        elif skill == 'click':
            text = params.get('text', '')
            is_menu_parent = params.get('isMenuParent', False)
            
            if text:
                # 通过文本定位按钮/链接
                selector = f'text="{text}"'
                return {
                    'action': '点击元素',
                    'target': selector,
                    'value': None,
                    'description': f'点击: {text}'
                }
        
        elif skill == 'select':
            label = params.get('label', '')
            value = params.get('value', '')
            
            # 选择操作：先点击打开下拉，再选择对应选项
            steps = []
            
            # 第一步：点击选择器
            selector = self._find_select_by_label(label)
            if selector:
                steps.append({
                    'action': '点击元素',
                    'target': selector,
                    'value': None,
                    'description': f'点击选择: {label}'
                })
            
            # 第二步：选择选项
            steps.append({
                'action': '点击元素',
                'target': f'text="{value}"',
                'value': None,
                'description': f'选择: {value}'
            })
            
            return steps[0] if len(steps) == 1 else None  # 复杂选择需要多步处理
        
        elif skill == 'verify':
            text = params.get('text', '')
            if text:
                return {
                    'action': '验证文本',
                    'target': 'body',
                    'value': text,
                    'description': f'验证包含: {text}'
                }
        
        return None
    
    def _find_input_by_placeholder(self, placeholder: str) -> Optional[str]:
        """通过 placeholder 查找输入框"""
        try:
            locator = self.page.get_by_placeholder(placeholder)
            if locator.count() > 0:
                return f'[placeholder="{placeholder}"]'
        except:
            pass
        return None
    
    def _find_input_by_label(self, label: str) -> Optional[str]:
        """通过 label 查找输入框"""
        try:
            # 尝试多种定位策略
            selectors = [
                f'input[name="{label}"]',
                f'input[placeholder="{label}"]',
                f'#{label.lower().replace(" ", "-")}',
                f'#product-name',  # 商品名称
                f'#product-price',  # 价格
                f'#product-stock',  # 库存
            ]
            for selector in selectors:
                try:
                    locator = self.page.locator(selector)
                    if locator.count() > 0:
                        return selector
                except:
                    continue
        except:
            pass
        return None
    
    def _find_select_by_label(self, label: str) -> Optional[str]:
        """通过 label 查找下拉选择器"""
        try:
            selectors = [
                f'select[name="{label}"]',
                f'select[placeholder="{label}"]',
                f'#{label.lower().replace(" ", "-")}',
            ]
            for selector in selectors:
                try:
                    locator = self.page.locator(selector)
                    if locator.count() > 0:
                        return selector
                except:
                    continue
        except:
            pass
        return None


def adapt_steps_for_worker(parsed_steps: List[Dict[str, Any]], page: Page, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    便捷函数：将解析步骤转换为 worker 格式
    
    参数：
    - parsed_steps: step_parser_service.parse_description() 的返回值
    - page: Playwright Page 对象
    - base_url: 基础URL
    
    返回：
    - ui_worker 格式的步骤列表
    """
    adapter = StepAdapter(page)
    return adapter.adapt_steps(parsed_steps, base_url)
