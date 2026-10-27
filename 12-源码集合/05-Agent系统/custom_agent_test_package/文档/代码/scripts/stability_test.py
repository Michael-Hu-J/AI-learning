#!/usr/bin/env python3
"""
Agent 稳定性测试脚本

功能：
1. 对同一任务多次执行，检测输出一致性
2. 计算成功率、输出相似度
3. 识别不稳定任务（波动大的任务）

用法：
    python3 scripts/stability_test.py --agent custom --out-dir results/stability --n-runs 10
"""
import json
import os
import sys
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter
import argparse

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluators.llm_client import LLMClient


class StabilityTester:
    """稳定性测试器"""
    
    def __init__(self, provider: str = "tongyi", model: str = "qwen-plus", temperature: float = 0.7):
        self.llm_client = LLMClient(provider=provider, model=model)
        self.temperature = temperature
        self.model = model
        self.results: List[Dict[str, Any]] = []
    
    def test_task(self, task: Dict, n_runs: int = 10) -> Dict[str, Any]:
        """对单个任务执行多次，检测稳定性"""
        task_id = task.get("id", "unknown")
        task_name = task.get("name", "unknown")
        
        outputs = []
        successes = []
        tokens_list = []
        
        print(f"  [{task_id}] {task_name} — 执行 {n_runs} 次...")
        
        for i in range(n_runs):
            prompt = f"请完成以下任务：\n\n{task.get('description', '')}\n\n目标：{task.get('goal', '')}"
            
            response = self.llm_client.chat(prompt)
            
            if response.success:
                outputs.append(response.content.strip())
                successes.append(True)
                tokens_list.append(response.total_tokens if hasattr(response, 'total_tokens') else 0)
            else:
                outputs.append(f"ERROR: {response.error}")
                successes.append(False)
                tokens_list.append(0)
        
        # 计算稳定性指标
        success_rate = sum(successes) / len(successes) if successes else 0
        
        # 计算输出一致性
        unique_outputs = set(outputs)
        consistency = len(unique_outputs) / len(outputs) if outputs else 0
        # 一致性取反：唯一输出越少，一致性越高
        consistency_score = 1.0 - consistency
        
        # 计算最常出现的输出比例
        if outputs:
            counter = Counter(outputs)
            most_common_count = counter.most_common(1)[0][1]
            dominant_output_rate = most_common_count / len(outputs)
        else:
            dominant_output_rate = 0.0
        
        # 计算 token 波动
        successful_tokens = [t for t in tokens_list if t > 0]
        if len(successful_tokens) > 1:
            import statistics
            token_std = statistics.stdev(successful_tokens)
            token_mean = statistics.mean(successful_tokens)
            token_cv = token_std / token_mean if token_mean > 0 else 0
        else:
            token_cv = 0.0
        
        # 稳定性评级
        if success_rate >= 0.9 and dominant_output_rate >= 0.5:
            stability = "stable"
        elif success_rate >= 0.7 and dominant_output_rate >= 0.3:
            stability = "moderate"
        else:
            stability = "unstable"
        
        result = {
            "task_id": task_id,
            "task_name": task_name,
            "n_runs": n_runs,
            "success_rate": success_rate,
            "consistency_score": consistency_score,
            "dominant_output_rate": dominant_output_rate,
            "unique_output_count": len(unique_outputs),
            "token_cv": token_cv,
            "stability": stability,
            "sample_outputs": outputs[:3],  # 保存前3个输出用于对比
        }
        
        status_icon = {"stable": "", "moderate": "", "unstable": ""}[stability]
        print(f"    {status_icon} 成功率: {success_rate:.0%}, 一致性: {dominant_output_rate:.0%}, 评级: {stability}")
        
        return result
    
    def test_all(self, benchmarks_dir: str, n_runs: int = 10) -> Dict[str, Any]:
        """对所有 benchmark 任务执行稳定性测试"""
        benchmarks_path = Path(benchmarks_dir)
        all_tasks = []
        
        for dim_dir in benchmarks_path.iterdir():
            if dim_dir.is_dir():
                tasks_file = dim_dir / "tasks.json"
                if tasks_file.exists():
                    with open(tasks_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for task in data.get("tasks", []):
                        task["_dimension"] = dim_dir.name
                        all_tasks.append(task)
        
        print(f"\n 开始稳定性测试")
        print(f"   模型: {self.model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   任务数: {len(all_tasks)}")
        print(f"   每任务运行次数: {n_runs}")
        print("=" * 60)
        
        for task in all_tasks:
            result = self.test_task(task, n_runs)
            self.results.append(result)
        
        # 生成汇总
        stable_count = sum(1 for r in self.results if r["stability"] == "stable")
        moderate_count = sum(1 for r in self.results if r["stability"] == "moderate")
        unstable_count = sum(1 for r in self.results if r["stability"] == "unstable")
        
        summary = {
            "total_tasks": len(all_tasks),
            "stable": stable_count,
            "moderate": moderate_count,
            "unstable": unstable_count,
            "stability_rate": stable_count / len(all_tasks) if all_tasks else 0,
            "model": self.model,
            "temperature": self.temperature,
            "timestamp": datetime.now().isoformat(),
        }
        
        return {
            "summary": summary,
            "results": self.results,
        }


def main():
    parser = argparse.ArgumentParser(description="Agent 稳定性测试")
    parser.add_argument("--agent", default="custom", help="Agent 名称（保留兼容）")
    parser.add_argument("--out-dir", default="results/stability", help="输出目录")
    parser.add_argument("--n-runs", type=int, default=10, help="每任务运行次数")
    parser.add_argument("--model", default="qwen-plus", help="模型名称")
    parser.add_argument("--provider", default="tongyi", help="LLM 提供商")
    parser.add_argument("--temperature", type=float, default=0.7, help="测试温度")
    
    args = parser.parse_args()
    
    tester = StabilityTester(
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
    )
    report = tester.test_all(
        benchmarks_dir="benchmarks/",
        n_runs=args.n_runs,
    )
    
    # 保存报告
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = out_dir / f"stability_report_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 稳定性报告已保存: {output_file}")
    
    # 打印摘要
    summary = report.get("summary", {})
    print(f"\n 稳定性摘要:")
    print(f"   稳定: {summary.get('stable', 0)} 任务")
    print(f"   中等: {summary.get('moderate', 0)} 任务")
    print(f"   不稳定: {summary.get('unstable', 0)} 任务")
    print(f"   稳定率: {summary.get('stability_rate', 0):.0%}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
