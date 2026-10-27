"""
分步演示：自然语言 → 解析 → 转换 → 执行
每一步都清晰展示，适合录屏演示

对应文章：第2篇-执行引擎、第3篇-三层定位降级
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from step_parser_service import step_parser_service


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_step(num: int, title: str):
    print(f"\n{'─'*40}")
    print(f"  步骤 {num}: {title}")
    print(f"{'─'*40}")


def demo_step_by_step(natural_language: str, base_url: str = "http://127.0.0.1:5000"):
    """
    分步演示：从自然语言到浏览器操作
    
    参数：
    - natural_language: 自然语言描述
    - base_url: 基础URL
    """
    print_header(" 分步演示：自然语言 → 浏览器操作")
    print(f"  输入: {natural_language}")
    print(f"  目标: {base_url}")
    
    # ==================== 第一步：解析自然语言 ====================
    print_step(1, "解析自然语言")
    print(f"  原始输入: {natural_language}")
    
    # 先显示分割结果
    parts = step_parser_service._split_description(natural_language)
    print(f"\n   分割结果 ({len(parts)} 个部分):")
    for i, part in enumerate(parts, 1):
        print(f"    [{i}] {part}")
    
    # 解析每个部分
    parsed_steps = step_parser_service.parse_description(natural_language, base_url)
    
    print(f"\n   解析结果 ({len(parsed_steps)} 个步骤):")
    for i, step in enumerate(parsed_steps, 1):
        skill = step.get('skill', 'unknown')
        params = step.get('params', {})
        desc = step.get('description', '')
        print(f"    [{i}] {skill}: {json.dumps(params, ensure_ascii=False)}")
        print(f"        → {desc}")
    
    # ==================== 第二步：Playwright 执行 ====================
    print_step(2, "启动浏览器并执行")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        results = []
        
        for i, parsed_step in enumerate(parsed_steps, 1):
            skill = parsed_step.get('skill', '')
            params = parsed_step.get('params', {})
            desc = parsed_step.get('description', '')
            
            print(f"\n  [执行步骤 {i}/{len(parsed_steps)}] {desc}")
            
            try:
                if skill == 'navigate':
                    url = params.get('url', base_url)
                    page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    print(f"     导航到: {page.url}")
                    results.append({'step': i, 'status': 'passed', 'action': 'navigate'})
                
                elif skill == 'input':
                    placeholder = params.get('placeholder', '')
                    value = params.get('value', '')
                    
                    try:
                        page.get_by_placeholder(placeholder).fill(value, timeout=5000)
                        print(f"     输入 {placeholder}: {value}")
                        results.append({'step': i, 'status': 'passed', 'action': 'input'})
                    except Exception as e:
                        try:
                            page.fill(f'[placeholder="{placeholder}"]', value, timeout=5000)
                            print(f"     输入 {placeholder}: {value} (降级定位)")
                            results.append({'step': i, 'status': 'passed', 'action': 'input'})
                        except Exception as e2:
                            print(f"     失败: {e2}")
                            results.append({'step': i, 'status': 'failed', 'action': 'input', 'error': str(e2)})
                
                elif skill == 'fill':
                    label = params.get('label', '')
                    value = params.get('value', '')
                    
                    # 商品相关字段的 id 映射
                    label_to_id = {
                        '商品名称': '#product-name',
                        '价格': '#product-price',
                        '单价': '#product-price',
                        '库存': '#product-stock',
                    }
                    
                    filled = False
                    selectors = [
                        f'input[name="{label}"]',
                        f'input[placeholder="{label}"]',
                    ]
                    if label in label_to_id:
                        selectors.insert(0, label_to_id[label])
                    
                    for selector in selectors:
                        try:
                            page.fill(selector, str(value), timeout=2000)
                            print(f"     填写 {label}: {value}")
                            results.append({'step': i, 'status': 'passed', 'action': 'fill'})
                            filled = True
                            break
                        except:
                            continue
                    
                    if not filled:
                        print(f"     失败: 找不到输入框 {label}")
                        results.append({'step': i, 'status': 'failed', 'action': 'fill', 'error': f'找不到输入框 {label}'})
                
                elif skill == 'click':
                    text = params.get('text', '')

                    try:
                        # 检测点击后是否触发页面跳转（通过后续步骤判断）
                        next_skill = parsed_steps[i]['skill'] if i < len(parsed_steps) else ''
                        waits_for_nav = next_skill in ('wait_url', 'navigate')

                        # 优先匹配可交互元素，避免点到标题/标签等不可点击元素
                        selectors = [
                            f'button:has-text("{text}")',
                            f'a:has-text("{text}")',
                            f'[role="button"]:has-text("{text}")',
                            f'input[type="submit"][value*="{text}"]',
                            f'text="{text}"',
                        ]

                        clicked = False
                        for sel in selectors:
                            try:
                                el = page.locator(sel).first
                                if el.is_visible() and el.is_enabled():
                                    if waits_for_nav:
                                        # 不等待导航，由后续 wait_url 步骤处理
                                        page.click(sel, timeout=5000)
                                        print(f"     点击: {text}（由后续步骤等待跳转）")
                                    else:
                                        page.click(sel, timeout=5000)
                                        page.wait_for_timeout(500)
                                        print(f"     点击: {text}")
                                    clicked = True
                                    break
                            except:
                                continue

                        if not clicked:
                            raise Exception(f'找不到可点击元素: {text}')

                        results.append({'step': i, 'status': 'passed', 'action': 'click'})
                    except Exception as e:
                        print(f"     失败: {e}")
                        results.append({'step': i, 'status': 'failed', 'action': 'click', 'error': str(e)})
                
                elif skill == 'wait_url':
                    pattern = params.get('pattern', '')
                    try:
                        page.wait_for_url(pattern, timeout=15000)
                        print(f"     等待 URL 匹配: {pattern} → 当前: {page.url}")
                        results.append({'step': i, 'status': 'passed', 'action': 'wait_url'})
                    except Exception:
                        # 如果 wait_for_url 超时，手动轮询
                        for _ in range(30):
                            page.wait_for_timeout(500)
                            if pattern.replace('**/', '') in page.url:
                                print(f"     等待 URL 匹配: {pattern} → 当前: {page.url}")
                                results.append({'step': i, 'status': 'passed', 'action': 'wait_url'})
                                break
                        else:
                            print(f"     失败: URL 未匹配 {pattern}（当前: {page.url}）")
                            results.append({'step': i, 'status': 'failed', 'action': 'wait_url', 'error': f'URL mismatch: {page.url}'})

                elif skill == 'select':
                    label = params.get('label', '')
                    value = params.get('value', '')
                    
                    try:
                        page.click(f'select[name="{label}"], select[placeholder="{label}"]', timeout=5000)
                        page.wait_for_timeout(500)
                        page.click(f'text="{value}"', timeout=5000)
                        print(f"     选择 {label}: {value}")
                        results.append({'step': i, 'status': 'passed', 'action': 'select'})
                    except Exception as e:
                        print(f"     失败: {e}")
                        results.append({'step': i, 'status': 'failed', 'action': 'select', 'error': str(e)})
                
                elif skill == 'verify':
                    text = params.get('text', '')
                    try:
                        body = page.content()
                        if text in body:
                            print(f"     验证通过：页面包含 '{text}'")
                            results.append({'step': i, 'status': 'passed', 'action': 'verify'})
                        else:
                            print(f"     验证失败：页面不包含 '{text}'")
                            results.append({'step': i, 'status': 'failed', 'action': 'verify'})
                    except Exception as e:
                        print(f"     失败: {e}")
                        results.append({'step': i, 'status': 'failed', 'action': 'verify', 'error': str(e)})
            
            except Exception as e:
                print(f"     步骤执行异常: {e}")
                results.append({'step': i, 'status': 'error', 'action': skill, 'error': str(e)})
        
        # ==================== 第三步：显示结果 ====================
        print_header(" 执行结果")
        
        passed = sum(1 for r in results if r['status'] == 'passed')
        failed = sum(1 for r in results if r['status'] != 'passed')
        
        print(f"  总计: {len(results)} 个步骤")
        print(f"   通过: {passed}")
        print(f"   失败: {failed}")
        print()
        
        for r in results:
            icon = "" if r['status'] == 'passed' else ""
            print(f"  {icon} 步骤 {r['step']}: {r['action']}")
        
        print(f"\n{'='*60}")
        print(f"  演示完成！")
        print(f"{'='*60}\n")
        
        browser.close()
    
    return results


def demo_login():
    """演示：登录系统"""
    natural_language = "用户名：admin，密码：admin123，点击登录"
    return demo_step_by_step(natural_language, "http://127.0.0.1:5000/login")


def demo_add_product():
    """演示：添加商品"""
    natural_language = "导航到：http://127.0.0.1:5000/products，点击新增商品按钮，商品名称：测试商品，价格：199.9，库存：50，点击确认添加"
    return demo_step_by_step(natural_language, "http://127.0.0.1:5000/products")


def demo_full_flow():
    """演示：完整流程"""
    natural_language = "用户名：admin，密码：admin123，点击登录，导航到：http://127.0.0.1:5000/products，点击新增商品，商品名称：Playwright测试商品，价格：299.9，库存：100，点击确认添加"
    return demo_step_by_step(natural_language, "http://127.0.0.1:5000/products")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="分步演示：自然语言 → 浏览器操作")
    parser.add_argument('--demo', choices=['login', 'add_product', 'full_flow'],
                       default='full_flow', help='选择演示场景')
    parser.add_argument('--custom', type=str, help='自定义自然语言描述')
    
    args = parser.parse_args()
    
    if args.custom:
        demo_step_by_step(args.custom, "http://127.0.0.1:5000")
    elif args.demo == 'login':
        demo_login()
    elif args.demo == 'add_product':
        demo_add_product()
    elif args.demo == 'full_flow':
        demo_full_flow()


if __name__ == "__main__":
    main()
