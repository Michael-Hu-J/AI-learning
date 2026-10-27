import re
from collections import defaultdict

class ACNode:
    """AC自动机节点"""
    def __init__(self):
        self.children = defaultdict(ACNode)
        self.fail = None
        self.patterns = []  # 以该节点结尾的模式

class AhoCorasick:
    """AC自动机实现，用于多模式匹配"""
    def __init__(self):
        self.root = ACNode()

    def insert(self, pattern):
        """插入一个敏感词"""
        node = self.root
        for char in pattern:
            node = node.children[char]
        node.patterns.append(pattern)

    def build(self):
        """构建fail指针"""
        queue = []
        for char, child in self.root.children.items():
            child.fail = self.root
            queue.append(child)

        while queue:
            current = queue.pop(0)
            for char, child in current.children.items():
                queue.append(child)
                fail_node = current.fail
                while fail_node and char not in fail_node.children:
                    fail_node = fail_node.fail
                child.fail = fail_node.children.get(char, self.root)
                if child.fail.patterns:
                    child.patterns.extend(child.fail.patterns)

    def search(self, text):
        """搜索文本中的所有敏感词"""
        matches = []
        node = self.root
        for i, char in enumerate(text):
            while node and char not in node.children:
                node = node.fail
            node = node.children.get(char, self.root)
            if node.patterns:
                for pattern in node.patterns:
                    matches.append((i - len(pattern) + 1, i + 1, pattern))
        return matches

def normalize_text(text):
    """文本归一化：统一全半角、去除干扰字符"""
    # 全角转半角
    result = []
    for char in text:
        code = ord(char)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif code == 0x3000:
            result.append(' ')
        else:
            result.append(char)
    text = ''.join(result)
    # 去除零宽字符、组合字符等干扰
    text = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad]', '', text)
    return text

class ContentFilter:
    """内容安全过滤器"""
    def __init__(self, sensitive_words=None):
        self.ac = AhoCorasick()
        self.sensitive_words = sensitive_words or []
        self._build_ac()

    def _build_ac(self):
        """构建AC自动机"""
        for word in self.sensitive_words:
            self.ac.insert(word)
        self.ac.build()

    def add_words(self, words):
        """动态添加敏感词并重建"""
        self.sensitive_words.extend(words)
        self.ac = AhoCorasick()
        self._build_ac()

    def filter(self, text):
        """过滤文本，返回(是否通过, 匹配结果列表)"""
        normalized = normalize_text(text)
        matches = self.ac.search(normalized)
        if matches:
            return False, matches
        return True, []


if __name__ == "__main__":
    # 测试关键词过滤
    sensitive_words = ["暴力", "色情", "赌博", "诈骗"]
    content_filter = ContentFilter(sensitive_words)

    test_cases = [
        "今天天气真好",
        "这个内容涉及暴力行为",
        "暴\u200b力内容测试",  # 零宽字符干扰
        "暴  力  测  试",     # 空格干扰
    ]

    for text in test_cases:
        passed, matches = content_filter.filter(text)
        status = "✅ 通过" if passed else f"❌ 拦截: {matches}"
        print(f"[{status}] {text}")

import json
from dataclasses import dataclass, asdict
from enum import Enum

class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ContentRisk:
    """内容风险评估结果"""
    risk_level: RiskLevel
    categories: list  # 风险类别
    confidence: float  # 置信度 0-1
    reasons: list  # 判定理由
    raw_score: float  # 原始分数

