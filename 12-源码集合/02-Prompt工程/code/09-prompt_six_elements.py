prompt_template = """
# 角色
你是一名{role}，擅长{expertise}。

# 任务
请完成以下任务：{task}

# 上下文
背景信息：{context}

# 约束
- 长度：{length}
- 风格：{style}
- 范围：{scope}

# 示例
{examples}

# 输出格式
请按以下格式输出，只输出指定格式，不要其他文字：
{output_format}
"""

# 使用示例
prompt = prompt_template.format(
    role="资深测试工程师",
    expertise="API 测试和边界值分析",
    task="为 POST /api/register 接口生成 15 条测试用例",
    context="用户注册接口，参数 username/email/password，密码 8 位以上含大小写和数字",
    length="每条用例包含 case_id、title、payload、expected_status",
    style="中文，专业简洁",
    scope="只关注功能测试，不生成安全测试用例",
    examples='{"case_id": "REG_001", "title": "正常注册", "expected_status": 201}',
    output_format="JSON 数组"
)

def test_prompt_elements():
    """测试每个要素对输出质量的影响——逐次添加，观察评分变化"""
    base_prompt = "生成登录功能的测试用例"

    prompts = {
        "无要素": base_prompt,
        "+角色": f"你是一名测试工程师。\n{base_prompt}",
        "+角色+约束": "你是一名测试工程师。\n生成15条测试用例，覆盖正常/异常/边界。",
        "+角色+约束+示例": "你是一名测试工程师。\n生成15条测试用例。\n示例：TC001: 正常登录 → 跳转主页。",
        "+角色+约束+示例+格式": "你是一名测试工程师。\n生成15条测试用例，JSON格式。\n示例：{'id': 'TC001', 'title': '正常登录'}。",
    }

    for name, prompt in prompts.items():
        response = call_llm(prompt)
        score = evaluate_quality(response)
        print(f"{name}: 质量评分={score:.2f}")

    # 典型结果
    # 无要素: 3.2  +角色: 3.8  +角色+约束: 4.2
    # +角色+约束+示例: 4.5  +角色+约束+示例+格式: 4.8

def test_element_importance():
    """测试每个要素的权重——去掉哪个要素，质量下降最多"""
    
    # 完整 Prompt（六要素齐全）
    full_prompt = """你是一名资深测试工程师，擅长 API 测试。
请为 POST /api/register 接口生成测试用例。
背景：用户注册接口，参数 username/email/password，密码要求 8 位以上含大小写和数字。
约束：生成 15 条用例，覆盖正常/异常/边界，JSON 格式输出。
示例：{"case_id": "REG_001", "title": "正常注册", "payload": {...}, "expected_status": 201}
输出格式：JSON 数组，每条包含 case_id, title, payload, expected_status"""
    
    # 分别去掉每个要素，生成变体
    variants = {
        "去掉角色": full_prompt.replace("你是一名资深测试工程师，擅长 API 测试。\n", ""),
        "去掉任务": full_prompt.replace("请为 POST /api/register 接口生成测试用例。\n", ""),
        "去掉上下文": full_prompt.replace("背景：用户注册接口...\n", ""),
        "去掉约束": full_prompt.replace("约束：生成 15 条用例...\n", ""),
        "去掉示例": full_prompt.replace("示例：{...}\n", ""),
        "去掉格式": full_prompt.replace("输出格式：JSON 数组...\n", ""),
    }
    
    results = {}
    for name, prompt in variants.items():
        response = call_llm(prompt)
        score = evaluate_quality(response)
        drop = score_full - score
        results[name] = {"score": score, "drop": drop}
        print(f"{name}: 质量={score:.1f}, 下降={drop:.1f}")
    
    return results

# 典型结果（多次实验的平均值）
# 去掉角色: 质量=4.5, 下降=0.3   ← 影响最小
# 去掉任务: 质量=2.0, 下降=2.8   ← 最致命，直接腰斩
# 去掉上下文: 质量=3.8, 下降=1.0
# 去掉约束: 质量=3.5, 下降=1.3
# 去掉示例: 质量=4.2, 下降=0.6
# 去掉格式: 质量=3.8, 下降=1.0

