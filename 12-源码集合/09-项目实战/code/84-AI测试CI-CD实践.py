from great_expectations.dataset import PandasDataset

def validate_data(df, expectations_suite):
    """用Great Expectations验证数据质量"""
    dataset = PandasDataset.from_pandas(df)
    # 加载预定义的验证规则
    results = dataset.validate(expectation_suite=expectations_suite)
    
    success = results['success']
    stats = results['statistics']
    
    print(f"数据验证{'✅通过' if success else '❌失败'}")
    print(f"总规则数: {stats['evaluated_expectations']}")
    print(f"通过规则数: {stats['successful_expectations']}")
    print(f"通过率: {stats['successful_expectations']/stats['evaluated_expectations']:.1%}")
    
    return success

def evaluate_model(model, test_data, baseline_metrics):
    """评估模型并和基线对比"""
    X_test, y_test = test_data
    y_pred = model.predict(X_test)
    
    # 计算各项指标
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, average='weighted'),
        'recall': recall_score(y_test, y_pred, average='weighted'),
        'f1': f1_score(y_test, y_pred, average='weighted'),
    }
    
    # 和基线对比
    regression = {}
    for metric, value in metrics.items():
        baseline = baseline_metrics.get(metric, 0)
        regression[metric] = value - baseline
    
    # 检查是否有性能回退
    passed = all(v >= -0.02 for v in regression.values())
    
    return {'metrics': metrics, 'regression': regression, 'passed': passed}

def canary_deploy(model_artifact, steps=[0.05, 0.1, 0.25, 0.5, 1.0]):
    """金丝雀部署：逐步放量"""
    for traffic in steps:
        print(f"将流量调整到 {traffic*100}%...")
        deploy_model(model_artifact, traffic_percentage=traffic)
        
        # 观察一段时间
        metrics = collect_metrics(duration_minutes=5)
        
        # 检查关键指标
        if metrics['accuracy'] < 0.80 or metrics['error_rate'] > 0.05:
            print(f"❌ 流量{traffic*100}%时指标异常，执行回滚")
            rollback()
            return False
        
        print(f"✅ 流量{traffic*100}%验证通过")
    
    print("🎉 金丝雀部署完成，100%流量切换到新模型")
    return True

from scipy import stats
import numpy as np

def detect_drift(baseline_data, current_data, threshold=0.05):
    """用KS检验检测数据漂移"""
    drift_results = {}
    
    for column in baseline_data.columns:
        # Kolmogorov-Smirnov检验
        ks_stat, p_value = stats.ks_2samp(
            baseline_data[column].dropna(),
            current_data[column].dropna()
        )
        
        drift_detected = p_value < threshold
        drift_results[column] = {
            'ks_statistic': ks_stat,
            'p_value': p_value,
            'drift_detected': drift_detected
        }
    
    # 汇总
    drifted_columns = [k for k, v in drift_results.items() if v['drift_detected']]
    print(f"检测到 {len(drifted_columns)}/{len(drift_results)} 个特征发生漂移")
    
    return drift_results
