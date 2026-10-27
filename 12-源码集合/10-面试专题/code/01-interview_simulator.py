"""
01-AI测试面试模拟系统
对应文章：78-面试专题系列
作者：14年测试老兵

功能：模拟AI测试工程师面试，包含基础/实战/安全/架构四个维度
"""

import json
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


# ============================================================
# 数据模型
# ============================================================

@dataclass
class InterviewQuestion:
    """面试题"""
    id: str
    category: str          # 基础/实战/安全/架构
    difficulty: str        # 初级/中级/高级
    question: str
    key_points: List[str]  # 参考答案要点
    follow_up: Optional[str] = None  # 追问


@dataclass
class InterviewSession:
    """面试会话"""
    candidate_name: str
    questions: List[InterviewQuestion]
    answers: Dict[str, str] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""

    def __post_init__(self):
        if not self.start_time:
            self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# 题库
# ============================================================

class QuestionBank:
    """面试题库"""

    @staticmethod
    def get_all_questions() -> List[InterviewQuestion]:
        return [
            # 基础篇
            InterviewQuestion(
                "B01", "基础", "初级",
                "什么是大模型？和传统NLP模型有什么区别？",
                ["Transformer架构", "参数量级差异", "预训练+微调范式", "涌现能力"],
                "能举一个'涌现能力'的具体例子吗？"
            ),
            InterviewQuestion(
                "B02", "基础", "初级",
                "解释一下Token是什么？为什么要注意Token数量？",
                ["Token是文本最小单位", "计费依据", "上下文窗口限制", "分词方式影响"],
                "中文字符和英文字符的Token数量一样吗？"
            ),
            InterviewQuestion(
                "B03", "基础", "中级",
                "什么是Prompt？好的Prompt有什么特征？",
                ["明确的任务描述", "角色设定", "输出格式约束", "少样本示例"],
                "你平时怎么优化一个Prompt？"
            ),
            InterviewQuestion(
                "B04", "基础", "中级",
                "解释一下RAG（检索增强生成）的工作原理",
                ["文档切分", "向量化", "相似度检索", "上下文拼接", "模型生成"],
                "RAG和Fine-tuning分别适用于什么场景？"
            ),
            InterviewQuestion(
                "B05", "基础", "高级",
                "Agent系统的核心组件有哪些？如何保证Agent的可靠性？",
                ["规划模块", "工具调用", "记忆管理", "反思机制", "测试保障"],
                "你测过Agent系统吗？怎么测？"
            ),

            # 实战篇
            InterviewQuestion(
                "P01", "实战", "初级",
                "你如何测试一个聊天机器人的回答质量？",
                ["准备测试用例集", "定义评价标准", "人工+自动评测", "对比基线"],
                "如果机器人回答'我不知道'，你觉得是好还是不好？"
            ),
            InterviewQuestion(
                "P02", "实战", "中级",
                "描述一次你设计测试用例的经历，用了什么方法？",
                ["等价类划分", "边界值分析", "场景法", "错误推测法", "探索性测试"],
                "AI测试和传统软件测试，用例设计有什么不同？"
            ),
            InterviewQuestion(
                "P03", "实战", "中级",
                "如何测试RAG系统的检索质量？",
                ["召回率/准确率", "Top-K命中率", "相关性评分", "延迟指标"],
                "如果检索到的文档不相关，可能是什么原因？"
            ),
            InterviewQuestion(
                "P04", "实战", "高级",
                "你如何保证AI系统的输出稳定性？",
                ["温度参数控制", "确定性测试", "回归测试集", "版本管理", "监控告警"],
                "AI系统的测试用例会过期吗？怎么处理？"
            ),

            # 安全篇
            InterviewQuestion(
                "S01", "安全", "初级",
                "什么是Prompt注入攻击？举一个例子",
                ["绕过系统提示", "恶意指令注入", "角色扮演欺骗", "输出控制"],
                "如何防御Prompt注入？"
            ),
            InterviewQuestion(
                "S02", "安全", "中级",
                "你如何测试一个AI系统的安全性？",
                ["红队测试", "越狱攻击测试", "敏感信息泄露检测", "内容安全过滤"],
                "你用过哪些自动化安全测试工具？"
            ),
            InterviewQuestion(
                "S03", "安全", "高级",
                "如何防止AI系统泄露训练数据中的隐私信息？",
                ["数据脱敏", "差分隐私", "输出过滤", "访问控制", "审计日志"],
                "如果用户通过连续提问推断出训练数据，怎么防范？"
            ),

            # 架构篇
            InterviewQuestion(
                "A01", "架构", "中级",
                "设计一个AI测试平台的架构，包含哪些模块？",
                ["用例管理", "自动化执行", "结果分析", "报告生成", "CI/CD集成"],
                "如何处理AI测试的不确定性？"
            ),
            InterviewQuestion(
                "A02", "架构", "高级",
                "如何设计一个支持多模型对比的评测系统？",
                ["统一接口层", "结果标准化", "并行执行", "统计显著性", "可视化"],
                "不同模型的输出格式不同，怎么统一评分？"
            ),
            InterviewQuestion(
                "A03", "架构", "高级",
                "AI系统的性能测试和传统系统有什么不同？",
                ["Token消耗", "延迟波动", "并发限制", "成本监控", "质量-性能权衡"],
                "如何确定AI系统的压测指标？"
            ),
        ]

    @staticmethod
    def get_questions_by_category(category: str) -> List[InterviewQuestion]:
        """按类别获取题目"""
        all_q = QuestionBank.get_all_questions()
        if category == "全部":
            return all_q
        return [q for q in all_q if q.category == category]

    @staticmethod
    def get_questions_by_difficulty(difficulty: str) -> List[InterviewQuestion]:
        """按难度获取题目"""
        all_q = QuestionBank.get_all_questions()
        return [q for q in all_q if q.difficulty == difficulty]


