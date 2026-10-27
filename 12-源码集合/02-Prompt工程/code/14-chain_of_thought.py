prompt = """
问题：小明有 5 个苹果，给了小红 2 个，又买了 3 个，现在有几个？

让我们一步步思考：
1. 初始：5 个
2. 给小红 2 个：5 - 2 = 3 个
3. 又买 3 个：3 + 3 = 6 个
4. 答案：6 个
"""

prompt = """
请判断以下问题是否需要复杂的推理步骤。

示例 1：
问题：一个水池有进水管和出水管，进水管 3 小时注满，出水管 5 小时排空。
两管同时开，几小时注满？
思考：进水管每小时注入 1/3，出水管每小时排出 1/5。
净注入速度 = 1/3 - 1/5 = 2/15。
注满时间 = 1 / (2/15) = 7.5 小时。
答案：需要复杂推理。

示例 2：
问题：天空是什么颜色的？
思考：这是一个常识问题，不需要计算或推理。
答案：不需要复杂推理。

现在请判断：
问题：一个电商系统支持满减、优惠券、会员折扣，三种优惠可以叠加使用。
用户购买了 200 元的商品，使用了满 100 减 20 的优惠券，是 VIP 会员享 9 折。
最终应付多少？
思考：
"""

def self_consistency(prompt, n=5):
    """让模型生成 n 条推理路径，取最一致的答案"""
    reasoning_paths = []
    answers = []
    
    for i in range(n):
        # 每次调用用不同的 temperature 增加多样性
        result = call_llm(prompt, temperature=0.7 + i * 0.1)
        reasoning_paths.append(result.reasoning)
        answers.append(result.answer)
    
    # 统计最常见的答案
    from collections import Counter
    most_common = Counter(answers).most_common(1)[0]
    
    return {
        "final_answer": most_common[0],
        "confidence": most_common[1] / n,
        "all_reasonings": reasoning_paths
    }

# 无 CoT
prompt_no_cot = """
为一个登录功能生成测试用例，覆盖正常和异常场景。
"""

# 有 CoT
prompt_cot = """
为一个登录功能生成测试用例，覆盖正常和异常场景。

让我一步步思考：
1. 先列出登录功能的输入：用户名、密码、登录按钮
2. 正常场景：输入正确的用户名和密码 → 登录成功
3. 异常场景：
   a. 密码错误 → 提示密码错误
   b. 账号不存在 → 提示账号不存在
   c. 用户名为空 → 提示请输入用户名
   d. 密码为空 → 提示请输入密码
4. 边界场景：用户名超长、密码超短
5. 安全场景：SQL 注入、XSS

基于以上分析，生成测试用例：
"""

result_no_cot = call_llm(prompt_no_cot)
result_cot = call_llm(prompt_cot)
# CoT 版本通常覆盖更全面，用例质量更高

# 支付接口测试设计
prompt = """
请为支付接口设计测试用例。
思考步骤：
1. 接口信息：POST /api/pay，参数 amount/currency/pay_method
2. 正常场景 → 金额正常、余额充足
3. 异常场景 → 金额为 0、余额不足、支付超时
4. 边界场景 → 最大/最小金额
5. 安全场景 → 重复支付、金额篡改
基于以上分析，输出测试用例。
"""

# Bug 根因分析
prompt = """
分析以下 Bug 的根因。
思考步骤：
1. Bug 现象是什么？
2. 触发条件是什么？
3. 可能的原因有哪些？
4. 如何验证每个原因？
5. 最可能的原因是哪个？
"""

prompt = """
分析以下 Bug 的根因。

请用以下 JSON 格式输出你的推理过程：
{
    "phenomenon": "Bug 现象描述",
    "hypotheses": [
        {
            "cause": "可能的原因",
            "evidence": "支持这个原因的证据",
            "confidence": "high/medium/low",
            "test_method": "如何验证这个原因"
        }
    ],
    "most_likely": "最可能的原因",
    "verification_steps": ["验证步骤1", "验证步骤2"],
    "confidence_score": 0.85
}

Bug 信息：
- 现象：用户提交订单后，页面显示"提交成功"，但订单列表中看不到
- 触发条件：高并发时段（下午 2-4 点）
- 错误日志：偶尔出现 "Connection pool timeout"
- 影响范围：约 5% 的用户反馈
"""

prompt = """
测试一个电商系统的优惠券功能。

请用思维树的方式分析：

第一层：列出所有测试维度（至少 6 个）
第二层：对每个维度，列出 2-3 个具体测试点
第三层：评估每个测试点的风险等级（高/中/低）
第四层：按风险等级排序，输出优先级最高的 5 个测试点

请逐步输出每一层的结果，不要跳过任何一层。
"""

prompt = """
分析以下性能问题的根因。请用思维图的方式推理。

问题：某 API 接口在高峰期响应时间从 200ms 飙升到 5s。

推理步骤：
1. 列出所有可能的原因（数据库、网络、代码、配置、外部依赖）
2. 对每对原因，分析它们之间是否有因果关系或关联关系
3. 构建原因依赖图
4. 找出最关键的根因节点
5. 给出验证方案和修复建议

请用以下格式输出：
节点：[原因名称]
依赖：[依赖的其他节点]
证据：[支持证据]
置信度：[高/中/低]
"""

