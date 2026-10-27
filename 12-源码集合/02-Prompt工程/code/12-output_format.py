prompt = """
请分析以下文本的情感，按 JSON 格式输出：

{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "keywords": ["关键词1", "关键词2"]
}

文本：{text}

只输出 JSON，不要输出其他文字。
"""

prompt = """
请按以下格式输出：

{
    "test_cases": [
        {
            "id": "TC001",
            "title": "用例标题",
            "priority": "P0"
        }
    ]
}

不要用 Markdown 代码块包裹，直接输出纯 JSON。
JSON 必须合法，能用 json.loads() 解析。
"""

prompt = """
请用 Markdown 格式输出：

# 测试报告

## 执行摘要
- 总用例数：{total}
- 通过：{passed}
- 失败：{failed}

## 详细结果
| 用例ID | 状态 | 耗时 |
|--------|------|------|
| TC001  | 通过 | 1.2s |
"""

# YAML：适合配置、人工可读；Prompt 里给缩进严格的示例，并要求「只输出 YAML」
prompt_yaml = """
请生成测试用例，用 YAML 格式输出：

test_cases:
  - id: TC001
    title: "正常登录"
    priority: P0
    steps:
      - 输入用户名
      - 输入密码
    expected: "登录成功，跳转首页"

只输出 YAML，不要其他文字。
"""

# XML：JUnit 报告、旧系统对接；强制要求 <?xml ...?> 声明和闭合标签
prompt_xml = """
请生成测试报告，用 XML 格式输出：

<?xml version="1.0" encoding="UTF-8"?>
<test-report>
  <summary>
    <total>50</total>
    <passed>45</passed>
    <failed>5</failed>
  </summary>
  <cases>
    <case id="TC001" status="pass"/>
  </cases>
</test-report>

只输出 XML，不要其他文字。
"""

import json
import re

def safe_parse_llm_output(response: str) -> dict | list:
    """
    安全解析 LLM 输出，处理各种异常情况
    按优先级尝试多种解析策略
    """
    # 策略 1：直接解析（最理想情况）
    cleaned = response.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 策略 2：去除 Markdown 代码块包裹 

import json
import re

def test_output_format(response: str) -> bool:
    """测试输出是否为合法 JSON（先直接解析，再正则兜底）"""
    try:
        parsed = json.loads(response)
        print(f"✅ 直接解析成功: {type(parsed).__name__}")
        return True
    except json.JSONDecodeError:
        match = re.search(r'(\{.*\}|\[.*\])', response, re.DOTALL)
        if match:
            try:
                json.loads(match.group())
                print("✅ 正则提取后解析成功")
                return True
            except json.JSONDecodeError:
                pass
    print("❌ 解析失败，输出不合法")
    return False

from typing import Any

class FormatValidator:
    """轻量级格式验证器"""

    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self, data: Any, path: str = "$") -> list[str]:
        """验证数据是否符合 schema，返回错误列表"""
        errors = []
        expected_type = self.schema.get("type")

        if expected_type == "object":
            if not isinstance(data, dict):
                errors.append(f"{path}: 期望 object，实际 {type(data).__name__}")
                return errors
            for field in self.schema.get("required", []):
                if field not in data:
                    errors.append(f"{path}: 缺少必填字段 '{field}'")
            for key, prop_schema in self.schema.get("properties", {}).items():
                if key in data:
                    child = FormatValidator(prop_schema)
                    errors.extend(child.validate(data[key], f"{path}.{key}"))

        elif expected_type == "array":
            if not isinstance(data, list):
                errors.append(f"{path}: 期望 array，实际 {type(data).__name__}")
                return errors
            items_schema = self.schema.get("items")
            if items_schema:
                for i, item in enumerate(data):
                    child = FormatValidator(items_schema)
                    errors.extend(child.validate(item, f"{path}[{i}]"))

        elif expected_type:
            type_map = {"string": str, "number": (int, float),
                        "integer": int, "boolean": bool}
            expected_py_type = type_map.get(expected_type)
            if expected_py_type and not isinstance(data, expected_py_type):
                errors.append(
                    f"{path}: 期望 {expected_type}，实际 {type(data).__name__} ({data!r})"
                )

        return errors

def validate_llm_json_output(response: str, schema: dict) -> tuple[dict, list[str]]:
    """解析并验证 LLM 的 JSON 输出"""
    data = safe_parse_llm_output(response)
    validator = FormatValidator(schema)
    errors = validator.validate(data)
    return data, errors

def test_format_stability(
    prompt_template: str,
    test_inputs: list[str],
    n_trials: int = 5,
    expected_format: str = "json"
) -> dict:
    """测试格式稳定性——多次调用输出格式是否一致"""
    results = {
        "total": 0,
        "parse_success": 0,
        "format_match": 0,
        "failures": []
    }

    for inp in test_inputs:
        for trial in range(n_trials):
            prompt = prompt_template.format(input=inp)
            response = call_llm(prompt)
            results["total"] += 1

            try:
                data = safe_parse_llm_output(response)
                results["parse_success"] += 1
            except ValueError:
                results["failures"].append({
                    "input": inp[:50], "trial": trial,
                    "error": "parse_failed"
                })
                continue

            actual_format = detect_format(response)
            if actual_format == expected_format:
                results["format_match"] += 1

    results["parse_rate"] = results["parse_success"] / results["total"]
    results["format_rate"] = results["format_match"] / results["total"]
    return results

def detect_format(text: str) -> str:
    """自动检测输出格式"""
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        try:
            json.loads(text)
            return "json"
        except:
            return "json_like"
    if text.startswith("<?xml") or (text.startswith("<") and ">" in text):
        return "xml"
    if ":" in text.split("\n")[0] and not text.startswith("{"):
        return "yaml"
    if "|" in text and "---" in text:
        return "markdown_table"
    return "text"

import pytest

class TestLLMOutputFormat:
    """LLM 输出格式自动化测试"""

    @pytest.fixture
    def prompt_template(self):
        return """生成测试用例，JSON 格式输出：
[{"id": "TC001", "title": "用例标题", "priority": "P0"}]
只输出 JSON，不要其他文字。
输入：{input}
"""

    @pytest.mark.parametrize("test_input", ["用户登录", "商品搜索", "订单支付"])
    def test_json_parse_success(self, prompt_template, test_input):
        """测试：输出能被 json.loads() 解析"""
        prompt = prompt_template.format(input=test_input)
        response = call_llm(prompt)
        data = safe_parse_llm_output(response)
        assert isinstance(data, (dict, list))

    def test_format_stability_regression(self):
        """回归测试：格式稳定性不能下降"""
        results = test_format_stability(
            prompt_template="生成测试用例，JSON 格式。输入：{input}",
            test_inputs=["登录", "搜索", "支付"],
            n_trials=3, expected_format="json"
        )
        assert results["parse_rate"] >= 0.90, \
            f"解析成功率 {results['parse_rate']:.0%} 低于阈值 90%"

response = response.replace('"', '"').replace('"', '"')

yaml_text = response.replace('\t', '  ')  # Tab 替换为 2 个空格
data = yaml.safe_load(yaml_text)
