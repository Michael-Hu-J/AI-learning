"""
模型对比报告生成器 - 对比多个模型的评测结果
使用方法：
  python compare_results.py \
    --model1 results/benchmark_glm-5.1_xxx.json \
    --model2 results/benchmark_glm-5.2_xxx.json \
    --model3 results/benchmark_deepseek-v4-pro_xxx.json
"""

import json
import os
import argparse
import html as html_module
from datetime import datetime
from typing import Dict, List, Any, Optional


MODEL_COLORS = ["#667eea", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"]


def _parse_seconds(time_str: str) -> float:
    if not time_str or time_str == "—":
        return 0.0
    return float(str(time_str).replace("s", "").strip() or 0)


def _esc(text: str) -> str:
    return html_module.escape(str(text or ""))


def _total_tokens(result: Dict) -> int:
    return sum(r.get("tokens_used", 0) for r in result.get("all_results", []))


def _build_auto_conclusion(results: List[Dict], comparison: Dict) -> Dict:
    """根据实测数据生成文章式结论要点"""
    if len(results) < 2:
        return {"summary": comparison["conclusion"], "bullets": []}

    baseline = results[0]
    b_summary = baseline["summary"]
    b_time = _parse_seconds(b_summary["avg_time"])
    b_tokens = int(b_summary["avg_tokens"])
    b_rate = _parse_pass_rate(b_summary["pass_rate"])

    bullets = []
    n_models = len(results)
    all_same_rate = len({int(_parse_pass_rate(r["summary"]["pass_rate"])) for r in results}) == 1
    if all_same_rate and b_rate == 100:
        bullets.append(
            f"✅ <strong>通过率</strong>：{n_models} 个模型均达到 {b_rate:.0f}% 通过（{b_summary['passed']}/{b_summary['total']}），质量整体接近。"
        )
    else:
        rates = "、".join(
            f"{r['model']} {r['summary']['passed']}/{r['summary']['total']}（{_parse_pass_rate(r['summary']['pass_rate']):.0f}%）"
            for r in results
        )
        bullets.append(f"✅ <strong>通过率</strong>：{rates}")

    fastest = min(results, key=lambda r: _parse_seconds(r["summary"]["avg_time"]))
    fastest_time = _parse_seconds(fastest["summary"]["avg_time"])
    if b_time > 0 and fastest["model"] != baseline["model"]:
        faster_pct = (b_time - fastest_time) / b_time * 100
        bullets.append(
            f"⚡ <strong>速度</strong>：{fastest['model']} 最快，比 {baseline['model']} 快 <strong>{faster_pct:.1f}%</strong>（{fastest_time:.1f}s vs {b_time:.1f}s）。"
        )

    cheapest = min(results, key=lambda r: int(r["summary"]["avg_tokens"]))
    cheapest_tokens = int(cheapest["summary"]["avg_tokens"])
    if b_tokens > 0 and cheapest["model"] != baseline["model"]:
        save_pct = (b_tokens - cheapest_tokens) / b_tokens * 100
        bullets.append(
            f"💰 <strong>Token 效率</strong>：{cheapest['model']} 最省，比 {baseline['model']} 省 <strong>{save_pct:.1f}%</strong>（{cheapest_tokens} vs {b_tokens} tokens/任务）。"
        )

    failed = [(r["model"], r["summary"]["failed"]) for r in results if r["summary"]["failed"] > 0]
    if failed:
        fail_text = "；".join(f"{name} 失败 {cnt} 条" for name, cnt in failed)
        bullets.append(f"⚠️ <strong>稳定性</strong>：{fail_text}，建议对失败任务单独重跑复核。")

    return {"summary": comparison["conclusion"], "bullets": bullets}


def _build_task_catalog_rows(tasks: List[Dict]) -> str:
    rows = ""
    for t in tasks:
        rows += f"""<tr>
            <td>{_esc(t.get('task_id', ''))}</td>
            <td>{_esc(t.get('category', ''))}</td>
            <td>{_esc(t.get('dimension', ''))}</td>
            <td>{_esc(t.get('difficulty', ''))}</td>
            <td>{_esc(t.get('description', ''))}</td>
        </tr>"""
    return rows


def _build_execution_logs(results: List[Dict]) -> str:
    blocks = ""
    for result in results:
        lines = []
        all_results = result.get("all_results", [])
        total = len(all_results)
        for i, r in enumerate(all_results, 1):
            mark = "✅" if r.get("passed") else "❌"
            lines.append(
                f"[{i:2d}/{total}] {r['task_id']} ({r.get('category', '')}, {r.get('difficulty', '')}) "
                f"... {mark} ({r.get('execution_time', 0):.1f}s, {r.get('tokens_used', 0)} tokens)"
            )
        s = result["summary"]
        lines.append("")
        lines.append(f"✅ 评测完成: {result['model']}")
        lines.append(
            f"通过率: {s['pass_rate']} ({s['passed']}/{s['total']}) | "
            f"平均耗时: {s['avg_time']} | 平均 Token: {s['avg_tokens']}"
        )
        blocks += f"""
        <div class="log-block">
            <h3>🚀 { _esc(result['model']) } 评测过程</h3>
            <pre>{_esc(chr(10).join(lines))}</pre>
        </div>"""
    return blocks


def _build_detailed_task_table(results: List[Dict], model_keys: List[str], model_names: List[str]) -> str:
    baseline_map = {r["task_id"]: r for r in results[0].get("all_results", [])}
    task_maps = [{r["task_id"]: r for r in res.get("all_results", [])} for res in results]

    rows = ""
    all_ids = sorted({tid for m in task_maps for tid in m.keys()})
    for task_id in all_ids:
        base = baseline_map.get(task_id, {})
        category = base.get("category", task_maps[0].get(task_id, {}).get("category", ""))
        difficulty = base.get("difficulty", task_maps[0].get(task_id, {}).get("difficulty", ""))
        base_time = base.get("execution_time", 0)
        base_tokens = base.get("tokens_used", 0)

        cells = ""
        for idx, (res, name) in enumerate(zip(results, model_names)):
            r = task_maps[idx].get(task_id)
            if not r:
                cells += "<td colspan='3'>—</td>"
                continue
            mark = "✅" if r.get("passed") else "❌"
            t = r.get("execution_time", 0)
            tok = r.get("tokens_used", 0)
            if idx == 0:
                time_diff = "—"
                token_diff = "—"
            else:
                time_diff = f"{t - base_time:+.1f}s"
                token_diff = f"{tok - base_tokens:+d}"
            cells += f"<td>{mark}<br><small>{t:.1f}s</small></td><td>{time_diff}</td><td>{token_diff}</td>"

        rows += f"<tr><td>{_esc(task_id)}</td><td>{_esc(category)}</td><td>{_esc(difficulty)}</td>{cells}</tr>"
    return rows


def _build_output_samples(results: List[Dict], sample_ids: List[str]) -> str:
    blocks = ""
    task_maps = [{r["task_id"]: r for r in res.get("all_results", [])} for res in results]
    for task_id in sample_ids:
        first = task_maps[0].get(task_id, {})
        category = first.get("category", task_id)
        blocks += f'<div class="sample-block"><h4>{_esc(task_id)} - {_esc(category)}</h4>'
        for res, tmap in zip(results, task_maps):
            r = tmap.get(task_id)
            if not r:
                continue
            snippet = (r.get("output") or r.get("error") or "（无输出）").strip()
            snippet = snippet[:280] + ("..." if len(snippet) > 280 else "")
            blocks += f"""
            <div class="sample-item">
                <div class="sample-meta"><strong>{_esc(res['model'])}</strong>
                （{r.get('execution_time', 0):.1f}s, {r.get('tokens_used', 0)} tokens）</div>
                <blockquote>{_esc(snippet)}</blockquote>
            </div>"""
        blocks += "</div>"
    return blocks


def _build_findings_html(results: List[Dict]) -> str:
    if len(results) < 2:
        return ""
    baseline = results[0]
    b_time = _parse_seconds(baseline["summary"]["avg_time"])
    b_map = {r["task_id"]: r for r in baseline.get("all_results", [])}

    fastest_wins = {r["model"]: 0 for r in results[1:]}
    for task_id, br in b_map.items():
        b_t = br.get("execution_time", 0)
        for res in results[1:]:
            r = next((x for x in res.get("all_results", []) if x["task_id"] == task_id), None)
            if r and r.get("execution_time", 0) < b_t:
                fastest_wins[res["model"]] += 1

    items = []
    for res in results[1:]:
        t = _parse_seconds(res["summary"]["avg_time"])
        tok = int(res["summary"]["avg_tokens"])
        if b_time > 0:
            items.append(f"<li><strong>{_esc(res['model'])}</strong>：平均耗时 {t:.1f}s，比基准快 {(b_time-t)/b_time*100:.1f}%；平均 Token {tok}。</li>")
        items.append(f"<li>在 10 条任务中有 <strong>{fastest_wins.get(res['model'], 0)}</strong> 条比 {baseline['model']} 更快。</li>")

    glm52 = next((r for r in results if "5.2" in r.get("model", "")), None)
    if glm52 and glm52["summary"]["failed"] > 0:
        failed_ids = [fc["task_id"] for fc in glm52.get("failed_cases", [])]
        items.append(f"<li><strong>GLM-5.2 注意点</strong>：{', '.join(failed_ids)} 未通过，需关注长耗时代码生成类任务稳定性。</li>")

    return "<ul class='finding-list'>" + "".join(items) + "</ul>"


def _build_recommendation_rows(results: List[Dict]) -> str:
    scenarios = [
        ("追求速度", min(results, key=lambda r: _parse_seconds(r["summary"]["avg_time"]))["model"], "平均耗时最低，适合批量跑评测"),
        ("追求 Token 成本", min(results, key=lambda r: int(r["summary"]["avg_tokens"]))["model"], "输出更精简，长任务成本更低"),
        ("追求通过率", max(results, key=lambda r: _parse_pass_rate(r["summary"]["pass_rate"]))["model"], "自动评分通过率最高"),
        ("国内百炼集成", next((r["model"] for r in results if "百炼" in r["model"]), results[0]["model"]), "阿里云百炼调用，国内访问更稳定"),
        ("复杂代码生成", results[-1]["model"] if "DeepSeek" in results[-1]["model"] else results[0]["model"], "Locust/脚本类任务表现稳定"),
    ]
    rows = ""
    for scene, model, reason in scenarios:
        rows += f"<tr><td>{_esc(scene)}</td><td><strong>{_esc(model)}</strong></td><td>{_esc(reason)}</td></tr>"
    return rows


def _status_class(status: str) -> str:
    if status == "✅":
        return "pass"
    if status == "❌":
        return "fail"
    return "neutral"


def load_result(filepath: str) -> Dict:
    """加载评测结果"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def _parse_pass_rate(pass_rate: str) -> float:
    return float(str(pass_rate).replace("%", ""))


def _rate_stats(stats: Dict) -> float:
    total = stats.get("total", 0)
    if total <= 0:
        return 0.0
    return stats["passed"] / total * 100


def compare_models(*results: Dict) -> Dict:
    """对比多个模型的结果"""
    if len(results) < 2:
        raise ValueError("至少需要 2 个模型的评测结果")

    model_keys = [f"model{i + 1}" for i in range(len(results))]
    summaries = [r["summary"] for r in results]

    comparison = {
        "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "models": {},
        "dimension_comparison": {},
        "category_comparison": {},
        "task_comparison": [],
        "conclusion": "",
    }

    for key, result in zip(model_keys, results):
        summary = result["summary"]
        comparison["models"][key] = {
            "name": result["model"],
            "pass_rate": summary["pass_rate"],
            "total": summary["total"],
            "passed": summary["passed"],
            "failed": summary["failed"],
            "avg_time": summary["avg_time"],
            "avg_tokens": summary["avg_tokens"],
        }

    all_dimensions = set()
    all_categories = set()
    for result in results:
        all_dimensions.update(result.get("by_dimension", {}).keys())
        all_categories.update(result.get("by_category", {}).keys())

    for dim in sorted(all_dimensions):
        comparison["dimension_comparison"][dim] = {}
        for key, result in zip(model_keys, results):
            stats = result.get("by_dimension", {}).get(dim, {"passed": 0, "total": 0})
            comparison["dimension_comparison"][dim][key] = f"{_rate_stats(stats):.0f}%"

    for cat in sorted(all_categories):
        comparison["category_comparison"][cat] = {}
        for key, result in zip(model_keys, results):
            stats = result.get("by_category", {}).get(cat, {"passed": 0, "total": 0})
            comparison["category_comparison"][cat][key] = f"{_rate_stats(stats):.0f}%"

    task_maps = []
    for result in results:
        task_maps.append({r["task_id"]: r for r in result.get("all_results", [])})

    all_task_ids = set()
    for task_map in task_maps:
        all_task_ids.update(task_map.keys())

    for task_id in sorted(all_task_ids):
        row = {"task_id": task_id, "category": ""}
        for idx, (key, task_map) in enumerate(zip(model_keys, task_maps), start=1):
            task_result = task_map.get(task_id)
            if not task_result:
                row[key] = "—"
                row[f"time{idx}"] = "—"
                row[f"tokens{idx}"] = "—"
                continue

            if not row["category"]:
                row["category"] = task_result.get("category", "")
            row[key] = "✅" if task_result.get("passed") else "❌"
            row[f"time{idx}"] = f"{task_result.get('execution_time', 0):.1f}s"
            row[f"tokens{idx}"] = task_result.get("tokens_used", 0)

        comparison["task_comparison"].append(row)

    pass_rates = [_parse_pass_rate(s["pass_rate"]) for s in summaries]
    best_idx = pass_rates.index(max(pass_rates))
    best_name = results[best_idx]["model"]
    best_rate = pass_rates[best_idx]

    if len(set(pass_rates)) == 1:
        comparison["conclusion"] = f"🤝 三个模型通过率相同（{best_rate:.1f}%）"
    else:
        ranking = sorted(
            zip(results, pass_rates),
            key=lambda item: item[1],
            reverse=True,
        )
        ranking_text = " > ".join(
            f"{item[0]['model']} ({item[1]:.1f}%)" for item in ranking
        )
        comparison["conclusion"] = f"🏆 通过率排名：{ranking_text}"

    return comparison


def print_comparison(comparison: Dict):
    """打印对比报告"""
    model_keys = list(comparison["models"].keys())
    models = comparison["models"]

    print("\n" + "=" * 90)
    print("📊 模型对比报告")
    print("=" * 90)
    print(f"测试日期: {comparison['test_date']}")
    for key in model_keys:
        model = models[key]
        print(
            f"  {model['name']}: 通过率 {model['pass_rate']} | "
            f"平均耗时 {model['avg_time']} | 平均 Token {model['avg_tokens']}"
        )

    print(f"\n🎯 结论: {comparison['conclusion']}")

    print("\n--- 维度对比 ---")
    header = f"  {'维度':<12}" + "".join(f"{models[k]['name'][:10]:>12}" for k in model_keys)
    print(header)
    print(f"  {'-' * (12 + 12 * len(model_keys))}")
    for dim, stats in comparison["dimension_comparison"].items():
        row = f"  {dim:<12}" + "".join(f"{stats[k]:>12}" for k in model_keys)
        print(row)

    print("\n--- 类别对比 ---")
    header = f"  {'类别':<15}" + "".join(f"{models[k]['name'][:10]:>12}" for k in model_keys)
    print(header)
    print(f"  {'-' * (15 + 12 * len(model_keys))}")
    for cat, stats in comparison["category_comparison"].items():
        row = f"  {cat:<15}" + "".join(f"{stats[k]:>12}" for k in model_keys)
        print(row)

    print("\n--- 逐任务对比 ---")
    header = (
        f"  {'任务ID':<12} {'类别':<12}"
        + "".join(f"{models[k]['name'][:8]:>10}" for k in model_keys)
        + "  耗时"
        + "  Token"
    )
    print(header)
    print(f"  {'-' * (24 + 10 * len(model_keys) + 20)}")
    for tc in comparison["task_comparison"]:
        pass_cols = "".join(f"{tc[k]:>10}" for k in model_keys)
        time_cols = "/".join(tc.get(f"time{i}", "—") for i in range(1, len(model_keys) + 1))
        token_cols = "/".join(str(tc.get(f"tokens{i}", "—")) for i in range(1, len(model_keys) + 1))
        print(
            f"  {tc['task_id']:<12} {tc['category']:<12}{pass_cols}  "
            f"{time_cols:<18} {token_cols}"
        )

    print("=" * 90)


def generate_markdown_report(comparison: Dict, output_path: str):
    """生成 Markdown 格式报告"""
    model_keys = list(comparison["models"].keys())
    models = comparison["models"]
    model_names = [models[k]["name"] for k in model_keys]

    md = f"""# 📊 模型对比评测报告

**测试日期**: {comparison['test_date']}

---

## 评测结论

{comparison['conclusion']}

---

## 总体对比

| 指标 | {' | '.join(model_names)} |
|------|{'|'.join(['------'] * len(model_names))}|
| 通过率 | {' | '.join(models[k]['pass_rate'] for k in model_keys)} |
| 通过/总数 | {' | '.join(f"{models[k]['passed']}/{models[k]['total']}" for k in model_keys)} |
| 平均耗时 | {' | '.join(models[k]['avg_time'] for k in model_keys)} |
| 平均 Token | {' | '.join(str(models[k]['avg_tokens']) for k in model_keys)} |

---

## 维度对比

| 维度 | {' | '.join(model_names)} |
|------|{'|'.join(['------'] * len(model_keys))}|
"""
    for dim, stats in comparison["dimension_comparison"].items():
        md += f"| {dim} | {' | '.join(stats[k] for k in model_keys)} |\n"

    md += "\n## 类别对比\n\n"
    md += f"| 类别 | {' | '.join(model_names)} |\n"
    md += f"|------|{'|'.join(['------'] * len(model_keys))}|\n"
    for cat, stats in comparison["category_comparison"].items():
        md += f"| {cat} | {' | '.join(stats[k] for k in model_keys)} |\n"

    md += "\n## 逐任务对比\n\n"
    md += (
        f"| 任务ID | 类别 | {' | '.join(model_names)} | 耗时 | Token |\n"
        f"|--------|------|{'|'.join(['------'] * len(model_keys))}|------|-------|\n"
    )
    for tc in comparison["task_comparison"]:
        pass_cols = " | ".join(tc[k] for k in model_keys)
        time_cols = "/".join(tc.get(f"time{i}", "—") for i in range(1, len(model_keys) + 1))
        token_cols = "/".join(str(tc.get(f"tokens{i}", "—")) for i in range(1, len(model_keys) + 1))
        md += f"| {tc['task_id']} | {tc['category']} | {pass_cols} | {time_cols} | {token_cols} |\n"

    md += (
        "\n---\n\n**评测工具**: 自研 Benchmark 评测子框架  \n"
        "**测试人员**: 测试员周周\n"
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"📝 Markdown 报告已保存: {output_path}")


def generate_html_report(
    comparison: Dict,
    output_path: str,
    results: Optional[List[Dict]] = None,
    tasks: Optional[List[Dict]] = None,
) -> None:
    from html_report import render_html_report
    render_html_report(comparison, output_path, results=results, tasks=tasks)


def main():
    parser = argparse.ArgumentParser(description='模型对比报告生成器')
    parser.add_argument('--model1', type=str, required=True, help='模型1 结果文件（GLM-5.1）')
    parser.add_argument('--model2', type=str, required=True, help='模型2 结果文件（GLM-5.2）')
    parser.add_argument('--model3', type=str, default=None, help='模型3 结果文件（DeepSeek-V4-Pro）')
    parser.add_argument('--output', type=str, default=None, help='输出 Markdown 报告路径')
    parser.add_argument('--html', type=str, default=None, help='输出 HTML 报告路径')

    args = parser.parse_args()

    result_files = [args.model1, args.model2]
    if args.model3:
        result_files.append(args.model3)

    results = [load_result(path) for path in result_files]
    comparison = compare_models(*results)
    print_comparison(comparison)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')

    if args.output:
        md_path = args.output
    else:
        md_path = os.path.join(reports_dir, f"comparison_{timestamp}.md")

    if args.html:
        html_path = args.html
    else:
        html_path = os.path.join(reports_dir, f"comparison_{timestamp}.html")

    generate_markdown_report(comparison, md_path)

    tasks_path = os.path.join(os.path.dirname(__file__), "tasks", "benchmark_tasks.json")
    tasks = []
    if os.path.exists(tasks_path):
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)

    generate_html_report(comparison, html_path, results=results, tasks=tasks)


if __name__ == '__main__':
    main()