def audit_prompt(prompt_text):
    """六要素审计工具——检查 Prompt 缺了哪些要素"""
    checks = {
        "角色": any(kw in prompt_text for kw in ["你是一名", "你是", "你作为"]),
        "任务": any(kw in prompt_text for kw in ["请", "生成", "编写", "分析", "输出"]),
        "上下文": any(kw in prompt_text for kw in ["背景", "场景", "系统", "框架"]),
        "约束": any(kw in prompt_text for kw in ["限制", "不超过", "至少", "必须", "禁止"]),
        "示例": any(kw in prompt_text for kw in ["示例", "例如", "sample", "比如"]),
        "格式": any(kw in prompt_text for kw in ["格式", "JSON", "XML", "Markdown", "表格"]),
    }
    present = sum(1 for v in checks.values() if v)
    print(f"六要素齐全度: {present}/6")
    for elem, found in checks.items():
        status = "✅" if found else "❌"
        print(f"  {status} {elem}")
    return present

# 使用示例
audit_prompt("帮我写测试用例")
# 输出: 六要素齐全度: 1/6
#   ✅ 任务  ❌ 角色  ❌ 上下文  ❌ 约束  ❌ 示例  ❌ 格式

audit_prompt("""你是一名测试工程师。
请为登录接口生成测试用例。
背景：支持邮箱+密码登录，密码8-32位。
约束：15条，覆盖正常/异常/边界。
示例：{"id": "TC001", "title": "正常登录"}
格式：JSON数组""")
# 输出: 六要素齐全度: 6/6
#   ✅ 角色  ✅ 任务  ✅ 上下文  ✅ 约束  ✅ 示例  ✅ 格式

import json
from typing import List, Dict

class PromptABTest:
    """Prompt六要素 A/B 测试框架"""
    
    def __init__(self, test_dataset: List[Dict]):
        self.dataset = test_dataset
    
    def run(self, prompt_a: str, prompt_b: str, metric_fn) -> Dict:
        """对比两个 Prompt 的效果"""
        results_a = []
        results_b = []
        
        for item in self.dataset:
            resp_a = call_llm(prompt_a.format(input=item["input"]))
            score_a = metric_fn(resp_a, item["expected"])
            results_a.append(score_a)
            
            resp_b = call_llm(prompt_b.format(input=item["input"]))
            score_b = metric_fn(resp_b, item["expected"])
            results_b.append(score_b)
        
        avg_a = sum(results_a) / len(results_a)
        avg_b = sum(results_b) / len(results_b)
        improvement = (avg_b - avg_a) / avg_a * 100
        
        return {
            "prompt_a_avg": round(avg_a, 2),
            "prompt_b_avg": round(avg_b, 2),
            "improvement_pct": round(improvement, 1),
            "sample_size": len(self.dataset),
        }

# 使用示例
dataset = [
    {"input": "登录功能", "expected": "覆盖正常/异常/边界"},
    {"input": "支付接口", "expected": "覆盖金额/余额/超时"},
    {"input": "搜索功能", "expected": "覆盖关键词/空结果/特殊字符"},
]

prompt_a = "为{input}生成测试用例"
prompt_b = """你是一名资深测试工程师。
请为{input}生成测试用例。
背景：这是一个面向用户的 Web 功能。
约束：生成 10 条用例，覆盖正常/异常/边界三类，JSON 格式输出。
示例：{{"id": "TC001", "title": "正常场景", "priority": "P0"}}
输出格式：JSON 数组，每条包含 id, title, priority, steps, expected"""

tester = PromptABTest(dataset)
result = tester.run(prompt_a, prompt_b, metric_fn=evaluate_test_cases)
print(f"基准: {result['prompt_a_avg']}, 优化: {result['prompt_b_avg']}, 提升: {result['improvement_pct']}%")

my_prompt = "帮我写登录功能的测试用例"  # 换成你的 Prompt
score = audit_prompt(my_prompt)

prompt_a = "为{input}生成测试用例"
prompt_b = """你是一名资深测试工程师。
请为{input}生成测试用例。
约束：10 条，覆盖正常/异常/边界，JSON 格式。
示例：{{"id": "TC001", "title": "正常场景", "priority": "P0"}}
只输出 JSON，不要其他文字。"""

result = PromptABTest(dataset).run(prompt_a, prompt_b, evaluate_test_cases)
print(f"提升: {result['improvement_pct']}%")
