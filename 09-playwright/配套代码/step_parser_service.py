"""
步骤描述解析服务
优先 LLM 拆分自然语言；无模型或失败时降级为规则解析。
"""
import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from loguru import logger


class StepParserService:
    """步骤描述解析服务"""
    
    def __init__(self):
        # 定义操作模式
        self.patterns = {
            'navigate': [
                r'导航到[：:]\s*([^\s，,。]+)',
                r'访问[：:]\s*([^\s，,。]+)',
                r'打开[：:]\s*([^\s，,。]+)',
                r'([a-zA-Z]+://[^\s，,。]+)',
            ],
            'input': [
                r'用户名[输入填写填入]*[：:]\s*([^\s，,。]+)',
                r'密码[输入填写填入]*[：:]\s*([^\s，,。]+)',
                r'([^，,。]+)[输入填写填入][：:]\s*([^\s，,。]+)',
                r'输入[：:]\s*([^\s，,。]+)',
                r'填写[：:]\s*([^\s，,。]+)',
            ],
            'fill': [
                r'把["""]([^"""]+)["""][改成改为修改为]*[：:]\s*([^\s，,。]+)',
                r'["""]([^"""]+)["""][改成改为修改为]*[：:]\s*([^\s，,。]+)',
                r'([^，,。]+)[改成改为修改为][：:]\s*([^\s，,。]+)',
                r'数量[填填写]*[：:]\s*(\d+)',
                r'单价[填填写]*[：:]\s*(\d+)',
            ],
            'click': [
                r'点击["""]([^"""]+)["""]',
                r'点击([^，,。]+)按钮',
                r'点击([^，,。]+)',
                r'左键点击["""]([^"""]+)["""]',
            ],
            'select': [
                r'选择["""]([^"""]+)["""]',
                r'供应商选择[：:]\s*([^\s，,。]+)',
                r'商品[明细]*选择[：:]\s*([^\s，,。]+)',
                r'([^，,。]+)选择[：:]\s*([^\s，,。]+)',
            ],
        }
    
    def parse_description(self, description: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        解析步骤描述，识别多个操作
        
        Args:
            description: 步骤描述文本
            base_url: 基础URL（如果描述中包含相对路径）
            
        Returns:
            拆分后的步骤列表
        """
        if not description or not description.strip():
            return []

        description = description.strip()

        mode = os.getenv("NL_PARSER", "auto").strip().lower()  # auto | llm | regex
        if mode in ("auto", "llm"):
            from llm_step_parser import llm_available, parse_with_llm

            if mode == "llm" or llm_available():
                try:
                    steps = parse_with_llm(description, base_url)
                    logger.info(f"LLM 拆分: {len(steps)} 个步骤")
                    return steps
                except Exception as e:
                    if mode == "llm":
                        raise
                    logger.warning(f"LLM 拆分失败，降级规则解析: {e}")

        steps = []
        
        # 按标点符号分割（保留分隔符以便上下文分析）
        # 使用更智能的分割方式
        parts = self._split_description(description)
        
        logger.info(f"解析描述: {description}")
        logger.info(f"分割后的部分: {parts}")
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 尝试识别各种操作
            parsed_steps = self._parse_part(part, base_url)
            steps.extend(parsed_steps)
        
        # 如果没有识别到任何操作，返回原始描述作为 navigate 步骤
        if not steps and base_url:
            steps.append({
                'skill': 'navigate',
                'params': {'url': base_url},
                'description': description
            })

        has_login_fields = any(
            s.get("skill") in ("input", "fill")
            and isinstance(s.get("params"), dict)
            and s["params"].get("placeholder") in ("用户名", "密码")
            for s in steps
        )

        if has_login_fields:
            origin = None
            if base_url:
                parsed = urlparse(base_url)
                if parsed.scheme and parsed.netloc:
                    origin = f"{parsed.scheme}://{parsed.netloc}"
            if not origin:
                for s in steps:
                    if s.get("skill") == "navigate" and isinstance(s.get("params"), dict):
                        url = s["params"].get("url")
                        if isinstance(url, str):
                            parsed = urlparse(url)
                            if parsed.scheme and parsed.netloc:
                                origin = f"{parsed.scheme}://{parsed.netloc}"
                                break

            if origin:
                login_url = f"{origin}/login"
                has_login_navigate = any(
                    s.get("skill") == "navigate"
                    and isinstance(s.get("params"), dict)
                    and isinstance(s["params"].get("url"), str)
                    and "/login" in s["params"]["url"]
                    for s in steps
                )
                if not has_login_navigate:
                    insert_at = 0
                    for i, s in enumerate(steps):
                        if s.get("skill") in ("input", "fill") and isinstance(s.get("params"), dict) and s["params"].get("placeholder") == "用户名":
                            insert_at = i
                            break
                    steps.insert(
                        insert_at,
                        {"skill": "navigate", "params": {"url": login_url}, "description": f"导航到 {login_url}"},
                    )

            has_login_click = any(
                s.get("skill") == "click"
                and isinstance(s.get("params"), dict)
                and s["params"].get("text") in ("登录", "Login")
                for s in steps
            )
            if not has_login_click:
                insert_at = None
                for i, s in enumerate(steps):
                    if s.get("skill") in ("input", "fill") and isinstance(s.get("params"), dict) and s["params"].get("placeholder") == "密码":
                        insert_at = i + 1
                        break
                if insert_at is not None:
                    steps.insert(insert_at, {"skill": "click", "params": {"text": "登录"}, "description": "点击: 登录"})

            if base_url and isinstance(base_url, str) and base_url.strip():
                has_target_navigate = any(
                    s.get("skill") == "navigate"
                    and isinstance(s.get("params"), dict)
                    and s["params"].get("url") == base_url
                    for s in steps
                )
                if not has_target_navigate:
                    last_login_click = None
                    for i, s in enumerate(steps):
                        if s.get("skill") == "click" and isinstance(s.get("params"), dict) and s["params"].get("text") in ("登录", "Login"):
                            last_login_click = i
                    if last_login_click is not None:
                        steps.insert(last_login_click + 1, {"skill": "navigate", "params": {"url": base_url}, "description": f"导航到 {base_url}"})
        
        logger.info(f"解析结果: {len(steps)} 个步骤")
        return steps
    
    def _split_description(self, description: str) -> List[str]:
        """智能分割描述文本"""
        # 先保护 URL（避免 URL 中的 . 被当成分隔符）
        url_placeholder = "__URL_PLACEHOLDER__"
        urls = []
        
        # 提取所有 URL
        def replace_url(match):
            urls.append(match.group(0))
            return url_placeholder
        
        protected = re.sub(r'https?://[^\s，,。]+', replace_url, description)
        
        # 按常见分隔符分割
        separators = ['，', ',', '。', '.', '；', ';', '、', '\n']
        
        parts = []
        current_part = ''
        
        for char in protected:
            if char in separators:
                if current_part.strip():
                    parts.append(current_part.strip())
                    current_part = ''
            else:
                current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        # 恢复 URL
        if not parts:
            parts = [description]
        
        # 替换回 URL
        final_parts = []
        url_idx = 0
        for part in parts:
            if url_placeholder in part and url_idx < len(urls):
                part = part.replace(url_placeholder, urls[url_idx])
                url_idx += 1
            final_parts.append(part)
        
        return final_parts
    
    def _parse_part(self, part: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """解析单个描述部分"""
        steps = []

        if any(sep in part for sep in ["-", "—", "－", ">", "＞", "→"]) and not any(
            k in part for k in ["http://", "https://", "输入", "填写", "填入", "点击", "选择", "导航", "访问", "打开"]
        ):
            segments = [s.strip() for s in re.split(r"[-—－>＞→]+", part) if s.strip()]
            if len(segments) >= 2:
                parent = segments[0]
                steps.append({"skill": "click", "params": {"text": parent, "isMenuParent": True}, "description": f"点击: {parent}"})
                for child in segments[1:]:
                    steps.append(
                        {
                            "skill": "click",
                            "params": {"text": child, "menuParent": parent, "isMenuChild": True},
                            "description": f"点击: {child}",
                        }
                    )
                return steps
        
        # 1. 检查是否是导航操作
        # 使用更精确的 URL 匹配，确保不包含前面的中文字符
        # 匹配模式：URL 前不能是中文字符或单词字符
        url_match = re.search(r'(?:^|[^\w\u4e00-\u9fa5])(https?://[^\s，,。]+)', part)
        if url_match:
            url = url_match.group(1).strip()  # 使用第二个捕获组（URL部分）
            # 验证 URL 格式
            if url.startswith('http://') or url.startswith('https://'):
                steps.append({
                    'skill': 'navigate',
                    'params': {'url': url},
                    'description': f'导航到 {url}'
                })
                return steps
        
        # 2. 检查是否是输入操作（用户名、密码等）
        # 用户名输入（支持多种格式：用户名输入admin、用户名：admin、用户名admin）
        # 注意：[：:\s]* 表示冒号或空格是可选的，支持"用户名输入admin"（无空格）格式
        username_patterns = [
            r'用户名[输入填写填入]*[：:\s]*([^\s，,。；;、]+)',  # 用户名输入admin、用户名输入 admin、用户名：admin
            r'用户[名]*[：:\s]*([^\s，,。；;、]+)',  # 用户：admin、用户 admin
        ]
        for pattern in username_patterns:
            username_match = re.search(pattern, part)
            if username_match:
                username = username_match.group(1).strip()
                steps.append({
                    'skill': 'input',
                    'params': {
                        'placeholder': '用户名',
                        'value': username
                    },
                    'description': f'输入用户名: {username}'
                })
                return steps  # 找到后立即返回，避免重复匹配
        
        # 密码输入（支持多种格式：密码输入admin123、密码：admin123、密码admin123）
        # 匹配：密码输入admin123、密码输入 admin123、密码：admin123、密码 admin123
        password_patterns = [
            r'密码[输入填写填入]*[：:\s]*([^\s，,。；;、]+)',  # 密码输入admin123、密码输入 admin123、密码：admin123
        ]
        for pattern in password_patterns:
            password_match = re.search(pattern, part)
            if password_match:
                password = password_match.group(1).strip()
                steps.append({
                    'skill': 'input',
                    'params': {
                        'placeholder': '密码',
                        'value': password
                    },
                    'description': f'输入密码: {password}'
                })
                return steps  # 找到后立即返回，避免重复匹配
        
        # 3. 检查是否是填充操作（商品名称、价格、库存等）
        # 商品名称
        product_name_match = re.search(r'商品名称[填填写]*[：:\s]*([^\s，,。；;、]+)', part)
        if product_name_match:
            product_name = product_name_match.group(1).strip()
            steps.append({
                'skill': 'fill',
                'params': {
                    'label': '商品名称',
                    'value': product_name
                },
                'description': f'填写商品名称: {product_name}'
            })
            return steps
        
        # 库存
        stock_match = re.search(r'库存[填填写]*[：:\s]*(\d+)', part)
        if stock_match:
            stock = stock_match.group(1)
            steps.append({
                'skill': 'fill',
                'params': {
                    'label': '库存',
                    'value': stock
                },
                'description': f'填写库存: {stock}'
            })
            return steps
        
        # 数量（支持多种格式）
        quantity_patterns = [
            r'购买数量[填填写]*[：:\s]*(\d+)',
            r'数量[填填写]*[：:\s]*(\d+)',
        ]
        for pattern in quantity_patterns:
            quantity_match = re.search(pattern, part)
            if quantity_match:
                quantity = quantity_match.group(1)
                steps.append({
                    'skill': 'fill',
                    'params': {
                        'label': '购买数量',
                        'value': quantity
                    },
                    'description': f'填写数量: {quantity}'
                })
                return steps
        
        # 单价/价格（支持小数）
        price_patterns = [
            r'单价[填填写]*[：:\s]*(\d+\.?\d*)',
            r'价格[填填写]*[：:\s]*(\d+\.?\d*)',
        ]
        for pattern in price_patterns:
            price_match = re.search(pattern, part)
            if price_match:
                price = price_match.group(1)
                steps.append({
                    'skill': 'fill',
                    'params': {
                        'label': '单价',
                        'value': price
                    },
                    'description': f'填写单价: {price}'
                })
                return steps
        
        # 通用填充模式：把"xxx"改成yyy
        fill_match = re.search(r'把["""]([^"""]+)["""][改成改为修改为]*[：:]\s*([^\s，,。]+)', part)
        if fill_match:
            field_name = fill_match.group(1)
            field_value = fill_match.group(2)
            steps.append({
                'skill': 'fill',
                'params': {
                    'label': field_name,
                    'value': field_value
                },
                'description': f'填写{field_name}: {field_value}'
            })
        
        # 4. 检查是否是点击操作（必须在 select 之前，避免 "点击新增商品按钮" 被误匹配）
        # 点击按钮（带引号）
        click_quoted_match = re.search(r'点击[""""]([^"""]+)[""""]', part)
        if click_quoted_match:
            button_text = click_quoted_match.group(1)
            steps.append({
                'skill': 'click',
                'params': {
                    'text': button_text
                },
                'description': f'点击: {button_text}'
            })
            return steps
        
        # 点击按钮（不带引号，但包含"按钮"）
        click_button_match = re.search(r'点击([^，,。]+)按钮', part)
        if click_button_match:
            button_text = click_button_match.group(1).strip()
            steps.append({
                'skill': 'click',
                'params': {
                    'text': button_text
                },
                'description': f'点击: {button_text}'
            })
            return steps
        
        # 5. 检查是否是选择操作
        # 供应商选择（支持多种格式：供应商选择苹果供应商、供应商：苹果供应商）
        # 注意：[：:\s]* 表示冒号或空格是可选的，支持"供应商选择苹果供应商"（无空格）格式
        supplier_patterns = [
            r'供应商选择[：:\s]*([^\s，,。；;、]+)',  # 供应商选择苹果供应商、供应商选择 苹果供应商
            r'供应商[：:\s]*([^\s，,。；;、]+)',  # 供应商：苹果供应商、供应商 苹果供应商
            r'选择供应商[：:\s]*([^\s，,。；;、]+)',  # 选择供应商：苹果供应商
        ]
        for pattern in supplier_patterns:
            supplier_match = re.search(pattern, part)
            if supplier_match:
                supplier = supplier_match.group(1).strip()
                steps.append({
                    'skill': 'select',
                    'params': {
                        'label': '供应商',
                        'value': supplier
                    },
                    'description': f'选择供应商: {supplier}'
                })
                return steps  # 找到后立即返回，避免重复匹配
        
        # 商品选择（支持多种格式：商品明细选择iphone 15 pro、商品选择iphone 15 pro）
        # 注意：商品名称可能包含空格，所以需要匹配到下一个分隔符（逗号、句号等）
        # [：:\s]* 表示冒号或空格是可选的，支持"商品明细选择iphone 15 pro"（无空格）格式
        product_patterns = [
            r'商品[明细]*选择[：:\s]*([^，,。；;、]+)',  # 商品明细选择iphone 15 pro（允许空格）
            r'商品[明细]*[：:\s]*([^，,。；;、]+)',  # 商品明细：iphone 15 pro、商品明细 iphone 15 pro
            r'选择商品[明细]*[：:\s]*([^，,。；;、]+)',  # 选择商品明细：iphone 15 pro
        ]
        for pattern in product_patterns:
            product_match = re.search(pattern, part)
            if product_match:
                product = product_match.group(1).strip()
                steps.append({
                    'skill': 'select',
                    'params': {
                        'label': '商品明细',
                        'value': product
                    },
                    'description': f'选择商品: {product}'
                })
                return steps  # 找到后立即返回，避免重复匹配
        
        # 6. 通用点击模式
        if '点击' in part and not any(step.get('skill') == 'click' for step in steps):
            # 提取点击的目标
            click_target_match = re.search(r'点击([^，,。]+)', part)
            if click_target_match:
                target = click_target_match.group(1).strip()
                steps.append({
                    'skill': 'click',
                    'params': {
                        'text': target
                    },
                    'description': f'点击: {target}'
                })
        
        # 6. 如果没有识别到任何操作，但包含导航相关关键词，创建导航步骤
        if not steps and base_url and any(keyword in part for keyword in ['导航', '访问', '打开']):
            steps.append({
                'skill': 'navigate',
                'params': {'url': base_url},
                'description': part
            })
        
        return steps


# 全局服务实例
step_parser_service = StepParserService()
