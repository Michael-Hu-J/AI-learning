# models/registry.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ModelStatus(Enum):
    TRAINING = "training"
    VALIDATING = "validating"
    CANARY = "canary"      # 灰度中
    PRODUCTION = "production"
    ROLLED_BACK = "rolled_back"
    DEPRECATED = "deprecated"

@dataclass
class ModelVersion:
    model_id: str
    version: str
    base_model: str
    training_data: str
    accuracy: float
    latency_p99_ms: float
    status: ModelStatus
    created_at: datetime
    deployed_at: datetime = None
    rolled_back_at: datetime = None

class ModelRegistry:
    """模型注册表 - 管理所有模型版本"""
    
    def __init__(self):
        self.models = {}
    
    def register(self, model: ModelVersion):
        """注册新模型版本"""
        key = f"{model.model_id}:{model.version}"
        self.models[key] = model
    
    def get_production(self, model_id: str) -> ModelVersion:
        """获取当前生产模型"""
        for model in self.models.values():
            if model.model_id == model_id and model.status == ModelStatus.PRODUCTION:
                return model
        return None
    
    def canary_deploy(self, model_id: str, version: str):
        """灰度部署"""
        key = f"{model_id}:{version}"
        if key in self.models:
            self.models[key].status = ModelStatus.CANARY
    
    def promote_to_production(self, model_id: str, version: str):
        """正式部署"""
        for model in self.models.values():
            if model.model_id == model_id and model.status == ModelStatus.PRODUCTION:
                model.status = ModelStatus.DEPRECATED
        key = f"{model_id}:{version}"
        self.models[key].status = ModelStatus.PRODUCTION
        self.models[key].deployed_at = datetime.now()
    
    def rollback(self, model_id: str, version: str):
        """回滚"""
        key = f"{model_id}:{version}"
        if key in self.models:
            self.models[key].status = ModelStatus.ROLLED_BACK
            self.models[key].rolled_back_at = datetime.now()

# app/middleware/model_router.py
import random

class ModelRouter:
    """模型路由器 - 实现灰度发布"""
    
    def __init__(self):
        self.canary_config = {
            "model_id": "qwen-finetune-v2",
            "version": "2024-01-15",
            "traffic_percent": 10,  # 10% 流量走新模型
        }
    
    def select_model(self, user_id: str) -> str:
        """根据用户 ID 选择模型版本"""
        # 使用用户 ID 的哈希值保证同一用户总是路由到同一模型
        user_hash = hash(user_id) % 100
        
        if user_hash < self.canary_config["traffic_percent"]:
            return f"{self.canary_config['model_id']}:{self.canary_config['version']}"
        else:
            return "qwen-base:latest"
    
    def update_traffic(self, percent: int):
        """更新灰度流量比例"""
        self.canary_config["traffic_percent"] = percent

# tests/test_model_regression.py
import pytest
import json
from app.model_client import ModelClient

@pytest.fixture
def model_client():
    return ModelClient(model_id="qwen-finetune-v2")

@pytest.fixture
def test_cases():
    with open("tests/model_test_set.json") as f:
        return json.load(f)

class TestModelRegression:
    """模型回归测试套件"""
    
    def test_overall_accuracy(self, model_client, test_cases):
        """整体准确率测试"""
        correct = 0
        total = len(test_cases)
        for case in test_cases:
            response = model_client.generate(case["input"])
            if self._evaluate(response, case["expected"]) >= 0.8:
                correct += 1
        accuracy = correct / total
        assert accuracy >= 0.85, f"整体准确率 {accuracy:.2%} < 85%"
    
    def test_logistics_query_accuracy(self, model_client, test_cases):
        """物流查询专项测试"""
        logistics_cases = [c for c in test_cases if c["category"] == "logistics"]
        correct = sum(
            1 for c in logistics_cases
            if self._evaluate(model_client.generate(c["input"]), c["expected"]) >= 0.8
        )
        accuracy = correct / len(logistics_cases)
        assert accuracy >= 0.80, f"物流查询准确率 {accuracy:.2%} < 80%"
    
    def test_complaint_handling_accuracy(self, model_client, test_cases):
        """投诉处理专项测试"""
        complaint_cases = [c for c in test_cases if c["category"] == "complaint"]
        correct = sum(
            1 for c in complaint_cases
            if self._evaluate(model_client.generate(c["input"]), c["expected"]) >= 0.8
        )
        accuracy = correct / len(complaint_cases)
        assert accuracy >= 0.70, f"投诉处理准确率 {accuracy:.2%} < 70%"
    
    def test_hallucination_rate(self, model_client, test_cases):
        """幻觉率测试"""
        hallucination_count = 0
        for case in test_cases:
            response = model_client.generate(case["input"])
            if self._check_hallucination(response, case["context"]):
                hallucination_count += 1
        rate = hallucination_count / len(test_cases)
        assert rate <= 0.05, f"幻觉率 {rate:.2%} > 5%"
    
    def _evaluate(self, response: str, expected: str) -> float:
        """评估回答质量（简化版，实际用LLM-as-a-Judge）"""
        # 实际项目中，这里会调用一个评估模型来打分
        # 这里用简单的字符串匹配做演示
        from difflib import SequenceMatcher
        return SequenceMatcher(None, response, expected).ratio()
    
    def _check_hallucination(self, response: str, context: str) -> bool:
        """检查是否存在幻觉"""
        # 检查回答中是否包含上下文中没有的信息
        # 实际项目中用LLM-as-a-Judge做事实一致性检查
        return False

# scripts/model_registry_mlflow.py
import mlflow
from mlflow.tracking import MlflowClient

client = MlflowClient()

def register_model(model_name, model_path, metrics):
    """注册模型到MLflow"""
    # 记录训练指标
    with mlflow.start_run():
        mlflow.log_params({"model_path": model_path})
        mlflow.log_metrics(metrics)
        mlflow.pytorch.log_model(model_path, "model")
        
        # 注册模型版本
        run_id = mlflow.active_run().info.run_id
        model_uri = f"runs:/{run_id}/model"
        mlflow.register_model(model_uri, f"production-{model_name}")

def transition_model_stage(model_name, stage):
    """切换模型阶段（None → Staging → Production → Archive）"""
    client.transition_model_version_stage(
        name=f"production-{model_name}",
        version="latest",
        stage=stage
    )

def get_production_model(model_name):
    """获取当前生产模型"""
    return client.get_model_version_by_alias(
        name=f"production-{model_name}",
        alias="production"
    )

# app/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 模型推理计数器
model_requests_total = Counter(
    'model_requests_total',
    'Total model requests',
    ['model_id', 'model_version', 'status']
)

# 模型推理延迟
model_latency_seconds = Histogram(
    'model_latency_seconds',
    'Model inference latency',
    ['model_id', 'model_version'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
)

# 模型准确率（由定期评估任务更新）
model_accuracy = Gauge(
    'model_accuracy',
    'Current model accuracy',
    ['model_id', 'model_version', 'category']
)

# 幻觉率
model_hallucination_rate = Gauge(
    'model_hallucination_rate',
    'Current model hallucination rate',
    ['model_id', 'model_version']
)

# 使用示例
def generate_response(model_id, user_input):
    start = time.time()
    try:
        response = call_model(model_id, user_input)
        latency = time.time() - start
        model_requests_total.labels(
            model_id=model_id, model_version="v2", status="success"
        ).inc()
        model_latency_seconds.labels(
            model_id=model_id, model_version="v2"
        ).observe(latency)
        return response
    except Exception as e:
        model_requests_total.labels(
            model_id=model_id, model_version="v2", status="error"
        ).inc()
        raise
