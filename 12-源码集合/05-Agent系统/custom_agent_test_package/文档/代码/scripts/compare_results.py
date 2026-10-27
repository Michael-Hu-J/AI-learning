#!/usr/bin/env python3
"""
评测结果对比脚本

功能：
1. 对比两次评测报告的差异
2. 检测行为漂移（同一任务在不同版本间的得分变化）
3. 生成对比报告

用法：
    python3 scripts/compare_results.py --baseline results/reports/eval_report_20260501.json --current results/reports/eval_report_20260513.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import argparse


class ResultComparator:
    """评测结果对比器"""
    
    def __init__(self, baseline_path: str, current_path: str):
        self.baseline = self._load_report(baseline_path)
        self.current = self._load_report(current_path)
        self.baseline_path = baseline_path
        self.current_path = current_path
    
    def _load_report(self, path: str) -> Dict[str, Any]:
        """加载评测报告"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def compare(self) -> Dict[str, Any]:
        """执行对比分析"""
        print(f"\n 评测结果对比")
        print(f"   基准: {self.baseline_path}")
        print(f"   当前: {self.current_path}")
        print("=" * 60)
        
        # 1. 维度得分对比
        dim_comparison = self._compare_dimensions()
        
        # 2. 任务级对比（如果有）
        task_comparison = self._compare_tasks()
        
        # 3. 总体趋势
        trend = self._analyze_trend(dim_comparison)
        
        report = {
            "baseline": self.baseline_path,
            "current": self.current_path,
            "baseline_timestamp": self.baseline.get("timestamp", "unknown"),
            "current_timestamp": self.current.get("timestamp", "unknown"),
            "dimension_comparison": dim_comparison,
            "task_comparison": task_comparison,
            "trend": trend,
            "timestamp": datetime.now().isoformat(),
        }
        
        self._print_report(report)
        return report
    
    def _compare_dimensions(self) -> Dict[str, Any]:
        """对比各维度得分"""
        baseline_scores = self.baseline.get("dimension_scores", {})
        current_scores = self.current.get("dimension_scores", {})
        
        comparison = {}
        
        all_dims = set(list(baseline_scores.keys()) + list(current_scores.keys()))
        
        for dim in all_dims:
            baseline_score = baseline_scores.get(dim, {}).get("overall", 0)
            current_score = current_scores.get(dim, {}).get("overall", 0)
            delta = current_score - baseline_score
            
            # 判断变化幅度
            if abs(delta) < 0.1:
                change = "stable"
            elif delta > 0:
                change = "improved"
            else:
                change = "degraded"
            
            comparison[dim] = {
                "baseline": baseline_score,
                "current": current_score,
                "delta": delta,
                "change": change,
            }
        
        return comparison
    
    def _compare_tasks(self) -> Dict[str, Any]:
        """对比任务级结果"""
        baseline_results = self.baseline.get("results", [])
        current_results = self.current.get("results", [])
        
        # 按 task_id 索引
        baseline_map = {r.get("task_id"): r for r in baseline_results}
        current_map = {r.get("task_id"): r for r in current_results}
        
        all_ids = set(list(baseline_map.keys()) + list(current_map.keys()))
        
        task_changes = []
        
        for task_id in all_ids:
            baseline_task = baseline_map.get(task_id, {})
            current_task = current_map.get(task_id, {})
            
            baseline_score = baseline_task.get("overall_score", 0)
            current_score = current_task.get("overall_score", 0)
            delta = current_score - baseline_score
            
            if abs(delta) >= 0.5:  # 显著变化阈值
                task_changes.append({
                    "task_id": task_id,
                    "baseline_score": baseline_score,
                    "current_score": current_score,
                    "delta": delta,
                    "significant": True,
                })
        
        return {
            "total_tasks": len(all_ids),
            "significant_changes": len(task_changes),
            "changes": task_changes[:20],  # 最多显示20个
        }
    
    def _analyze_trend(self, dim_comparison: Dict) -> Dict[str, Any]:
        """分析总体趋势"""
        improved = sum(1 for d in dim_comparison.values() if d["change"] == "improved")
        degraded = sum(1 for d in dim_comparison.values() if d["change"] == "degraded")
        stable = sum(1 for d in dim_comparison.values() if d["change"] == "stable")
        
        if improved > degraded:
            overall_trend = "improving"
        elif degraded > improved:
            overall_trend = "degrading"
        else:
            overall_trend = "stable"
        
        return {
            "overall_trend": overall_trend,
            "improved_count": improved,
            "degraded_count": degraded,
            "stable_count": stable,
        }
    
    def _print_report(self, report: Dict):
        """打印对比报告"""
        dim_comp = report["dimension_comparison"]
        trend = report["trend"]
        
        print(f"\n 维度得分对比:")
        print(f"{'维度':<20} {'基准':>8} {'当前':>8} {'变化':>8} {'趋势':>10}")
        print("-" * 60)
        
        for dim, stats in dim_comp.items():
            delta_str = f"+{stats['delta']:.2f}" if stats['delta'] >= 0 else f"{stats['delta']:.2f}"
            change_icon = {"improved": "↑", "degraded": "↓", "stable": "→"}[stats['change']]
            print(f"{dim:<20} {stats['baseline']:>7.2f} {stats['current']:>7.2f} "
                  f"{delta_str:>8} {change_icon:>10}")
        
        print(f"\n 总体趋势:")
        print(f"   提升: {trend['improved_count']} 个维度")
        print(f"   下降: {trend['degraded_count']} 个维度")
        print(f"   稳定: {trend['stable_count']} 个维度")
        print(f"   整体: {trend['overall_trend']}")
        
        task_comp = report.get("task_comparison", {})
        if task_comp.get("significant_changes", 0) > 0:
            print(f"\n  显著变化的任务 ({task_comp['significant_changes']} 个):")
            for change in task_comp.get("changes", [])[:10]:
                delta_str = f"+{change['delta']:.1f}" if change['delta'] >= 0 else f"{change['delta']:.1f}"
                print(f"   {change['task_id']}: {change['baseline_score']:.1f} → {change['current_score']:.1f} ({delta_str})")


def main():
    parser = argparse.ArgumentParser(description="评测结果对比")
    parser.add_argument("--baseline", required=True, help="基准报告路径")
    parser.add_argument("--current", required=True, help="当前报告路径")
    parser.add_argument("--output", default=None, help="对比报告输出路径")
    
    args = parser.parse_args()
    
    comparator = ResultComparator(args.baseline, args.current)
    report = comparator.compare()
    
    # 保存报告
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n💾 对比报告已保存: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
