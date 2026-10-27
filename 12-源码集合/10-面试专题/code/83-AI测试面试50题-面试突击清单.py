import tiktoken

def count_tokens(text, model="gpt-4"):
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))

# 测试Prompt模板的Token消耗
prompt = f"请总结以下内容：{content}"
print(f"Token数: {count_tokens(prompt)}")

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# 准备测试数据集
dataset = {
    'question': [...],      # 问题列表
    'answer': [...],        # 模型回答
    'contexts': [...]       # 检索到的文档
}

# 运行评估
score = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision])
print(score)

import pytest
from unittest.mock import MagicMock

def test_agent_tool_selection():
    """测试Agent是否正确选择工具"""
    agent = create_agent(tools=[search_tool, calculate_tool, weather_tool])
    
    # 测试场景：问天气
    result = agent.run("北京今天天气怎么样？")
    assert result.selected_tool == "weather_tool"
    assert result.tool_params["city"] == "北京"
    
    # 测试场景：算数学
    result = agent.run("123乘以456等于多少？")
    assert result.selected_tool == "calculate_tool"

def test_agent_error_handling():
    """测试Agent的错误处理能力"""
    # Mock工具返回错误
    weather_tool.return_value = {"error": "API限流"}
    result = agent.run("北京天气")
    # 验证Agent是否重试或降级
    assert result.action in ["retry", "fallback", "inform_user"]

from locust import HttpUser, task, between

class AIAPILoadTest(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def test_chat_completion(self):
        response = self.client.post("/v1/chat/completions", json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "你好"}],
            "temperature": 0
        })
        assert response.status_code == 200
        # 验证响应时间
        assert response.elapsed.total_seconds() < 10
