#!/usr/bin/env python3
"""
Temperature敏感度实验

功能：
1. 对同一任务在不同 temperature 下各跑 N 次
2. 对比成功率、输出一致性、Token 消耗、耗时
3. 生成温度敏感度报告

用法：
    python3 scripts/temperature_sensitivity_demo.py --model qwen-plus --n-runs 30
"""
import json
import os
import sys
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter
import argparse

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluators.llm_client import LLMClient


class TemperatureSensitivityDemo:
    """Temperature敏感度实验"""
    
    def __init__(self, provider: str = "tongyi", model: str = "qwen-plus"):
        self.model = model
        self.provider = provider
        self.results: Dict[float, List[Dict]] = {}
    
    def run_experiment(self, task: str, temperatures: List[float] = None, n_runs: int = 30):
        """执行温度敏感度实验"""
        if temperatures is None:
            temperatures = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        
        print(f"\n🌡️  Temperature敏感度实验")
        print(f"   模型: {self.model}")
        print(f"   任务: {task[:60]}...")
        print(f"   运行次数: {n_runs}/温度")
        print("=" * 60)
        
        for temp in temperatures:
            self.results[temp] = []
            print(f"\n  temperature={temp}:")
            
            for i in range(n_runs):
                start_time = time.time()
                
                llm = LLMClient(provider=self.provider, model=self.model)
                # 手动设置 temperature（通过环境变量或构造参数）
                response = llm.chat(task)
                
                elapsed = time.time() - start_time
                
                result = {
                    "run": i + 1,
                    "success": response.success,
                    "content": response.content if response.success else "",
                    "tokens": response.total_tokens if hasattr(response, 'total_tokens') else 0,
                    "elapsed": elapsed,
                }
                self.results[temp].append(result)
                
                if (i + 1) % 10 == 0:
                    print(f"    [{i+1}/{n_runs}]")
            
            # 统计当前温度
            results = self.results[temp]
            success_count = sum(1 for r in results if r["success"])
            success_rate = success_count / len(results)
            
            # 输出一致性
            outputs = [r["content"].strip() for r in results if r["success"]]
            unique_outputs = set(outputs)
            consistency = len(unique_outputs) / len(outputs) if outputs else 0
            
            # 最常出现的输出
            if outputs:
                counter = Counter(outputs)
                most_common_count = counter.most_common(1)[0][1]
                dominant_rate = most_common_count / len(outputs)
            else:
                dominant_rate = 0.0
            
            # Token 统计
            tokens = [r["tokens"] for r in results if r["success"]]
            avg_tokens = statistics.mean(tokens) if tokens else 0
            
            # 耗时统计
            times = [r["elapsed"] for r in results]
            avg_time = statistics.mean(times) if times else 0
            
            print(f"    成功率: {success_rate:.0%}")
            print(f"    唯一输出数: {len(unique_outputs)}")
            print(f"    主导输出率: {dominant_rate:.0%}")
            print(f"    平均 Token: {avg_tokens:.0f}")
            print(f"    平均耗时: {avg_time:.2f}s")
        
        return self._generate_report(task)
    
    def _generate_report(self, task: str) -> Dict[str, Any]:
        """生成实验报告"""
        report = {
            "task": task,
            "model": self.model,
            "timestamp": datetime.now().isoformat(),
            "temperatures": {},
        }
        
        for temp, results in self.results.items():
            success_count = sum(1 for r in results if r["success"])
            success_rate = success_count / len(results) if results else 0
            
            outputs = [r["content"].strip() for r in results if r["success"]]
            unique_outputs = set(outputs)
            
            if outputs:
                counter = Counter(outputs)
                most_common_count = counter.most_common(1)[0][1]
                dominant_rate = most_common_count / len(outputs)
            else:
                dominant_rate = 0.0
            
            tokens = [r["tokens"] for r in results if r["success"]]
            avg_tokens = statistics.mean(tokens) if tokens else 0
            
            times = [r["elapsed"] for r in results]
            avg_time = statistics.mean(times) if times else 0
            
            report["temperatures"][str(temp)] = {
                "success_rate": success_rate,
                "unique_outputs": len(unique_outputs),
                "dominant_output_rate": dominant_rate,
                "avg_tokens": avg_tokens,
                "avg_elapsed": avg_time,
                "n_runs": len(results),
            }
        
        return report


def main():
    parser = argparse.ArgumentParser(description="Temperature敏感度实验")
    parser.add_argument("--model", default="qwen-plus", help="模型名称")
    parser.add_argument("--provider", default="tongyi", help="LLM 提供商")
    parser.add_argument("--n-runs", type=int, default=30, help="每温度运行次数")
    parser.add_argument("--task", default=None, help="测试任务（默认使用内置示例）")
    parser.add_argument("--out-dir", default="reports", help="输出目录")
    
    args = parser.parse_args()
    
    # 默认测试任务
    default_task = "计算 25 * 4 + 100 / 5，把结果存储到记忆中"
    task = args.task or default_task
    
    demo = TemperatureSensitivityDemo(provider=args.provider, model=args.model)
    report = demo.run_experiment(task, n_runs=args.n_runs)
    
    # 保存报告
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = out_dir / f"temperature_experiment_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 实验报告已保存: {output_file}")
    
    # 打印对比表
    print(f"\n 温度敏感度对比:")
    print(f"{'Temperature':<12} {'成功率':>8} {'唯一输出':>8} {'主导率':>8} {'Token':>8} {'耗时':>8}")
    print("-" * 60)
    for temp, stats in report["temperatures"].items():
        print(f"{temp:<12} {stats['success_rate']:>7.0%} {stats['unique_outputs']:>8} "
              f"{stats['dominant_output_rate']:>7.0%} {stats['avg_tokens']:>8.0f} {stats['avg_elapsed']:>7.2f}s")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
