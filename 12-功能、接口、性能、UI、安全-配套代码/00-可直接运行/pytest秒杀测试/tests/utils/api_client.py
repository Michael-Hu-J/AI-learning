"""API 请求工具类"""
import requests
import json
from datetime import datetime


class ApiClient:
    """封装 HTTP 请求，让测试用例更干净"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.logs = []

    def _log(self, method, url, status, body):
        self.logs.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "method": method,
            "url": url,
            "status": status,
            "body": body[:200] if body else "",
        })

    def request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, timeout=10, **kwargs)

        try:
            body = response.json()
        except ValueError:
            body = response.text

        self._log(
            method,
            url,
            response.status_code,
            json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else body,
        )
        return response

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def set_token(self, token):
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def print_logs(self):
        print("\n=== 请求日志 ===")
        for log in self.logs:
            print(f"[{log['time']}] {log['method']} {log['url']} → {log['status']}")
        print("================")
