seckill_finance_system/
├── tests/
│   ├── conftest.py              # 全局配置、fixture
│   ├── pytest.ini               # pytest 配置
│   ├── config.json              # 环境配置
│   ├── test_data/               # 测试数据
│   │   ├── login_cases.json
│   │   ├── product_cases.json
│   │   └── order_cases.json
│   ├── utils/                   # 工具类
│   │   ├── __init__.py
│   │   ├── api_client.py        # 封装 HTTP 请求
│   │   └── db_helper.py         # 数据库验证
│   ├── test_01_auth.py          # 认证模块
│   ├── test_02_products.py      # 商品管理
│   ├── test_03_orders.py        # 订单管理
│   └── test_04_seckill.py       # 秒杀核心
└── requirements.txt             # 加上 pytest 相关依赖
