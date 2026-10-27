"""
03-模型评测自动化：批量测试+自动报告生成
对应文章：【评测系列2】54个任务5个维度-OpenClaw-Agent评测
作者：14年测试老兵
"""

import json
import time
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict
from datetime import datetime


# ============================================================
# 数据模型
# ============================================================

@dataclass
class TestCase:
    """测试用例"""
    id: str
    category: str          # 任务类别：写作/编程/推理/对话/知识
    difficulty: str        # 难度：简单/中等/困难
    prompt: str
    expected_keywords: List[str] = field(default_factory=list)
    expected_avoid: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """测试结果"""
    test_case: TestCase
    response: str
    success: bool
    score: float           # 0-100
    issues: List[str] = field(default_factory=list)
    latency_ms: float = 0


@dataclass
class EvaluationReport:
    """评测报告"""
    model_name: str
    total_cases: int
    passed: int
    failed: int
    avg_score: float
    avg_latency_ms: float
    category_scores: Dict[str, float]
    results: List[TestResult]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# 评测引擎
# ============================================================

class ModelEvaluator:
    """模型评测器"""

    def __init__(self, model_name: str = "qwen3.5-plus"):
        self.model_name = model_name
        self.results: List[TestResult] = []

    def run_single_test(self, test_case: TestCase) -> TestResult:
        """执行单个测试用例"""
        print(f"  执行: [{test_case.category}/{test_case.difficulty}] {test_case.prompt[:30]}...")

        start = time.time()

        # 模拟调用模型（实际使用时替换为真实API调用）
        response = self._call_model(test_case.prompt)

        latency = (time.time() - start) * 1000

        # 自动评分
        score = self._auto_score(test_case, response)
        issues = self._extract_issues(test_case, response)

        result = TestResult(
            test_case=test_case,
            response=response,
            success=score >= 60,
            score=score,
            issues=issues,
            latency_ms=latency
        )

        self.results.append(result)
        return result

    def run_batch(self, test_cases: List[TestCase]) -> EvaluationReport:
        """批量执行测试"""
        print(f"\n🚀 开始批量评测: {self.model_name}")
        print(f"   用例数: {len(test_cases)}")
        print("-" * 60)

        for tc in test_cases:
            self.run_single_test(tc)

        # 生成报告
        passed = sum(1 for r in self.results if r.success)
        failed = len(self.results) - passed
        avg_score = sum(r.score for r in self.results) / len(self.results)
        avg_latency = sum(r.latency_ms for r in self.results) / len(self.results)

        # 按类别统计
        category_scores = {}
        for r in self.results:
            cat = r.test_case.category
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(r.score)

        category_avg = {
            cat: sum(scores) / len(scores)
            for cat, scores in category_scores.items()
        }

        report = EvaluationReport(
            model_name=self.model_name,
            total_cases=len(test_cases),
            passed=passed,
            failed=failed,
            avg_score=avg_score,
            avg_latency_ms=avg_latency,
            category_scores=category_avg,
            results=self.results
        )

        return report

    def _call_model(self, prompt: str) -> str:
        """调用模型API（模拟实现）"""
        # 实际使用时替换为：
        # from openai import OpenAI
        # client = OpenAI()
        # response = client.chat.completions.create(
        #     model=self.model_name,
        #     messages=[{"role": "user", "content": prompt}]
        # )
        # return response.choices[0].message.content

        # 模拟响应
        mock_responses = {
            "写作": "这是一篇关于人工智能发展的文章。AI正在改变我们的生活方式...",
            "编程": "以下是Python代码实现：\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
            "推理": "根据已知条件，我们可以得出以下结论：\n1. 如果A则B\n2. 已知A成立\n3. 因此B成立",
            "对话": "你好！我是AI助手，很高兴为你服务。请问有什么可以帮你的？",
            "知识": "Python是一种解释型、面向对象的高级编程语言，由Guido van Rossum于1991年发布。"
        }

        # 根据prompt关键词选择模拟响应
        for key, response in mock_responses.items():
            if key in prompt:
                return response

        return "这是一个通用的AI响应。"

    def _auto_score(self, test_case: TestCase, response: str) -> float:
        """自动评分（基于关键词匹配）"""
        score = 50  # 基础分

        # 包含期望关键词：+10分/个
        for kw in test_case.expected_keywords:
            if kw in response:
                score += 10

        # 包含应避免内容：-20分/个
        for avoid in test_case.expected_avoid:
            if avoid in response:
                score -= 20

        # 响应长度合理：+10分
        if 50 < len(response) < 2000:
            score += 10

        return min(max(score, 0), 100)

    def _extract_issues(self, test_case: TestCase, response: str) -> List[str]:
        """提取问题"""
        issues = []

        if len(response) < 20:
            issues.append("响应过短")

        for avoid in test_case.expected_avoid:
            if avoid in response:
                issues.append(f"包含不应出现的内容: {avoid}")

        missing_kw = [kw for kw in test_case.expected_keywords if kw not in response]
        if missing_kw:
            issues.append(f"缺少关键词: {', '.join(missing_kw)}")

        return issues


