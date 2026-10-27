"""摘要质量评估：ROUGE / 信息覆盖率 / 事实一致性 / 可读性"""

import re
import math
import logging
from typing import List, Dict, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class SummaryEvaluator:
    """摘要质量评估器"""

    def evaluate(self, original: str, summary: str) -> Dict:
        """综合评估摘要质量"""
        if not original or not summary:
            return {"error": "原文或摘要为空"}

        return {
            "rouge_1": self.rouge_n(original, summary, n=1),
            "rouge_2": self.rouge_n(original, summary, n=2),
            "rouge_l": self.rouge_l(original, summary),
            "compression_ratio": round(len(summary) / len(original), 4) if original else 0,
            "information_coverage": self._information_coverage(original, summary),
            "factual_consistency": self._factual_consistency(original, summary),
            "readability": self._readability(summary),
        }

    def rouge_n(self, original: str, summary: str, n: int = 1) -> Dict:
        """计算 ROUGE-N 得分"""
        orig_ngrams = self._get_ngrams(original, n)
        sum_ngrams = self._get_ngrams(summary, n)

        if not sum_ngrams or not orig_ngrams:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        # 计算重叠
        overlap = 0
        for ng, cnt in sum_ngrams.items():
            overlap += min(cnt, orig_ngrams.get(ng, 0))

        total_sum = sum(sum_ngrams.values())
        total_orig = sum(orig_ngrams.values())

        precision = overlap / total_sum if total_sum > 0 else 0
        recall = overlap / total_orig if total_orig > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    def rouge_l(self, original: str, summary: str) -> Dict:
        """计算 ROUGE-L 得分（基于最长公共子序列）"""
        orig_chars = list(original)
        sum_chars = list(summary)

        lcs_length = self._lcs_length(orig_chars, sum_chars)

        precision = lcs_length / len(sum_chars) if sum_chars else 0
        recall = lcs_length / len(orig_chars) if orig_chars else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    def _get_ngrams(self, text: str, n: int) -> Counter:
        """获取 n-gram 集合（字粒度）"""
        chars = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
        ngrams = []
        for i in range(len(chars) - n + 1):
            ngrams.append(chars[i:i + n])
        return Counter(ngrams)

    @staticmethod
    def _lcs_length(seq1: List, seq2: List) -> int:
        """计算最长公共子序列长度"""
        m, n = len(seq1), len(seq2)
        if m == 0 or n == 0:
            return 0
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]

    def _information_coverage(self, original: str, summary: str) -> float:
        """信息覆盖率：摘要覆盖原文多少关键信息"""
        key_points = self._extract_key_points(original)
        if not key_points:
            return 1.0

        covered = sum(1 for kp in key_points if kp in summary)
        return round(covered / len(key_points), 4)

    def _extract_key_points(self, text: str) -> List[str]:
        """提取关键信息点"""
        key_points = []
        # 提取数字
        numbers = re.findall(r"\d{4}年|\d+%|\d+\.\d+", text)
        key_points.extend(numbers)
        # 提取专有名词
        proper_nouns = re.findall(r"[A-Z]{2,}|[\u4e00-\u9fff]{4,}", text)
        key_points.extend(proper_nouns[:10])
        return key_points

    def _factual_consistency(self, original: str, summary: str) -> Dict:
        """事实一致性检查"""
        orig_numbers = set(re.findall(r"\d+", original))
        sum_numbers = set(re.findall(r"\d+", summary))

        hallucinated = sum_numbers - orig_numbers
        consistency_score = 1.0 - (len(hallucinated) / len(sum_numbers)) if sum_numbers else 1.0

        return {
            "score": round(consistency_score, 4),
            "hallucinated_numbers": list(hallucinated),
            "total_numbers_in_summary": len(sum_numbers),
        }

    @staticmethod
    def _readability(summary: str) -> Dict:
        """可读性评估"""
        sentences = re.split(r"[。！？；]", summary)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {"avg_sentence_length": 0, "score": 0}

        avg_length = sum(len(s) for s in sentences) / len(sentences)
        if 15 <= avg_length <= 25:
            score = 1.0
        elif avg_length < 10:
            score = 0.7
        else:
            score = max(0.3, 1.0 - (avg_length - 25) / 50)

        return {
            "avg_sentence_length": round(avg_length, 1),
            "sentence_count": len(sentences),
            "score": round(score, 2),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    evaluator = SummaryEvaluator()

    original = """人工智能是计算机科学的一个分支，用于开发能够模拟人类智能行为的系统。
2012年，深度学习在图像识别领域取得突破，AlexNet将错误率从26%降低到15%。
2017年，Google提出Transformer架构，彻底改变了自然语言处理领域。
基于Transformer的BERT和GPT等模型在多项任务上刷新记录。"""

    summary = """人工智能用于模拟人类智能。2012年深度学习在图像识别取得突破，
错误率从26%降到15%。2017年Transformer架构改变了NLP领域，BERT和GPT刷新多项记录。"""

    results = evaluator.evaluate(original, summary)
    print("=== 摘要质量评估 ===")
    for metric, value in results.items():
        print(f"{metric}: {value}")
