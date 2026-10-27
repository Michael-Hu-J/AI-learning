"""
内置演示应用 — 电商登录/注册/商品系统
不依赖任何外部项目，纯 Flask 内置

启动：python demo_app/app.py
访问：http://127.0.0.1:5000

安全提示：仅用于本机教学演示，勿暴露公网或用于生产；固定口令与 secret_key 不具备真实安全性。

对应文章：第1篇-架构定位、第9篇-浏览器API实战
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "demo-key"  # 演示用；生产环境须使用随机密钥并配合真实会话存储

USERS = {"admin": {"pwd": "admin123", "role": "admin", "token": "tok_admin"},
         "testuser": {"pwd": "test123", "role": "user", "token": "tok_test"}}
PRODUCTS = [{"id":1,"name":"商品A-手机","price":2999,"stock":100},{"id":2,"name":"商品B-耳机","price":399,"stock":200},{"id":3,"name":"商品C-平板","price":1999,"stock":50}]
_next_id = 4

@app.route("/")
def index(): return redirect(url_for("products_page"))

@app.route("/login", methods=["GET","POST"])
def login_page():
    if request.method == "GET": return render_template("login.html")
    u, p = request.form.get("username",""), request.form.get("password","")
    user = USERS.get(u)
    if user and user["pwd"] == p:
        session["user"] = u
        session["token"] = user["token"]
        return redirect(url_for("products_page"))
    return render_template("login.html", error="用户名或密码错误")

@app.route("/register", methods=["GET","POST"])
def register_page():
    if request.method == "GET": return render_template("register.html")
    u, p = request.form.get("username",""), request.form.get("password","")
    if u in USERS: return jsonify({"success":False,"message":"用户名已存在"})
    USERS[u] = {"pwd":p,"role":"user","token":f"tok_{u}_{uuid.uuid4().hex[:8]}"}
    return jsonify({"success":True,"token":USERS[u]["token"],"user":u})

@app.route("/products")
def products_page(): return render_template("products.html", products=PRODUCTS, now=datetime.now().strftime("%Y-%m-%d %H:%M"))

@app.route("/dashboard")
def dashboard_page(): return render_template("dashboard.html", user=session.get("user"), token=session.get("token"))

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True) if request.is_json else request.form
    user = USERS.get(data.get("username",""))
    if user and user["pwd"] == data.get("password",""): return jsonify({"success":True,"token":user["token"],"user":data.get("username")})
    return jsonify({"success":False,"message":"认证失败"}),401

@app.route("/api/products")
def api_products(): return jsonify(PRODUCTS)

@app.route("/api/products", methods=["POST"])
def api_add_product():
    global _next_id
    data = request.get_json(force=True) if request.is_json else request.form
    name = data.get("name", "")
    price = float(data.get("price", 0))
    stock = int(data.get("stock", 0))
    if not name:
        return jsonify({"success": False, "message": "商品名称不能为空"}), 400
    product = {"id": _next_id, "name": name, "price": price, "stock": stock}
    PRODUCTS.append(product)
    _next_id += 1
    return jsonify(product), 201

@app.route("/products", methods=["POST"])
def add_product_page():
    global _next_id
    data = request.get_json(force=True) if request.is_json else request.form
    name = data.get("name", "")
    price = float(data.get("price", 0))
    stock = int(data.get("stock", 0))
    if not name:
        return jsonify({"success": False, "message": "商品名称不能为空"}), 400
    product = {"id": _next_id, "name": name, "price": price, "stock": stock}
    PRODUCTS.append(product)
    _next_id += 1
    return jsonify({"success": True, "product": product})

if __name__ == "__main__":
    print("="*50); print(" 演示应用已启动"); print("   地址: http://127.0.0.1:5000"); print("   账号: admin/admin123"); print("="*50)
    app.run(host="127.0.0.1", port=5000, debug=False)
