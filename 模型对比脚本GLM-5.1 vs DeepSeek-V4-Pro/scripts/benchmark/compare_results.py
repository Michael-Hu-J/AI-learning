"""
模型对比报告生成器 - 对比两个模型的评测结果
使用方法：python compare_results.py --model1 results/benchmark_current_xxx.json --model2 results/benchmark_new_xxx.json
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any


def load_result(filepath: str) -> Dict:
    """加载评测结果"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_models(result1: Dict, result2: Dict) -> Dict:
    """对比两个模型的结果"""
    s1 = result1["summary"]
    s2 = result2["summary"]
    
    # 基础对比
    comparison = {
        "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "models": {
            "model1": {
                "name": result1["model"],
                "pass_rate": s1["pass_rate"],
                "total": s1["total"],
                "passed": s1["passed"],
                "failed": s1["failed"],
                "avg_time": s1["avg_time"],
                "avg_tokens": s1["avg_tokens"],
            },
            "model2": {
                "name": result2["model"],
                "pass_rate": s2["pass_rate"],
                "total": s2["total"],
                "passed": s2["passed"],
                "failed": s2["failed"],
                "avg_time": s2["avg_time"],
                "avg_tokens": s2["avg_tokens"],
            },
        },
        "dimension_comparison": {},
        "category_comparison": {},
        "task_comparison": [],
        "conclusion": "",
    }
    
    # 维度对比
    d1 = result1.get("by_dimension", {})
    d2 = result2.get("by_dimension", {})
    for dim in set(list(d1.keys()) + list(d2.keys())):
        r1 = d1.get(dim, {"passed": 0, "total": 1})
        r2 = d2.get(dim, {"passed": 0, "total": 1})
        rate1 = r1["passed"] / r1["total"] * 100 if r1["total"] > 0 else 0
        rate2 = r2["passed"] / r2["total"] * 100 if r2["total"] > 0 else 0
        comparison["dimension_comparison"][dim] = {
            "model1": f"{rate1:.0f}%",
            "model2": f"{rate2:.0f}%",
            "difference": f"{rate2 - rate1:+.0f}%",
        }
    
    # 类别对比
    c1 = result1.get("by_category", {})
    c2 = result2.get("by_category", {})
    for cat in set(list(c1.keys()) + list(c2.keys())):
        r1 = c1.get(cat, {"passed": 0, "total": 1})
        r2 = c2.get(cat, {"passed": 0, "total": 1})
        rate1 = r1["passed"] / r1["total"] * 100 if r1["total"] > 0 else 0
        rate2 = r2["passed"] / r2["total"] * 100 if r2["total"] > 0 else 0
        comparison["category_comparison"][cat] = {
            "model1": f"{rate1:.0f}%",
            "model2": f"{rate2:.0f}%",
            "difference": f"{rate2 - rate1:+.0f}%",
        }
    
    # 逐任务对比
    all1 = {r["task_id"]: r for r in result1.get("all_results", [])}
    all2 = {r["task_id"]: r for r in result2.get("all_results", [])}
    
    for task_id in set(list(all1.keys()) + list(all2.keys())):
        r1 = all1.get(task_id)
        r2 = all2.get(task_id)
        
        if r1 and r2:
            comparison["task_comparison"].append({
                "task_id": task_id,
                "category": r1.get("category", ""),
                "model1": "✅" if r1.get("passed") else "❌",
                "model2": "✅" if r2.get("passed") else "❌",
                "time1": f"{r1.get('execution_time', 0):.1f}s",
                "time2": f"{r2.get('execution_time', 0):.1f}s",
                "tokens1": r1.get("tokens_used", 0),
                "tokens2": r2.get("tokens_used", 0),
            })
    
    # 结论
    rate1 = float(s1["pass_rate"].replace("%", ""))
    rate2 = float(s2["pass_rate"].replace("%", ""))
    diff = rate2 - rate1
    
    if diff > 5:
        comparison["conclusion"] = f"🎉 {result2['model']} 明显优于 {result1['model']}（+{diff:.1f}%）"
    elif diff > 0:
        comparison["conclusion"] = f"👍 {result2['model']} 略优于 {result1['model']}（+{diff:.1f}%）"
    elif diff > -5:
        comparison["conclusion"] = f"🤝 两个模型表现接近（{diff:.1f}%）"
    else:
        comparison["conclusion"] = f"⚠️ {result2['model']} 落后于 {result1['model']}（{diff:.1f}%）"
    
    return comparison


