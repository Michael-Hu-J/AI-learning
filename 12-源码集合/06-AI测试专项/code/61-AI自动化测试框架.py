# conftest.py - pytest的配置文件
import pytest
import json

@pytest.fixture(scope="session")
def model_config():
    """加载模型配置"""
    with open("config/model_config.json", "r") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def test_dataset():
    """加载测试数据集"""
    with open("data/test_dataset.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def model_client(model_config):
    """创建模型客户端"""
    from model_client import ModelClient
    client = ModelClient(
        endpoint=model_config["endpoint"],
        timeout=model_config["timeout"],
        retry_count=model_config["retry_count"]
    )
    yield client
    client.close()

class TestCaseGenerator:
    """测试用例生成器"""
    
    def __init__(self, config):
        self.config = config
        self.strategies = {
            "historical": self._generate_from_history,
            "adversarial": self._generate_adversarial,
            "boundary": self._generate_boundary,
            "mutation": self._generate_mutation,
        }
    
    def generate(self, strategy_names=None):
        """根据策略生成测试用例"""
        if strategy_names is None:
            strategy_names = list(self.strategies.keys())
        
        all_cases = []
        for name in strategy_names:
            if name in self.strategies:
                cases = self.strategies[name]()
                all_cases.extend(cases)
        
        return all_cases
    
    def _generate_from_history(self):
        """从历史数据生成"""
        import pandas as pd
        df = pd.read_csv(self.config["history_data_path"])
        # 采样60%作为测试数据
        sampled = df.sample(frac=0.6, random_state=42)
        return sampled.to_dict("records")
    
    def _generate_adversarial(self):
        """生成对抗性测试用例"""
        base_cases = self._generate_from_history()
        adversarial_cases = []
        for case in base_cases[:100]:  # 取前100条做对抗
            mutated = self._add_noise(case)
            adversarial_cases.append(mutated)
        return adversarial_cases
    
    def _add_noise(self, case):
        """对文本添加噪声"""
        import random
        text = case["text"]
        # 随机插入错别字、特殊字符等
        noise_types = ["typo", "special_char", "repetition"]
        noise_type = random.choice(noise_types)
        # ... 具体的噪声添加逻辑
        return {"text": text, "expected": case["expected"], "type": "adversarial"}

class AssertionEngine:
    """断言引擎"""
    
    def __init__(self):
        self.assertions = {
            "accuracy": self._assert_accuracy,
            "precision": self._assert_precision,
            "recall": self._assert_recall,
            "f1": self._assert_f1,
            "fairness": self._assert_fairness,
            "robustness": self._assert_robustness,
            "consistency": self._assert_consistency,
            "latency": self._assert_latency,
        }
    
    def validate(self, results, config):
        """执行所有配置的断言"""
        outcomes = {}
        for assertion_name, assertion_config in config.items():
            if assertion_name in self.assertions:
                outcomes[assertion_name] = self.assertions[assertion_name](
                    results, assertion_config
                )
        return outcomes
    
    def _assert_accuracy(self, results, config):
        """准确率断言"""
        threshold = config.get("threshold", 0.90)
        correct = sum(1 for r in results if r["predicted"] == r["expected"])
        actual = correct / len(results) if results else 0
        return {
            "passed": actual >= threshold,
            "actual": actual,
            "threshold": threshold,
            "message": f"准确率 {actual:.3f} {'≥' if actual >= threshold else '<'} 阈值 {threshold}",
        }
    
    def _assert_fairness(self, results, config):
        """公平性断言"""
        threshold = config.get("threshold", 0.10)
        groups = self._group_by_sensitive_attr(results, config["sensitive_attr"])
        rates = {g: self._positive_rate(g) for g in groups}
        max_diff = max(rates.values()) - min(rates.values())
        return {
            "passed": max_diff <= threshold,
            "actual": max_diff,
            "threshold": threshold,
            "group_rates": rates,
            "message": f"公平性差异 {max_diff:.3f} {'≤' if max_diff <= threshold else '>'} 阈值 {threshold}",
        }

class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.formats = {
            "html": self._generate_html_report,
            "json": self._generate_json_report,
            "markdown": self._generate_markdown_report,
        }
    
    def generate(self, results, assertions, metrics, fmt="html"):
        """生成指定格式的报告"""
        if fmt in self.formats:
            return self.formats[fmt](results, assertions, metrics)
        raise ValueError(f"不支持的报告格式: {fmt}")
    
    def _generate_html_report(self, results, assertions, metrics):
        """生成HTML报告"""
        from jinja2 import Template
        template = Template(self._load_template("report.html"))
        return template.render(
            total_tests=len(results),
            passed=sum(1 for a in assertions.values() if a["passed"]),
            assertions=assertions,
            metrics=metrics,
            timestamp=datetime.now().isoformat(),
        )

import pytest
import allure

@allure.feature("情感分析模型测试")
@allure.story("准确性验证")
class TestSentimentAccuracy:
    
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("正面评论识别准确率测试")
    def test_positive_accuracy(self, model_client, test_dataset):
        positive_samples = [s for s in test_dataset if s["label"] == "positive"]
        correct = 0
        for sample in positive_samples:
            result = model_client.predict(sample["text"])
            if result["prediction"] == "positive":
                correct += 1
        
        accuracy = correct / len(positive_samples)
        allure.attach(
            f"准确率: {accuracy:.3f} ({correct}/{len(positive_samples)})",
            name="测试结果",
            attachment_type=allure.attachment_type.TEXT,
        )
        assert accuracy >= 0.90, f"正面评论准确率 {accuracy:.3f} 低于阈值 0.90"

import great_expectations as ge

# 加载测试数据集
df = ge.read_csv("data/test_dataset.json")

# 定义期望
expectations = [
    # 数据集不能为空
    {"expectation_type": "expect_table_columns_to_match_ordered_list", "kwargs": {"column_list": ["text", "label", "source"]}},
    # 文本字段不能为空
    {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "text"}},
    # 标签必须在合法范围内
    {"expectation_type": "expect_column_values_to_be_in_set", "kwargs": {"column": "label", "value_set": ["positive", "negative", "neutral"]}},
    # 数据集大小至少1000条
    {"expectation_type": "expect_table_row_count_to_be_between", "kwargs": {"min_value": 1000}},
]

