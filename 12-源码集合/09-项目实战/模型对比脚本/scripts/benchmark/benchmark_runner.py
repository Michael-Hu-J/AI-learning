"""
模型评测执行引擎（curl 版）- 新模型上线对比测试
作者：测试员周周（14 年测试经验）
使用方法：python benchmark_runner.py --model current  或  --model new
"""

import json
import time
import os
import sys
import argparse
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class BenchmarkConfig:
    """评测配置"""
    model_name: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 120
    repeat_count: int = 1


@dataclass
class TaskResult:
    """单条任务结果"""
    task_id: str
    category: str
    dimension: str
    difficulty: str
    model: str
    input: str
    output: str
    passed: bool
    execution_time: float
    tokens_used: int
    error: str = ""
    timestamp: str = ""
    notes: str = ""


class BenchmarkRunner:
    """评测执行器（使用 curl 调用 API）"""
    
    def __init__(self, config: BenchmarkConfig, tasks_file: str = None):
        self.config = config
        self.tasks_file = tasks_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'tasks', 'benchmark_tasks.json'
        )
        self.results: List[TaskResult] = []
    
    def _load_tasks(self) -> List[Dict]:
        """加载测试任务"""
        with open(self.tasks_file, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        print(f"✅ 加载 {len(tasks)} 条测试任务")
        return tasks
    
    def _call_model(self, prompt: str) -> Dict:
        """使用 curl 调用模型 API"""
        payload = json.dumps({
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }, ensure_ascii=False)
        
        try:
            result = subprocess.run(
                [
                    "curl", "-s", "--max-time", str(self.config.timeout),
                    "-X", "POST",
                    f"{self.config.base_url}/chat/completions",
                    "-H", "Content-Type: application/json",
                    "-H", f"Authorization: Bearer {self.config.api_key}",
                    "-d", payload,
                ],
                capture_output=True,
                text=True,
                timeout=self.config.timeout + 10,
            )
            
            if result.returncode != 0:
                return {"content": "", "tokens": 0, "error": f"curl error: {result.stderr}"}
            
            resp = json.loads(result.stdout)
            
            if "error" in resp:
                return {"content": "", "tokens": 0, "error": resp["error"].get("message", str(resp["error"]))}
            
            content = resp["choices"][0]["message"]["content"]
            tokens = resp.get("usage", {}).get("total_tokens", 0)
            return {"content": content, "tokens": tokens, "error": ""}
            
        except subprocess.TimeoutExpired:
            return {"content": "", "tokens": 0, "error": "请求超时"}
        except Exception as e:
            return {"content": "", "tokens": 0, "error": str(e)}
    
    def _evaluate_result(self, task: Dict, output: str) -> tuple:
        """评估结果是否通过"""
        if not output:
            return False, "模型返回为空"
        
        if len(output) < 20:
            return False, "输出过短，可能未完整回答"
        
        criteria = task.get("evaluation_criteria", [])
        passed_count = 0
        failed_criteria = []
        
        for criterion in criteria:
            if self._check_criterion(criterion, output):
                passed_count += 1
            else:
                failed_criteria.append(criterion)
        
        threshold = max(1, len(criteria) * 0.6) if criteria else 1
        passed = passed_count >= threshold
        
        notes = ""
        if failed_criteria:
            notes = f"未通过标准: {', '.join(failed_criteria)}"
        
        return passed, notes
    
    def _check_criterion(self, criterion: str, output: str) -> bool:
        """检查单个评价标准"""
        output_lower = output.lower()
        
        keyword_map = {
            "用例数量": ["用例", "case", "test"],
            "覆盖": ["覆盖", "正常", "异常", "边界", "功能"],
            "前置条件": ["前置", "前提", "准备", "before"],
            "预期结果": ["预期", "assert", "验证", "should"],
            "完整性": ["完整", "全面", "覆盖"],
            "可执行性": ["执行", "运行", "步骤"],
            "语法正确": ["import", "def ", "class ", "assert"],
            "断言完整": ["assert", "验证", "expect"],
            "可执行": ["import", "def ", "assert"],
            "目标合理": ["QPS", "响应时间", "目标", "TPS"],
            "策略可行": ["并发", "阶梯", "压测", "策略"],
            "指标完整": ["监控", "指标", "CPU", "内存"],
            "通过标准": ["通过", "标准", "阈值"],
            "瓶颈定位": ["瓶颈", "原因", "问题"],
            "根因分析": ["根因", "原因", "导致"],
            "建议可执行": ["建议", "优化", "改进"],
            "结构完整": ["概述", "统计", "分析", "建议"],
            "分析深入": ["分析", "原因", "问题"],
            "建议合理": ["建议", "优化", "改进"],
            "覆盖全面": ["覆盖", "全面", "完整"],
            "要点准确": ["测试", "检查", "验证"],
            "分类合理": ["功能", "边界", "异常", "安全"],
            "建议具体": ["建议", "改进", "优化"],
            "有代码示例": ["```", "code", "示例"],
        }
        
        for keyword, synonyms in keyword_map.items():
            if keyword in criterion:
                return any(s in output_lower for s in synonyms)
        
        return True
    
    def run_single_task(self, task: Dict) -> TaskResult:
        """执行单条任务"""
        start_time = time.time()
        result = self._call_model(task["input"])
        execution_time = time.time() - start_time
        
        passed, notes = self._evaluate_result(task, result["content"])
        
        return TaskResult(
            task_id=task["task_id"],
            category=task["category"],
            dimension=task["dimension"],
            difficulty=task["difficulty"],
            model=self.config.model_name,
            input=task["input"],
            output=result["content"],
            passed=passed,
            execution_time=round(execution_time, 2),
            tokens_used=result["tokens"],
            error=result["error"],
            timestamp=datetime.now().isoformat(),
            notes=notes,
        )
    
    def run_all(self, task_filter: str = None, max_tasks: int = None):
        """批量执行所有任务"""
        tasks = self._load_tasks()
        
        if task_filter:
            tasks = [t for t in tasks if task_filter in t.get("category", "") 
                     or task_filter in t.get("dimension", "")]
        
        if max_tasks:
            tasks = tasks[:max_tasks]
        
        total = len(tasks)
        print(f"\n🚀 开始评测: {self.config.model_name}")
        print(f"   模型: {self.config.model}")
        print(f"   任务数: {total}")
        print(f"   重复次数: {self.config.repeat_count}")
        print("-" * 60)
        
        all_results = []
        
        for round_idx in range(self.config.repeat_count):
            if self.config.repeat_count > 1:
                print(f"\n📌 第 {round_idx + 1}/{self.config.repeat_count} 轮")
            
            for i, task in enumerate(tasks, 1):
                print(f"[{i:2d}/{total}] {task['task_id']} ({task['category']}, {task['difficulty']}) ... ", end="", flush=True)
                
                result = self.run_single_task(task)
                all_results.append(result)
                
                if result.error:
                    print(f"❌ 错误: {result.error[:50]}")
                elif result.passed:
                    print(f"✅ ({result.execution_time:.1f}s, {result.tokens_used} tokens)")
                else:
                    print(f"❌ ({result.execution_time:.1f}s) {result.notes[:40]}")
                
                if i % 5 == 0:
                    passed = sum(1 for r in all_results if r.passed)
                    print(f"   → 进度: {passed}/{len(all_results)} 通过 ({passed/len(all_results)*100:.0f}%)")
        
        self.results = all_results
        print("-" * 60)
        print(f"✅ 评测完成: {self.config.model_name}")
    
    def generate_report(self) -> Dict:
        """生成评测报告"""
        if not self.results:
            return {"error": "No results yet"}
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        
        by_dimension = {}
        for r in self.results:
            if r.dimension not in by_dimension:
                by_dimension[r.dimension] = {"total": 0, "passed": 0}
            by_dimension[r.dimension]["total"] += 1
            if r.passed:
                by_dimension[r.dimension]["passed"] += 1
        
        by_category = {}
        for r in self.results:
            if r.category not in by_category:
                by_category[r.category] = {"total": 0, "passed": 0}
            by_category[r.category]["total"] += 1
            if r.passed:
                by_category[r.category]["passed"] += 1
        
        by_difficulty = {}
        for r in self.results:
            if r.difficulty not in by_difficulty:
                by_difficulty[r.difficulty] = {"total": 0, "passed": 0}
            by_difficulty[r.difficulty]["total"] += 1
            if r.passed:
                by_difficulty[r.difficulty]["passed"] += 1
        
        avg_time = sum(r.execution_time for r in self.results) / total
        avg_tokens = sum(r.tokens_used for r in self.results) / total
        
        failed_cases = [r for r in self.results if not r.passed]
        
        return {
            "model": self.config.model_name,
            "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": f"{passed/total*100:.1f}%",
                "avg_time": f"{avg_time:.1f}s",
                "avg_tokens": int(avg_tokens),
            },
            "by_dimension": by_dimension,
            "by_category": by_category,
            "by_difficulty": by_difficulty,
            "failed_cases": [
                {"task_id": r.task_id, "category": r.category, "dimension": r.dimension, "notes": r.notes}
                for r in failed_cases
            ],
            "all_results": [asdict(r) for r in self.results],
        }
    
    def print_report(self):
        """打印评测报告"""
        report = self.generate_report()
        s = report["summary"]
        
        print("\n" + "=" * 60)
        print(f"📊 评测报告: {report['model']}")
        print("=" * 60)
        print(f"测试日期: {report['test_date']}")
        print(f"总任务: {s['total']}")
        print(f"通过: {s['passed']}  ✅")
        print(f"失败: {s['failed']}  ❌")
        print(f"通过率: {s['pass_rate']}")
        print(f"平均耗时: {s['avg_time']}")
        print(f"平均 Token: {s['avg_tokens']}")
        
        print("\n--- 按维度 ---")
        for d, stats in report["by_dimension"].items():
            rate = stats["passed"] / stats["total"] * 100
            print(f"  {d}: {rate:.0f}% ({stats['passed']}/{stats['total']})")
        
        print("\n--- 按类别 ---")
        for c, stats in report["by_category"].items():
            rate = stats["passed"] / stats["total"] * 100
            print(f"  {c}: {rate:.0f}% ({stats['passed']}/{stats['total']})")
        
        print("\n--- 按难度 ---")
        for d, stats in report["by_difficulty"].items():
            rate = stats["passed"] / stats["total"] * 100
            print(f"  {d}: {rate:.0f}% ({stats['passed']}/{stats['total']})")
        
        if report["failed_cases"]:
            print(f"\n--- 失败用例 ({len(report['failed_cases'])} 条) ---")
            for r in report["failed_cases"]:
                print(f"  {r['task_id']} ({r['category']}, {r['dimension']})")
                print(f"    → {r['notes']}")
        
        print("=" * 60)
    
    def save_results(self, filepath: str = None):
        """保存结果到 JSON 文件"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_safe = self.config.model.replace("/", "_")
            filepath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'results',
                f"benchmark_{model_safe}_{timestamp}.json"
            )
        
        report = self.generate_report()
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存: {filepath}")
        return filepath


def load_config(config_file: str = None) -> Dict:
    """加载模型配置"""
    if config_file is None:
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'models.yaml')
    
    try:
        import yaml
    except ImportError:
        print("❌ 缺少 yaml 库，请安装: pip install pyyaml")
        sys.exit(1)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def main():
    parser = argparse.ArgumentParser(description='模型评测执行引擎')
    parser.add_argument('--model', type=str, default='model1',
                        choices=['model1', 'model2'],
                        help='选择评测的模型 (model1=GLM-5.1, model2=DeepSeek-V4)')
    parser.add_argument('--filter', type=str, default=None,
                        help='过滤任务类别')
    parser.add_argument('--max-tasks', type=int, default=None,
                        help='最大任务数（用于快速验证）')
    parser.add_argument('--repeat', type=int, default=None,
                        help='重复次数')
    parser.add_argument('--output', type=str, default=None,
                        help='输出文件路径')
    
    args = parser.parse_args()
    
    config = load_config()
    model_config = config.get(f'{args.model}', config['model1'])
    
    # 支持从多个环境变量读取 API Key
    api_key = model_config.get('api_key', '')
    if not api_key:
        # 根据模型类型尝试不同环境变量
        env_vars = {
            'model1': ['GLM_API_KEY', 'DASHSCOPE_API_KEY'],
            'model2': ['DEEPSEEK_API_KEY'],
        }
        for env_var in env_vars.get(args.model, ['DASHSCOPE_API_KEY']):
            api_key = os.environ.get(env_var, '')
            if api_key:
                break
    
    if not api_key:
        print(f"❌ 未配置 API Key")
        print(f"   请设置环境变量: {', '.join(env_vars.get(args.model, ['DASHSCOPE_API_KEY']))}")
        sys.exit(1)
    
    benchmark_config = config.get('benchmark', {})
    bench = BenchmarkConfig(
        model_name=model_config['name'],
        model=model_config['model'],
        api_key=api_key,
        base_url=model_config.get('base_url', ''),
        temperature=model_config.get('temperature', 0.3),
        max_tokens=benchmark_config.get('max_tokens', 4096),
        timeout=benchmark_config.get('timeout', 120),
        repeat_count=args.repeat or benchmark_config.get('repeat_count', 1),
    )
    
    runner = BenchmarkRunner(bench)
    runner.run_all(
        task_filter=args.filter,
        max_tasks=args.max_tasks,
    )
    
    runner.print_report()
    runner.save_results(args.output)


if __name__ == '__main__':
    main()
