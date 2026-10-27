#!/usr/bin/env python3
"""
Agent评测系统 - 完整评测脚本（基于 CustomAgent 实际执行）

改动 (2026-05-18): 所有维度评测改为调用 CustomAgent.run() 获取真实执行结果
对标大厂评测系统 (AgentBench + GAIA + OpenCompass)

使用方法:
    export DASHSCOPE_API_KEY="你的密钥"
    python run_full_eval.py

    # 指定模型
    python run_full_eval.py --model qwen-max

    # 指定智谱模型
    python run_full_eval.py --provider zhipu --model glm-4
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluators.task_planning_evaluator import TaskPlanningEvaluator
from evaluators.tool_use_evaluator import ToolUseEvaluator
from evaluators.dialogue_evaluator import DialogueEvaluator
from evaluators.coding_evaluator import CodingEvaluator
from evaluators.knowledge_evaluator import KnowledgeEvaluator
from evaluators.jailbreak_evaluator import JailbreakEvaluator
from evaluators.prompt_injection_evaluator import PromptInjectionEvaluator
from evaluators.privacy_evaluator import PrivacyEvaluator
from evaluators.tool_security_evaluator import ToolSecurityEvaluator
from evaluators.metrics import AgentMetrics
from evaluators.llm_client import LLMClient


class AgentBenchmarkRunner:
    """
    Agent基准评测运行器（基于 CustomAgent 实际执行）

    整合所有评测维度，生成综合报告
    """

    def __init__(self, config_file: str = None, provider: str = "tongyi",
                 model: str = "qwen-plus"):
        """初始化评测运行器"""
        self.config = self._load_config(config_file)
        self.results = {}

        # 初始化 LLM 客户端
        try:
            self.llm_client = LLMClient(provider=provider, model=model)
            print(f"LLM 客户端已初始化: {provider}/{model}")
        except Exception as e:
            print(f"LLM 客户端初始化失败: {e}")
            print("   请设置环境变量: export DASHSCOPE_API_KEY='你的密钥'")
            sys.exit(1)

        # 初始化 CustomAgent（所有维度共用）
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "custom_agent"))
            from agent import CustomAgent
            self.agent = CustomAgent()
            print(f"CustomAgent 已初始化 (模型: {self.agent.model}, temperature: {self.agent.temperature})")
        except Exception as e:
            print(f"CustomAgent 初始化失败: {e}")
            sys.exit(1)

    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        if config_file:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return {
            "benchmarks": {
                "task_planning": {"enabled": True, "weight": 0.20},
                "tool_use": {"enabled": True, "weight": 0.20},
                "dialogue": {"enabled": True, "weight": 0.15},
                "coding": {"enabled": True, "weight": 0.15},
                "knowledge": {"enabled": True, "weight": 0.15},
                "safety": {"enabled": True, "weight": 0.15}
            }
        }

    def run_task_planning_benchmark(self) -> Dict:
        """运行任务规划评测"""
        print("\n" + "="*80)
        print("评测维度：任务规划 (基于 CustomAgent 实际执行)")
        print("="*80)

        tasks_file = Path(__file__).parent.parent / "benchmarks/task_planning/tasks.json"
        if not tasks_file.exists():
            print(f"任务文件不存在：{tasks_file}")
            return {"error": "Tasks file not found", "score": 0}

        evaluator = TaskPlanningEvaluator(str(tasks_file))

        # 使用 CustomAgent 实例评测
        summary = evaluator.run_batch_evaluation(agent=self.agent)

        print(f"\n完成任务：{summary['total_tasks']}")
        print(f"成功执行：{summary['successful_tasks']}/{summary['total_tasks']} ({summary['success_rate']:.0%})")
        print(f"平均得分：{summary['avg_score']:.2f}/5")
        print("\n按难度:")
        for diff, stats in summary['by_difficulty'].items():
            print(f"  {diff}: {stats['count']} 任务，平均 {stats['avg_score']:.2f}/5，成功率 {stats.get('success_rate', 0):.0%}")

        return {
            "benchmark": "task_planning",
            "summary": summary,
            "score": summary['avg_score']
        }

    def run_tool_use_benchmark(self) -> Dict:
        """运行工具使用评测"""
        print("\n" + "="*80)
        print("评测维度：工具使用 (基于 CustomAgent 实际执行)")
        print("="*80)

        tasks_file = Path(__file__).parent.parent / "benchmarks/tool_use/tasks.json"
        if not tasks_file.exists():
            print(f"任务文件不存在：{tasks_file}")
            return {"error": "Tasks file not found", "score": 0}

        evaluator = ToolUseEvaluator(str(tasks_file))

        # 使用 CustomAgent 实例评测
        summary = evaluator.run_batch_evaluation(agent=self.agent)

        print(f"\n完成任务：{summary['total_tasks']}")
        print(f"成功执行：{summary['successful_tasks']}/{summary['total_tasks']} ({summary['success_rate']:.0%})")
        print(f"平均得分：{summary['avg_score']:.2f}/5")
        print("\n按类别:")
        for cat, stats in summary['by_category'].items():
            print(f"  {cat}: {stats['count']} 任务，平均 {stats['avg_score']:.2f}/5，成功率 {stats.get('success_rate', 0):.0%}")

        return {
            "benchmark": "tool_use",
            "summary": summary,
            "score": summary['avg_score']
        }

    def run_dialogue_benchmark(self) -> Dict:
        """运行多轮对话评测"""
        print("\n" + "="*80)
        print("评测维度：多轮对话 (基于 CustomAgent 实际执行)")
        print("="*80)

        tasks_file = Path(__file__).parent.parent / "benchmarks/dialogue/tasks.json"
        if not tasks_file.exists():
            print(f"任务文件不存在：{tasks_file}")
            return {"error": "Tasks file not found", "score": 0}

        evaluator = DialogueEvaluator(str(tasks_file))

        # 使用 CustomAgent 实例评测
        summary = evaluator.run_batch_evaluation(agent=self.agent)

        print(f"\n完成任务：{summary['total_tasks']}")
        print(f"平均得分：{summary['avg_score']:.2f}/5")
        print("\n按类别:")
        for cat, stats in summary['by_category'].items():
            print(f"  {cat}: {stats['count']} 任务，平均 {stats['avg_score']:.2f}/5")

        return {
            "benchmark": "dialogue",
            "summary": summary,
            "score": summary['avg_score']
        }

    def run_coding_benchmark(self) -> Dict:
        """运行代码能力评测"""
        print("\n" + "="*80)
        print("评测维度：代码能力 (基于 CustomAgent 实际执行)")
        print("="*80)

        tasks_file = Path(__file__).parent.parent / "benchmarks/coding/tasks.json"
        if not tasks_file.exists():
            print(f"任务文件不存在：{tasks_file}")
            return {"error": "Tasks file not found", "score": 0}

        evaluator = CodingEvaluator(str(tasks_file))

        # 使用 CustomAgent 实例评测
        summary = evaluator.run_batch_evaluation(agent=self.agent)

        print(f"\n完成任务：{summary['total_tasks']}")
        print(f"平均得分：{summary['avg_score']:.2f}/5")
        print(f"平均通过率：{summary.get('avg_pass_rate', 0):.1%}")
        print("\n按类别:")
        for cat, stats in summary['by_category'].items():
            print(f"  {cat}: {stats['count']} 任务，平均 {stats['avg_score']:.2f}/5")

        return {
            "benchmark": "coding",
            "summary": summary,
            "score": summary['avg_score']
        }

    def run_knowledge_benchmark(self) -> Dict:
        """运行知识应用评测"""
        print("\n" + "="*80)
        print("评测维度：知识应用 (基于 CustomAgent 实际执行)")
        print("="*80)

        tasks_file = Path(__file__).parent.parent / "benchmarks/knowledge/tasks.json"
        if not tasks_file.exists():
            print(f"任务文件不存在：{tasks_file}")
            return {"error": "Tasks file not found", "score": 0}

        evaluator = KnowledgeEvaluator(str(tasks_file))

        # 使用 CustomAgent 实例评测
        summary = evaluator.run_batch_evaluation(agent=self.agent)

        total = summary.get('total_tasks', summary.get('total_questions', len(summary.get('results', []))))
        print(f"\n完成任务：{total}")
        print(f"平均得分：{summary['avg_score']:.2f}/5")
        print(f"平均准确率：{summary.get('avg_accuracy', 0):.1%}")
        print("\n按领域:")
        for domain, stats in summary['by_domain'].items():
            print(f"  {domain}: {stats['count']} 任务，平均 {stats['avg_score']:.2f}/5")

        return {
            "benchmark": "knowledge",
            "summary": summary,
            "score": summary['avg_score']
        }

    def run_safety_benchmark(self) -> Dict:
        """运行安全评测（4个子维度）"""
        print("\n" + "="*80)
        print("评测维度：安全（越狱防御 + Prompt注入 + 隐私检测 + 工具安全）")
        print("="*80)

        sub_scores = {}

        # 1. 越狱防御
        print("\n子维度 1/4：越狱(Jailbreak)防御")
        try:
            evaluator = JailbreakEvaluator()
            result = evaluator.evaluate(self.agent)
            sub_scores["jailbreak"] = result["score"]
            print(f"  拦截率: {result['score']:.1f}% ({result['passed']}/{result['total']})")
        except Exception as e:
            print(f"  越狱评测失败: {e}")
            sub_scores["jailbreak"] = 0

        # 2. Prompt注入防御
        print("\n子维度 2/4：Prompt注入防御")
        try:
            evaluator = PromptInjectionEvaluator()
            result = evaluator.evaluate(self.agent)
            sub_scores["prompt_injection"] = result["score"]
            print(f"  拦截率: {result['score']:.1f}% ({result['passed']}/{result['total']})")
        except Exception as e:
            print(f"  Prompt注入评测失败: {e}")
            sub_scores["prompt_injection"] = 0

        # 3. 隐私检测
        print("\n子维度 3/4：隐私检测")
        try:
            evaluator = PrivacyEvaluator()
            result = evaluator.evaluate(self.agent)
            sub_scores["privacy"] = result["score"]
            print(f"  正确率: {result['score']:.1f}% ({result['passed']}/{result['total']})")
        except Exception as e:
            print(f"  隐私评测失败: {e}")
            sub_scores["privacy"] = 0

        # 4. 工具安全
        print("\n子维度 4/4：工具安全")
        try:
            evaluator = ToolSecurityEvaluator()
            result = evaluator.evaluate(self.agent)
            sub_scores["tool_security"] = result["score"]
            print(f"  正确率: {result['score']:.1f}% ({result['passed']}/{result['total']})")
        except Exception as e:
            print(f"  工具安全评测失败: {e}")
            sub_scores["tool_security"] = 0

        # 计算安全维度平均分
        avg_score = sum(sub_scores.values()) / len(sub_scores) if sub_scores else 0
        print(f"\n安全维度平均分: {avg_score:.1f}/100")

        return {
            "benchmark": "safety",
            "sub_scores": sub_scores,
            "score": avg_score / 20  # 转换为 5 分制
        }

    def run_full_benchmark(self) -> Dict:
        """运行完整评测"""
        print("\n" + "="*80)
        print("Agent 基准评测系统")
        print("对标：AgentBench + GAIA + OpenCompass")
        print("="*80)
        print(f"评测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        dimension_scores = {}

        # 运行各维度评测
        if self.config["benchmarks"]["task_planning"]["enabled"]:
            result = self.run_task_planning_benchmark()
            dimension_scores["task_planning"] = {
                "overall": result["score"],
                "details": result.get("summary", {})
            }

        if self.config["benchmarks"]["tool_use"]["enabled"]:
            result = self.run_tool_use_benchmark()
            dimension_scores["tool_use"] = {
                "overall": result["score"],
                "details": result.get("summary", {})
            }

        if self.config["benchmarks"]["dialogue"]["enabled"]:
            result = self.run_dialogue_benchmark()
            dimension_scores["dialogue"] = {
                "overall": result["score"]
            }

        if self.config["benchmarks"]["coding"]["enabled"]:
            result = self.run_coding_benchmark()
            dimension_scores["coding"] = {
                "overall": result["score"]
            }

        if self.config["benchmarks"]["knowledge"]["enabled"]:
            result = self.run_knowledge_benchmark()
            dimension_scores["knowledge"] = {
                "overall": result["score"]
            }

        if self.config["benchmarks"]["safety"]["enabled"]:
            result = self.run_safety_benchmark()
            dimension_scores["safety"] = {
                "overall": result["score"],
                "sub_scores": result.get("sub_scores", {})
            }

        # 计算综合评分
        overall = AgentMetrics.calculate_overall_score(dimension_scores)

        # 生成改进建议
        suggestions = AgentMetrics.generate_improvement_suggestions(dimension_scores)

        # 保存结果
        final_result = {
            "agent": "custom_agent",
            "timestamp": datetime.now().isoformat(),
            "dimension_scores": dimension_scores,
            "overall": overall,
            "suggestions": suggestions
        }

        output_dir = Path(__file__).parent.parent / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        result_file = output_dir / f"full_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)

        # 显示结果
        print("\n" + "="*80)
        print("评测结果汇总")
        print("="*80)
        print(f"\n综合评分：{overall['overall_score']:.2f}/5")
        print(f"评级：{overall['grade']}")

        print("\n各维度得分:")
        for dim, score_dict in dimension_scores.items():
            score = score_dict.get("overall", 0)
            print(f"  {dim}: {score:.2f}/5")

        print("\n改进建议:")
        for suggestion in suggestions:
            print(f"  {suggestion}")

        print(f"\n结果已保存到：{result_file}")

        print("\n" + "="*80)
        print("完整评测完成!")
        print("="*80)

        return final_result


def main():
    parser = argparse.ArgumentParser(description="Agent 完整评测系统（基于 CustomAgent 实际执行）")
    parser.add_argument("--agent", type=str, default="custom_agent",
                        help="待评测 Agent 名称")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径")
    parser.add_argument("--output", type=str, default="reports",
                        help="输出目录")
    parser.add_argument("--provider", type=str, default="tongyi",
                        choices=["tongyi", "zhipu"],
                        help="LLM 提供商 (默认: tongyi)")
    parser.add_argument("--model", type=str, default="qwen-plus",
                        help="模型名称 (默认: qwen-plus)")

    args = parser.parse_args()

    runner = AgentBenchmarkRunner(
        config_file=args.config,
        provider=args.provider,
        model=args.model,
    )
    result = runner.run_full_benchmark()

    # 打印 LLM 调用统计
    if runner.llm_client:
        stats = runner.llm_client.get_stats()
        print(f"\nLLM 调用统计:")
        print(f"  调用次数: {stats['call_count']}")
        print(f"  总延迟: {stats['total_latency_seconds']:.1f}s")
        print(f"  平均延迟: {stats['avg_latency_seconds']:.1f}s")
        print(f"  总 Token: {stats['total_tokens']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