# ============================================================
# 报告生成
# ============================================================

class ReportGenerator:
    """报告生成器"""

    @staticmethod
    def generate_markdown(report: EvaluationReport) -> str:
        """生成Markdown格式报告"""
        lines = []
        lines.append(f"# 模型评测报告: {report.model_name}")
        lines.append(f"\n**评测时间**: {report.timestamp}")
        lines.append(f"\n**总用例数**: {report.total_cases}")
        lines.append(f"**通过率**: {report.passed}/{report.total_cases} ({report.passed/report.total_cases*100:.1f}%)")
        lines.append(f"**平均得分**: {report.avg_score:.1f}/100")
        lines.append(f"**平均延迟**: {report.avg_latency_ms:.0f}ms")

        lines.append("\n## 各维度得分\n")
        lines.append("| 维度 | 平均分 | 评级 |")
        lines.append("|------|--------|------|")
        for cat, score in report.category_scores.items():
            level = "⭐⭐⭐" if score >= 80 else "⭐⭐" if score >= 60 else "⭐"
            lines.append(f"| {cat} | {score:.1f} | {level} |")

        lines.append("\n## 失败用例\n")
        failed = [r for r in report.results if not r.success]
        if failed:
            lines.append(f"| 用例ID | 类别 | 难度 | 得分 | 问题 |")
            lines.append("|--------|------|------|------|------|")
            for r in failed:
                issues_str = "; ".join(r.issues) if r.issues else "-"
                lines.append(f"| {r.test_case.id} | {r.test_case.category} | {r.test_case.difficulty} | {r.score:.1f} | {issues_str} |")
        else:
            lines.append("✅ 全部通过！")

        return "\n".join(lines)

    @staticmethod
    def generate_json(report: EvaluationReport) -> str:
        """生成JSON格式报告"""
        data = {
            "model_name": report.model_name,
            "timestamp": report.timestamp,
            "summary": {
                "total": report.total_cases,
                "passed": report.passed,
                "failed": report.failed,
                "avg_score": report.avg_score,
                "avg_latency_ms": report.avg_latency_ms,
            },
            "category_scores": report.category_scores,
            "results": [
                {
                    "id": r.test_case.id,
                    "category": r.test_case.category,
                    "difficulty": r.test_case.difficulty,
                    "success": r.success,
                    "score": r.score,
                    "latency_ms": r.latency_ms,
                    "issues": r.issues
                }
                for r in report.results
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 使用示例
# ============================================================

def create_test_suite() -> List[TestCase]:
    """创建测试用例集（54个任务示例）"""
    test_cases = [
        # 写作类
        TestCase("W01", "写作", "简单", "写一篇关于AI发展的短文", ["AI", "发展", "未来"]),
        TestCase("W02", "写作", "中等", "写一封商务邮件，邀请客户参加产品发布会", ["邀请", "产品", "发布会"]),
        TestCase("W03", "写作", "困难", "写一个科幻小说开头，要求有反转", ["科幻", "反转", "小说"]),

        # 编程类
        TestCase("P01", "编程", "简单", "用Python写一个计算斐波那契数列的函数", ["def", "fibonacci", "return"]),
        TestCase("P02", "编程", "中等", "实现一个LRU缓存", ["LRU", "缓存", "dict"]),
        TestCase("P03", "编程", "困难", "写一个并发爬虫框架", ["并发", "爬虫", "async"]),

        # 推理类
        TestCase("R01", "推理", "简单", "如果天下雨，地面就会湿。现在地面是湿的，能推出天下雨了吗？", ["不能", "充分条件", "必要条件"]),
        TestCase("R02", "推理", "中等", "三个人戴帽子，两黑三白，猜自己帽子颜色", ["推理", "白色", "逻辑"]),
        TestCase("R03", "推理", "困难", "爱因斯坦谜题：五栋房子，猜谁养鱼", ["推理", "步骤", "结论"]),

        # 对话类
        TestCase("D01", "对话", "简单", "你好，请介绍一下你自己", ["你好", "介绍", "助手"]),
        TestCase("D02", "对话", "中等", "我最近工作压力很大，怎么办？", ["理解", "建议", "缓解"]),
        TestCase("D03", "对话", "困难", "用苏格拉底式提问法引导我思考人生意义", ["提问", "思考", "意义"]),

        # 知识类
        TestCase("K01", "知识", "简单", "Python是什么语言？", ["Python", "编程语言", "解释型"]),
        TestCase("K02", "知识", "中等", "解释一下TCP三次握手", ["TCP", "三次握手", "连接"]),
        TestCase("K03", "知识", "困难", "对比Redis和Memcached的适用场景", ["Redis", "Memcached", "对比"]),
    ]

    # 扩充到54个（模拟）
    categories = ["写作", "编程", "推理", "对话", "知识"]
    difficulties = ["简单", "中等", "困难"]
    prompts = [
        "写一篇技术博客", "写一首诗", "翻译这段英文", "总结这篇文章",
        "写一个排序算法", "实现一个链表", "写一个正则表达式",
        "分析这个逻辑问题", "解决这个数学题", "解释这个概念",
        "扮演一个角色对话", "回答用户问题", "提供建议",
        "解释量子计算", "对比两种技术", "介绍一个框架"
    ]

    for i in range(14, 55):
        cat = categories[i % len(categories)]
        diff = difficulties[i % len(difficulties)]
        prompt = prompts[i % len(prompts)]
        test_cases.append(TestCase(
            f"T{i:03d}", cat, diff,
            f"{prompt}（测试用例{i}）",
            expected_keywords=[prompt[:5]]
        ))

    return test_cases


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 模型评测自动化框架")
    print("   对应文章：【评测系列2】54个任务5个维度")
    print("=" * 60)

    # 1. 创建测试用例
    test_cases = create_test_suite()
    print(f"\n📋 测试用例: {len(test_cases)} 个")
    print(f"   类别分布: 写作/编程/推理/对话/知识")
    print(f"   难度分布: 简单/中等/困难")

    # 2. 执行评测
    evaluator = ModelEvaluator(model_name="qwen3.5-plus")
    report = evaluator.run_batch(test_cases)

    # 3. 生成报告
    generator = ReportGenerator()

    # Markdown报告
    md_report = generator.generate_markdown(report)
    print("\n" + md_report)

    # 保存JSON报告
    json_report = generator.generate_json(report)
    report_path = "evaluation_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(json_report)
    print(f"\n💾 JSON报告已保存: {report_path}")

    # 4. 输出关键指标
    print("\n" + "=" * 60)
    print("📊 评测总结")
    print("=" * 60)
    print(f"模型: {report.model_name}")
    print(f"通过率: {report.passed}/{report.total_cases} ({report.passed/report.total_cases*100:.1f}%)")
    print(f"平均得分: {report.avg_score:.1f}/100")
    print(f"平均延迟: {report.avg_latency_ms:.0f}ms")

    print("\n各维度得分:")
    for cat, score in report.category_scores.items():
        bar = "█" * int(score / 5)
        print(f"  {cat:4s} {score:5.1f} {bar}")

    print("\n✅ 评测完成！")


if __name__ == "__main__":
    main()
