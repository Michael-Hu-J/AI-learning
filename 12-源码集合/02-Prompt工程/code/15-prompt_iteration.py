# 对比测试脚本 - 比较多个 Prompt 版本
test_cases = [
    {"input": "如何修改密码？", "category": "账户安全"},
    {"input": "订单显示已签收但没收到货怎么办？", "category": "物流异常"},
    {"input": "优惠券过期了还能用吗？", "category": "营销活动"},
    {"input": "我要投诉客服", "category": "投诉建议"},
    {"input": "你们这什么破 App，老是闪退！", "category": "情绪化输入"},
]

def evaluate_response(response, case):
    """评估单次输出，返回各维度分数"""
    scores = {
        "相关性": check_relevance(response, case["input"]),
        "完整性": check_completeness(response),
        "准确性": check_accuracy(response),
        "格式": check_format(response),
    }
    scores["综合"] = sum(scores.values()) / len(scores)
    return scores

def compare_prompts(prompt_versions, test_cases):
    """对比多个 Prompt 版本"""
    results = {}
    for name, prompt in prompt_versions.items():
        scores_list = []
        for case in test_cases:
            response = call_llm(prompt.format(question=case["input"]))
            score = evaluate_response(response, case)
            scores_list.append(score)
        
        # 统计
        avg = {k: sum(s[k] for s in scores_list) / len(scores_list) 
               for k in scores_list[0]}
        results[name] = {
            "平均分": avg,
            "最低分": min(s["综合"] for s in scores_list),
            "最高分": max(s["综合"] for s in scores_list),
            "详细": scores_list,
        }
    return results

# 使用
versions = {
    "V1_基础版": "回答客户的问题：{question}",
    "V2_加角色": "你是一名资深客服专员。回答客户的问题：{question}",
    "V3_加格式": "你是一名资深客服专员。按'问题归类→解决步骤→注意事项'格式回答：{question}",
    "V4_加示例": "你是一名资深客服专员。参考示例格式回答：{question}（示例略）",
}

results = compare_prompts(versions, test_cases)
for name, data in results.items():
    print(f"{name}: 平均 {data['平均分']['综合']:.2f}, "
          f"最低 {data['最低分']:.2f}, 最高 {data['最高分']:.2f}")

test_cases = [
    "如何修改密码？",
    "订单显示已签收但没收到货怎么办？",
    "优惠券怎么使用？",
]

def evaluate_prompt(prompt_template, test_cases):
    results = []
    for case in test_cases:
        response = call_llm(prompt_template.format(question=case))
        results.append({
            "相关性": check_relevance(response, case),
            "完整性": check_completeness(response),
            "格式": check_format(response),
        })
    return results

v1_results = evaluate_prompt(prompt_v1, test_cases)
v2_results = evaluate_prompt(prompt_v2, test_cases)

def regression_test(old_prompt, new_prompt, golden_cases):
    """
    golden_cases: 一组"已知好"的输入输出对
    确保新 Prompt 不会让这些好结果变差
    """
    regressions = []
    
    for case in golden_cases:
        old_output = call_llm(old_prompt.format(**case["input"]))
        new_output = call_llm(new_prompt.format(**case["input"]))
        
        old_score = evaluate(case["input"], old_output)
        new_score = evaluate(case["input"], new_output)
        
        # 允许 0.3 的波动（模型本身有随机性）
        if new_score < old_score - 0.3:
            regressions.append({
                "input": case["input"],
                "old_score": old_score,
                "new_score": new_score,
                "regression_amount": old_score - new_score,
                "old_output": old_output[:100],
                "new_output": new_output[:100],
            })
    
    if regressions:
        print(f"⚠️ 发现 {len(regressions)} 个回归:")
        for r in regressions:
            print(f"  输入: {r['input']}")
            print(f"  分数: {r['old_score']:.1f} → {r['new_score']:.1f} "
                  f"(下降 {r['regression_amount']:.1f})")
    else:
        print("✅ 无回归，新 Prompt 可以发布")
    
    return regressions

# ❌ 错误：一次改了三处——不知谁起作用
v1 = "写测试用例"
v2 = "你是一名资深测试工程师，请为登录功能编写15条测试用例，覆盖正常/异常/边界，JSON格式输出"

# ✅ 正确：逐次添加，建立因果关系
v1 = "写测试用例"
v2 = "你是一名测试工程师。写测试用例"           # 只加角色
v3 = v2 + "，生成15条"                          # 只加数量
v4 = v3 + "，JSON格式输出"                       # 只加格式

def should_stop_iteration(current_score, history_scores, target_score=4.5):
    """判断是否应该停止迭代"""
    
    # 条件 1：达到目标分数
    if current_score >= target_score:
        return True, f"已达到目标分数 {target_score}"
    
    # 条件 2：连续 3 次迭代没有提升（收益递减）
    if len(history_scores) >= 3:
        recent = history_scores[-3:]
        if max(recent) - min(recent) < 0.1:
            return True, "连续3次迭代提升<0.1，收益递减"
    
    # 条件 3：迭代次数超过上限（防沉迷）
    if len(history_scores) >= 10:
        return True, "迭代次数已达上限(10次)，建议换个方向"
    
    return False, "继续迭代"

# 使用示例
history = [2.0, 3.5, 4.0, 4.2, 4.3, 4.3]
stop, reason = should_stop_iteration(4.3, history)
print(f"停止: {stop}, 原因: {reason}")
# 输出: 停止: True, 原因: 连续3次迭代提升<0.1，收益递减
