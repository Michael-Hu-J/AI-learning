# 进到 tests 目录
cd seckill_finance_system/tests

# 运行所有测试
pytest -v

# 只跑冒烟测试
pytest -m smoke -v

# 生成 HTML 报告
pytest --html=report.html --self-contained-html

# 并行跑
pytest -n 4 -v
