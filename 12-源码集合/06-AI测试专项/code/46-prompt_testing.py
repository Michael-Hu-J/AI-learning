import json
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class PromptResult:
    """单次 Prompt 测试结果"""
    prompt_id: str
    prompt_text: str
    response: str
    score_relevance: float = 0.0
    score_completeness: float = 0.0
    score_accuracy: float = 0.0
    score_readability: float = 0.0
    token_count: int = 0
    latency_ms: float = 0.0


class PromptComparator:
    """Prompt 对比测试器"""

    def __init__(self, llm_call_func):
        self.llm = llm_call_func

    def compare_prompts(
        self,
        prompt_variants: List[Tuple[str, str]],
        test_inputs: List[str],
        temperature: float = 0.3
    ) -> List[PromptResult]:
        """对比多个 Prompt 变体"""
        results = []

        for pid, prompt_text in prompt_variants:
            for test_input in test_inputs:
                full_prompt = f"{prompt_text}\n\n用户输入：{test_input}"
                response = self.llm(full_prompt, temperature=temperature)

                result = PromptResult(
                    prompt_id=pid,
                    prompt_text=prompt_text,
                    response=response,
                    score_relevance=self._score_relevance(test_input, response),
                    score_completeness=self._score_completeness(response),
                    score_accuracy=self._score_accuracy(response),
                    score_readability=self._score_readability(response),
                    token_count=len(response),
                )
                results.append(result)

        return results

    def generate_comparison_report(self, results: List[PromptResult]) -> str:
        """生成对比报告"""
        by_prompt = {}
        for r in results:
            by_prompt.setdefault(r.prompt_id, []).append(r)

        report = "=== Prompt 对比报告 ===\n\n"
        for pid, prompt_results in by_prompt.items():
            avg_relevance = sum(r.score_relevance for r in prompt_results) / len(prompt_results)
            avg_completeness = sum(r.score_completeness for r in prompt_results) / len(prompt_results)
            avg_accuracy = sum(r.score_accuracy for r in prompt_results) / len(prompt_results)
            avg_readability = sum(r.score_readability for r in prompt_results) / overall = (avg_relevance * 0.3 + avg_completeness * 0.25 +
                       avg_accuracy * 0.25 + avg_readability * 0.2)

            report += (
                f"Prompt [{pid}]:\n"
                f"  相关性: {avg_relevance:.2f} | 完整性: {avg_completeness:.2f} | "
                f"准确性: {avg_accuracy:.2f} | 可读性: {avg_readability:.2f}\n"
                f"  综合评分: {overall:.2f}\n\n"
            )

        return report

    def _score_relevance(self, question: str, answer: str) -> float:
        """评估回答与问题的相关性"""
        question_words = set(re.findall(r'[\u4e00-\u9fff\w]+', question.lower()))
        answer_words = set(re.findall(r'[\u4e00-\u9fff\w]+', answer.lower()))
        if not question_words:
            return 0.0
        overlap = len(question_words & answer_words) / len(question_words)
        return min(overlap * 2, 1.0)

    def _score_completeness(self, answer: str) -> float:
        """评估回答的完整性"""
        if len(answer) < 20:
            return 0.2
        if len(answer) < 100:
            return 0.5
        has_structure = any(c in answer for c in ['\n', '首先', '其次', '最后', '1.', '2.'])
        return 0.7 if has_structure else 0.6

    def _score_accuracy(self, answer: str) -> float:
        """评估回答的准确性"""
        error_patterns = ['我不知道', '我无法', '作为AI', '我不能']
        error_count = sum(1 for p in error_patterns if p in answer)
        return max(0, 1.0 - error_count * 0.2)

    def _score_readability(self, answer: str) -> float:
        """评估回答的可读性"""
        if not answer:
            return 0.0
        sentences = re.split(r'[。！？]', answer)
        avg_len = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        if 10 <= avg_len <= 50:
            return 0.8
        return 0.5

import re
import json
from typing import List, Dict


class PromptAutoEvaluator:
    """Prompt 自动化评测器（LLM Judge 版）"""

    def __init__(self, llm_call_func, judge_llm_func=None):
        self.llm = llm_call_func
        self.judge_llm = judge_llm_func or llm_call_func

    def evaluate_with_llm_judge(
        self,
        prompt: str,
        test_input: str,
        response: str,
        criteria: Dict[str, str]
    ) -> Dict[str, float]:
        """用 LLM-as-a-Judge 方法评测 Prompt 输出"""
        criteria_text = "\n".join([f"- {k}: {v}" for k, v in criteria.items()])

        judge_prompt = (
            f"请根据以下标准对 AI 的回答进行评分（1-5分）：\n\n"
            f"评测标准：\n{criteria_text}\n\n"
            f"用户 Prompt：{prompt}\n"
            f"用户输入：{test_input}\n"
            f"AI 回答：{response}\n\n"
            f"请严格按以下 JSON 格式返回评分：\n"
            f'{{"relevance": 分数, "completeness": 分数, "accuracy": 分数, "readability": 分数}}'
        )

        judge_result = self.judge_llm(judge_prompt)
        json_match = re.search(r'\{[^}]+\}', judge_result)
        if json_match:
            return json.loads(json_match.group())
        return {"relevance": 3, "completeness": 3, "accuracy": 3, "readability": 3}

    def batch_evaluate(
        self,
        prompt: str,
        test_cases: List[Dict[str, str]],
        criteria: Dict[str, str]
    ) -> Dict:
        """批量评测一个 Prompt"""
        scores = {"relevance": [], "completeness": [], "accuracy": [], "readability": []}

        for case in test_cases:
            response = self.llm(f"{prompt}\n\n输入：{case['input']}")
            result = self.evaluate_with_llm_judge(prompt, case['input'], response, criteria)
            for key in scores:
                scores[key].append(result.get(key, 3))

        import statistics
        return {
            metric: {
                "mean": round(statistics.mean(vals), 2),
                "min": min(vals),
                "max": max(vals),
                "std": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0
            }
            for metric, vals in scores.items()
        }

def test_prompt_stability(prompt, num_runs=20, threshold=0.85, temperature=0.3):
    """同 Prompt 跑 N 次，两两算语义相似度 — 勿用字符串完全匹配"""
    responses = [call_llm(prompt, temperature=temperature) for _ in range(num_runs)]
    embeddings = model.encode(responses)
    sim_matrix = util.cos_sim(embeddings, embeddings)
    similarities = [sim_matrix[i][j].item() for i in range(n) for j in range(i+1, n)]
    avg_sim = np.mean(similarities)
    return {"avg_similarity": avg_sim, "stable": avg_sim >= threshold}
