#!/usr/bin/env python3
"""
Agent测试数据集审计脚本

功能：
1. 检查 benchmark JSON 文件的完整性和一致性
2. 统计各维度任务数量、难度分布
3. 检测重复 ID、缺失字段
4. 生成审计报告

用法：
    python3 scripts/audit_dataset.py --benchmarks benchmarks/ --output results/audits/audit_report.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import argparse


class DatasetAuditor:
    """数据集审计器"""
    
    # 各维度必需字段
    REQUIRED_FIELDS = {
        "task_planning": ["id", "name", "description", "goal", "subtasks", "dependencies", "difficulty"],
        "tool_use": ["id", "name", "description", "goal", "tools", "difficulty"],
        "dialogue": ["id", "name", "description", "goal", "turns", "difficulty"],
        "coding": ["id", "name", "description", "goal", "input", "difficulty"],
        "knowledge": ["id", "name", "description", "goal", "input", "difficulty"],
    }
    
    VALID_DIFFICULTIES = ["easy", "medium", "hard"]
    
    def __init__(self, benchmarks_dir: str):
        self.benchmarks_dir = Path(benchmarks_dir)
        self.issues: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}
        
    def audit(self) -> Dict[str, Any]:
        """执行完整审计"""
        print(f" 开始审计数据集: {self.benchmarks_dir}")
        print("=" * 60)
        
        # 1. 检查目录结构
        self._check_directory_structure()
        
        # 2. 审计每个维度的任务文件
        dimensions = {}
        for dim, fields in self.REQUIRED_FIELDS.items():
            tasks_file = self.benchmarks_dir / dim / "tasks.json"
            if tasks_file.exists():
                dim_result = self._audit_dimension(dim, tasks_file, fields)
                dimensions[dim] = dim_result
                print(f"   {dim}: {dim_result['total_tasks']} 条任务")
            else:
                self.issues.append({
                    "type": "missing_file",
                    "dimension": dim,
                    "message": f"任务文件不存在: {tasks_file}",
                    "severity": "error",
                })
                print(f"   {dim}: 文件不存在")
        
        # 3. 检查跨维度一致性
        self._check_cross_dimension_consistency(dimensions)
        
        # 4. 生成统计报告
        self.stats = self._generate_stats(dimensions)
        
        # 5. 打印审计摘要
        self._print_summary()
        
        return {
            "audit_timestamp": datetime.now().isoformat(),
            "benchmarks_dir": str(self.benchmarks_dir),
            "dimensions": dimensions,
            "stats": self.stats,
            "issues": self.issues,
            "issue_count": len(self.issues),
        }
    
    def _check_directory_structure(self):
        """检查基准目录结构"""
        if not self.benchmarks_dir.exists():
            self.issues.append({
                "type": "missing_directory",
                "message": f"基准目录不存在: {self.benchmarks_dir}",
                "severity": "error",
            })
            return
        
        expected_dirs = list(self.REQUIRED_FIELDS.keys())
        actual_dirs = [d.name for d in self.benchmarks_dir.iterdir() if d.is_dir()]
        
        for expected in expected_dirs:
            if expected not in actual_dirs:
                self.issues.append({
                    "type": "missing_dimension_dir",
                    "dimension": expected,
                    "message": f"维度目录不存在: {self.benchmarks_dir / expected}",
                    "severity": "warning",
                })
    
    def _audit_dimension(self, dim: str, tasks_file: Path, required_fields: List[str]) -> Dict[str, Any]:
        """审计单个维度的任务文件"""
        result = {
            "dimension": dim,
            "file": str(tasks_file),
            "total_tasks": 0,
            "by_difficulty": {},
            "issues": [],
        }
        
        # 加载 JSON
        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.issues.append({
                "type": "invalid_json",
                "dimension": dim,
                "message": f"JSON 解析失败: {e}",
                "severity": "error",
            })
            return result
        
        tasks = data.get("tasks", [])
        result["total_tasks"] = len(tasks)
        
        # 检查 ID 唯一性
        ids = [t.get("id") for t in tasks]
        duplicate_ids = [id for id in ids if ids.count(id) > 1]
        if duplicate_ids:
            self.issues.append({
                "type": "duplicate_id",
                "dimension": dim,
                "ids": list(set(duplicate_ids)),
                "severity": "error",
            })
        
        # 检查每个任务的字段
        for i, task in enumerate(tasks):
            task_id = task.get("id", f"unknown_{i}")
            
            # 检查必需字段
            for field in required_fields:
                if field not in task:
                    self.issues.append({
                        "type": "missing_field",
                        "dimension": dim,
                        "task_id": task_id,
                        "field": field,
                        "severity": "warning",
                    })
            
            # 检查难度值
            difficulty = task.get("difficulty", "")
            if difficulty and difficulty not in self.VALID_DIFFICULTIES:
                self.issues.append({
                    "type": "invalid_difficulty",
                    "dimension": dim,
                    "task_id": task_id,
                    "value": difficulty,
                    "severity": "warning",
                })
            
            # 统计难度分布
            if difficulty:
                if difficulty not in result["by_difficulty"]:
                    result["by_difficulty"][difficulty] = 0
                result["by_difficulty"][difficulty] += 1
        
        return result
    
    def _check_cross_dimension_consistency(self, dimensions: Dict):
        """检查跨维度一致性"""
        # 检查难度值是否在各维度中一致使用
        all_difficulties = set()
        for dim, result in dimensions.items():
            all_difficulties.update(result.get("by_difficulty", {}).keys())
        
        invalid = all_difficulties - set(self.VALID_DIFFICULTIES)
        if invalid:
            self.issues.append({
                "type": "inconsistent_difficulty",
                "values": list(invalid),
                "severity": "warning",
            })
    
    def _generate_stats(self, dimensions: Dict) -> Dict[str, Any]:
        """生成统计摘要"""
        total = sum(d["total_tasks"] for d in dimensions.values())
        by_difficulty = {}
        for d in dimensions.values():
            for diff, count in d.get("by_difficulty", {}).items():
                by_difficulty[diff] = by_difficulty.get(diff, 0) + count
        
        return {
            "total_tasks": total,
            "dimensions_count": len(dimensions),
            "by_difficulty": by_difficulty,
            "tasks_per_dimension": {dim: d["total_tasks"] for dim, d in dimensions.items()},
        }
    
    def _print_summary(self):
        """打印审计摘要"""
        errors = [i for i in self.issues if i.get("severity") == "error"]
        warnings = [i for i in self.issues if i.get("severity") == "warning"]
        
        print("\n" + "=" * 60)
        print(" 审计摘要")
        print("=" * 60)
        print(f"总任务数: {self.stats.get('total_tasks', 0)}")
        print(f"维度数: {self.stats.get('dimensions_count', 0)}")
        print(f"难度分布: {self.stats.get('by_difficulty', {})}")
        print(f"\n问题数: {len(self.issues)} (错误: {len(errors)}, 警告: {len(warnings)})")
        
        if errors:
            print("\n 错误:")
            for issue in errors:
                print(f"  - [{issue['dimension']}] {issue['message']}")
        
        if warnings:
            print(f"\n  警告 (前10条):")
            for issue in warnings[:10]:
                dim = issue.get('dimension', 'unknown')
                msg = issue.get('message', issue.get('field', ''))
                print(f"  - [{dim}] {msg}")


def main():
    parser = argparse.ArgumentParser(description="Agent测试数据集审计")
    parser.add_argument("--benchmarks", default="benchmarks/", help="基准目录路径")
    parser.add_argument("--output", default=None, help="审计报告输出路径")
    
    args = parser.parse_args()
    
    auditor = DatasetAuditor(args.benchmarks)
    report = auditor.audit()
    
    # 保存报告
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n💾 审计报告已保存: {output_path}")
    
    # 返回状态码
    errors = [i for i in report["issues"] if i.get("severity") == "error"]
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
