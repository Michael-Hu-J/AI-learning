[pytest]
# 测试文件命名规则
python_files = test_*.py
# 测试函数命名规则
python_functions = test_*
# 测试类命名规则
python_classes = Test*
# 自定义标记
markers =
    smoke: 冒烟测试
    p0: 最高优先级
    slow: 慢速测试
# 命令行参数（每次运行时自动加）
addopts = -v --tb=short --html=report.html --self-contained-html
# 指定测试路径
testpaths = tests
