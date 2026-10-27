import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris

# 设置实验（相当于给一组实验起个名字）
mlflow.set_experiment("my_classification_project")

# 开始一次实验运行
with mlflow.start_run(run_name="rf_baseline"):
    # 记录参数
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)
    mlflow.log_param("random_seed", 42)
    
    # 训练模型
    X, y = load_iris(return_X_y=True)
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X, y)
    
    # 记录指标
    accuracy = model.score(X, y)
    mlflow.log_metric("accuracy", accuracy)
    
    # 保存模型
    mlflow.sklearn.log_model(model, "model")

import os
import random
import numpy as np

def set_reproducibility(seed=42):
    """一键设置所有随机种子"""
    # Python内置
    random.seed(seed)
    # NumPy
    np.random.seed(seed)
    # PyTorch
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass
    # TensorFlow
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
        os.environ['TF_DETERMINISTIC_OPS'] = '1'
    except ImportError:
        pass
    # 哈希种子（影响Python的dict/set遍历顺序）
    os.environ['PYTHONHASHSEED'] = str(seed)

import platform
import sys
import pkg_resources
import hashlib
import json

def capture_environment():
    """捕获当前环境的完整信息"""
    env_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "packages": {}
    }
    
    # 记录所有已安装包的版本
    for dist in pkg_resources.working_set:
        env_info["packages"][dist.project_name] = dist.version
    
    # 生成环境指纹
    env_str = json.dumps(env_info, sort_keys=True, default=str)
    env_info["fingerprint"] = hashlib.sha256(env_str.encode()).hexdigest()[:16]
    
    return env_info

def worker_init_fn(worker_id):
    np.random.seed(np.random.get_state()[1][0] + worker_id)
    
loader = DataLoader(dataset, batch_size=32, num_workers=4, 
                    worker_init_fn=worker_init_fn)