# 执行验证
for exp in expectations:
    getattr(df, exp["expectation_type"])(**exp["kwargs"])

from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset

# 创建监控报告
report = Report(metrics=[
    DataDriftPreset(),
    TargetDriftPreset(),
])

# 对比参考数据集和当前数据集
report.run(
    reference_data=reference_df,
    current_data=current_df,
)

# 生成HTML报告
report.save_html("reports/drift_monitoring.html")

import mlflow

# 启动MLflow追踪
mlflow.set_experiment("sentiment-model-testing")

with mlflow.start_run():
    # 记录模型参数
    mlflow.log_param("model_type", "bert-base-chinese")
    mlflow.log_param("learning_rate", 2e-5)
    mlflow.log_param("epochs", 3)
    
    # 记录测试结果
    mlflow.log_metric("accuracy", 0.923)
    mlflow.log_metric("f1_score", 0.910)
    mlflow.log_metric("fairness_diff", 0.05)
    mlflow.log_metric("avg_latency_ms", 45.2)
    
    # 记录测试报告
    mlflow.log_artifact("reports/test_report.html")

from locust import HttpUser, task, between

class ModelLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def predict(self):
        import random
        samples = [
            "这个产品真的很好用",
            "质量太差了，完全不推荐",
            "中规中矩，没什么特别的",
        ]
        text = random.choice(samples)
        self.client.post(
            "/predict",
            json={"text": text},
            name="predict",
        )

import random
import numpy as np
import torch

def set_seeds(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

@pytest.mark.timeout(300)  # 单个测试最多5分钟
def test_adversarial_robustness():
    # 对抗性测试逻辑
    pass

def load_model(model_version):
    """加载指定版本的模型"""
    model_path = f"models/{model_version}/model.pt"
    model_hash = compute_hash(model_path)
    
    # 验证模型hash是否与预期一致
    expected_hash = get_expected_hash(model_version)
    if model_hash != expected_hash:
        raise ValueError(f"模型hash不匹配: 期望{expected_hash}, 实际{model_hash}")
    
    return torch.load(model_path)
