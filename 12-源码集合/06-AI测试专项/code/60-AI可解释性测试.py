# 核心思路
for feature in features:
    for value in range(low, high, step):
        modified_input = base_input.copy()
        modified_input[feature] = value
        prediction = model.predict([modified_input])
        # 记录 prediction 随 value 的变化

import shap
import xgboost as xgb
from sklearn.datasets import make_classification

# 训练一个示例模型
X, y = make_classification(n_samples=1000, n_features=10, random_state=42)
model = xgb.XGBClassifier(random_state=42)
model.fit(X, y)

# 创建 SHAP 解释器
explainer = shap.Explainer(model)
shap_values = explainer(X)

# 全局解释：特征重要性条形图
shap.plots.bar(shap_values)

# 局部解释：单个样本的瀑布图
shap.plots.waterfall(shap_values[0])

# 总结图：所有样本的特征影响分布
shap.plots.beeswarm(shap_values)

from lime.lime_tabular import LimeTabularExplainer
import numpy as np

# 创建 LIME 解释器
explainer = LimeTabularExplainer(
    training_data=X_train,
    feature_names=['age', 'income', 'credit_score', 'debt_ratio', 'employment_years'],
    class_names=['批准', '拒绝'],
    mode='classification',
    random_state=42  # 一定要设随机种子！
)

# 解释单个样本
exp = explainer.explain_instance(
    X_test[0],
    model.predict_proba,
    num_features=5,
    num_samples=5000  # 增加采样数提高稳定性
)

# 查看解释结果
print(exp.as_list())
exp.as_pyplot_figure()

# 核心调用
path = model.decision_path([sample])  # 获取路径
leaf_id = model.apply([sample])[0]    # 获取叶子节点
# 遍历路径中的节点，提取特征名、阈值、判断方向

# 核心思路伪代码
for feature in features:
    for value in range(low, high, step):
        modified_input = base_input.copy()
        modified_input[feature] = value
        prediction = model.predict([modified_input])

# 核心思路
shap_top5 = get_top_features(shap_values)
lime_top5 = get_top_features(lime_values)
perm_top5 = get_top_features(permutation_values)
# 计算三组 Top-5 特征的 Jaccard 相似度
consistency = jaccard(shap_top5, lime_top5, perm_top5)

class InterpretabilityTestSuite:
    """可解释性测试套件 - 封装所有可解释性测试方法"""
    
    def __init__(self, model, X_train, feature_names):
        self.model = model
        self.X_train = X_train
        self.feature_names = feature_names
        self.results = {}
    
    def run_all_tests(self, test_samples):
        """一键运行全部测试"""
        self.results['global_importance'] = self.test_global_importance(test_samples)
        self.results['local_consistency'] = self.test_local_consistency(test_samples)
        self.results['sensitivity'] = self.test_sensitivity(test_samples)
        self.results['stability'] = self.test_stability(test_samples)
        self.results['counterfactual'] = self.test_counterfactual(test_samples)
        return self.results
    
    def generate_report(self):
        """生成可读的测试报告"""
        report = "=== 可解释性测试报告 ===\n"
        for key, value in self.results.items():
            report += f"{key}: {value}\n"
        return report
