#!/usr/bin/env python3
"""
Agent 评测报告生成器
生成纯 SVG 可视化报告 (零依赖)
"""
import json
from pathlib import Path
from datetime import datetime
import argparse


def generate_radar_svg(scores: dict, width: int = 400, height: int = 400) -> str:
    """生成雷达图 SVG"""
    categories = list(scores.keys())
    values = list(scores.values())
    n = len(categories)
    
    cx, cy, r = width // 2, height // 2, min(width, height) // 2 - 60
    
    import math
    
    def get_point(angle_deg: float, radius: float):
        angle_rad = math.radians(angle_deg - 90)
        x = cx + radius * math.cos(angle_rad)
        y = cy + radius * math.sin(angle_rad)
        return (x, y)
    
    # 背景网格
    grid_svg = ""
    for i in range(1, 6):
        radius = r * i / 5
        points = " ".join(
            f"{get_point(360 * j / n, radius)[0]:.1f},{get_point(360 * j / n, radius)[1]:.1f}"
            for j in range(n)
        )
        grid_svg += f'  <polygon points="{points}" fill="none" stroke="#e2e8f0" stroke-width="1"/>\n'
    
    # 轴线
    axis_svg = ""
    for j in range(n):
        p = get_point(360 * j / n, r)
        axis_svg += f'  <line x1="{cx}" y1="{cy}" x2="{p[0]:.1f}" y2="{p[1]:.1f}" stroke="#e2e8f0" stroke-width="1"/>\n'
    
    # 数据多边形
    data_points = " ".join(
        f"{get_point(360 * j / n, r * v / 5)[0]:.1f},{get_point(360 * j / n, r * v / 5)[1]:.1f}"
        for j, v in enumerate(values)
    )
    data_svg = f'  <polygon points="{data_points}" fill="rgba(79, 70, 229, 0.2)" stroke="rgb(79, 70, 229)" stroke-width="2"/>\n'
    
    # 数据点
    dots_svg = ""
    for j, v in enumerate(values):
        p = get_point(360 * j / n, r * v / 5)
        dots_svg += f'  <circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="4" fill="rgb(79, 70, 229)"/>\n'
    
    # 标签
    labels_svg = ""
    for j, cat in enumerate(categories):
        p = get_point(360 * j / n, r + 25)
        labels_svg += f'  <text x="{p[0]:.1f}" y="{p[1]:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="#64748b">{cat}</text>\n'
    
    # 分数标签
    score_labels = ""
    for j, v in enumerate(values):
        p = get_point(360 * j / n, r * v / 5 - 15)
        score_labels += f'  <text x="{p[0]:.1f}" y="{p[1]:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="10" fill="#4f46e5" font-weight="bold">{v:.1f}</text>\n'
    
    return f'''<svg viewBox="0 0 {width} {height}" style="max-width: {width}px; width: 100%; height: auto;">
{grid_svg}
{axis_svg}
{data_svg}
{dots_svg}
{score_labels}
{labels_svg}
</svg>'''


def generate_bar_svg(scores: dict, width: int = 500, height: int = 300) -> str:
    """生成柱状图 SVG"""
    categories = list(scores.keys())
    values = list(scores.values())
    n = len(categories)
    
    margin = {'top': 20, 'right': 20, 'bottom': 60, 'left': 50}
    chart_w = width - margin['left'] - margin['right']
    chart_h = height - margin['top'] - margin['bottom']
    
    colors = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
    
    bars_svg = ""
    bar_w = chart_w / n * 0.6
    gap = chart_w / n
    
    for j, v in enumerate(values):
        x = margin['left'] + gap * j + (gap - bar_w) / 2
        bar_h = chart_h * v / 5
        y = margin['top'] + chart_h - bar_h
        bars_svg += f'  <rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{colors[j % len(colors)]}" rx="4"/>\n'
        bars_svg += f'  <text x="{x + bar_w/2:.1f}" y="{y - 5:.1f}" text-anchor="middle" font-size="11" fill="#1e293b" font-weight="bold">{v:.1f}</text>\n'
    
    # Y 轴刻度
    y_axis_svg = ""
    for i in range(0, 6):
        y = margin['top'] + chart_h * (1 - i / 5)
        y_axis_svg += f'  <line x1="{margin["left"]}" y1="{y:.1f}" x2="{width - margin["right"]}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>\n'
        y_axis_svg += f'  <text x="{margin["left"] - 5:.1f}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="#64748b">{i}</text>\n'
    
    # X 轴标签
    x_labels_svg = ""
    for j, cat in enumerate(categories):
        x = margin['left'] + gap * j + gap / 2
        x_labels_svg += f'  <text x="{x:.1f}" y="{height - margin["bottom"] + 20:.1f}" text-anchor="middle" font-size="10" fill="#64748b" transform="rotate(-45 {x:.1f} {height - margin["bottom"] + 20:.1f})">{cat}</text>\n'
    
    return f'''<svg viewBox="0 0 {width} {height}" style="max-width: {width}px; width: 100%; height: auto;">
{y_axis_svg}
{bars_svg}
{x_labels_svg}
</svg>'''


