"""
Mock Server — API 测试的后端模拟服务
提供登录、注册、商品列表、购物车等 HTTP API
用于 Appium 课程配套的 API 测试

启动方式：cd demo_app && python app.py
访问地址：http://127.0.0.1:5001（可用环境变量 MOCK_SERVER_PORT 改端口）

注意：这不是被测 App 本身，而是一个 HTTP 后端模拟。
Appium UI 测试需要真实的 Android 设备或模拟器。
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import hashlib
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-appium-test-key'

# 模拟数据库
users_db = {}
products = [
    {"id": 1, "name": "iPhone 15", "price": 5999.0, "stock": 100, "image": ""},
    {"id": 2, "name": "MacBook Pro", "price": 14999.0, "stock": 50, "image": ""},
    {"id": 3, "name": "AirPods Pro", "price": 1899.0, "stock": 200, "image": ""},
    {"id": 4, "name": "iPad Air", "price": 4799.0, "stock": 80, "image": ""},
    {"id": 5, "name": "Apple Watch", "price": 2999.0, "stock": 150, "image": ""},
]

orders = {}


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


# ── 页面路由 ──────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/products')
def products_page():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return render_template('products.html', products=products)


@app.route('/cart')
def cart_page():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    cart = session.get('cart', {})
    cart_items = []
    for pid, qty in cart.items():
        for p in products:
            if str(p['id']) == str(pid):
                cart_items.append({**p, 'quantity': qty})
                break
    return render_template('cart.html', items=cart_items)


@app.route('/orders')
def orders_page():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    username = session['username']
    user_orders = orders.get(username, [])
    return render_template('orders.html', orders=user_orders)


# ── API 路由 ──────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '')

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    if username in users_db:
        return jsonify({"error": "用户名已存在"}), 409

    users_db[username] = {
        "password": hash_password(password),
        "email": email,
        "created_at": time.time()
    }

    session['username'] = username
    return jsonify({
        "message": "注册成功",
        "user": {"username": username, "email": email}
    }), 201


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if username not in users_db:
        return jsonify({"error": "用户名或密码错误"}), 401

    if users_db[username]['password'] != hash_password(password):
        return jsonify({"error": "用户名或密码错误"}), 401

    session['username'] = username
    return jsonify({
        "message": "登录成功",
        "user": {"username": username}
    })


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"message": "已退出登录"})


@app.route('/api/products', methods=['GET'])
def api_products():
    return jsonify(products)


@app.route('/api/products/<int:product_id>', methods=['GET'])
def api_product_detail(product_id):
    for p in products:
        if p['id'] == product_id:
            return jsonify(p)
    return jsonify({"error": "商品不存在"}), 404


@app.route('/api/cart/add', methods=['POST'])
def api_cart_add():
    if 'username' not in session:
        return jsonify({"error": "请先登录"}), 401

    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    if 'cart' not in session:
        session['cart'] = {}

    pid = str(product_id)
    session['cart'][pid] = session['cart'].get(pid, 0) + quantity
    session.modified = True

    return jsonify({"message": "已加入购物车", "cart": session['cart']})


@app.route('/api/cart', methods=['GET'])
def api_cart():
    if 'username' not in session:
        return jsonify({"error": "请先登录"}), 401

    cart = session.get('cart', {})
    cart_items = []
    for pid, qty in cart.items():
        for p in products:
            if str(p['id']) == pid:
                cart_items.append({**p, 'quantity': qty})
                break

    return jsonify(cart_items)


@app.route('/api/cart/clear', methods=['POST'])
def api_cart_clear():
    session['cart'] = {}
    session.modified = True
    return jsonify({"message": "购物车已清空"})


@app.route('/api/order/checkout', methods=['POST'])
def api_checkout():
    if 'username' not in session:
        return jsonify({"error": "请先登录"}), 401

    cart = session.get('cart', {})
    if not cart:
        return jsonify({"error": "购物车为空"}), 400

    username = session['username']
    order_id = int(time.time() * 1000) % 1000000

    items = []
    total = 0
    for pid, qty in cart.items():
        for p in products:
            if str(p['id']) == pid:
                items.append({"product_id": p['id'], "name": p['name'], "price": p['price'], "quantity": qty})
                total += p['price'] * qty
                break

    order = {
        "order_id": order_id,
        "items": items,
        "total": round(total, 2),
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    if username not in orders:
        orders[username] = []
    orders[username].append(order)

    session['cart'] = {}
    session.modified = True

    return jsonify({"message": "下单成功", "order": order}), 201


@app.route('/api/user/info', methods=['GET'])
def api_user_info():
    if 'username' not in session:
        return jsonify({"error": "未登录"}), 401
    return jsonify({"username": session['username']})


@app.route('/api/test/init', methods=['POST'])
def api_test_init():
    """测试初始化接口 — 创建测试账号"""
    users_db['testuser'] = {"password": hash_password("test123"), "email": "test@test.com"}
    users_db['admin'] = {"password": hash_password("admin123"), "email": "admin@test.com"}
    return jsonify({"message": "测试数据已初始化"})


if __name__ == '__main__':
    import os

    port = int(os.environ.get("MOCK_SERVER_PORT", "5001"))
    # 初始化测试数据
    users_db['testuser'] = {"password": hash_password("test123"), "email": "test@test.com"}
    users_db['admin'] = {"password": hash_password("admin123"), "email": "admin@test.com"}
    print(f" Mock Server 启动: http://127.0.0.1:{port}")
    print(" 测试账号: testuser/test123, admin/admin123")
    app.run(host='0.0.0.0', port=port, debug=True)
