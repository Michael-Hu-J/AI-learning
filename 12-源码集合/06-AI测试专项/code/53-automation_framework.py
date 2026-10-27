import yaml
from dataclasses import dataclass

@dataclass
class TestCase:
    id: str
    category: str
    input: str
    expected_keywords: list
    expected_semantic: str
    forbidden_keywords: list = None
    min_similarity: float = 0.80
    timeout: int = 30
    priority: str = "P1"

class TestCaseManager:
    def __init__(self, test_cases_file: str):
        self.test_cases = []
        with open(test_cases_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        for item in data['test_cases']:
            self.test_cases.append(TestCase(**item))

    def get_by_category(self, category: str):
        return [tc for tc in self.test_cases if tc.category == category]

    def get_by_priority(self, priority: str):
        return [tc for tc in self.test_cases
                if getattr(tc, 'priority', 'P1') == priority]

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

logger = logging.getLogger(__name__)

class TestExecutor:
    def __init__(self, api_key, base_url, model="gpt-4",
                 max_workers=10, rate_limit=10.0):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.max_workers = max_workers
        self.rate_limit = rate_limit
        self._last_request_time = 0

    def _wait_for_rate_limit(self):
        """限流：确保请求频率不超过设定值"""
        elapsed = time.time() - self._last_request_time
        min_interval = 1.0 / self.rate_limit
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def execute_single(self, test_case):
        """执行单个测试用例"""
        start_time = time.time()
        self._wait_for_rate_limit()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": test_case.input}],
                temperature=0.3,
                max_tokens=500,
                timeout=test_case.timeout
            )
            return {
                'test_case_id': test_case.id,
                'response': response.choices[0].message.content,
                'elapsed': time.time() - start_time,
                'status': 'success',
                'tokens': response.usage.total_tokens
            }
        except Exception as e:
            return {
                'test_case_id': test_case.id,
                'response': None,
                'elapsed': time.time() - start_time,
                'status': 'error',
                'error': str(e)
            }

from sentence_transformers import SentenceTransformer, util

class TestAssert:
    def __init__(self):
        self.embedding_model = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2')

    def assert_forbidden(self, response, forbidden):
        """第一层：禁止词——最快，安全红线"""
        if not forbidden:
            return {'passed': True, 'hit': []}
        hit = [kw for kw in forbidden if kw in response]
        return {'passed': len(hit) == 0, 'hit': hit}

    def assert_keywords(self, response, expected_keywords):
        """第二层：关键词——必须全部命中"""
        if not expected_keywords:
            return {'passed': True}
        missing = [kw for kw in expected_keywords if kw not in response]
        return {'passed': len(missing) == 0, 'missing': missing}

    def assert_semantic(self, response, expected, threshold=0.80):
        """第三层：语义相似度——有计算成本"""
        if not expected:
            return {'passed': True}
        emb1 = self.embedding_model.encode([response])
        emb2 = self.embedding_model.encode([expected])
        similarity = util.cos_sim(emb1, emb2)[0][0].item()
        return {
            'passed': similarity >= threshold,
            'similarity': round(similarity, 4)
        }

def llm_judge(client, model, question, response, rubric):
    prompt = f"""你是测试评估员。根据评分标准判断回答是否合格。
问题：{question}
回答：{response}
评分标准：{rubric}
输出 JSON：{{"score": 1-5, "passed": true/false, "reason": "..."}}"""
    result = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        temperature=0, max_tokens=300)
    return json.loads(result.choices[0].message.content)

def compare_reports(old_report, new_report):
    old_map = {r['id']: r['passed'] for r in old_report['details']}
    new_map = {r['id']: r['passed'] for r in new_report['details']}
    regressions = [id for id in new_map if old_map.get(id) and not new_map[id]]
    fixes = [id for id in new_map if not old_map.get(id, True) and new_map[id]]
    return {'regressions': regressions, 'fixes': fixes}

import pytest
from test_framework import TestCaseManager, TestExecutor, TestAssert

manager = TestCaseManager('test_cases.yaml')
executor = TestExecutor(api_key="key", base_url="url", model="gpt-4")
assertion = TestAssert()

@pytest.mark.parametrize("tc", manager.get_by_priority("P0"))
def test_p0(tc):
    result = executor.execute_single(tc)
    assert result['status'] == 'success'
    r = assertion.assert_all(result['response'], tc)
    assert r['passed'], f"{tc.id} failed: {r}"

from sentence_transformers import SentenceTransformer, util

MODELS = [
    'paraphrase-multilingual-MiniLM-L12-v2',
    'shibing624/text2vec-base-chinese',
    'BAAI/bge-large-zh-v1.5',
]

def compare_models(sentence_pairs):
    results = {}
    for name in MODELS:
        model = SentenceTransformer(name)
        sims = []
        for s1, s2 in sentence_pairs:
            sim = util.cos_sim(
                model.encode([s1]), model.encode([s2])
            )[0][0].item()
            sims.append(round(sim, 4))
        results[name] = {'mean': sum(sims)/len(sims), 'scores': sims}
    return results

from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(
    input="我的订单到哪了",
    actual_output="您的订单已发货，预计明天到达",
    expected_output="您的订单已发货，预计明天到达",
)
result = evaluate(test_cases=[test_case],
    metrics=[AnswerRelevancyMetric(threshold=0.7)])