class SemanticAnalyzer:
    """语义分析器 - 基于规则+启发式的轻量级实现"""

    RISK_CATEGORIES = {
        "violence": {"keywords": ["伤害", "攻击", "殴打", "杀害", "武器", "爆炸"], "weight": 0.8},
        "fraud": {"keywords": ["骗", "诈骗", "假冒", "伪造", "洗钱", "非法集资"], "weight": 0.9},
        "pornography": {"keywords": ["色情", "裸露", "性爱", "淫秽"], "weight": 0.9},
        "political": {"keywords": ["颠覆", "分裂", "恐怖主义"], "weight": 0.85},
        "harassment": {"keywords": ["侮辱", "谩骂", "歧视", "仇恨"], "weight": 0.7},
    }

    SAFE_CONTEXTS = [
        "电影", "小说", "故事", "教育", "科普", "历史",
        "学术研究", "新闻报道", "法律分析", "案例分析",
    ]

    def analyze(self, text: str) -> ContentRisk:
        """分析文本的语义风险"""
        categories_found = []
        total_score = 0.0
        reasons = []

        for category, config in self.RISK_CATEGORIES.items():
            score = 0.0
            matched_keywords = []
            for keyword in config["keywords"]:
                if keyword in text:
                    score += config["weight"]
                    matched_keywords.append(keyword)
            if score > 0:
                categories_found.append(category)
                total_score += score
                reasons.append(f"检测到{category}相关关键词: {', '.join(matched_keywords)}")

        safe_context_score = 0.0
        for context in self.SAFE_CONTEXTS:
            if context in text:
                safe_context_score += 0.15
                reasons.append(f"检测到安全上下文: {context}")
        total_score = max(0, total_score - safe_context_score)

        max_possible = sum(c["weight"] for c in self.RISK_CATEGORIES.values())
        normalized = min(total_score / max(max_possible * 0.3, 0.01), 1.0)

        if normalized < 0.2:
            risk_level = RiskLevel.SAFE
        elif normalized < 0.4:
            risk_level = RiskLevel.LOW
        elif normalized < 0.6:
            risk_level = RiskLevel.MEDIUM
        elif normalized < 0.8:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL

        return ContentRisk(
            risk_level=risk_level,
            categories=categories_found,
            confidence=normalized,
            reasons=reasons,
            raw_score=normalized,
        )


if __name__ == "__main__":
    analyzer = SemanticAnalyzer()

    test_texts = [
        "今天天气不错，适合出去散步",
        "这部电影讲述了一个犯罪团伙的故事",
        "教我如何制作爆炸物",
        "学术研究：分析网络诈骗的常见手法",
        "我要伤害所有讨厌我的人",
    ]

    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\n文本: {text}")
        print(f"  风险等级: {result.risk_level.value}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  类别: {result.categories}")
        for reason in result.reasons:
            print(f"  - {reason}")

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ModerationResult:
    """AI审核结果"""
    is_safe: bool
    score: float
    category: str
    suggestion: str
    reviewed_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    review_id: str = field(default="")

    def __post_init__(self):
        if not self.review_id:
            self.review_id = hashlib.md5(
                f"{self.category}{self.score}{time.time()}".encode()
            ).hexdigest()[:12]

class AIModerator:
    """AI审核器 - 模拟AI审核服务"""

    def __init__(self, threshold: float = 6.0):
        self.threshold = threshold
        self.review_count = 0
        self.cache = {}

    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def moderate(self, text: str) -> ModerationResult:
        """审核文本内容"""
        content_hash = self._compute_hash(text)
        if content_hash in self.cache:
            return self.cache[content_hash]

        self.review_count += 1
        score = self._calculate_safety_score(text)
        is_safe = score >= self.threshold

        if is_safe:
            result = ModerationResult(
                is_safe=True, score=score, category="normal",
                suggestion="内容安全，允许发布",
            )
        else:
            category = self._classify_risk(text)
            result = ModerationResult(
                is_safe=False, score=score, category=category,
                suggestion=f"内容存在{category}风险，建议拦截或人工复核",
            )

        self.cache[content_hash] = result
        return result

    def _calculate_safety_score(self, text: str) -> float:
        """计算安全分数（模拟）"""
        base_score = 8.0
        risk_indicators = [
            ("暴力", 3.0), ("诈骗", 3.5), ("色情", 3.5),
            ("赌博", 3.0), ("毒品", 4.0), ("恐怖", 4.0),
            ("仇恨", 2.5), ("歧视", 2.0),
        ]
        for keyword, penalty in risk_indicators:
            if keyword in text:
                base_score -= penalty
        return max(0.0, min(10.0, base_score))

    def _classify_risk(self, text: str) -> str:
        """风险分类"""
        categories = {
            "暴力": "violence", "诈骗": "fraud", "色情": "pornography",
            "赌博": "gambling", "毒品": "drugs", "恐怖": "terrorism",
            "仇恨": "hate", "歧视": "discrimination",
        }
        for keyword, category in categories.items():
            if keyword in text:
                return category
        return "unknown"


