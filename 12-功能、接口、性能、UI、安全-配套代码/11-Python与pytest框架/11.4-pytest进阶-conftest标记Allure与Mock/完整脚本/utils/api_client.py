tests/
├── conftest.py              # 全局 fixture
├── pytest.ini               # pytest 配置
├── test_data/               # 测试数据
│   ├── login_cases.json
│   └── product_cases.json
├── utils/                   # 工具类
│   └── api_client.py        # 封装好的 HTTP 客户端
├── test_01_auth.py          # 认证模块
├── test_02_products.py      # 商品模块
├── test_03_orders.py        # 订单模块
└── test_04_seckill.py       # 秒杀模块
