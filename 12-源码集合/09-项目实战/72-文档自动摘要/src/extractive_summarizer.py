"""抽取式摘要：基于 TextRank 算法"""

import re
import math
import logging
from typing import List, Dict, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class ExtractiveSummarizer:
    """抽取式摘要：基于 TextRank 算法"""

    def __init__(self, damping: float = 0.85, iterations: int = 50):
        self.damping = damping
        self.iterations = iterations

    def summarize(self, text: str, summary_ratio: float = 0.2) -> str:
        """
        生成抽取式摘要
        summary_ratio: 摘要占原文的比例
        """
        if not text or not text.strip():
            return ""

        sentences = self._split_sentences(text)
        if len(sentences) <= 3:
            return text

        # 构建句子相似度矩阵
        n = len(sentences)
        similarity_matrix = self._build_similarity_matrix(sentences)

        # TextRank 迭代
        scores = self._textrank(similarity_matrix, n)

        # 按得分排序，选取 Top-K
        ranked_indices = sorted(range(n), key=lambda i: scores[i], reverse=True)
        k = max(1, int(n * summary_ratio))
        top_indices = sorted(ranked_indices[:k])  # 保持原文顺序

        # 按原文顺序拼接
        summary_sentences = [sentences[i] for i in top_indices]
        result = "\n".join(summary_sentences)
        logger.info(f"抽取式摘要: {len(sentences)}句 -> {k}句 (压缩比: {len(result)/len(text):.1%})")
        return result

    def _split_sentences(self, text: str) -> List[str]:
        """按句子切分"""
        sentences = re.split(r"([。！？；]+)", text)
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if sentence.strip():
                result.append(sentence.strip())
        return result

    def _build_similarity_matrix(self, sentences: List[str]) -> List[List[float]]:
        """构建句子相似度矩阵（基于词重叠）"""
        n = len(sentences)
        matrix = [[0.0] * n for _ in range(n)]
        word_sets = [self._extract_words(s) for s in sentences]

        for i in range(n):
            for j in range(i + 1, n):
                overlap = len(word_sets[i] & word_sets[j])
                if not word_sets[i] or not word_sets[j]:
                    continue
                sim = overlap / math.sqrt(len(word_sets[i]) * len(word_sets[j]))
                matrix[i][j] = sim
                matrix[j][i] = sim

        return matrix

    def _textrank(self, matrix: List[List[float]], n: int) -> List[float]:
        """TextRank 迭代算法"""
        scores = [1.0] * n

        for _ in range(self.iterations):
            new_scores = [0.0] * n
            for i in range(n):
                score = 1 - self.damping
                for j in range(n):
                    if i != j and matrix[j][i] > 0:
                        denom = sum(matrix[j][k] for k in range(n) if k != j)
                        if denom > 0:
                            score += self.damping * (matrix[j][i] / denom) * scores[j]
                new_scores[i] = score
            scores = new_scores

        # 归一化
        max_score = max(scores) if scores else 1
        if max_score > 0:
            scores = [s / max_score for s in scores]
        return scores

    @staticmethod
    def _extract_words(text: str) -> set:
        """提取词语集合（字粒度）"""
        chars = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
        return set(chars)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample = """人工智能（Artificial Intelligence，简称 AI）是计算机科学的一个分支，
用于开发能够模拟人类智能行为的系统。自 1956 年达特茅斯会议首次提出"人工智能"概念以来，
该领域经历了多次发展浪潮。

机器学习是人工智能的核心技术之一。2012 年，深度学习在图像识别领域取得突破性进展，
AlexNet 在 ImageNet 竞赛中将错误率从 26% 降低到 15%。此后，深度学习在语音识别、
自然语言处理、机器翻译等领域相继取得重大突破。

2017 年，Google 提出了 Transformer 架构，彻底改变了自然语言处理领域。
基于 Transformer 的 BERT、GPT 等模型在多项 NLP 任务上刷新了记录。"""

    extractor = ExtractiveSummarizer()
    result = extractor.summarize(sample, summary_ratio=0.3)
    print("=== 抽取式摘要 ===")
    print(result)
    print(f"\n原文字数: {len(sample)} | 摘要字数: {len(result)} | 压缩比: {len(result)/len(sample):.1%}")
