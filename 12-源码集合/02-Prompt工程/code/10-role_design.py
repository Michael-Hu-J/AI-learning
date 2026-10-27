def test_role_effectiveness():
    task = "为登录功能设计测试用例"
    
    prompts = {
        "无角色": task,
        "基础角色": f"你是一名测试工程师。{task}",
        "专业角色": f"你是一名资深测试工程师，擅长 API 测试。{task}",
        "场景角色": f"你是一名资深测试工程师，10 年经验，正在为电商公司测试登录系统。{task}",
    }
    
    for name, prompt in prompts.items():
        response = call_llm(prompt)
        score = evaluate_test_cases(response)
        print(f"{name}: 质量评分={score:.2f}")
    
    # 典型结果
    # 无角色: 3.50 | 基础角色: 4.00 | 专业角色: 4.30 | 场景角色: 4.70

def get_user(user_id):
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()

prompt = """
现在请三位专家共同评审以下代码：

【安全专家】关注点：SQL 注入、XSS、权限越权、数据泄露
【性能专家】关注点：响应时间、并发能力、资源消耗
【可维护性专家】关注点：代码结构、注释、扩展性

请分别给出三位专家的评审意见，最后汇总优先级最高的 3 个问题。
"""

def test_role_granularity():
    """测试角色描述的精细度对输出的影响"""
    task = "分析以下接口日志，找出性能瓶颈"
    log_data = "GET /api/search?q=手机 200 450ms | POST /api/order 201 1200ms | ..."
    
    roles = {
        "泛角色": f"你是一个专家。\n{task}\n{log_data}",
        "专业角色": f"你是一名后端开发工程师。\n{task}\n{log_data}",
        "精细角色": f"你是一名资深性能测试工程师，8年经验，擅长API性能分析和数据库慢查询优化。\n{task}\n{log_data}",
        "场景角色": f"你是一名资深性能测试工程师，8年经验。你正在为一家日活100万的电商系统做性能诊断。\n{task}\n{log_data}",
    }
    
    for name, prompt in roles.items():
        response = call_llm(prompt)
        insights = count_actionable_insights(response)  # 可执行建议数量
        depth = evaluate_analysis_depth(response)       # 分析深度评分
        print(f"{name}: 可执行建议={insights}, 分析深度={depth:.1f}")
    
    # 典型结果
    # 泛角色: 可执行建议=2, 分析深度=2.5
    # 专业角色: 可执行建议=4, 分析深度=3.5
    # 精细角色: 可执行建议=6, 分析深度=4.2
    # 场景角色: 可执行建议=7, 分析深度=4.5

# 按测试类型分类（测试专项）
test_roles = {
    "功能测试": "你是一名资深功能测试工程师，擅长需求分析和测试用例设计，熟悉等价类划分、边界值分析、因果图等测试设计方法。",
    "API测试": "你是一名资深 API 测试工程师，擅长 RESTful API 测试，熟悉 HTTP 协议、状态码、请求方法、认证机制，能设计覆盖正常/异常/边界/安全的完整测试用例。",
    "性能测试": "你是一名资深性能测试工程师，8 年经验，擅长接口性能分析、数据库慢查询优化、JMeter/LoadRunner 压测方案设计，能定位 CPU/内存/IO/网络层面的性能瓶颈。",
    "安全测试": "你是一名资深安全测试工程师，擅长 Web 安全渗透测试，熟悉 OWASP Top 10、SQL 注入、XSS、CSRF、越权漏洞的发现和修复方案。",
    "自动化测试": "你是一名资深自动化测试工程师，擅长 Python + pytest + requests 自动化测试框架设计，能编写可维护、可扩展、可集成的自动化测试脚本。",
    "数据测试": "你是一名资深数据测试工程师，擅长数据库测试、数据迁移验证、数据质量检查，熟悉 SQL 优化、数据一致性验证、ETL 测试。",
    "兼容性测试": "你是一名资深兼容性测试工程师，擅长跨浏览器、跨设备、跨操作系统的兼容性测试，熟悉 Chrome/Firefox/Safari/Edge 的渲染差异和移动端适配问题。",
    "UX测试": "你是一名资深 UX 测试工程师，擅长用户界面可用性评估、交互流程优化、无障碍测试，熟悉 WCAG 2.1 标准和用户行为分析方法。",
}