prompt = """
你是一个资深测试工程师。请分析以下 Bug 的根因。

Bug 信息：
- 模块：用户中心
- 现象：部分用户登录后，个人信息页面显示其他用户的数据
- 频率：约 2% 的请求
- 时间：昨天下午 3 点上线后开始出现
- 最近变更：更新了 session 管理模块

请按照以下步骤推理：
1. 列出所有可能的原因（至少 5 个）
2. 对每个原因，给出支持证据和反对证据
3. 排除明显不可能的原因
4. 对剩余原因按可能性排序
5. 给出最可能的原因和验证方案

输出格式：
【可能原因 1】
- 描述：...
- 支持证据：...
- 反对证据：...
- 可能性：高/中/低

...

【最终结论】
最可能的原因：...
验证方案：...
"""

prompt = """
为以下功能设计测试用例。

功能：用户注册
输入：用户名（3-20 字符，字母数字下划线）、密码（8-32 字符，含大小写+数字）、手机号
输出：注册成功/失败，失败时给出原因

请用思维链的方式设计测试用例：

第一步：识别所有输入字段及其约束条件
第二步：对每个字段，列出正常值、边界值、异常值
第三步：考虑字段之间的组合约束
第四步：考虑业务流程（注册→验证→登录）
第五步：考虑安全场景
第六步：考虑性能和并发场景
第七步：整理输出测试用例表格

测试用例格式：
| 编号 | 场景 | 输入 | 预期结果 | 优先级 |
"""

prompt = """
分析以下性能问题并给出调优建议。

系统现状：
- API 接口：/api/order/list（用户订单列表）
- 当前性能：P95 响应时间 3.2s，目标 < 500ms
- 数据量：单用户平均 500 条订单，最大 50000 条
- 数据库：MySQL，订单表 2000 万行
- 缓存：Redis，缓存命中率 60%

请逐步分析：
1. 可能的性能瓶颈在哪里？（数据库查询、缓存、网络、序列化、业务逻辑）
2. 每个瓶颈的证据是什么？
3. 针对每个瓶颈，给出优化方案
4. 评估每个方案的效果和成本
5. 给出优先级排序

输出格式：
【瓶颈 1】
- 位置：...
- 证据：...
- 优化方案：...
- 预期效果：...
- 实施成本：高/中/低
"""

prompt = """
分析以下测试结果并生成测试报告。

测试结果数据：
- 总用例数：256
- 通过：218（85.2%）
- 失败：28（10.9%）
- 跳过：10（3.9%）
- 失败用例分布：
  - 支付模块：12 个（其中 5 个 P0）
  - 用户模块：8 个（其中 1 个 P0）
  - 订单模块：5 个（其中 2 个 P0）
  - 其他模块：3 个

请用思维链分析：
1. 整体质量评估
2. 失败用例的模式识别（哪些模块问题最多？什么类型的 Bug 最多？）
3. 风险评估（当前质量是否允许上线？）
4. 改进建议（下一步该做什么？）
"""

prompt = """
为以下系统生成安全测试用例。

系统：用户登录 + 密码重置功能
技术栈：Spring Boot + MySQL + Redis

请用思维链分析攻击面：
1. 列出所有用户输入点（登录表单、密码重置、API 接口等）
2. 对每个输入点，列出可能的攻击类型
3. 考虑认证和授权漏洞
4. 考虑数据泄露风险
5. 考虑业务逻辑漏洞
6. 输出安全测试用例列表
"""

prompt = """
为以下项目设计完整的测试方案。

项目：支付系统升级（从 V1 升级到 V2）
变更内容：
- 新增支付宝、微信、银联三种支付方式
- 退款流程重构
- 对账系统升级
- 数据库从 MySQL 5.7 升级到 8.0

请用思维链设计测试方案：
1. 确定测试范围（哪些要测、哪些不用测）
2. 设计测试策略（功能、性能、安全、兼容性、回归）
3. 规划测试环境（需要哪些环境、数据怎么准备）
4. 评估测试风险（哪些地方最容易出问题）
5. 制定测试计划（时间线、人员分配）
"""

import json
import re

def validate_cot_quality(prompt, response):
    """验证 CoT 推理质量"""
    issues = []
    
    # 1. 检查推理步骤数量
    steps = re.findall(r'第[一二三四五六七八九十\d]+步[：:]', response)
    if len(steps) < 2:
        issues.append("推理步骤太少（少于2步），可能没有真正推理")
    if len(steps) > 15:
        issues.append("推理步骤太多（超过15步），可能过度推理")
    
    # 2. 检查是否有明确的结论
    conclusion_patterns = [
        r'结论[：:]', r'答案[：:]', r'最终[：:]',
        r'因此[，。]', r'所以[，。]'
    ]
    has_conclusion = any(re.search(p, response) for p in conclusion_patterns)
    if not has_conclusion:
        issues.append("没有明确的结论")
    
    # 3. 检查推理是否自洽（简单检查）
    # 如果推理中出现了矛盾的数字或结论，可能是问题
    numbers = re.findall(r'\d+', response)
    if len(numbers) > 50:
        issues.append("推理中数字过多，可能存在计算混乱")
    
    # 4. 检查推理长度是否合理
    token_estimate = len(response) // 2  # 粗略估计
    if token_estimate < 30:
        issues.append("推理过程太短，可能没有充分推理")
    if token_estimate > 1000:
        issues.append("推理过程太长，可能过度推理或包含无关内容")
    
    return {
        "quality_score": max(0, 100 - len(issues) * 20),
        "issues": issues,
        "step_count": len(steps),
        "token_estimate": token_estimate
    }

