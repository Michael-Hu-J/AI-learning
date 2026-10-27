import requests
import json

def safe_request(method, url, **kwargs):
    """安全的接口调用，任何情况都不崩"""
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        
        # 尝试解析 JSON
        try:
            data = response.json()
        except ValueError:
            data = response.text
        
        return {
            "success": True,
            "status_code": response.status_code,
            "data": data
        }
        
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "连接失败"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 使用
result = safe_request("POST", "http://localhost:5001/api/auth/login",
                     json={"username": "admin", "password": "admin123"})

if result["success"]:
    print(f"状态码：{result['status_code']}")
    print(f"返回数据：{result['data']}")
else:
    print(f"请求失败：{result['error']}")
