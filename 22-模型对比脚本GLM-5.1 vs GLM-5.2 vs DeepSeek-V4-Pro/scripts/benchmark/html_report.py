"""HTML 对比报告渲染（评测系列6文章风格，支持多模型）"""

import json
import os
from typing import Dict, List, Any, Optional

from compare_results import (
    MODEL_COLORS,
    _build_auto_conclusion,
    _build_detailed_task_table,
    _build_execution_logs,
    _build_findings_html,
    _build_output_samples,
    _build_recommendation_rows,
    _build_task_catalog_rows,
    _esc,
    _parse_pass_rate,
    _parse_seconds,
    _status_class,
    _total_tokens,
)


def render_html_report(
    comparison: Dict,
    output_path: str,
    results: Optional[List[Dict]] = None,
    tasks: Optional[List[Dict]] = None,
) -> None:
    results = results or []
    tasks = tasks or []
    model_keys = list(comparison["models"].keys())
    models = comparison["models"]
    model_names = [models[k]["name"] for k in model_keys]
    colors = MODEL_COLORS[:len(model_keys)]

    pass_rates = [_parse_pass_rate(models[k]["pass_rate"]) for k in model_keys]
    avg_times = [_parse_seconds(models[k]["avg_time"]) for k in model_keys]
    avg_tokens = [int(models[k]["avg_tokens"]) for k in model_keys]

    auto = _build_auto_conclusion(results, comparison) if results else {"summary": comparison["conclusion"], "bullets": []}
    bullet_html = "".join(f"<li>{b}</li>" for b in auto["bullets"])

    summary_cards = ""
    for idx, key in enumerate(model_keys):
        m = models[key]
        total_tok = _total_tokens(results[idx]) if results and idx < len(results) else "—"
        summary_cards += f"""
        <div class="model-card" style="border-top:4px solid {colors[idx]}">
            <h3>{_esc(m['name'])}</h3>
            <div class="metric"><span>通过率</span><strong>{_esc(m['pass_rate'])}</strong></div>
            <div class="metric"><span>通过/总数</span><strong>{m['passed']}/{m['total']}</strong></div>
            <div class="metric"><span>平均耗时</span><strong>{_esc(m['avg_time'])}</strong></div>
            <div class="metric"><span>平均 Token</span><strong>{m['avg_tokens']}</strong></div>
            <div class="metric"><span>总 Token</span><strong>{total_tok}</strong></div>
        </div>"""

    overall_rows = ""
    metrics = [
        ("通过率", [models[k]["pass_rate"] for k in model_keys]),
        ("通过/总数", [f"{models[k]['passed']}/{models[k]['total']}" for k in model_keys]),
        ("平均耗时", [models[k]["avg_time"] for k in model_keys]),
        ("平均 Token", [str(models[k]["avg_tokens"]) for k in model_keys]),
        ("总 Token", [str(_total_tokens(results[i])) if results and i < len(results) else "—" for i in range(len(model_keys))]),
    ]
    for label, vals in metrics:
        overall_rows += f"<tr><td>{_esc(label)}</td>" + "".join(f"<td>{_esc(v)}</td>" for v in vals) + "</tr>"

    model_headers = "".join(f"<th>{_esc(n)}</th>" for n in model_names)

    dim_rows = "".join(
        f"<tr><td>{_esc(dim)}</td>" + "".join(f"<td>{stats[k]}</td>" for k in model_keys) + "</tr>"
        for dim, stats in comparison["dimension_comparison"].items()
    )
    cat_rows = "".join(
        f"<tr><td>{_esc(cat)}</td>" + "".join(f"<td>{stats[k]}</td>" for k in model_keys) + "</tr>"
        for cat, stats in comparison["category_comparison"].items()
    )

    task_rows = ""
    for tc in comparison["task_comparison"]:
        status_cells = "".join(
            f"<td><span class='badge badge-{_status_class(tc[k])}'>{tc[k]}</span></td>"
            for k in model_keys
        )
        time_cols = " / ".join(tc.get(f"time{i}", "—") for i in range(1, len(model_keys) + 1))
        token_cols = " / ".join(str(tc.get(f"tokens{i}", "—")) for i in range(1, len(model_keys) + 1))
        task_rows += f"<tr><td>{_esc(tc['task_id'])}</td><td>{_esc(tc['category'])}</td>{status_cells}<td>{time_cols}</td><td>{token_cols}</td></tr>"

    task_catalog = _build_task_catalog_rows(tasks) if tasks else ""
    exec_logs = _build_execution_logs(results) if results else ""
    detailed_table = _build_detailed_task_table(results, model_keys, model_names) if results else ""
    findings = _build_findings_html(results) if results else ""
    samples = _build_output_samples(results, ["BENCH_001", "BENCH_004", "BENCH_005", "BENCH_007"]) if results else ""
    rec_rows = _build_recommendation_rows(results) if results else ""

    cost_rows = ""
    if results:
        for res in results:
            total = _total_tokens(res)
            if "DeepSeek" in res["model"]:
                cost = f"约 {total / 1000 * 0.04:.2f} 元"
                note = "按官方定价估算"
            else:
                cost = "0 元（百炼免费额度）"
                note = "百炼免费额度"
            cost_rows += f"<tr><td>{_esc(res['model'])}</td><td>{total:,}</td><td>{cost}</td><td>{note}</td></tr>"

    speed_series = []
    speed_legend = []
    task_ids_chart = []
    if len(results) >= 2:
        baseline_map = {r["task_id"]: r for r in results[0].get("all_results", [])}
        task_ids_chart = sorted(baseline_map.keys())
        for idx, res in enumerate(results[1:], start=1):
            rmap = {r["task_id"]: r for r in res.get("all_results", [])}
            data = []
            for tid in task_ids_chart:
                bt = baseline_map[tid].get("execution_time", 0)
                t = rmap.get(tid, {}).get("execution_time", 0)
                pct = round((bt - t) / bt * 100, 1) if bt > 0 else 0
                data.append(pct)
            speed_series.append({"name": res["model"], "data": data, "color": colors[idx] if idx < len(colors) else "#999"})
            speed_legend.append(res["model"])

    title_models = " vs ".join(model_names)
    intro = (
        "新模型发布，媒体通稿满天飞。\"XX 模型全面超越 XX\"——这些数字你怎么验证？"
        "我从测试平台抽了 <strong>10 条真实任务</strong>，让三个模型各跑一遍，记录耗时、Token 消耗、输出质量。"
        f"本次对比：<strong>{_esc(title_models)}</strong>。"
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新模型上线怎么测？{title_models} 对比评测报告</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f5f7fa; color:#333; line-height:1.75; }}
        .container {{ max-width:1180px; margin:0 auto; padding:24px; }}
        .hero {{ background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:#fff; padding:40px 36px; border-radius:16px; margin-bottom:24px; box-shadow:0 8px 24px rgba(102,126,234,.35); }}
        .hero .tag {{ display:inline-block; background:rgba(255,255,255,.18); padding:4px 12px; border-radius:20px; font-size:13px; margin-bottom:12px; }}
        .hero h1 {{ font-size:28px; margin-bottom:8px; line-height:1.35; }}
        .hero .sub {{ opacity:.92; font-size:15px; }}
        .intro {{ background:#fff; padding:20px 24px; border-radius:12px; margin-bottom:24px; box-shadow:0 2px 8px rgba(0,0,0,.06); font-size:15px; }}
        .section {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:24px; box-shadow:0 2px 8px rgba(0,0,0,.08); }}
        .section h2 {{ font-size:20px; margin-bottom:14px; padding-bottom:8px; border-bottom:2px solid #f0f0f0; }}
        .section h3 {{ font-size:16px; margin:16px 0 10px; color:#555; }}
        .conclusion-box {{ background:#f6f8ff; border-left:4px solid #667eea; padding:16px 20px; border-radius:8px; }}
        .conclusion-box ul {{ margin:12px 0 0 20px; }}
        .conclusion-box li {{ margin:8px 0; }}
        .model-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin:16px 0; }}
        .model-card {{ background:#fafafa; border-radius:10px; padding:18px; }}
        .model-card h3 {{ font-size:16px; margin-bottom:10px; }}
        .metric {{ display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #eee; font-size:14px; }}
        .metric:last-child {{ border-bottom:none; }}
        .chart {{ height:360px; margin-top:12px; }}
        .chart-speed {{ height:420px; margin-top:16px; }}
        table {{ width:100%; border-collapse:collapse; font-size:14px; }}
        th,td {{ padding:10px 12px; text-align:left; border-bottom:1px solid #f0f0f0; vertical-align:top; }}
        th {{ background:#fafafa; color:#666; font-weight:600; }}
        .badge {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:12px; color:#fff; }}
        .badge-pass {{ background:#52c41a; }} .badge-fail {{ background:#ff4d4f; }} .badge-neutral {{ background:#d9d9d9; color:#666; }}
        .log-block {{ margin:16px 0; }}
        .log-block pre {{ background:#1e1e1e; color:#d4d4d4; padding:16px; border-radius:8px; overflow-x:auto; font-size:12px; line-height:1.5; }}
        .method-list {{ margin:12px 0 0 20px; }} .method-list li {{ margin:6px 0; }}
        .sample-block {{ margin:20px 0; padding:16px; background:#fafafa; border-radius:8px; }}
        .sample-item {{ margin:12px 0; }}
        .sample-meta {{ font-size:13px; color:#666; margin-bottom:6px; }}
        blockquote {{ border-left:3px solid #667eea; padding:8px 14px; background:#fff; color:#555; font-size:14px; }}
        .finding-list li {{ margin:8px 0; }}
        .footer {{ text-align:center; color:#999; padding:24px 0; font-size:13px; }}
        .note {{ color:#888; font-size:13px; margin-top:8px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="hero">
        <div class="tag">【评测系列6 扩展版】新模型上线怎么测？</div>
        <h1>我用 10 条真实任务对比了 {title_models}</h1>
        <p class="sub">测试员周周 · 14 年测试经验 · 用数据说话 · 测试日期 {comparison['test_date']}</p>
    </div>

    <div class="intro">{intro}</div>

    <div class="section">
        <h2>🛑 先说结论</h2>
        <div class="conclusion-box">
            <p><strong>一句话总结：</strong>{_esc(auto['summary'])}</p>
            <ul>{bullet_html}</ul>
        </div>
        <div class="model-grid">{summary_cards}</div>
    </div>

    <div class="section">
        <h2>我测了什么？怎么测的？</h2>
        <h3>测试平台</h3>
        <p>基于多 Agent 测试平台的真实使用场景，包含需求解析、用例生成、脚本生成、性能方案、Bug 诊断、安全数据、报告生成等完整测试工程链路。本次 <strong>10 条任务</strong> 全部来自平台真实场景，不是公开数据集。</p>
        <h3>10 条评测任务</h3>
        <table>
            <tr><th>任务ID</th><th>类别</th><th>维度</th><th>难度</th><th>测试内容</th></tr>
            {task_catalog}
        </table>
        <h3>评测方法（关键原则）</h3>
        <ol class="method-list">
            <li>配置模型：{' + '.join(model_names)}</li>
            <li>固定参数：temperature=0.3, max_tokens=4096</li>
            <li>逐条执行：每条任务调用模型 API，记录输入、输出、耗时、Token</li>
            <li>自动评分：根据预设评价标准自动判定是否通过</li>
            <li>人工复核：检查关键任务输出质量</li>
        </ol>
        <p class="note">关键原则：三模型使用完全相同的 prompt；记录真实 API 调用数据；评测框架独立于业务系统。</p>
    </div>

    <div class="section">
        <h2>评测过程：实测日志</h2>
        {exec_logs}
    </div>

    <div class="section">
        <h2>评测结果：数据说话</h2>
        <h3>总体对比</h3>
        <table>
            <tr><th>指标</th>{model_headers}</tr>
            {overall_rows}
        </table>
        <div id="chart-overview" class="chart"></div>
        <h3>逐任务对比（相对 {model_names[0]} 的耗时/Token 差）</h3>
        <table>
            <tr><th>任务</th><th>类别</th><th>难度</th>
            {''.join(f'<th colspan="3">{_esc(n)}</th>' for n in model_names)}
            </tr>
            <tr><th></th><th></th><th></th>
            {''.join('<th>结果</th><th>耗时差</th><th>Token差</th>' for _ in model_names)}
            </tr>
            {detailed_table}
        </table>
        <h3>相对 {_esc(model_names[0])} 的速度提升（正值表示比基准更快）</h3>
        <div id="chart-speed" class="chart chart-speed"></div>
    </div>

    <div class="section">
        <h2>关键发现</h2>
        {findings}
    </div>

    <div class="section">
        <h2>输出质量对比（抽样）</h2>
        {samples}
    </div>

    <div class="section">
        <h2>成本对比（估算）</h2>
        <table>
            <tr><th>模型</th><th>总 Token</th><th>估算成本</th><th>说明</th></tr>
            {cost_rows}
        </table>
        <p class="note">注：百炼 GLM 系列使用免费额度；DeepSeek 按官方定价估算，实际因套餐而异。</p>
    </div>

    <div class="section">
        <h2>推荐建议</h2>
        <table>
            <tr><th>场景</th><th>推荐模型</th><th>理由</th></tr>
            {rec_rows}
        </table>
    </div>

    <div class="section">
        <h2>🧭 维度对比</h2>
        <table><tr><th>维度</th>{model_headers}</tr>{dim_rows}</table>
    </div>

    <div class="section">
        <h2>📂 类别对比</h2>
        <table><tr><th>类别</th>{model_headers}</tr>{cat_rows}</table>
    </div>

    <div class="section">
        <h2>📝 逐任务通过情况</h2>
        <table>
            <tr><th>任务ID</th><th>类别</th>{model_headers}<th>耗时</th><th>Token</th></tr>
            {task_rows}
        </table>
    </div>

    <div class="section">
        <h2>写在最后</h2>
        <p>第一，<strong>质量差距在缩小</strong>——多数模型在真实测试任务上通过率接近，国产模型在测试工程领域已具备实用能力。</p>
        <p>第二，<strong>效率差距在扩大</strong>——DeepSeek-V4-Pro 在速度和 Token 效率上优势明显；GLM-5.2 作为新版本需关注复杂代码生成任务的稳定性。</p>
        <p>第三，<strong>新模型上线建议</strong>：先用本框架跑 10 条真实任务，再看速度/成本/质量三维数据做选型，不要只看通稿数字。</p>
    </div>

    <div class="section">
        <h2>🔜 下篇预告</h2>
        <ol class="method-list">
            <li>完整展示 10 条任务的 Prompt（每条任务的实际输入）</li>
            <li>逐条对比三个模型的完整输出（代码质量、分析深度）</li>
            <li>评测框架开源（可直接用于新模型上线测试）</li>
        </ol>
        <p>想看完整 Prompt 和输出对比？关注「测试员周周」，下篇不见不散。</p>
    </div>

    <div class="section">
        <h2>💬 互动时间</h2>
        <p>你觉得新模型上线，最该测什么？</p>
        <ul class="method-list">
            <li><strong>A.</strong> 代码生成能力</li>
            <li><strong>B.</strong> 推理和逻辑能力</li>
            <li><strong>C.</strong> 安全性和合规性</li>
            <li><strong>D.</strong> 速度和成本</li>
        </ul>
        <p>留言告诉我你的选择 + 理由，我会抽 3 个最有价值的评论，送出一份完整的评测报告模板。</p>
        <p class="note">📌 收藏本文：下次新模型发布，直接用这个框架跑一遍，用数据说话。<br>🔗 完整源码：测试员周周回复「源码」免费获取</p>
    </div>

    <div class="footer">
        评测工具：Benchmark 评测子框架 · 测试人员：测试员周周 · 微信公众号：测试员周周
    </div>
</div>
<script>
const modelNames = {json.dumps(model_names, ensure_ascii=False)};
const passRates = {json.dumps(pass_rates)};
const avgTimes = {json.dumps(avg_times)};
const avgTokens = {json.dumps(avg_tokens)};
const colors = {json.dumps(colors)};
const taskIds = {json.dumps(task_ids_chart, ensure_ascii=False)};
const speedSeries = {json.dumps(speed_series, ensure_ascii=False)};

const chart1 = echarts.init(document.getElementById('chart-overview'));
chart1.setOption({{
    tooltip: {{ trigger: 'axis' }},
    legend: {{ data: ['通过率(%)', '平均耗时(s)', '平均Token(/100)'] }},
    xAxis: {{ type: 'category', data: modelNames }},
    yAxis: {{ type: 'value' }},
    series: [
        {{ name: '通过率(%)', type: 'bar', data: passRates, itemStyle: {{ color: colors[0] }} }},
        {{ name: '平均耗时(s)', type: 'bar', data: avgTimes, itemStyle: {{ color: colors[1] || '#f59e0b' }} }},
        {{ name: '平均Token(/100)', type: 'bar', data: avgTokens.map(v => (v/100).toFixed(1)), itemStyle: {{ color: colors[2] || '#10b981' }} }}
    ]
}});

if (document.getElementById('chart-speed') && speedSeries.length) {{
    const chart2 = echarts.init(document.getElementById('chart-speed'));
    const baselineName = modelNames[0] || '基准模型';
    chart2.setOption({{
        tooltip: {{
            trigger: 'axis',
            formatter: function(params) {{
                let lines = [params[0].axisValue];
                params.forEach(p => {{
                    const sign = p.value >= 0 ? '+' : '';
                    lines.push(p.marker + p.seriesName + ': ' + sign + p.value + '%');
                }});
                lines.push('（相对 ' + baselineName + '）');
                return lines.join('<br/>');
            }}
        }},
        legend: {{
            type: 'plain',
            orient: 'horizontal',
            top: 8,
            left: 'center',
            itemGap: 28,
            textStyle: {{ fontSize: 12 }},
            data: speedSeries.map(s => s.name)
        }},
        grid: {{ top: 52, left: '3%', right: '4%', bottom: 72, containLabel: true }},
        xAxis: {{ type: 'category', data: taskIds, axisLabel: {{ rotate: 30, fontSize: 11 }} }},
        yAxis: {{ type: 'value', name: '提升 %', nameGap: 12 }},
        series: speedSeries.map((s, i) => ({{
            name: s.name, type: 'bar', data: s.data, barMaxWidth: 28,
            itemStyle: {{ color: s.color }}
        }}))
    }});
    window.addEventListener('resize', () => chart2.resize());
}}
window.addEventListener('resize', () => chart1.resize());
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🌐 HTML 报告已保存: {output_path}")
