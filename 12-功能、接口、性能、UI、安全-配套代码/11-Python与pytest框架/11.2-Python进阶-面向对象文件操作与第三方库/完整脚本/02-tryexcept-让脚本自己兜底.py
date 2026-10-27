import requests

try:
    response = requests.get("http://localhost:5001/api/health", timeout=5)
    data = response.json()
    print(f"服务状态：{data}")
except requests.exceptions.ConnectionError:
    print("❌ 连接失败：服务器没启动")
except requests.exceptions.Timeout:
    print("❌ 请求超时：服务器响应太慢")
except ValueError:
    print("❌ 返回的不是 JSON")
except Exception as e:
    print(f"❌ 未知错误：{e}")