def print_comparison(comparison: Dict):
    """打印对比报告"""
    m1 = comparison["models"]["model1"]
    m2 = comparison["models"]["model2"]
    
    print("\n" + "=" * 70)
    print("📊 模型对比报告")
    print("=" * 70)
    print(f"测试日期: {comparison['test_date']}")
    print(f"  {m1['name']}: 通过率 {m1['pass_rate']} | 平均耗时 {m1['avg_time']} | 平均 Token {m1['avg_tokens']}")
    print(f"  {m2['name']}: 通过率 {m2['pass_rate']} | 平均耗时 {m2['avg_time']} | 平均 Token {m2['avg_tokens']}")
    
    print(f"\n🎯 结论: {comparison['conclusion']}")
    
    print("\n--- 维度对比 ---")
    print(f"  {'维度':<12} {'模型1':>8} {'模型2':>8} {'差异':>8}")
    print(f"  {'-'*40}")
    for dim, stats in comparison["dimension_comparison"].items():
        print(f"  {dim:<12} {stats['model1']:>8} {stats['model2']:>8} {stats['difference']:>8}")
    
    print("\n--- 类别对比 ---")
    print(f"  {'类别':<15} {'模型1':>8} {'模型2':>8} {'差异':>8}")
    print(f"  {'-'*43}")
    for cat, stats in comparison["category_comparison"].items():
        print(f"  {cat:<15} {stats['model1']:>8} {stats['model2']:>8} {stats['difference']:>8}")
    
    print("\n--- 逐任务对比 ---")
    print(f"  {'任务ID':<12} {'类别':<12} {'模型1':>6} {'模型2':>6} {'耗时对比':>15} {'Token对比':>12}")
    print(f"  {'-'*68}")
    for tc in comparison["task_comparison"]:
        print(f"  {tc['task_id']:<12} {tc['category']:<12} {tc['model1']:>6} {tc['model2']:>6} "
              f"{tc['time1']}/{tc['time2']:>10} {tc['tokens1']}/{tc['tokens2']:>8}")
    
    # 差异分析
    model1_only = [tc for tc in comparison["task_comparison"] 
                   if tc["model1"] == "✅" and tc["model2"] == "❌"]
    model2_only = [tc for tc in comparison["task_comparison"] 
                   if tc["model1"] == "❌" and tc["model2"] == "✅"]
    
    if model1_only:
        print(f"\n--- 模型1 优于模型2 的任务 ({len(model1_only)} 条) ---")
        for tc in model1_only:
            print(f"  {tc['task_id']} ({tc['category']})")
    
    if model2_only:
        print(f"\n--- 模型2 优于模型1 的任务 ({len(model2_only)} 条) ---")
        for tc in model2_only:
            print(f"  {tc['task_id']} ({tc['category']})")
    
    print("=" * 70)


def generate_markdown_report(comparison: Dict, output_path: str):
    """生成 Markdown 格式报告（适合公众号文章）"""
    m1 = comparison["models"]["model1"]
    m2 = comparison["models"]["model2"]
    
    md = f"""# 📊 模型对比评测报告

**测试日期**: {comparison['test_date']}

---

## 评测结论

{comparison['conclusion']}

---

## 总体对比

| 指标 | {m1['name']} | {m2['name']} |
|------|-------------|-------------|
| 通过率 | {m1['pass_rate']} | {m2['pass_rate']} |
| 通过/总数 | {m1['passed']}/{m1['total']} | {m2['passed']}/{m2['total']} |
| 平均耗时 | {m1['avg_time']} | {m2['avg_time']} |
| 平均 Token | {m1['avg_tokens']} | {m2['avg_tokens']} |

---

## 维度对比

| 维度 | {m1['name']} | {m2['name']} | 差异 |
|------|-------------|-------------|------|
"""
    for dim, stats in comparison["dimension_comparison"].items():
        md += f"| {dim} | {stats['model1']} | {stats['model2']} | {stats['difference']} |\n"
    
    md += "\n## 类别对比\n\n"
    md += f"| 类别 | {m1['name']} | {m2['name']} | 差异 |\n"
    md += "|------|-------------|-------------|------|\n"
    for cat, stats in comparison["category_comparison"].items():
        md += f"| {cat} | {stats['model1']} | {stats['model2']} | {stats['difference']} |\n"
    
    md += "\n## 逐任务对比\n\n"
    md += f"| 任务ID | 类别 | {m1['name']} | {m2['name']} | 耗时 | Token |\n"
    md += "|--------|------|-------------|-------------|------|-------|\n"
    for tc in comparison["task_comparison"]:
        md += f"| {tc['task_id']} | {tc['category']} | {tc['model1']} | {tc['model2']} | {tc['time1']}/{tc['time2']} | {tc['tokens1']}/{tc['tokens2']} |\n"
    
    md += (
        "\n---\n\n**评测工具**: 自研 Benchmark 评测子框架  \n"
        "**测试人员**: 测试员周周\n"
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    print(f"📝 Markdown 报告已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='模型对比报告生成器')
    parser.add_argument('--model1', type=str, required=True,
                        help='模型1 结果文件路径')
    parser.add_argument('--model2', type=str, required=True,
                        help='模型2 结果文件路径')
    parser.add_argument('--output', type=str, default=None,
                        help='输出文件路径（Markdown）')
    
    args = parser.parse_args()
    
    # 加载结果
    result1 = load_result(args.model1)
    result2 = load_result(args.model2)
    
    # 对比
    comparison = compare_models(result1, result2)
    
    # 打印
    print_comparison(comparison)
    
    # 保存 Markdown
    if args.output:
        generate_markdown_report(comparison, args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(__file__), 'reports',
            f"comparison_{timestamp}.md"
        )
        generate_markdown_report(comparison, output_path)


if __name__ == '__main__':
    main()
