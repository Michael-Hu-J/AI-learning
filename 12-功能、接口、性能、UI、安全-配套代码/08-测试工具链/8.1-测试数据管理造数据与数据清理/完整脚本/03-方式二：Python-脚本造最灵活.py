import random
import requests
import string

def generate_phone():
    """生成随机手机号（139 开头）"""
    return f"139{random.randint(10000000, 99999999)}"

def generate_name():
    """生成随机中文名"""
    surnames = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴"]
    given = ["伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "洋"]
    return random.choice(surnames) + random.choice(given) + random.choice(given)

def generate_password():
    """生成随机密码"""
    chars = string.ascii_letters + string.digits
    return "Test" + ''.join(random.choices(chars, k=6))

def create_user(session, name, phone, password):
    """通过接口创建用户"""
    response = session.post("http://test-api.example.com/api/v1/user/register", json={
        "name": name,
        "phone": phone,
        "password": password
    })
    return response.json()

# 造 100 个用户
session = requests.Session()
for i in range(100):
    name = generate_name()
    phone = generate_phone()
    password = generate_password()
    result = create_user(session, name, phone, password)
    if result.get("code") == 0:
        print(f"✅ 用户 {i+1}: {name} {phone}")
    else:
        print(f"❌ 用户 {i+1} 创建失败: {result.get('message')}")