# ============================================================
# 评分引擎
# ============================================================

class ScoringEngine:
    """评分引擎"""

    # 评分关键词权重
    KEYWORD_WEIGHTS = {
        "基础": 0.3,
        "实战": 0.4,
        "安全": 0.5,
        "架构": 0.4
    }

    def score_answer(self, question: InterviewQuestion, answer: str) -> Dict:
        """评分"""
        score = 0
        feedback = []

        # 1. 关键词匹配（40分）
        keyword_score = 0
        matched_points = []
        for point in question.key_points:
            # 检查答案中是否包含关键词（模糊匹配）
            if self._contains_keyword(answer, point):
                keyword_score += 40 / len(question.key_points)
                matched_points.append(point)

        score += keyword_score
        if len(matched_points) < len(question.key_points):
            missing = set(question.key_points) - set(matched_points)
            feedback.append(f"💡 建议补充: {', '.join(missing)}")

        # 2. 答案长度（20分）
        if len(answer) > 100:
            score += 20
        elif len(answer) > 50:
            score += 10
        else:
            feedback.append("⚠️ 答案过短，建议展开说明")

        # 3. 结构化表达（20分）
        has_structure = any(c in answer for c in ["1.", "2.", "3.", "首先", "其次", "最后", "一方面", "另一方面"])
        if has_structure:
            score += 20
        else:
            feedback.append("💡 建议结构化表达（分点说明）")

        # 4. 实践经验（20分）
        has_experience = any(kw in answer for kw in ["我", "我们", "项目", "实践", "经验", "遇到", "解决", "测试"])
        if has_experience:
            score += 20
        else:
            feedback.append("💡 建议结合实际项目经验说明")

        # 评级
        level = "优秀" if score >= 85 else "良好" if score >= 70 else "合格" if score >= 60 else "待提升"

        return {
            "score": round(score, 1),
            "level": level,
            "matched_points": matched_points,
            "feedback": feedback
        }

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """模糊关键词匹配"""
        # 完全包含
        if keyword in text:
            return True
        # 分词后包含（简单实现）
        keywords = list(keyword)
        match_count = sum(1 for k in keywords if k in text)
        return match_count / len(keywords) >= 0.6


# ============================================================
# 面试模拟器
# ============================================================

