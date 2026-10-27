#!/usr/bin/env python3
"""
Agent 性能测试脚本

功能：
1. 对每个 benchmark 任务执行多次，记录耗时、Token 消耗、成本
2. 计算 P50/P90/P95 延迟
3. 生成性能报告

用法：
    python3 scripts/performance_test.py --agent custom --out-dir results/performance --n-tasks 20
"""
import json
import os
import sys
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import argparse

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluators.llm_client import LLMClient


class PerformanceTester:
    """性能测试器"""
    
    # 千问 API 单价 (元/千Token)
    PRICING = {
        "qwen-plus": {"input": 0.004, "output": 0.004},
        "qwen-max": {"input": 0.04, "output": 0.12},
        "qwen-turbo": {"input": 0.001, "output": 0.001},
    }
    
    def __init__(self, provider: str = "tongyi", model: str = "qwen-plus"):
        self.llm_client = LLMClient(provider=provider, model=model)
        self.model = model
        self.results: List[Dict[str, Any]] = []
        
    def test_task(self, task: Dict, n_runs: int = 3) -> Dict[str, Any]:
        """对单个任务执行多次性能测试"""
        task_id = task.get("id", "unknown")
        task_name = task.get("name", "unknown")
        run_times = []
        token_counts = []
        costs = []
        
        print(f"  [{task_id}] {task_name} — 执行 {n_runs} 次...")
        
        for i in range(n_runs):
            start_time = time.time()
            
            # 构造测试 prompt
            prompt = f"请完成以下任务：\n\n{task.get('description', '')}\n\n目标：{task.get('goal', '')}"
            
            response = self.llm_client.chat(prompt)
            
            elapsed = time.time() - start_time
            
            if response.success:
                tokens = response.total_tokens if hasattr(response, 'total_tokens') else 0
                cost = self._calculate_cost(tokens)
                
                run_times.append(elapsed)
                token_counts.append(tokens)
                costs.append(cost)
                
                print(f"    第{i+1}次: {elapsed:.2f}s, {tokens} tokens, ¥{cost:.4f}")
            else:
                print(f"    第{i+1}次: 失败 - {response.error}")
        
        # 计算统计值
        if run_times:
            return {
                "task_id": task_id,
                "task_name": task_name,
                "n_runs": len(run_times),
                "avg_time": statistics.mean(run_times),
                "p50_time": statistics.median(run_times),
                "p90_time": self._percentile(run_times, 90),
                "p95_time": self._percentile(run_times, 95),
                "min_time": min(run_times),
                "max_time": max(run_times),
                "avg_tokens": statistics.mean(token_counts),
                "total_tokens": sum(token_counts),
                "avg_cost": statistics.mean(costs),
                "total_cost": sum(costs),
            }
        else:
            return {
                "task_id": task_id,
                "task_name": task_name,
                "n_runs": 0,
                "error": "所有运行均失败",
            }
    
    def test_all(self, benchmarks_dir: str, n_tasks: int = 20, n_runs: int = 3) -> Dict[str, Any]:
        """对所有 benchmark 任务执行性能测试"""
        benchmarks_path = Path(benchmarks_dir)
        all_tasks = []
        
        # 收集所有任务
        for dim_dir in benchmarks_path.iterdir():
            if dim_dir.is_dir():
                tasks_file = dim_dir / "tasks.json"
                if tasks_file.exists():
                    with open(tasks_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for task in data.get("tasks", []):
                        task["_dimension"] = dim_dir.name
                        all_tasks.append(task)
        
        # 限制任务数量
        all_tasks = all_tasks[:n_tasks]
        
        print(f"\n 开始性能测试")
        print(f"   模型: {self.model}")
        print(f"   任务数: {len(all_tasks)}")
        print(f"   每任务运行次数: {n_runs}")
        print("=" * 60)
        
        for task in all_tasks:
            result = self.test_task(task, n_runs)
            self.results.append(result)
        
        # 生成汇总
        successful = [r for r in self.results if r.get("n_runs", 0) > 0]
        
        if successful:
            summary = {
                "total_tasks": len(all_tasks),
                "successful_tasks": len(successful),
                "avg_latency": statistics.mean([r["avg_time"] for r in successful]),
                "p50_latency": statistics.median([r["p50_time"] for r in successful]),
                "p90_latency": self._percentile([r["avg_time"] for r in successful], 90),
                "avg_tokens": statistics.mean([r["avg_tokens"] for r in successful]),
                "total_cost": sum([r["total_cost"] for r in successful]),
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            summary = {"error": "没有成功的任务"}
        
        return {
            "summary": summary,
            "results": self.results,
        }
    
    def _calculate_cost(self, tokens: int) -> float:
        """计算成本（元）"""
        pricing = self.PRICING.get(self.model, self.PRICING["qwen-plus"])
        # 简化：假设输入输出各占一半
        input_tokens = tokens // 2
        output_tokens = tokens - input_tokens
        cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
        return cost
    
    def _percentile(self, data: List[float], p: float) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100)
        f = int(k)
        c = f + 1
        if c >= len(sorted_data):
            return sorted_data[-1]
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def main():
    parser = argparse.ArgumentParser(description="Agent 性能测试")
    parser.add_argument("--agent", default="custom", help="Agent 名称（保留兼容）")
    parser.add_argument("--out-dir", default="results/performance", help="输出目录")
    parser.add_argument("--n-tasks", type=int, default=20, help="测试任务数量")
    parser.add_argument("--n-runs", type=int, default=3, help="每任务运行次数")
    parser.add_argument("--model", default="qwen-plus", help="模型名称")
    parser.add_argument("--provider", default="tongyi", help="LLM 提供商")
    
    args = parser.parse_args()
    
    tester = PerformanceTester(provider=args.provider, model=args.model)
    report = tester.test_all(
        benchmarks_dir="benchmarks/",
        n_tasks=args.n_tasks,
        n_runs=args.n_runs,
    )
    
    # 保存报告
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = out_dir / f"performance_report_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 性能报告已保存: {output_file}")
    
    # 打印摘要
    summary = report.get("summary", {})
    if "error" not in summary:
        print(f"\n 性能摘要:")
        print(f"   平均延迟: {summary['avg_latency']:.2f}s")
        print(f"   P50 延迟: {summary['p50_latency']:.2f}s")
        print(f"   P90 延迟: {summary['p90_latency']:.2f}s")
        print(f"   平均 Token: {summary['avg_tokens']:.0f}")
        print(f"   总成本: ¥{summary['total_cost']:.4f}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
