import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance

class ExplainabilityEvaluator:
    """可解释性评估器——我们在多个项目里用的框架"""
    
    def __init__(self, model, X_train, y_train, X_test, y_test):
        self.model = model
        self.X_train = X_train
        self.y_train = y_train
        self.X_test = X_test
        self.y_test = y_test
    
    def evaluate_all(self):
        """一键跑全套评估"""
        results = {}
        results['feature_importance'] = self._feature_importance()
        results['shap_global'] = self._shap_global()
        results['shap_local'] = self._shap_local()
        results['permutation'] = self._permutation_importance()
        results['stability'] = self._stability_check()
        return results
    
    def _feature_importance(self):
        """模型内置特征重要性"""
        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_
        return None
    
    def _shap_global(self):
        """全局 SHAP 分析"""
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer(self.X_test[:500])  # 抽样加速
        return shap_values
    
    def _shap_local(self, sample_idx=0):
        """单个样本的 SHAP 解释"""
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer(self.X_test[sample_idx:sample_idx+1])
        return shap_values
    
    def _permutation_importance(self):
        """排列重要性"""
        result = permutation_importance(
            self.model, self.X_test, self.y_test,
            n_repeats=10, random_state=42
        )
        return result.importances_mean
    
    def _stability_check(self):
        """解释稳定性：加噪声看解释是否变化"""
        base_shap = self._shap_global().values.mean(axis=0)
        noisy_shaps = []
        for seed in range(5):
            X_noisy = self.X_test + np.random.normal(0, 0.01, self.X_test.shape)
            explainer = shap.TreeExplainer(self.model)
            noisy_shap = explainer(X_noisy[:500]).values.mean(axis=0)
            noisy_shaps.append(noisy_shap)
        correlations = [np.corrcoef(base_shap, ns)[0, 1] for ns in noisy_shaps]
        return np.mean(correlations)

import shap
import matplotlib.pyplot as plt

# 训练模型
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 创建解释器
explainer = shap.TreeExplainer(model)
shap_values = explainer(X_test)

# 1. Summary Plot——全局特征重要性 + 方向
shap.summary_plot(shap_values, X_test, plot_type="bar")

# 2. Force Plot——单个样本的解释
shap.force_plot(explainer.expected_value, shap_values[0], X_test.iloc[0])

# 3. Dependence Plot——特征值 vs SHAP 值的关系
shap.dependence_plot("income", shap_values.values, X_test)

class TrustworthinessAssessor:
    """信任度评估器——从七个维度给模型打分"""
    
    def __init__(self, model, X_train, y_train, X_test, y_test):
        self.model = model
        self.X_train = X_train
        self.y_train = y_train
        self.X_test = X_test
        self.y_test = y_test
    
    def assess(self):
        """综合信任度评估"""
        scores = {}
        scores['reliability'] = self._reliability()
        scores['robustness'] = self._robustness()
        scores['consistency'] = self._consistency()
        scores['transparency'] = self._transparency()
        scores['fairness'] = self._fairness()
        scores['accountability'] = self._accountability()
        scores['explainability'] = self._explainability()
        overall = np.mean(list(scores.values()))
        return {'scores': scores, 'overall': overall}
    
    def _reliability(self):
        """可靠性：准确率和稳定性"""
        from sklearn.metrics import accuracy_score
        from sklearn.model_selection import cross_val_score
        acc = accuracy_score(self.y_test, self.model.predict(self.X_test))
        cv_scores = cross_val_score(self.model, self.X_train, self.y_train, cv=5)
        return 0.6 * acc + 0.4 * max(0, 1 - cv_scores.std())
    
    def _robustness(self):
        """鲁棒性：抗干扰能力"""
        base_acc = accuracy_score(self.y_test, self.model.predict(self.X_test))
        degraded = []
        for noise in [0.01, 0.05, 0.1]:
            X_noisy = self.X_test + np.random.normal(0, noise, self.X_test.shape)
            degraded.append(accuracy_score(self.y_test, self.model.predict(X_noisy)))
        avg_drop = base_acc - np.mean(degraded)
        return max(0, 1 - avg_drop * 5)

def counterfactual_explanation(model, sample, feature_idx, change_amount):
    """生成反事实解释——回答"如果...会怎样""""
    counterfactual = sample.copy()
    counterfactual[feature_idx] += change_amount
    original_pred = model.predict([sample])[0]
    cf_pred = model.predict([counterfactual])[0]
    return {
        'original_prediction': original_pred,
        'counterfactual_prediction': cf_pred,
        'change_needed': change_amount,
        'outcome_changed': original_pred != cf_pred
    }
