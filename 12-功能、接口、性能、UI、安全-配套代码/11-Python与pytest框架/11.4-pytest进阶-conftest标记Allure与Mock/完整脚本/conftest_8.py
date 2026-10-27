# 只跑冒烟测试
pytest -m smoke -v

# 只跑 p0 级别
pytest -m p0 -v

# 不跑慢速测试
pytest -m "not slow" -v

# 组合：p0 且 冒烟
pytest -m "p0 and smoke" -v

# 组合：p0 或 冒烟
pytest -m "p0 or smoke" -v
