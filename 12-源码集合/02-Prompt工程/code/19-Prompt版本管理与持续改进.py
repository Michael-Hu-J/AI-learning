# prompt_rollback.py
import yaml
import subprocess
from datetime import datetime

def rollback_prompt(prompt_id: str, target_version: str, reason: str):
    """回滚 Prompt 到指定版本"""
    from_path = f"prompts/{prompt_id}/history/{target_version}.md"
    to_path = f"prompts/{prompt_id}/prompt.md"
    subprocess.run(["cp", from_path, to_path], check=True)

    result = subprocess.run(
        ["python", "-m", "pytest", f"tests/{prompt_id}/", "-v"],
        capture_output=True,
    )
    if result.returncode == 0:
        log = {
            "prompt_id": prompt_id,
            "to_version": target_version,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "test_result": "pass",
        }
        with open(f"logs/rollback_{prompt_id}.yaml", "a") as f:
            yaml.dump(log, f)
        print(f"✅ 回滚到 {target_version} 成功")
    else:
        print("❌ 回滚后测试未通过，需人工介入")

# rollback_prompt("customer-service-reply", "v2.0-20260120", "v3 上线后满意度下降")

def notify_downstream(prompt_id, old_version, new_version, changes):
    """Prompt 变更后通知所有下游消费方"""
    consumers = get_consumers(prompt_id)  # 从配置文件读取
    for consumer in consumers:
        send_notification(
            to=consumer["channel"],
            message=f"""
📢 Prompt 变更通知
- Prompt: {prompt_id}
- 版本: {old_version} → {new_version}
- 变更: {changes}
- 影响: {consumer['impact_description']}
- 行动: {consumer['action_required']}
            """
        )

def monthly_prompt_metrics():
    """月度 Prompt 改进度量"""
    return {
        "prompt_count": 15,                    # 管理的 Prompt 总数
        "version_changes": 23,                 # 本月变更次数
        "avg_improvement_per_change": "+3.2%", # 平均每次变更提升
        "regression_count": 1,                 # 回归次数（改坏了的次数）
        "rollback_count": 2,                   # 回滚次数
        "time_to_detect": "2h",                # 从改坏到发现的时间
        "time_to_fix": "4h",                   # 从发现到修复的时间
        "test_coverage": "92%",                # Prompt 测试覆盖率
        "ci_pass_rate": "96%",                 # CI 通过率
    }

# prompt_diff.py
import yaml
import subprocess
from difflib import unified_diff

def compare_prompts(old_path, new_path, test_set_path):
    """对比两个版本的 Prompt 和效果"""
    # 1. 文本差异
    with open(old_path) as f:
        old_content = f.read()
    with open(new_path) as f:
        new_content = f.read()
    
    diff = list(unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        fromfile="old_version",
        tofile="new_version",
        lineterm=""
    ))
    print("=== 文本差异 ===")
    print("\n".join(diff))
    
    # 2. 效果对比
    with open(test_set_path) as f:
        test_set = yaml.safe_load(f)
    
    old_metrics = evaluate_prompt(old_path, test_set)
    new_metrics = evaluate_prompt(new_path, test_set)
    
    print("\n=== 效果对比 ===")
    for key in old_metrics:
        old_val = old_metrics[key]
        new_val = new_metrics[key]
        change = new_val - old_val if isinstance(old_val, (int, float)) else "N/A"
        arrow = "↑" if change > 0 else ("↓" if change < 0 else "→")
        print(f"{key}: {old_val} → {new_val} {arrow}")

def evaluate_prompt(prompt_path, test_set):
    """用测试集评估 Prompt"""
    with open(prompt_path) as f:
        prompt = f.read()
    
    results = {"format_accuracy": 0, "content_coverage": 0, "accuracy": 0, "hallucination_rate": 0}
    total = len(test_set["test_cases"])
    
    for case in test_set["test_cases"]:
        response = call_llm(prompt, case["input"])
        if check_format(response, case):
            results["format_accuracy"] += 1
        if check_content(response, case):
            results["content_coverage"] += 1
        if check_accuracy(response, case):
            results["accuracy"] += 1
        if check_hallucination(response):
            results["hallucination_rate"] += 1
    
    # 转换为百分比
    for key in results:
        results[key] = round(results[key] / total * 100, 1)
    
    return results

