from datetime import datetime
import json

class TestReportGenerator:
    """测试报告生成器"""
    
    def generate_one_page_summary(self, results: dict) -> str:
        """生成一页纸摘要"""
        conclusion = '✅ 可以上线' if results['overall_pass'] else (
            '⚠️ 有条件上线' if results.get('conditional_pass') else '❌ 不能上线'
        )
        return f"""
# 测试报告摘要

**项目**：{results.get('project', 'AI客服系统')}
**测试日期**：{datetime.now().strftime('%Y-%m-%d')}
**测试人员**：测试员周周
**Prompt 版本**：{results.get('prompt_version', 'v1.0')}
**模型**：{results.get('model', 'GPT-4')}

## 测试结论
{conclusion}

## 核心指标
| 指标 | 结果 | 目标 | 状态 |
|------|------|------|------|
| 功能通过率 | {results['functional_pass_rate']*100:.1f}% | ≥95% | {'✅' if results['functional_pass_rate'] >= 0.95 else '❌'} |
| 语义准确率 | {results['semantic_accuracy']*100:.1f}% | ≥85% | {'✅' if results['semantic_accuracy'] >= 0.85 else '❌'} |
| 安全拦截率 | {results['security_intercept_rate']*100:.1f}% | 100% | {'✅' if results['security_intercept_rate'] >= 1.0 else '❌'} |
| 幻觉率 | {results.get('hallucination_rate', 0)*100:.1f}% | ≤5% | {'✅' if results.get('hallucination_rate', 0) <= 0.05 else '❌'} |
| 响应时间 P95 | {results.get('p95_latency', 0):.1f}s | ≤3s | {'✅' if results.get('p95_latency', 99) <= 3 else '❌'} |

## 风险等级
{results['risk_level']} — {results.get('risk_summary', '')}

## 上线建议
{results['recommendation']}

## 版本对比（如有）
- 回归用例：{len(results.get('regressions', []))} 条
- 修复用例：{len(results.get('fixes', []))} 条
"""

    def generate_full_report(self, results: dict) -> str:
        """生成完整测试报告"""
        report = self.generate_one_page_summary(results)
        
        report += f"""
---

## 测试概述

### 测试范围
**已测试**：{chr(10).join(f'- {item}' for item in results['tested_items'])}
**未测试**：{chr(10).join(f'- {item}' for item in results['untested_items'])}

### 测试环境
- **硬件**：{results['hardware']}
- **软件**：{results['software']}
- **测试用例数**：{results.get('total_cases', 'N/A')}（P0: {results.get('p0_cases', 'N/A')}）
"""
        
        report += """
---

## 详细测试结果

### 功能测试
| 模块 | 用例数 | 通过 | 失败 | 通过率 |
|------|--------|------|------|--------|
"""
        for module, stats in results['functional_results'].items():
            rate = stats['passed'] / stats['total'] * 100
            report += f"| {module} | {stats['total']} | {stats['passed']} | {stats['failed']} | {rate:.1f}% |\n"
        
        if results.get('regressions'):
            report += f"\n### 回归退化用例\n"
            for case_id in results['regressions']:
                report += f"- {case_id}\n"
        
        if results.get('bad_cases'):
            report += f"\n### Top Bad Case 样例\n"
            for case in results['bad_cases'][:10]:
                report += f"""
**{case['id']}**: {case['input']}
- 预期：{case['expected']}
- 实际：{case['actual']}
- 根因：{case['root_cause']}
"""
        
        return report

import matplotlib.pyplot as plt
import pandas as pd

def generate_trend_report(history: list, output_dir: str = "./reports"):
    """
    生成趋势报告
    history: 历次测试结果的列表，每个元素包含日期和各项指标
    """
    df = pd.DataFrame(history)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # 通过率趋势
    plt.figure(figsize=(10, 5))
    plt.plot(df['date'], df['functional_pass_rate'] * 100, marker='o', label='功能通过率')
    plt.plot(df['date'], df['semantic_accuracy'] * 100, marker='s', label='语义准确率')
    plt.axhline(y=95, color='r', linestyle='--', label='目标线(95%)')
    plt.xlabel('日期')
    plt.ylabel('通过率 (%)')
    plt.title('测试通过率趋势')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/pass_rate_trend.png')
    
    # 幻觉率趋势
    plt.figure(figsize=(10, 5))
    plt.plot(df['date'], df['hallucination_rate'] * 100, marker='^', color='orange')
    plt.axhline(y=5, color='r', linestyle='--', label='目标线(5%)')
    plt.xlabel('日期')
    plt.ylabel('幻觉率 (%)')
    plt.title('幻觉率趋势')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{output_dir}/hallucination_trend.png')
    
    # 响应时间趋势
    plt.figure(figsize=(10, 5))
    plt.plot(df['date'], df['p95_latency'], marker='d', color='green')
    plt.axhline(y=3, color='r', linestyle='--', label='目标线(3s)')
    plt.xlabel('日期')
    plt.ylabel('P95 响应时间 (s)')
    plt.title('P95 响应时间趋势')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{output_dir}/latency_trend.png')
    
    return f"趋势报告已生成，保存在 {output_dir}/ 目录下"
