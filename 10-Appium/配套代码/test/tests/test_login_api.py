"""
登录功能测试 — 真实 API 调用（示例代码）

本测试基于 requests 库直接调用 Mock Server API 进行验证。
对应 Appium 项目的 API 测试框架思想，可直接替换为 Appium UI 测试。

前置条件：Mock Server 已启动（cd demo_app && python app.py）

对应文章：第06节-API测试封装、第07节-pytest集成
"""
import pytest
import requests
from config import MOCK_SERVER_URL


class TestLoginAPI:
    """登录接口测试 — 真实断言"""

    BASE_URL = MOCK_SERVER_URL

    def setup_method(self):
        """每个测试前初始化 session"""
        self.session = requests.Session()

    def test_login_success(self):
        """ 有效用户登录成功（admin/admin123）"""
        resp = self.session.post(f"{self.BASE_URL}/api/login", json={
            "username": "admin",
            "password": "admin123"
        })
        data = resp.json()
        assert resp.status_code == 200, f"登录应返回200，实际: {resp.status_code}"
        assert data["message"] == "登录成功", f"消息应为'登录成功'，实际: {data.get('message')}"
        assert data["user"]["username"] == "admin", f"用户名应为admin，实际: {data['user'].get('username')}"

    def test_login_wrong_password(self):
        """ 错误密码登录失败"""
        resp = self.session.post(f"{self.BASE_URL}/api/login", json={
            "username": "admin",
            "password": "wrong_password"
        })
        assert resp.status_code == 401, f"错误密码应返回401，实际: {resp.status_code}"
        data = resp.json()
        assert "错误" in data.get("error", ""), f"错误信息应包含'错误'，实际: {data.get('error')}"

    def test_login_empty_username(self):
        """ 空用户名登录失败"""
        resp = self.session.post(f"{self.BASE_URL}/api/login", json={
            "username": "",
            "password": "test123"
        })
        assert resp.status_code == 401, f"空用户名应返回401，实际: {resp.status_code}"

    def test_login_nonexistent_user(self):
        """ 不存在的用户登录失败"""
        resp = self.session.post(f"{self.BASE_URL}/api/login", json={
            "username": "nonexistent_user_xyz",
            "password": "test123"
        })
        assert resp.status_code == 401, f"不存在用户应返回401，实际: {resp.status_code}"

    def test_login_session_persist(self):
        """ 登录后 session 保持状态"""
        # 登录
        resp = self.session.post(f"{self.BASE_URL}/api/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert resp.status_code == 200

        # 验证登录状态
        resp2 = self.session.get(f"{self.BASE_URL}/api/user/info")
        data = resp2.json()
        assert resp2.status_code == 200
        assert data["username"] == "admin", f"session 应保持登录状态，实际: {data.get('username')}"

    def test_login_required_for_user_info(self):
        """ 未登录无法获取用户信息"""
        session2 = requests.Session()
        resp = session2.get(f"{self.BASE_URL}/api/user/info")
        assert resp.status_code == 401, f"未登录应返回401，实际: {resp.status_code}"