# 通用角色（写文档、写代码、咨询等非测试任务时复用）
general_roles = {
    "测试工程师": "你是一名资深测试工程师，擅长功能测试、自动化测试和性能测试。",
    "程序员": "你是一名资深 Python 工程师，擅长编写简洁、高效、可维护的代码。",
    "作家": "你是一名畅销书作家，擅长用生动的语言讲述故事。",
    "教师": "你是一名经验丰富的老师，擅长用简单易懂的方式讲解复杂概念。",
    "顾问": "你是一名专业顾问，擅长分析问题并提供可行的建议。",
    "安全专家": "你是一名网络安全专家，擅长发现系统漏洞和安全风险。",
}

# 按业务场景分类
business_roles = {
    "电商": "你是一名电商领域的资深测试工程师，熟悉商品管理、购物车、订单、支付、物流、售后等核心业务流程。",
    "金融": "你是一名金融领域的资深测试工程师，熟悉支付清算、风控、账务、对账等核心业务，对数据一致性和安全性有极高要求。",
    "医疗": "你是一名医疗领域的资深测试工程师，熟悉 HIPAA 合规要求、电子病历系统、医疗数据安全规范。",
    "教育": "你是一名教育领域的资深测试工程师，熟悉在线学习平台、考试系统、课程管理、学习数据分析等业务场景。",
}


def build_role(test_type, business_domain):
    """组合测试类型和业务场景，生成精准角色"""
    return f"{test_roles[test_type]}你正在为一家{business_domain}公司工作。"

# 示例：role = build_role("API测试", "电商")

def validate_role(role_description, test_questions):
    """
    验证角色设定是否有效
    
    role_description: 角色描述字符串
    test_questions: 测试问题列表
    """
    scores = []
    for q in test_questions:
        prompt = f"{role_description}\n\n请回答：{q}"
        response = call_llm(prompt)
        
        # 评估标准：
        # 1. 是否使用了角色相关的专业术语
        # 2. 是否给出了具体的、可操作的建议
        # 3. 是否避免了泛泛而谈
        score = evaluate_role_consistency(response, role_description)
        scores.append(score)
    
    avg = sum(scores) / len(scores)
    print(f"角色验证得分: {avg:.2f}/5.0")
    return avg

# 验证"资深 API 测试工程师"角色
role = "你是一名资深 API 测试工程师，8 年经验，擅长 RESTful API 测试和自动化测试框架设计。"
questions = [
    "如何测试一个用户注册 API？",
    "API 返回 500 错误，如何排查？",
    "如何设计 API 的自动化测试框架？",
]
validate_role(role, questions)
# 如果得分 >= 4.0，说明角色设定有效
# 如果得分 < 3.0，说明角色描述需要调整

def ab_test_roles(role_a, role_b, task, test_cases=None):
    """对比两个角色设定的效果"""
    if test_cases is None:
        test_cases = ["登录", "支付", "搜索"]
    results_a = []
    results_b = []
    
    for case in test_cases:
        prompt_a = f"{role_a}\n\n{task}: {case}"
        prompt_b = f"{role_b}\n\n{task}: {case}"
        
        resp_a = call_llm(prompt_a)
        resp_b = call_llm(prompt_b)
        
        results_a.append(evaluate(resp_a))
        results_b.append(evaluate(resp_b))
    
    print(f"角色A平均分: {sum(results_a)/len(results_a):.2f}")
    print(f"角色B平均分: {sum(results_b)/len(results_b):.2f}")
    
# 对比两个角色描述
role_a = "你是一名测试工程师。"
role_b = "你是一名资深测试工程师，8年经验，擅长API测试和自动化测试。"
ab_test_roles(role_a, role_b, "生成测试用例", test_cases=["登录", "支付", "搜索"])

prompt = """
你是一名测试工程师。

行为规则：
1. 只基于提供的信息做判断，不要自行补充假设
2. 每个结论必须标注依据（引用原文或数据）
3. 如果信息不足，明确标注"无法判断"，不要猜测
4. 输出用中文，避免英文缩写
5. 不确定时，给出可能的原因范围，不要给出确定结论

请分析以下测试日志：
[日志内容]
"""

