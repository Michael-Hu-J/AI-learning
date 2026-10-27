from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import numpy as np

class ModelEvaluator:
    """多维度模型评估器"""

    def __init__(self, model, X_test, y_test):
        self.model = model
        self.X_test = X_test
        self.y_test = y_test

    def evaluate_accuracy(self):
        """准确性评估"""
        y_pred = self.model.predict(self.X_test)
        y_proba = self.model.predict_proba(self.X_test)[:, 1] \
            if hasattr(self.model, 'predict_proba') else None

        return {
            'accuracy': accuracy_score(self.y_test, y_pred),
            'precision': precision_score(self.y_test, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(self.y_test, y_pred, average='weighted', zero_division=0),
            'f1': f1_score(self.y_test, y_pred, average='weighted', zero_division=0),
            'auc': roc_auc_score(self.y_test, y_proba) if y_proba is not None else None,
            'confusion_matrix': confusion_matrix(self.y_test, y_pred).tolist(),
            'per_class_report': classification_report(self.y_test, y_pred, output_dict=True)
        }

    def evaluate_robustness(self, noise_levels=[0.01, 0.05, 0.1]):
        """鲁棒性评估：测试不同噪声水平下的性能衰减"""
        base_acc = accuracy_score(self.y_test, self.model.predict(self.X_test))
        results = {}

        for level in noise_levels:
            X_noisy = self.X_test + np.random.normal(0, level, self.X_test.shape)
            noisy_acc = accuracy_score(self.y_test, self.model.predict(X_noisy))
            results[level] = {
                'accuracy': noisy_acc,
                'accuracy_drop': base_acc - noisy_acc,
                'robustness_score': noisy_acc / base_acc if base_acc > 0 else 0
            }

        return {'base_accuracy': base_acc, 'noise_results': results}

    def evaluate_fairness(self, X_test_df, sensitive_column):
        """公平性评估：按敏感属性分组比较"""
        groups = X_test_df.groupby(sensitive_column)
        group_metrics = {}

        for group_name, group_data in groups:
            indices = group_data.index
            y_true_group = self.y_test[indices]
            y_pred_group = self.model.predict(self.X_test.iloc[indices])
            group_metrics[group_name] = {
                'accuracy': accuracy_score(y_true_group, y_pred_group),
                'sample_size': len(group_data)
            }

        acc_values = [m['accuracy'] for m in group_metrics.values()]
        return {
            'group_metrics': group_metrics,
            'max_accuracy_gap': max(acc_values) - min(acc_values),
            'fairness_score': 1 - (max(acc_values) - min(acc_values))
        }

evaluator = ModelEvaluator(model, X_test, y_test)
acc_results = evaluator.evaluate_accuracy()
robust_results = evaluator.evaluate_robustness()
fair_results = evaluator.evaluate_fairness(X_test_df, 'city_tier')

print(f"F1 Score: {acc_results['f1']:.4f}")
print(f"鲁棒性分数: {robust_results['noise_results'][0.05]['robustness_score']:.4f}")
print(f"公平性分数: {fair_results['fairness_score']:.4f}")

import time
import psutil
import os

def evaluate_efficiency(model, X_test, num_iterations=100):
    """评估模型推理效率"""
    # 预热
    for _ in range(10):
        _ = model.predict(X_test[:1])

    # 单条推理延迟
    start = time.time()
    for i in range(num_iterations):
        _ = model.predict(X_test[i:i+1])
    single_latency = (time.time() - start) / num_iterations * 1000

    # 批量推理吞吐
    batch_size = 100
    start = time.time()
    _ = model.predict(X_test[:batch_size])
    batch_throughput = batch_size / (time.time() - start)

    # 内存占用
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / (1024 * 1024)

    return {
        'avg_latency_ms': single_latency,
        'batch_throughput_per_sec': batch_throughput,
        'memory_usage_mb': memory_mb,
        'efficiency_grade': 'high' if single_latency < 50 else 'medium' if single_latency < 200 else 'low'
    }

def generate_evaluation_report(model, X_test, y_test, X_test_df=None, sensitive_col=None):
    """生成完整的评估报告"""
    evaluator = ModelEvaluator(model, X_test, y_test)

    report = {
        'accuracy': evaluator.evaluate_accuracy(),
        'robustness': evaluator.evaluate_robustness(),
        'efficiency': evaluate_efficiency(model, X_test),
    }

    if X_test_df is not None and sensitive_col:
        report['fairness'] = evaluator.evaluate_fairness(X_test_df, sensitive_col)

    scores = []
    if 'f1' in report['accuracy']:
        scores.append(report['accuracy']['f1'])
    if 'robustness_score' in str(report['robustness']):
        avg_robust = np.mean([
            v['robustness_score'] for v in report['robustness']['noise_results'].values()
        ])
        scores.append(avg_robust)
    if 'fairness_score' in report.get('fairness', {}):
        scores.append(report['fairness']['fairness_score'])

    report['overall_score'] = np.mean(scores) if scores else 0
    report['recommendation'] = (
        '可以上线' if report['overall_score'] >= 0.8 else
        '需要改进' if report['overall_score'] >= 0.6 else
        '不建议上线'
    )
    return report

def validate_for_production(report, thresholds=None):
    """验证模型是否可以上线"""
    if thresholds is None:
        thresholds = {
            'min_f1': 0.75,
            'min_robustness': 0.7,
            'max_latency_ms': 500,
            'min_fairness': 0.8,
            'max_memory_mb': 512
        }

    checks = []
    f1 = report['accuracy'].get('f1', 0)
    checks.append({
        'name': '准确性(F1)', 'value': f1,
        'threshold': thresholds['min_f1'],
        'passed': f1 >= thresholds['min_f1']
    })

    robust = np.mean([
        v['robustness_score'] for v in report['robustness']['noise_results'].values()
    ])
    checks.append({
        'name': '鲁棒性', 'value': robust,
        'threshold': thresholds['min_robustness'],
        'passed': robust >= thresholds['min_robustness']
    })

    latency = report['efficiency']['avg_latency_ms']
    checks.append({
        'name': '推理延迟', 'value': latency,
        'threshold': thresholds['max_latency_ms'],
        'passed': latency <= thresholds['max_latency_ms']
    })

    if 'fairness' in report:
        fairness = report['fairness']['fairness_score']
        checks.append({
            'name': '公平性', 'value': fairness,
            'threshold': thresholds['min_fairness'],
            'passed': fairness >= thresholds['min_fairness']
        })

    all_passed = all(c['passed'] for c in checks)
    return {
        'checks': checks,
        'all_passed': all_passed,
        'recommendation': '可以上线' if all_passed else '需要整改后重新评估'
    }
