import pytest
import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "https://api.example.com/v1/chat/completions"

class TestAIAPI:
    """AI API 稳定性测试"""
    
    def test_consistency(self):
        """一致性测试：temperature=0 时输出应完全一致"""
        prompt = "1+1等于？"
        results = []
        
        for i in range(10):
            r = requests.post(API_URL, json={
                "model": "qwen3.5-plus",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "seed": 42  # 关键：加上 seed 参数
            })
            assert r.status_code == 200
            response = r.json()["choices"][0]["message"]["content"]
            results.append(response)
        
        unique_results = set(results)
        assert len(unique_results) == 1, \
            f"temperature=0 时输出应完全一致，但有 {len(unique_results)} 种不同输出"
    
    def test_concurrent_stability(self):
        """并发稳定性测试"""
        def call_api(i):
            start = time.time()
            try:
                r = requests.post(API_URL, json={
                    "model": "qwen3.5-plus",
                    "messages": [{"role": "user", "content": f"测试{i}"}],
                    "temperature": 0
                }, timeout=30)
                return time.time() - start, r.status_code, True
            except Exception as e:
                return time.time() - start, 0, False
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(call_api, i) for i in range(100)]
            results = [f.result() for f in as_completed(futures)]
        
        latencies = [r[0] * 1000 for r in results if r[2]]
        success_rate = len(latencies) / 100
        
        print(f"成功率: {success_rate*100:.1f}%")
        print(f"P50: {statistics.median(latencies):.0f}ms")
        print(f"P95: {sorted(latencies)[int(len(latencies)*0.95)]:.0f}ms")
        print(f"P99: {sorted(latencies)[int(len(latencies)*0.99)]:.0f}ms")
        
        assert success_rate > 0.95, f"成功率 {success_rate*100:.1f}% 低于 95%"

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevance, context_precision
from datasets import Dataset

# 准备测试数据
data = {
    'question': ['中国的首都是哪里？', 'Python是什么语言？'],
    'answer': ['北京', 'Python是一种解释型编程语言'],
    'contexts': [['北京是中国的首都，也是政治文化中心'],
                 ['Python由Guido van Rossum创建，是一种高级编程语言']],
    'ground_truth': ['北京', 'Python是一种解释型、面向对象的高级编程语言']
}

dataset = Dataset.from_dict(data)
result = evaluate(dataset, metrics=[faithfulness, answer_relevance, context_precision])
print(result)

from playwright.sync_api import sync_playwright

def test_ai_chat_ui():
    """AI 聊天 UI 测试"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:3000/chat")
        
        # 测试输入和发送
        page.fill("#chat-input", "你好")
        page.click("#send-btn")
        
        # 测试加载状态
        assert page.is_visible("#loading-indicator")
        
        # 测试回答显示
        page.wait_for_selector(".ai-response", timeout=10000)
        response = page.text_content(".ai-response")
        assert len(response) > 0
        
        # 测试流式输出
        # 流式输出时，文字应该逐字出现，不是一次性显示
        # 这里可以检查 DOM 更新的频率
        
        browser.close()

# conftest.py - pytest 配置文件
import pytest

@pytest.fixture(scope="session")
def api_client():
    """共享的 API 客户端，避免每次测试都创建新连接"""
    from requests import Session
    session = Session()
    session.headers.update({
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    })
    yield session
    session.close()

@pytest.fixture
def test_prompt():
    """测试用的 Prompt 模板"""
    return {
        "model": "qwen3.5-plus",
        "temperature": 0,
        "seed": 42
    }

# 测试报告生成
# 命令行运行：pytest --html=report.html --self-contained-html --json-report