prompt = """
你是一名资深测试工程师，10 年经验，擅长 API 测试和性能测试。

行为规则：
1. 优先关注边界情况和异常场景
2. 每个建议都要给出具体可执行的步骤
3. 不确定时明确标注，不要猜测
4. 用中文输出，避免英文缩写

请为以下接口设计测试方案：
[接口信息]
"""

prompt = """
你是一名资深测试工程师。

示例：
输入：登录接口，支持邮箱+密码
输出：生成 15 条测试用例，覆盖正常/异常/边界，JSON 格式

输入：支付接口，支持支付宝+微信
输出：生成 20 条测试用例，覆盖正常/异常/边界/安全，JSON 格式

请为以下接口生成测试用例：
[接口信息]
"""

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "你是一名资深测试工程师，10年经验，擅长API测试。"},
        {"role": "user", "content": "为登录功能生成测试用例。"}
    ]
)

response = anthropic.Anthropic().messages.create(
    model="claude-3-5-sonnet-20241022",
    system="你是一名资深测试工程师，10年经验，擅长API测试。",
    messages=[
        {"role": "user", "content": "为登录功能生成测试用例。"}
    ]
)

response = dashscope.Generation.call(
    model="qwen-max",
    messages=[
        {"role": "system", "content": "你是一名资深测试工程师，10年经验，擅长API测试。"},
        {"role": "user", "content": "为登录功能生成测试用例。"}
    ]
)

def test_role_persistence(role, max_turns=20):
    """测试角色在多轮对话中的持久性"""
    messages = [
        {"role": "system", "content": role},
        {"role": "user", "content": "请确认你的角色。"}
    ]
    
    for turn in range(max_turns):
        response = call_llm(messages)
        messages.append({"role": "assistant", "content": response})
        
        # 每5轮检查一次角色是否还在
        if (turn + 1) % 5 == 0:
            check_msg = "请再次确认你的角色。"
            messages.append({"role": "user", "content": check_msg})
            resp = call_llm(messages)
            is_role = "测试工程师" in resp or "测试" in resp
            print(f"第{turn+1}轮: 角色保持={'✅' if is_role else '❌'}")
            messages.append({"role": "assistant", "content": resp})

# 测试结果
# GPT-4o: 20轮后角色仍然保持 ✅
# Claude 3.5: 20轮后角色仍然保持 ✅
# 通义千问 Max: 15轮后角色开始模糊 ⚠️
# Gemini 1.5 Pro: 18轮后角色仍然保持 ✅

prompt = """
你是一名测试工程师。

你不是：
- 开发工程师（不要给出代码实现方案）
- 产品经理（不要给出功能设计建议）
- 项目经理（不要给出排期和优先级建议）

你是：
- 测试工程师（只关注测试用例设计、测试策略、质量评估）

请为以下功能设计测试方案：
[功能描述]
"""

def role_combination_experiment(task, role_variants, test_cases):
    """
    系统性地测试不同角色设定的效果
    
    role_variants: 角色描述列表
    test_cases: 测试用例列表
    """
    results = {}
    
    for role in role_variants:
        scores = []
        for case in test_cases:
            prompt = f"{role}\n\n{task}: {case}"
            response = call_llm(prompt)
            score = evaluate(response)
            scores.append(score)
        
        avg = sum(scores) / len(scores)
        variance = sum((s - avg)**2 for s in scores) / len(scores)
        results[role] = {"avg": avg, "variance": variance}
    
    # 排序
    sorted_roles = sorted(results.items(), key=lambda x: x[1]["avg"], reverse=True)
    
    print(f"{'角色描述':<50} {'平均分':>8} {'方差':>8}")
    print("-" * 70)
    for role, metrics in sorted_roles:
        print(f"{role[:48]:<50} {metrics['avg']:>8.2f} {metrics['variance']:>8.3f}")
    
    return results

# 使用
roles = [
    "你是一名测试工程师。",
    "你是一名资深测试工程师。",
    "你是一名资深测试工程师，10年经验。",
    "你是一名资深测试工程师，10年经验，擅长API测试。",
    "你是一名资深测试工程师，10年经验，擅长API测试和自动化测试。",
    "你是一名资深测试工程师，正在为电商公司测试登录系统。",
]

results = role_combination_experiment(
    task="生成测试用例",
    role_variants=roles,
    test_cases=["登录功能", "支付功能", "搜索功能"]
)
