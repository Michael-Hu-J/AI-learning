project/
├── pages/                  # 页面对象层
│   ├── __init__.py
│   ├── login_page.py       # 登录页
│   ├── order_page.py       # 下单页
│   └── payment_page.py     # 支付页
├── tests/                  # 测试用例层
│   ├── __init__.py
│   ├── test_login.py
│   └── test_order.py
├── conftest.py             # pytest 配置（浏览器初始化）
└── config.py               # 环境配置
