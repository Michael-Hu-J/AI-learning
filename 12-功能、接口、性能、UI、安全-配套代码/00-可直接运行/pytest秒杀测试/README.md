# pytest 秒杀系统自动化测试

> 对应课程 **11.5 pytest实战**，可直接复制到 `seckill_finance_system/tests/` 使用。

## 目录结构

```
tests/
├── conftest.py           # fixture：admin_api、user_api、db
├── pytest.ini            # 标记：smoke / p0 / slow
├── config.json           # 环境配置（改 base_url 和数据库）
├── test_data/
│   └── login_cases.json
├── utils/
│   ├── api_client.py
│   └── db_helper.py
├── test_01_auth.py       # 登录参数化 + SQL注入
├── test_02_products.py   # 商品 CRUD + 权限
└── test_04_seckill.py    # 并发秒杀 + 防超卖
```

## 快速开始

```bash
# 1. 启动秒杀系统
cd seckill_finance_system && docker compose up -d

# 2. 复制 tests 目录（或直接用本目录）
cp -r tests /path/to/seckill_finance_system/

# 3. 修改 config.json
#    base_url: http://localhost:5001
#    database: 对应 MySQL 端口和密码

# 4. 安装依赖并运行
pip install -r requirements.txt
cd tests
pytest -v
pytest -m smoke -v
pytest --html=report.html --self-contained-html
```

## 测试覆盖

| 文件 | 覆盖场景 |
|------|---------|
| test_01_auth | 登录成功/失败/空参/SQL注入/405 |
| test_02_products | CRUD、负价格、未认证、普通用户越权 |
| test_04_seckill | 单用户秒杀、50并发防超卖 |
