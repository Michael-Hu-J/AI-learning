"""
浏览器 API + Worker 测试
对应文章：第1/2/9篇
"""
import pytest, json, tempfile, os


class TestWorker:
    def test_config(self):
        import json
        c = {"exec_id": "t1", "steps": [{"action": "打开页面", "target": "/"}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(c, f)
            f.flush()
            with open(f.name) as f2:
                r = json.load(f2)
            os.unlink(f.name)
        assert r["exec_id"] == "t1"
        assert len(r["steps"]) == 1

    def test_result(self):
        import json
        r = {"exec_id": "t1", "status": "completed"}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            p = f.name
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump(r, f)
        with open(p) as f:
            assert json.load(f)["status"] == "completed"
        os.unlink(p)

    def test_log_func(self):
        logs = []

        def push_log(logs, msg, level="info"):
            logs.append({"message": msg, "level": level})
            if len(logs) > 500:
                logs[:] = logs[-500:]

        push_log(logs, "一", "info")
        push_log(logs, "二", "warning")
        assert len(logs) == 2
        assert logs[0]["message"] == "一"
        assert logs[1]["message"] == "二"
        assert logs[0]["level"] == "info"
        assert logs[1]["level"] == "warning"

    def test_log_cap(self):
        logs = []

        def push_log(logs, msg, level="info"):
            logs.append({"message": msg, "level": level})
            if len(logs) > 500:
                logs[:] = logs[-500:]

        for i in range(600):
            push_log(logs, f"n{i}", "info")
        assert len(logs) <= 500

class TestBrowser:
    def test_login_page(self, page, demo_app):
        page.goto("http://127.0.0.1:5000/login")
        assert page.locator("#username").is_visible()
        assert page.locator("#password").is_visible()
    def test_login_ok(self, page, demo_app):
        page.goto("http://127.0.0.1:5000/login")
        page.fill("#username","admin"); page.fill("#password","admin123"); page.click("button[type=submit]")
        page.wait_for_timeout(1000)
        assert "products" in page.url or "商品" in page.text_content("body")
    def test_login_fail(self, page, demo_app):
        page.goto("http://127.0.0.1:5000/login")
        page.fill("#username","admin"); page.fill("#password","wrong"); page.click("button[type=submit]")
        page.wait_for_timeout(1000)
        body=page.text_content("body"); assert "错误" in body or "失败" in body
    def test_products(self, page, demo_app):
        page.goto("http://127.0.0.1:5000/products")
        assert "商品" in page.text_content("body") or "列表" in page.text_content("body")
    def test_register_page(self, page, demo_app):
        page.goto("http://127.0.0.1:5000/register")
        body = page.text_content("body")
        assert "注册" in body or "用户名" in body