# 使用示例
result = validate_cot_quality(prompt, cot_response)
if result["quality_score"] < 60:
    print(f"推理质量较低，问题：{result['issues']}")
    # 可以触发重试或人工审核

def compare_cot_strategies(task_description, strategies=None):
    """对比不同 CoT 策略的效果"""
    if strategies is None:
        strategies = {
            "zero_shot": "让我们一步步思考：",
            "few_shot": _get_few_shot_prompt(),
            "structured": _get_structured_prompt(),
            "tree_of_thoughts": _get_tot_prompt(),
        }
    
    results = {}
    for name, prompt_suffix in strategies.items():
        full_prompt = task_description + "\n\n" + prompt_suffix
        
        # 调用 LLM
        response = call_llm(full_prompt, temperature=0.3)
        
        # 验证质量
        quality = validate_cot_quality(full_prompt, response.text)
        
        results[name] = {
            "response": response.text,
            "quality": quality,
            "tokens_used": response.usage.total_tokens,
            "cost": response.usage.total_tokens * 0.001,  # 假设每 token 0.001 元
        }
    
    # 输出对比报告
    print("=== CoT 策略对比报告 ===")
    for name, data in results.items():
        print(f"\n策略：{name}")
        print(f"  质量评分：{data['quality']['quality_score']}")
        print(f"  Token 消耗：{data['tokens_used']}")
        print(f"  预估成本：¥{data['cost']:.4f}")
        print(f"  问题：{data['quality']['issues']}")
    
    # 推荐最佳策略
    best = max(results.items(), key=lambda x: x[1]['quality']['quality_score'])
    print(f"\n推荐策略：{best[0]}（质量 {best[1]['quality']['quality_score']} 分）")
    
    return results

def smart_cot(prompt, task_type, budget_tokens=500):
    """智能 CoT 策略选择 + 成本优化"""
    
    # 策略 1：简单任务不用 CoT
    simple_tasks = ["情感分析", "关键词提取", "语言检测", "文本分类"]
    if task_type in simple_tasks:
        return call_llm(prompt), {"strategy": "no_cot", "tokens": 0}
    
    # 策略 2：中等复杂度用精简 CoT
    medium_tasks = ["测试用例设计", "Bug 描述生成", "测试数据生成"]
    if task_type in medium_tasks:
        cot_prompt = prompt + "\n\n简要说明推理思路（不超过3句话），然后给出结果。"
        response = call_llm(cot_prompt)
        return response, {"strategy": "light_cot", "tokens": response.usage.completion_tokens}
    
    # 策略 3：高复杂度用完整 CoT，但限制推理长度
    complex_tasks = ["Bug 根因分析", "测试方案设计", "性能调优建议"]
    if task_type in complex_tasks:
        cot_prompt = prompt + "\n\n请逐步推理，但推理过程控制在 300 字以内。"
        response = call_llm(cot_prompt, max_tokens=budget_tokens)
        return response, {"strategy": "bounded_cot", "tokens": response.usage.completion_tokens}
    
    # 策略 4：默认用 Zero-Shot CoT
    cot_prompt = prompt + "\n\n让我们一步步思考："
    response = call_llm(cot_prompt, max_tokens=budget_tokens)
    return response, {"strategy": "zero_shot_cot", "tokens": response.usage.completion_tokens}


def cost_tracker():
    """CoT 成本追踪器"""
    import time
    
    class CostTracker:
        def __init__(self):
            self.calls = []
            self.total_tokens = 0
            self.total_cost = 0
        
        def record(self, task_type, strategy, tokens, cost):
            self.calls.append({
                "time": time.time(),
                "task": task_type,
                "strategy": strategy,
                "tokens": tokens,
                "cost": cost
            })
            self.total_tokens += tokens
            self.total_cost += cost
        
        def report(self):
            print(f"总调用次数：{len(self.calls)}")
            print(f"总 Token 消耗：{self.total_tokens}")
            print(f"总成本：¥{self.total_cost:.2f}")
            print(f"平均每次：¥{self.total_cost / len(self.calls):.4f}")
            
            # 按策略统计
            from collections import defaultdict
            by_strategy = defaultdict(list)
            for call in self.calls:
                by_strategy[call['strategy']].append(call['cost'])
            
            print("\n按策略统计：")
            for strategy, costs in by_strategy.items():
                print(f"  {strategy}: {len(costs)} 次, 平均 ¥{sum(costs)/len(costs):.4f}")
    
    return CostTracker()
