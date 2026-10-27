"""
02-AI测试岗位能力评估工具
对应文章：82-AI测试面试题-架构篇
作者：14年测试老兵

功能：评估测试工程师的AI能力矩阵，生成技能雷达图数据
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime


# ============================================================
# 能力模型
# ============================================================

@dataclass
class SkillDimension:
    """技能维度"""
    name: str
    description: str
    sub_skills: List[str]
    weight: float  # 权重


@dataclass
class SkillAssessment:
    """技能评估结果"""
    candidate_name: str
    dimensions: Dict[str, Dict[str, int]]  # 维度 -> {子技能: 分数}
    overall_score: float = 0.0
    level: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# 能力矩阵定义
# ============================================================

SKILL_MATRIX = {
    "大模型基础": SkillDimension(
        "大模型基础",
        "理解LLM基本原理、架构、参数、Token等基础知识",
        ["Transformer架构", "Token与上下文窗口", "温度与采样参数", "模型选择", "API调用"],
        0.15
    ),
    "Prompt工程": SkillDimension(
        "Prompt工程",
        "设计、优化、测试Prompt的能力",
        ["Prompt设计", "少样本学习", "思维链", "Prompt迭代", "自动化评测"],
        0.15
    ),
    "RAG系统": SkillDimension(
        "RAG系统",
        "构建和测试检索增强生成系统",
        ["文档处理", "向量化", "检索优化", "混合检索", "RAG评测"],
        0.15
    ),
    "Agent系统": SkillDimension(
        "Agent系统",
        "构建和测试多Agent协作系统",
        ["Agent架构", "工具调用", "任务规划", "记忆管理", "工作流编排"],
        0.15
    ),
    "AI测试方法": SkillDimension(
        "AI测试方法",
        "AI系统特有的测试方法论",
        ["幻觉检测", "稳定性测试", "回归测试", "探索性测试", "自动化框架"],
        0.20
    ),
    "安全与合规": SkillDimension(
        "安全与合规",
        "AI系统的安全测试和合规要求",
        ["Prompt注入", "越狱测试", "数据隐私", "内容安全", "审计日志"],
        0.10
    ),
    "性能与成本": SkillDimension(
        "性能与成本",
        "AI系统的性能优化和成本控制",
        ["延迟优化", "并发测试", "缓存策略", "成本估算", "监控告警"],
        0.10
    ),
}


# ============================================================
# 评估引擎
# ============================================================

class SkillAssessor:
    """技能评估器"""

    def __init__(self):
        self.matrix = SKILL_MATRIX

    def assess(self, candidate_name: str, skill_scores: Dict[str, Dict[str, int]]) -> SkillAssessment:
        """
        评估技能

        Args:
            candidate_name: 候选人姓名
            skill_scores: {维度: {子技能: 分数(1-5)}}

        Returns:
            SkillAssessment
        """
        assessment = SkillAssessment(
            candidate_name=candidate_name,
            dimensions=skill_scores
        )

        total_score = 0
        total_weight = 0
        strengths = []
        weaknesses = []

        for dim_name, dim in self.matrix.items():
            if dim_name not in skill_scores:
                continue

            scores = skill_scores[dim_name]
            dim_score = sum(scores.values()) / len(scores) if scores else 0
            weighted_score = dim_score * dim.weight

            total_score += weighted_score
            total_weight += dim.weight

            # 找出强项和弱项
            best_skill = max(scores, key=scores.get) if scores else ""
            worst_skill = min(scores, key=scores.get) if scores else ""

            if scores.get(best_skill, 0) >= 4:
                strengths.append(f"{dim_name}: {best_skill}")
            if scores.get(worst_skill, 0) <= 2:
                weaknesses.append(f"{dim_name}: {worst_skill}")

        # 计算总分
        assessment.overall_score = (total_score / total_weight * 20) if total_weight > 0 else 0  # 转换为百分制

        # 评级
        if assessment.overall_score >= 90:
            assessment.level = "专家"
        elif assessment.overall_score >= 80:
            assessment.level = "高级"
        elif assessment.overall_score >= 70:
            assessment.level = "中级"
        elif assessment.overall_score >= 60:
            assessment.level = "初级"
        else:
            assessment.level = "入门"

        assessment.strengths = strengths
        assessment.weaknesses = weaknesses

        return assessment


# ============================================================
# 报告生成
# ============================================================

class AssessmentReport:
    """评估报告生成器"""

    @staticmethod
    def generate_markdown(assessment: SkillAssessment) -> str:
        """生成Markdown报告"""
        lines = []
        lines.append(f"# AI测试能力评估报告: {assessment.candidate_name}")
        lines.append(f"\n**评估时间**: {assessment.timestamp}")
        lines.append(f"\n**综合评分**: {assessment.overall_score:.1f}/100")
        lines.append(f"**能力等级**: {assessment.level}")

        # 各维度得分
        lines.append("\n## 各维度得分\n")
        lines.append("| 维度 | 平均分 | 评级 | 进度条 |")
        lines.append("|------|--------|------|--------|")

        for dim_name, scores in assessment.dimensions.items():
            avg = sum(scores.values()) / len(scores) if scores else 0
            level = "⭐⭐⭐" if avg >= 4 else "⭐⭐" if avg >= 3 else "⭐"
            bar = "█" * int(avg * 4) + "░" * (20 - int(avg * 4))
            lines.append(f"| {dim_name} | {avg:.1f}/5 | {level} | {bar} |")

        # 强项
        if assessment.strengths:
            lines.append("\n## ✅ 强项\n")
            for s in assessment.strengths:
                lines.append(f"- {s}")

        # 弱项
        if assessment.weaknesses:
            lines.append("\n## ⚠️ 待提升\n")
            for w in assessment.weaknesses:
                lines.append(f"- {w}")

        # 学习建议
        lines.append("\n## 📚 学习建议\n")
        lines.append("1. 优先提升弱项维度，建议从基础开始系统学习")
        lines.append("2. 结合实际项目实践，边学边练")
        lines.append("3. 参加开源项目或自建项目积累经验")
        lines.append("4. 关注AI测试领域最新发展和工具")

        return "\n".join(lines)

    @staticmethod
    def generate_json(assessment: SkillAssessment) -> str:
        """生成JSON报告"""
        data = {
            "candidate_name": assessment.candidate_name,
            "timestamp": assessment.timestamp,
            "overall_score": assessment.overall_score,
            "level": assessment.level,
            "dimensions": {},
            "strengths": assessment.strengths,
            "weaknesses": assessment.weaknesses
        }

        for dim_name, scores in assessment.dimensions.items():
            data["dimensions"][dim_name] = {
                "scores": scores,
                "average": sum(scores.values()) / len(scores) if scores else 0
            }

        return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 使用示例
# ============================================================

def create_sample_assessment() -> Dict[str, Dict[str, int]]:
    """创建示例评估数据"""
    return {
        "大模型基础": {
            "Transformer架构": 4,
            "Token与上下文窗口": 5,
            "温度与采样参数": 3,
            "模型选择": 4,
            "API调用": 5
        },
        "Prompt工程": {
            "Prompt设计": 4,
            "少样本学习": 3,
            "思维链": 4,
            "Prompt迭代": 5,
            "自动化评测": 3
        },
        "RAG系统": {
            "文档处理": 3,
            "向量化": 4,
            "检索优化": 3,
            "混合检索": 2,
            "RAG评测": 4
        },
        "Agent系统": {
            "Agent架构": 3,
            "工具调用": 4,
            "任务规划": 3,
            "记忆管理": 2,
            "工作流编排": 3
        },
        "AI测试方法": {
            "幻觉检测": 4,
            "稳定性测试": 5,
            "回归测试": 4,
            "探索性测试": 5,
            "自动化框架": 4
        },
        "安全与合规": {
            "Prompt注入": 3,
            "越狱测试": 2,
            "数据隐私": 3,
            "内容安全": 4,
            "审计日志": 3
        },
        "性能与成本": {
            "延迟优化": 3,
            "并发测试": 4,
            "缓存策略": 3,
            "成本估算": 4,
            "监控告警": 3
        }
    }


def main():
    """主函数"""
    print("=" * 60)
    print("📊 AI测试能力评估工具")
    print("   对应文章：82-AI测试面试题-架构篇")
    print("=" * 60)

    # 创建评估器
    assessor = SkillAssessor()

    # 获取评估数据
    skill_scores = create_sample_assessment()

    # 执行评估
    assessment = assessor.assess("测试工程师", skill_scores)

    # 生成报告
    reporter = AssessmentReport()

    # Markdown报告
    md_report = reporter.generate_markdown(assessment)
    print("\n" + md_report)

    # 保存JSON报告
    json_report = reporter.generate_json(assessment)
    report_path = "skill_assessment.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(json_report)
    print(f"\n💾 JSON报告已保存: {report_path}")

    # 输出总结
    print("\n" + "=" * 60)
    print("📊 评估总结")
    print("=" * 60)
    print(f"候选人: {assessment.candidate_name}")
    print(f"综合评分: {assessment.overall_score:.1f}/100")
    print(f"能力等级: {assessment.level}")

    if assessment.strengths:
        print(f"\n✅ 强项 ({len(assessment.strengths)}项):")
        for s in assessment.strengths:
            print(f"   - {s}")

    if assessment.weaknesses:
        print(f"\n⚠️ 待提升 ({len(assessment.weaknesses)}项):")
        for w in assessment.weaknesses:
            print(f"   - {w}")

    print("\n✅ 评估完成！")


if __name__ == "__main__":
    main()