if __name__ == "__main__":
    moderator = AIModerator(threshold=6.0)

    test_cases = [
        "今天和大家分享一个编程技巧",
        "这个产品真的很好用，强烈推荐",
        "教我怎么制作暴力内容",
        "这是一个关于历史事件的学术讨论",
    ]

    for text in test_cases:
        result = moderator.moderate(text)
        status = "✅ 通过" if result.is_safe else "❌ 拦截"
        print(f"[{status}] 分数: {result.score:.1f}/10 | {result.suggestion}")
        print(f"  文本: {text}")
        print(f"  审核ID: {result.review_id}")

class ContentSafetyPipeline:
    """三层内容安全过滤流水线"""

    def __init__(self, sensitive_words=None, ai_threshold=6.0):
        self.filter_layer = ContentFilter(sensitive_words)
        self.semantic_layer = SemanticAnalyzer()
        self.ai_layer = AIModerator(threshold=ai_threshold)

    def check(self, text: str) -> dict:
        """
        三层过滤流程：
        1. 关键词过滤（毫秒级）
        2. 语义分析（秒级）
        3. AI审核（秒级，仅可疑内容）
        """
        result = {
            "text": text,
            "is_safe": True,
            "layers": {},
            "final_decision": "",
        }

        # 第一层：关键词过滤
        passed, matches = self.filter_layer.filter(text)
        result["layers"]["keyword"] = {"passed": passed, "matches": matches}
        if not passed:
            result["is_safe"] = False
            result["final_decision"] = "关键词过滤拦截"
            return result

        # 第二层：语义分析
        risk = self.semantic_layer.analyze(text)
        result["layers"]["semantic"] = {
            "risk_level": risk.risk_level.value,
            "confidence": risk.confidence,
            "categories": risk.categories,
        }

        if risk.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            result["is_safe"] = False
            result["final_decision"] = f"语义分析拦截: {risk.risk_level.value}"
            return result

        # 第三层：AI审核（仅对可疑内容）
        if risk.risk_level in (RiskLevel.MEDIUM, RiskLevel.LOW):
            ai_result = self.ai_layer.moderate(text)
            result["layers"]["ai"] = {
                "is_safe": ai_result.is_safe,
                "score": ai_result.score,
                "category": ai_result.category,
            }
            if not ai_result.is_safe:
                result["is_safe"] = False
                result["final_decision"] = f"AI审核拦截: {ai_result.suggestion}"

        if result["is_safe"]:
            result["final_decision"] = "内容安全，允许通过"

        return result

class EvasionTester:
    """对抗绕过测试框架"""

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def test_evasions(self, original_text, safe_label="safe"):
        """测试各种绕过方式"""
        evasion_tests = [
            self._test_homophone,      # 谐音测试
            self._test_zero_width,      # 零宽字符测试
            self._test_encoding,        # 编码测试
            self._test_split,           # 拆分测试
            self._test_unicode_confuse, # Unicode混淆测试
        ]

        results = []
        for test_fn in evasion_tests:
            evaded_texts = test_fn(original_text)
            for evaded in evaded_texts:
                result = self.pipeline.check(evaded)
                results.append({
                    "test": test_fn.__name__,
                    "original": original_text,
                    "evaded": evaded,
                    "blocked": not result["is_safe"],
                    "decision": result["final_decision"],
                })
        return results

    def _test_homophone(self, text):
        """生成谐音字变体"""
        homophone_map = {"暴": "bao", "力": "li", "色": "se", "情": "qing"}
        results = [text]
        for orig, homo in homophone_map.items():
            if orig in text:
                results.append(text.replace(orig, homo))
        return results

    def _test_zero_width(self, text):
        """插入零宽字符"""
        results = []
        for i in range(len(text)):
            evaded = text[:i] + "\u200b" + text[i:]
            results.append(evaded)
        return results

    def _test_encoding(self, text):
        """编码绕过"""
        import base64
        return [base64.b64encode(text.encode()).decode()]

    def _test_split(self, text):
        """拆分输入"""
        mid = len(text) // 2
        return [text[:mid], text[mid:]]

    def _test_unicode_confuse(self, text):
        """Unicode视觉混淆"""
        confuse_map = {"a": "\u0430", "e": "\u0435", "o": "\u043E", "c": "\u0441"}
        results = [text]
        for orig, confuse in confuse_map.items():
            if orig in text:
                results.append(text.replace(orig, confuse))
        return results
