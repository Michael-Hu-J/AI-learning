def test_task_description_quality():
    """测试不同层次任务描述对输出质量的影响"""
    descriptions = {
        "动词": "写测试用例",
        "动词+对象": "写登录功能测试用例",
        "动词+对象+约束": "写登录功能测试用例，覆盖正常/异常/边界，15 条",
        "动词+对象+约束+示例": (
            "写登录功能测试用例，覆盖正常/异常/边界，15 条，JSON格式。"
            "示例：{'id': 'TC001', 'title': '正常登录'}"
        ),
    }

    for name, desc in descriptions.items():
        response = call_llm(desc)
        quality = evaluate_output(response)
        print(f"{name}: 质量={quality:.2f}")

    # 典型结果
    # 动词: 2.5 | 动词+对象: 3.0 | +约束: 4.0 | +示例: 4.5

def test_verb_precision():
    """测试不同动词对输出质量的影响"""
    verbs = {
        "想": "帮我想想以下登录功能的测试方案",
        "写": "请写下以下登录功能的测试方案",
        "设计": "请设计以下登录功能的测试方案",
        "制定": "请制定以下登录功能的测试方案",
        "规划": "请规划以下登录功能的测试方案",
    }

    for verb, prompt in verbs.items():
        response = call_llm(prompt)
        coverage = count_test_scenarios(response)
        print(f"动词='{verb}': 覆盖场景数={coverage}")

    # 典型结果
    # 想: 5  写: 8  设计: 12  制定: 11  规划: 10

import re

def check_task_description(task_text):
    """自动检查任务描述的质量"""
    issues = []
    
    # 1. 检查动作动词
    action_verbs = ["生成", "编写", "分析", "设计", "创建", "输出", "列出", "计算"]
    vague_verbs = ["想想", "看看", "搞搞"]
    if not any(v in task_text for v in action_verbs):
        issues.append("缺少明确的动作动词")
    if any(v in task_text for v in vague_verbs):
        issues.append("使用了模糊动词，建议改为精确动词")
    
    # 2. 检查数量约束
    if not re.search(r'\d+', task_text):
        issues.append("缺少数量/范围约束")
    
    # 3. 检查否定句式
    if any(w in task_text for w in ["不要", "不该", "别"]):
        issues.append("使用了否定句式，建议改为正面描述")
    
    # 4. 检查多重任务
    conjunctions = task_text.count("并") + task_text.count("然后") + task_text.count("并且")
    if conjunctions >= 2:
        issues.append("包含多个子任务，建议拆分")
    
    # 5. 检查输出格式
    if not any(kw in task_text for kw in ["格式", "JSON", "表格"]):
        issues.append("未指定输出格式")
    
    # 6. 检查模糊范围词
    if any(w in task_text for w in ["尽可能", "尽量", "全面", "详细"]):
        issues.append("使用了模糊范围词，建议改为具体数字")
    
    return issues

# 测试
bad_task = "帮我想想登录功能怎么测，不要写太长，然后生成报告和写代码"
print(check_task_description(bad_task))
# ['缺少明确的动作动词', '缺少数量/范围约束', '使用了否定句式',
#  '包含多个子任务，建议拆分', '未指定输出格式']

my_task = "帮我分析一下登录功能"  # 换成你的
print(check_task_description(my_task))
