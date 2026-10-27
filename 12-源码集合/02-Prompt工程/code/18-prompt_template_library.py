from string import Template

class PromptTemplate:
    """简易 Prompt模板引擎"""
    
    def __init__(self, template_str: str):
        self.template = Template(template_str)
    
    def render(self, **kwargs) -> str:
        """用传入的参数渲染模板"""
        return self.template.safe_substitute(kwargs)

# 模板 3（测试用例生成）的实际用法
TEMPLATE_3 = """你是一名测试工程师，擅长${test_type}测试。请为以下功能编写测试用例。功能描述：${description}。测试范围：${scope}。

输出格式：用例ID、测试项、前置条件、步骤、预期结果。"""

prompt = PromptTemplate(TEMPLATE_3)
result = prompt.render(
    test_type="接口",
    description="根据订单号查询订单状态",
    scope="正常查询、不存在订单、参数缺失、权限校验"
)
print(result)

class AdvancedPromptTemplate:
    """支持默认值和变量校验的模板引擎"""
    
    DEFAULTS = {
        "role": "测试工程师",
        "language": "中文",
        "output_format": "markdown",
        "temperature": "0.3",  # 稳定输出场景建议低温度
    }
    
    REQUIRED = ["task"]  # 必填变量
    
    def __init__(self, template_str: str):
        self.template = template_str
    
    def render(self, **kwargs) -> str:
        # 合并默认值
        params = {**self.DEFAULTS, **kwargs}
        
        # 校验必填变量
        missing = [v for v in self.REQUIRED if v not in kwargs]
        if missing:
            raise ValueError(f"缺少必填变量: {', '.join(missing)}")
        
        # 变量替换
        result = self.template
        for key, value in params.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

# 使用：只传必要的参数，其余用默认值
prompt = AdvancedPromptTemplate("你是一名{role}。用{language}回答。{task}")
print(prompt.render(task="什么是回归测试？"))
# 输出：你是一名测试工程师。用中文回答。什么是回归测试？

def pipeline_prompt(requirement_text: str) -> dict:
    """三步流水线：需求分析 → 测试用例 → Bug 报告模板"""
    
    # 第一步：需求分析
    analysis = call_llm(TEMPLATE_8.render(requirement=requirement_text))
    
    # 第二步：基于分析结果生成测试用例
    test_cases = call_llm(TEMPLATE_3.render(
        test_type="功能",
        description=analysis,
        scope="正向流程、逆向流程、边界值"
    ))
    
    # 第三步：生成对应的 Bug 报告模板
    bug_template = call_llm(TEMPLATE_6.render(
        description=f"基于测试用例发现的潜在缺陷：{test_cases}",
        environment="测试环境",
        severity="待评估"
    ))
    
    return {
        "analysis": analysis,
        "test_cases": test_cases,
        "bug_template": bug_template
    }

def test_template_output(template_name: str, test_inputs: list, expected_fields: list):
    """测试模板输出是否包含期望的字段"""
    template = load_template(template_name)
    
    for inp in test_inputs:
        output = call_llm(template.render(**inp))
        
        for field in expected_fields:
            if field not in output:
                print(f"⚠️ 模板 {template_name} 缺少字段: {field}")
                print(f"   输入: {inp}")
                print(f"   输出: {output[:200]}...")

# 测试 Bug 报告模板
test_template_output(
    template_name="bug_report",
    test_inputs=[
        {"description": "页面白屏", "environment": "Chrome", "severity": "P0"},
        {"description": "数据加载慢", "environment": "Firefox", "severity": "P2"},
    ],
    expected_fields=["标题", "严重程度", "复现步骤", "预期结果", "实际结果", "复现概率"]
)

def test_template(template_name, test_inputs, expected_fields):
    """断言版：模板输出必须包含期望字段"""
    template = load_template(template_name)
    for inp in test_inputs:
        output = call_llm(template.render(**inp))
        for field in expected_fields:
            assert field in output, f"模板 {template_name} 缺少字段: {field}"

from string import Template

class PromptTemplate:
    def __init__(self, template_str: str):
        self.template = Template(template_str)
    def render(self, **kwargs) -> str:
        return self.template.safe_substitute(kwargs)

TEMPLATE_3 = """你是一名测试工程师，擅长${test_type}测试。请为以下功能编写测试用例。
功能描述：${description}。测试范围：${scope}。
输出格式：用例ID、测试项、前置条件、步骤、预期结果。"""

print(PromptTemplate(TEMPLATE_3).render(
    test_type="接口",
    description="根据订单号查询订单状态",
    scope="正常查询、不存在订单、参数缺失、权限校验"
))