# prompt_regression.py
import pytest
import yaml
import subprocess
from datetime import datetime

class PromptRegressionTest:
    """Prompt 回归测试框架"""
    
    def __init__(self, prompt_path, test_suite_path):
        with open(prompt_path) as f:
            self.prompt = f.read()
        with open(test_suite_path) as f:
            self.test_suite = yaml.safe_load(f)
        self.results = []
    
    def run_all(self):
        """运行所有测试用例"""
        for case in self.test_suite["test_cases"]:
            result = self.run_case(case)
            self.results.append(result)
        return self.generate_report()
    
    def run_case(self, case):
        """运行单个测试用例"""
        response = self.call_llm(case["input"])
        passed = True
        failures = []
        
        # 检查关键词
        if "expected_keywords" in case:
            for kw in case["expected_keywords"]:
                if kw not in response:
                    passed = False
                    failures.append(f"缺少关键词: {kw}")
        
        # 检查不应包含的内容
        if "should_not_contain" in case:
            for text in case["should_not_contain"]:
                if text in response:
                    passed = False
                    failures.append(f"不应包含: {text}")
        
        return {
            "case_id": case["id"],
            "passed": passed,
            "failures": failures,
            "response_length": len(response),
        }
    
    def generate_report(self):
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        pass_rate = round(passed / total * 100, 1)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate}%",
            "failed_cases": [r for r in self.results if not r["passed"]],
        }
        
        # 保存报告
        with open(f"reports/regression_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml", "w") as f:
            yaml.dump(report, f, allow_unicode=True)
        
        return report
    
    def call_llm(self, input_text):
        """调用 LLM（简化版）"""
        # 实际项目中替换为真实的 API 调用
        pass

# scripts/check_quality_gate.py
import argparse
import yaml

def check_quality_gate(report_path, threshold):
    """检查质量门禁"""
    with open(report_path) as f:
        report = yaml.safe_load(f)
    
    pass_rate = report["pass_rate"].replace("%", "")
    pass_rate = float(pass_rate) / 100
    
    if pass_rate >= threshold:
        print(f"✅ 质量门禁通过: {pass_rate*100}% >= {threshold*100}%")
        return True
    else:
        print(f"❌ 质量门禁未通过: {pass_rate*100}% < {threshold*100}%")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.95)
    args = parser.parse_args()
    
    success = check_quality_gate("reports/latest.yaml", args.threshold)
    exit(0 if success else 1)

# prompt_dashboard.py
import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

class PromptDashboard:
    """Prompt 效果追踪看板"""
    
    def __init__(self, metrics_csv_path):
        self.metrics = []
        with open(metrics_csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.metrics.append(row)
    
    def plot_accuracy_trend(self):
        """绘制准确率趋势图"""
        dates = [row["date"] for row in self.metrics]
        accuracies = [float(row["accuracy"]) for row in self.metrics]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, accuracies, marker='o', linewidth=2)
        plt.xlabel("日期")
        plt.ylabel("准确率 (%)")
        plt.title("Prompt 准确率趋势")
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig("reports/accuracy_trend.png")
    
    def generate_weekly_report(self):
        """生成周报"""
        # 取最近 7 天的数据
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        recent = [m for m in self.metrics if m["date"] >= cutoff]
        
        if not recent:
            return "本周无数据"
        
        latest = recent[-1]
        first = recent[0]
        
        report = f"""
## 本周 Prompt 效果报告

- 当前版本: {latest['prompt_version']}
- 准确率: {latest['accuracy']}% (上周: {first['accuracy']}%)
- 格式正确率: {latest['format_accuracy']}%
- 幻觉率: {latest['hallucination_rate']}%
- 平均响应时间: {latest['response_time']}s
- 本周变更次数: {len(recent)}
"""
        return report
