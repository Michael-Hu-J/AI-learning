# 运行所有用例
pytest

# 运行指定文件
pytest test_01_auth.py

# 运行指定目录
pytest tests/

# 显示详细输出（推荐）
pytest -v

# 显示 print 输出
pytest -s

# 只运行名字包含 "login" 的用例
pytest -k "login"

# 只运行标记为 smoke 的用例
pytest -m smoke

# 失败时显示详细信息
pytest -v --tb=long

# 遇到第一个失败就停止
pytest -x

# 生成 HTML 报告
pytest --html=report.html

# 多线程运行（需要安装 pytest-xdist）
pytest -n 4  # 4 个线程并行