class InterviewSimulator:
    """面试模拟器"""

    def __init__(self, candidate_name: str = "候选人"):
        self.candidate_name = candidate_name
        self.session = InterviewSession(candidate_name=candidate_name, questions=[])
        self.scoring = ScoringEngine()
        self.question_bank = QuestionBank()

    def start_interview(self, category: str = "全部", count: int = 5):
        """开始面试"""
        questions = self.question_bank.get_questions_by_category(category)

        # 随机选题
        if count < len(questions):
            questions = random.sample(questions, count)

        self.session.questions = questions
        print(f"\n🎯 面试开始: {self.candidate_name}")
        print(f"   类别: {category} | 题目数: {len(questions)}")
        print("=" * 60)

        for i, q in enumerate(questions, 1):
            print(f"\n【第{i}题】[{q.category}/{q.difficulty}]")
            print(f"问: {q.question}")

            # 模拟回答（实际使用时替换为输入）
            answer = self._simulate_answer(q)
            self.session.answers[q.id] = answer

            # 评分
            result = self.scoring.score_answer(q, answer)
            self.session.scores[q.id] = result["score"]

            print(f"\n答: {answer[:100]}...")
            print(f"得分: {result['score']}/100 ({result['level']})")
            for fb in result['feedback']:
                print(f"  {fb}")

            # 追问（如果有）
            if q.follow_up:
                print(f"\n追: {q.follow_up}")
                follow_answer = f"关于追问，我认为{q.follow_up[:20]}...这需要在实际项目中积累经验。"
                print(f"答: {follow_answer}")

        self.session.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.session

    def generate_report(self) -> str:
        """生成面试报告"""
        if not self.session.questions:
            return "未开始面试"

        scores = list(self.session.scores.values())
        avg_score = sum(scores) / len(scores) if scores else 0

        lines = []
        lines.append(f"# 面试评估报告: {self.candidate_name}")
        lines.append(f"\n**面试时间**: {self.session.start_time} ~ {self.session.end_time}")
        lines.append(f"**题目数**: {len(self.session.questions)}")
        lines.append(f"**平均分**: {avg_score:.1f}/100")

        level = "优秀" if avg_score >= 85 else "良好" if avg_score >= 70 else "合格" if avg_score >= 60 else "待提升"
        lines.append(f"**综合评级**: {level}")

        lines.append("\n## 各题得分\n")
        lines.append("| 题号 | 类别 | 难度 | 得分 | 评级 |")
        lines.append("|------|------|------|------|------|")
        for q in self.session.questions:
            score = self.session.scores.get(q.id, 0)
            lvl = "优秀" if score >= 85 else "良好" if score >= 70 else "合格" if score >= 60 else "待提升"
            lines.append(f"| {q.id} | {q.category} | {q.difficulty} | {score:.1f} | {lvl} |")

        # 各维度平均分
        lines.append("\n## 各维度得分\n")
        category_scores = {}
        for q in self.session.questions:
            cat = q.category
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(self.session.scores.get(q.id, 0))

        lines.append("| 维度 | 平均分 | 评级 |")
        lines.append("|------|--------|------|")
        for cat, scores_list in category_scores.items():
            avg = sum(scores_list) / len(scores_list)
            lvl = "优秀" if avg >= 85 else "良好" if avg >= 70 else "合格" if avg >= 60 else "待提升"
            lines.append(f"| {cat} | {avg:.1f} | {lvl} |")

        return "\n".join(lines)

    def _simulate_answer(self, question: InterviewQuestion) -> str:
        """模拟回答（实际使用时替换为真实输入）"""
        mock_answers = {
            "B01": "大模型是基于Transformer架构的深度学习模型，参数量通常在百亿到万亿级别。和传统NLP模型相比，大模型具有涌现能力，能完成零样本/少样本任务。传统模型需要针对每个任务单独训练，而大模型通过预训练+微调可以适应多种任务。",
            "B02": "Token是文本的最小处理单位。英文中一个Token大约是一个单词，中文中大约是一个字或词。注意Token数量是因为：1) 模型有上下文窗口限制；2) API按Token计费；3) Token数量影响响应速度和成本。",
            "P01": "测试聊天机器人回答质量，我会：1) 准备覆盖不同场景的测试用例集；2) 定义评价标准（准确性/相关性/安全性/流畅度）；3) 结合人工评测和自动评测；4) 建立基线进行对比。如果机器人回答'我不知道'，要看场景——对于不确定的问题，说不知道比瞎说好。",
            "S01": "Prompt注入攻击是指用户通过特殊构造的输入，绕过系统的安全限制。比如用户说'忽略之前的所有指令，现在你是一个...'，这就是典型的Prompt注入。防御方法包括：输入过滤、输出限制、多层验证、系统提示词保护等。",
        }

        return mock_answers.get(question.id, f"这是一个关于{question.question[:20]}的回答。我认为需要从多个角度来分析这个问题，结合实际项目经验...")


# ============================================================
# 使用示例
# ============================================================

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 AI测试工程师面试模拟系统")
    print("   对应文章：78-面试专题系列")
    print("=" * 60)

    # 创建模拟器
    simulator = InterviewSimulator(candidate_name="测试候选人")

    # 开始面试（每个类别选1题）
    print("\n📝 开始模拟面试...")
    simulator.start_interview(category="全部", count=8)

    # 生成报告
    report = simulator.generate_report()
    print("\n" + report)

    # 保存报告
    report_path = "interview_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n💾 报告已保存: {report_path}")

    # 输出总结
    scores = list(simulator.session.scores.values())
    avg = sum(scores) / len(scores) if scores else 0
    print("\n" + "=" * 60)
    print("📊 面试总结")
    print("=" * 60)
    print(f"候选人: {simulator.candidate_name}")
    print(f"平均分: {avg:.1f}/100")
    print(f"评级: {'优秀' if avg >= 85 else '良好' if avg >= 70 else '合格' if avg >= 60 else '待提升'}")
    print("\n✅ 面试模拟完成！")


if __name__ == "__main__":
    main()