def generate_report(result_file: str, output_file: str = None):
    """生成 HTML 报告"""
    
    # 加载评测结果
    with open(result_file, 'r', encoding='utf-8') as f:
        result = json.load(f)
    
    # 提取维度得分
    dim_scores = {}
    for dim, score_dict in result.get('dimension_scores', {}).items():
        dim_scores[dim] = score_dict.get('overall', 0)
    
    # 生成图表
    radar_svg = generate_radar_svg(dim_scores)
    bar_svg = generate_bar_svg(dim_scores)
    
    # 获取总体评分
    overall = result.get('overall', {})
    overall_score = overall.get('overall_score', 0)
    grade = overall.get('grade', 'N/A')
    
    # 生成 HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent 评测报告</title>
    <style>
        :root {{ --primary: #4f46e5; --success: #10b981; --warning: #f59e0b; --danger: #ef4444; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', system-ui, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 30px; }}
        .score-card {{ background: white; border-radius: 16px; padding: 30px; text-align: center; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .score-value {{ font-size: 72px; font-weight: bold; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .grade-badge {{ display: inline-block; padding: 8px 24px; border-radius: 999px; font-size: 24px; font-weight: bold; margin-top: 10px; }}
        .grade-S {{ background: #fbbf24; color: white; }}
        .grade-A {{ background: #10b981; color: white; }}
        .grade-B {{ background: #3b82f6; color: white; }}
        .grade-C {{ background: #f59e0b; color: white; }}
        .grade-D {{ background: #ef4444; color: white; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .card h2 {{ font-size: 18px; color: var(--primary); margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
        .rec-item {{ padding: 12px; margin: 8px 0; border-left: 4px solid var(--primary); background: #f8fafc; border-radius: 4px; }}
        .rec-item.warning {{ border-left-color: var(--warning); }}
        .rec-item.danger {{ border-left-color: var(--danger); }}
        .footer {{ text-align: center; padding: 30px; color: #64748b; font-size: 14px; }}
        .benchmark-info {{ background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px; }}
        .metric {{ background: #f8fafc; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: var(--primary); }}
        .metric-label {{ font-size: 12px; color: #64748b; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Agent 能力评测报告</h1>
            <p><strong>对标大厂标准</strong> - AgentBench + GAIA + OpenCompass</p>
            <p>评测时间：{result.get('timestamp', 'N/A')}</p>
            <p>评测 Agent: {result.get('agent', 'N/A')}</p>
        </div>
        
        <div class="score-card">
            <div class="score-value">{overall_score:.1f}</div>
            <div class="grade-badge grade-{grade}"> 评级：{grade}</div>
            <p style="margin-top: 15px; color: #64748b;">综合评分 (0-5 分制)</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2> 多维度能力雷达图</h2>
                {radar_svg}
                <p style="font-size: 12px; color: #94a3b8; text-align: center; margin-top: 10px;">纯 SVG 绘制，零依赖</p>
            </div>
            <div class="card">
                <h2> 维度得分对比</h2>
                {bar_svg}
                <p style="font-size: 12px; color: #94a3b8; text-align: center; margin-top: 10px;">纯 SVG 绘制，零依赖</p>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 30px;">
            <h2> 评测基准说明</h2>
            <div class="benchmark-info">
                <strong>任务规划</strong> (对标 AgentBench): 评测任务分解、依赖识别、执行规划能力<br>
                <strong>工具使用</strong> (对标 GAIA): 评测 API 调用、文件操作、多工具协作能力<br>
                <strong>多轮对话</strong> (对标 LiveBench): 评测上下文理解、指代消解、意图识别能力<br>
                <strong>代码能力</strong> (对标 HumanEval): 评测代码生成、调试、测试能力<br>
                <strong>知识应用</strong> (对标 MMLU): 评测知识检索、事实核查、领域知识应用能力
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 30px;">
            <h2> 改进建议</h2>
"""
    
    suggestions = result.get('suggestions', [])
    for suggestion in suggestions:
        rec_class = ""
        if "" in suggestion:
            rec_class = "danger"
        elif "" in suggestion:
            rec_class = "warning"
        html += f'            <div class="rec-item {rec_class}">{suggestion}</div>\n'
    
    html += """
        </div>
        
        <div class="card">
            <h2> 详细评测结果</h2>
            <div class="metric-grid">
"""
    
    # 添加各维度详细指标
    for dim, score_dict in result.get('dimension_scores', {}).items():
        score = score_dict.get('overall', 0)
        html += f'''
                <div class="metric">
                    <div class="metric-value">{score:.1f}</div>
                    <div class="metric-label">{dim}</div>
                </div>
'''
    
    html += f"""
            </div>
        </div>
        
        <div class="footer">
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Agent 评测系统 v1.0</p>
            <p style="margin-top: 10px;">对标：AgentBench (任务规划) | GAIA (工具使用) | LiveBench (对话) | HumanEval (代码) | MMLU (知识)</p>
        </div>
    </div>
</body>
</html>
"""
    
    # 保存报告
    if not output_file:
        output_file = Path(result_file).parent / f"agent_eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description="生成 Agent 评测报告")
    parser.add_argument("--result", type=str, required=True,
                        help="评测结果 JSON 文件路径")
    parser.add_argument("--output", type=str, default=None,
                        help="输出 HTML 文件路径")
    
    args = parser.parse_args()
    
    output_file = generate_report(args.result, args.output)
    
    print(f" 报告已生成：{output_file}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
