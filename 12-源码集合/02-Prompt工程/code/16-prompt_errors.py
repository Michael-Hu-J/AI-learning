def debug_prompt(prompt):
    """检测 Prompt 中的常见问题"""
    issues = []
    
    # 检查角色定义
    if not any(kw in prompt for kw in ["你是一名", "你是", "你作为", "扮演"]):
        issues.append("⚠️ 缺少角色定义——模型可能不知道以什么身份回答")
    
    # 检查指令动词
    action_verbs = ["生成", "编写", "分析", "设计", "创建", "输出", "列出", "总结", "评估"]
    if not any(v in prompt for v in action_verbs):
        issues.append("⚠️ 缺少明确的指令动词——模型可能不清楚要做什么")
    
    # 检查输出格式
    if not any(kw in prompt for kw in ["格式", "JSON", "XML", "Markdown", "表格", "列表"]):
        issues.append("💡 建议指定输出格式——便于后续处理")
    
    # 检查长度控制
    if not any(kw in prompt for kw in ["字数", "不超过", "至少", "最多", "条", "个"]):
        issues.append("💡 建议加入长度或数量控制——避免输出过长或过短")
    
    # 检查示例
    if not any(kw in prompt for kw in ["示例", "例如", "比如", "sample", "example"]):
        issues.append("💡 考虑加入 few-shot 示例——提升输出质量")
    
    # 检查约束冲突
    import re
    constraints = re.findall(r'[不不要]|[^只]仅|必须|禁止', prompt)
    if len(constraints) > 8:
        issues.append("🚨 约束条件过多（超过 8 条）——模型可能顾此失彼")
    
    return issues if issues else ["✅ Prompt 看起来不错！"]

# 使用示例
prompt = "帮我写测试用例"
print(debug_prompt(prompt))
# 输出：
# ['⚠️ 缺少角色定义——模型可能不知道以什么身份回答',
#  '⚠️ 缺少明确的指令动词——模型可能不清楚要做什么',
#  '💡 建议指定输出格式——便于后续处理',
#  '💡 建议加入长度或数量控制——避免输出过长或过短',
#  '💡 考虑加入 few-shot 示例——提升输出质量']

def suggest_fixes(issues, original_prompt):
    """根据检测结果给出修复建议"""
    fixes = []
    
    for issue in issues:
        if "缺少角色定义" in issue:
            fixes.append("在 Prompt 开头加上：'你是一名[具体角色]，擅长[相关领域]'")
        elif "缺少明确的指令动词" in issue:
            fixes.append("用具体的动词替换模糊表达，如'生成 10 条测试用例'而不是'帮我弄一下'")
        elif "建议指定输出格式" in issue:
            fixes.append("在 Prompt 末尾加上格式模板，例如：'输出 JSON 格式，包含以下字段：...'")
        elif "建议加入长度或数量控制" in issue:
            fixes.append("加上数量约束，如'不少于 15 条'或'不超过 500 字'")
        elif "考虑加入 few-shot 示例" in issue:
            fixes.append("提供 2-3 个输入输出示例，格式如：'输入：... → 输出：...'")
        elif "约束条件过多" in issue:
            fixes.append("保留最关键的 5-8 条约束，其他的合并或去掉")
    
    return fixes

# 使用示例
issues = debug_prompt("帮我写测试用例")
fixes = suggest_fixes(issues, "帮我写测试用例")
for fix in fixes:
    print(fix)

import json

def batch_test_prompt(prompt_template, test_inputs, run_count=3):
    """批量测试 Prompt 的稳定性"""
    results = {}
    
    for i, test_input in enumerate(test_inputs):
        prompt = prompt_template.replace("{input}", test_input)
        outputs = []
        
        for _ in range(run_count):
            # 这里替换成你实际的模型调用
            # output = call_llm(prompt)
            outputs.append(output)
        
        # 检查输出一致性
        unique_outputs = set(json.dumps(o, ensure_ascii=False) for o in outputs)
        consistency = 1.0 / len(unique_outputs)  # 越接近 1 越一致
        
        results[f"test_{i+1}"] = {
            "input": test_input,
            "outputs": outputs,
            "consistency": consistency,
            "status": "stable" if consistency > 0.8 else "unstable"
        }
    
    return results

# 使用示例
test_inputs = [
    "用户登录功能",
    "密码重置功能",
    "文件上传功能",
    "搜索功能",
]

results = batch_test_prompt(
    "你是一名测试工程师，请为{input}编写测试用例，输出 JSON 格式",
    test_inputs
)

for test_id, result in results.items():
    print(f"{test_id}: 一致性={result['consistency']:.2f}, 状态={result['status']}")

import re

def prompt_health_score(prompt_text):
    """给 Prompt 打分，0-100 分"""
    score = 0

    # 角色定义 (20分)
    if any(kw in prompt_text for kw in ["你是一名", "你是", "你作为"]):
        score += 10
        if any(kw in prompt_text for kw in ["资深", "经验", "擅长"]):
            score += 5
        if any(kw in prompt_text for kw in ["行为规则", "约束", "要求"]):
            score += 5

    # 任务明确性 (25分)
    action_verbs = ["生成", "编写", "分析", "设计", "创建", "输出", "列出"]
    if any(v in prompt_text for v in action_verbs):
        score += 15
    if re.search(r'\d+', prompt_text):
        score += 10

    # 输出格式 (25分)
    if any(kw in prompt_text for kw in ["格式", "JSON", "XML", "Markdown"]):
        score += 15
        if "只输出" in prompt_text or "不要" in prompt_text:
            score += 10

    # 示例 (15分)
    if any(kw in prompt_text for kw in ["示例", "例如", "sample"]):
        score += 15

    # 上下文 (15分)
    if any(kw in prompt_text for kw in ["背景", "场景", "系统", "需求"]):
        score += 15

    print(f"Prompt 健康度: {score}/100")
    if score < 60:
        print("⚠️ 建议大幅改进")
    elif score < 80:
        print("💡 有改进空间")
    else:
        print("✅ 质量良好")
    return score

# prompt_health_score("帮我写测试用例")        # → 15/100
# prompt_health_score("你是一名资深测试工程师...")  # → 90/100

my_prompt = "请写代码"  # 换成你的 Prompt
print(debug_prompt(my_prompt))
print(prompt_health_score(my_prompt))
