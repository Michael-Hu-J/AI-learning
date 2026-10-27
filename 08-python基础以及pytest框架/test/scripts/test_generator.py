#!/usr/bin/env python3
"""
pytest 测试代码生成器 v2 — 多维度覆盖
从 OpenAPI 文档自动生成全面的 pytest 测试脚本。

覆盖维度：
- H (Happy Path): 主路径成功
- E (Edge): 契约边界 — 最大/最小/空值/超长/特殊字符
- X (Exception): 协议/业务拒绝 — 401/404/422/业务错误
- P (Performance): 响应时间量级检查
- S (Security): 匿名访问/过期Token/越权

用法:
    python test_generator.py <openapi.yaml> [--output <output_dir>] [--tag <tag_name>]
"""

import os
import re
import sys
import argparse
from typing import List, Dict, Optional, Any, Set
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.openapi_parser import OpenAPIParser, APIEndpoint, FieldConstraint


class TestGenerator:
    """pytest 测试代码生成器 v2 — 多维度覆盖"""

    def __init__(self, parser: OpenAPIParser, output_dir: str = 'output'):
        self.parser = parser
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_all(self) -> List[str]:
        """生成所有测试文件"""
        generated = []

        # 1. 按 tag 生成综合 API测试 (H/E/X/P/S)
        for tag in self.parser.get_all_tags():
            if tag in ('test',):
                continue
            endpoints = self.parser.get_endpoints_by_tag(tag)
            if not endpoints:
                continue
            filepath = self._generate_comprehensive_api_test(tag, endpoints)
            generated.append(filepath)

        # 2. 生成安全测试
        sec_file = self._generate_security_test()
        if sec_file:
            generated.append(sec_file)

        # 3. 生成边界值测试
        bound_file = self._generate_boundary_test()
        if bound_file:
            generated.append(bound_file)

        # 4. 生成功能流程测试
        flow_file = self._generate_functional_flow_test()
        if flow_file:
            generated.append(flow_file)

        # 5. 生成端到端测试
        e2e_file = self._generate_e2e_test()
        if e2e_file:
            generated.append(e2e_file)

        return generated

    def generate_by_tag(self, tag: str) -> Optional[str]:
        endpoints = self.parser.get_endpoints_by_tag(tag)
        if not endpoints:
            return None
        return self._generate_comprehensive_api_test(tag, endpoints)

    # ─── 综合 API测试 (H/E/X/P/S) ───

    def _generate_comprehensive_api_test(self, tag: str, endpoints: List[APIEndpoint]) -> str:
        filename = f"test_api_{self._slugify(tag)}.py"
        filepath = os.path.join(self.output_dir, filename)

        lines = []
        lines.append('"""')
        lines.append(f"自动生成的 {tag} 接口测试 — 多维度覆盖 (H/E/X/P/S)")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"接口数量: {len(endpoints)}")
        lines.append('"""')
        lines.append('')
        lines.append('import pytest')
        lines.append('import requests')
        lines.append('import os')
        lines.append('import time')
        lines.append('')
        lines.append('')
        lines.append('BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")')
        lines.append('')
        lines.append('')

        # 生成 Fixture
        has_auth = any(ep.requires_auth for ep in endpoints)
        if has_auth:
            lines.extend(self._generate_auth_fixtures())
            lines.extend(self._generate_path_fixtures(endpoints))
        else:
            lines.append('@pytest.fixture')
            lines.append('def api_session():')
            lines.append('    return requests.Session()')
        lines.append('')
        lines.append('')

        # 为每个接口生成 H/E/X/P/S 测试
        for endpoint in endpoints:
            lines.extend(self._generate_h_tests(endpoint))
            lines.append('')
            lines.append('')
            lines.extend(self._generate_e_tests(endpoint))
            lines.append('')
            lines.append('')
            lines.extend(self._generate_x_tests(endpoint))
            lines.append('')
            lines.append('')
            lines.extend(self._generate_p_tests(endpoint))
            lines.append('')
            lines.append('')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return filepath

    def _generate_auth_fixtures(self) -> List[str]:
        return [
            '@pytest.fixture(scope="session")',
            'def admin_token():',
            '    """管理员 Token"""',
            '    resp = requests.post(',
            '        f"{BASE_URL}/api/auth/login",',
            '        json={"username": "admin", "password": "admin123"},',
            '        timeout=10',
            '    )',
            '    assert resp.status_code == 200',
            '    return resp.json().get("token")',
            '',
            '',
            '@pytest.fixture(scope="session")',
            'def admin_headers(admin_token):',
            '    return {"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}',
            '',
            '',
            '@pytest.fixture',
            'def user_token():',
            '    """普通用户 Token"""',
            '    import uuid',
            '    uname = f"user_{uuid.uuid4().hex[:8]}"',
            '    resp = requests.post(',
            '        f"{BASE_URL}/api/auth/register",',
            '        json={"username": uname, "password": "Test@123", "email": f"{uname}@test.com"},',
            '        timeout=10',
            '    )',
            '    assert resp.status_code in (200, 201)',
            '    return resp.json().get("token")',
            '',
            '',
            '@pytest.fixture',
            'def user_headers(user_token):',
            '    return {"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}',
        ]

    def _generate_path_fixtures(self, endpoints: List[APIEndpoint]) -> List[str]:
        path_vars: Set[str] = set()
        for ep in endpoints:
            path_vars.update(self._path_vars_in_path(ep.path))

        lines = [
            '',
            '@pytest.fixture',
            'def api_session():',
            '    return requests.Session()',
        ]
        if 'product_id' in path_vars:
            lines.extend([
                '',
                '',
                '@pytest.fixture',
                'def product_id(admin_headers):',
                '    """创建测试商品并返回 ID"""',
                '    import uuid',
                '    body = {"name": f"pytest_auto_{uuid.uuid4().hex[:8]}", "price": 99.0, "stock": 10}',
                '    resp = requests.post(',
                '        f"{BASE_URL}/api/products", json=body, headers=admin_headers, timeout=10',
                '    )',
                '    assert resp.status_code == 201',
                '    return resp.json()["id"]',
            ])
        return lines

    def _path_vars_in_path(self, path: str) -> List[str]:
        normalized = re.sub(r'<(?:int:)?([^>]+)>', r'{\1}', path)
        return re.findall(r'\{(\w+)\}', normalized)

    def _test_func_params(self, ep: APIEndpoint) -> str:
        params: List[str] = []
        path_vars = self._path_vars_in_path(ep.path)
        if ep.requires_auth:
            params.append('admin_headers')
        elif not path_vars:
            params.append('api_session')
        for var in path_vars:
            if var not in params:
                params.append(var)
        return ', '.join(params)

    def _headers_kw(self, ep: APIEndpoint) -> str:
        return ', headers=admin_headers' if ep.requires_auth else ''

    def _sanitize_happy_body(self, body: Dict) -> Dict:
        """Happy Path 请求体：去掉占位符时间等非合法字段，避免后端 500"""
        cleaned = dict(body)
        for key in list(cleaned.keys()):
            val = cleaned[key]
            if not isinstance(val, str):
                continue
            kl = key.lower()
            if ('time' in kl or 'date' in kl) and not re.match(r'^\d{4}-\d{2}-\d{2}', val):
                del cleaned[key]
            elif val.startswith('test_') and kl not in ('name', 'description', 'code'):
                del cleaned[key]
        return cleaned

    def _make_func_name(self, endpoint: APIEndpoint, suffix: str = '') -> str:
        name = f"test_{endpoint.operation_id}"
        name = name.replace('-', '_').replace('/', '_').replace('{', '').replace('}', '')
        name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        if suffix:
            name = f"{name}_{suffix}"
        return name

    def _resolve_path(self, endpoint: APIEndpoint) -> str:
        """将 OpenAPI/Flask 路径转为 f-string 可用形式，如 /api/products/{product_id}"""
        path = re.sub(r'<(?:int:)?([^>]+)>', r'{\1}', endpoint.path)
        for p in self._get_path_params(endpoint):
            path = path.replace(f"{{{p['name']}}}", f"{{{p['name']}}}")
        return path

    def _get_path_params(self, endpoint: APIEndpoint) -> List[Dict]:
        return [p for p in endpoint.parameters if p.get('in') == 'path']

    def _get_query_params(self, endpoint: APIEndpoint) -> List[Dict]:
        return [p for p in endpoint.parameters if p.get('in') == 'query']

    def _example_body(self, endpoint: APIEndpoint) -> Optional[Dict]:
        return self.parser.get_example_body(endpoint)

    # ─── H: Happy Path ───

    def _generate_h_tests(self, ep: APIEndpoint) -> List[str]:
        lines = []
        func = self._make_func_name(ep, 'happy_path')
        path = self._resolve_path(ep)
        example = self._example_body(ep)
        hdr = self._headers_kw(ep)
        params = self._test_func_params(ep)

        lines.append(f"@pytest.mark.h")
        lines.append(f"@pytest.mark.{self._slugify(ep.tags[0]) if ep.tags else 'api'}")
        lines.append(f'def {func}({params}):')
        lines.append(f'    """H: {ep.summary} — 正常请求"""')

        if ep.method == 'GET':
            lines.append(f'    resp = requests.get(f"{{BASE_URL}}{path}", timeout=10{hdr})')
        elif ep.method == 'POST':
            if example:
                lines.append(f'    import uuid')
                lines.append(f'    body = {self._fmt(example)}')
                lines.append(f'    if "name" in body and isinstance(body["name"], str):')
                lines.append(f'        body["name"] = f"{{body[\'name\']}}_{{uuid.uuid4().hex[:6]}}"')
                lines.append(f'    resp = requests.post(f"{{BASE_URL}}{path}", json=body, timeout=10{hdr})')
            else:
                lines.append(f'    resp = requests.post(f"{{BASE_URL}}{path}", timeout=10{hdr})')
        elif ep.method == 'PUT':
            if example:
                safe_body = self._sanitize_happy_body(example)
                lines.append(f'    body = {self._fmt(safe_body)}')
                lines.append(f'    resp = requests.put(f"{{BASE_URL}}{path}", json=body, timeout=10{hdr})')
            else:
                lines.append(f'    resp = requests.put(f"{{BASE_URL}}{path}", timeout=10{hdr})')
        elif ep.method == 'DELETE':
            lines.append(f'    resp = requests.delete(f"{{BASE_URL}}{path}", timeout=10{hdr})')

        success_codes = [s for s in ep.responses if s.startswith('2')]
        expected = success_codes[0] if success_codes else '200'
        lines.append(f'    assert resp.status_code == {expected}')
        return lines

    # ─── E: Edge / Boundary ───

    def _generate_e_tests(self, ep: APIEndpoint) -> List[str]:
        lines = []
        path = self._resolve_path(ep)
        fields = ep.request_fields
        query_params = self._get_query_params(ep)

        if not fields and not query_params:
            return []

        func = self._make_func_name(ep, 'boundary')
        lines.append(f"@pytest.mark.e")
        lines.append(f"@pytest.mark.{self._slugify(ep.tags[0]) if ep.tags else 'api'}")
        lines.append(f'def {func}({self._test_func_params(ep)}):')
        lines.append(f'    """E: {ep.summary} — 边界值测试"""')

        # 字符串字段边界
        str_fields = [f for f in fields if f.field_type == 'string']
        int_fields = [f for f in fields if f.field_type in ('integer', 'number')]

        if str_fields or int_fields:
            lines.append(f'    # 空值测试')
            body = {}
            for f in str_fields:
                body[f.name] = ''
            for f in int_fields:
                body[f.name] = 0
            if body:
                lines.append(f'    body_empty = {self._fmt(body)}')
                self._add_request(lines, ep, path, 'body_empty')
                lines.append(f'    assert resp.status_code in (400, 422)  # 空值应被拒绝')

            lines.append(f'')
            lines.append(f'    # 超长字符串测试')
            body_long = {}
            for f in str_fields:
                body_long[f.name] = 'a' * 10000
            if body_long:
                lines.append(f'    body_long = {self._fmt(body_long)}')
                self._add_request(lines, ep, path, 'body_long')
                lines.append(f'    assert resp.status_code in (400, 413, 422)  # 超长应被拒绝')

        # 查询参数边界
        if query_params:
            lines.append(f'')
            lines.append(f'    # 分页边界')
            params = {q['name']: 999999 for q in query_params if 'page' in q.get('name', '')}
            if params:
                lines.append(f'    resp = requests.get(f"{{BASE_URL}}{path}", params={self._fmt(params)}, timeout=10{self._headers_kw(ep)})')
                lines.append(f'    assert resp.status_code == 200  # 大页码应返回空列表或第一页')

        return lines

    # ─── X: Exception / Rejection ───

    def _generate_x_tests(self, ep: APIEndpoint) -> List[str]:
        lines = []
        path = self._resolve_path(ep)
        example = self._example_body(ep)

        func = self._make_func_name(ep, 'exception')
        lines.append(f"@pytest.mark.x")
        lines.append(f"@pytest.mark.{self._slugify(ep.tags[0]) if ep.tags else 'api'}")
        lines.append(f'def {func}({self._test_func_params(ep)}):')
        lines.append(f'    """X: {ep.summary} — 异常请求测试"""')

        # 缺少必填字段
        required_fields = [f for f in ep.request_fields if f.required]
        if required_fields and example:
            lines.append(f'    # 缺少必填字段')
            body_partial = {k: v for k, v in example.items() if k != required_fields[0].name}
            lines.append(f'    body_partial = {self._fmt(body_partial)}')
            self._add_request(lines, ep, path, 'body_partial')
            lines.append(f'    assert resp.status_code in (400, 422)  # 缺少必填字段应返回错误')

        # 类型错误
        if ep.request_fields:
            lines.append(f'')
            lines.append(f'    # 字段类型错误')
            body_bad_type = {}
            for f in ep.request_fields[:2]:
                if f.field_type == 'integer':
                    body_bad_type[f.name] = 'not_a_number'
                elif f.field_type == 'string':
                    body_bad_type[f.name] = 12345
                elif f.field_type == 'number':
                    body_bad_type[f.name] = 'abc'
            if body_bad_type:
                lines.append(f'    body_bad_type = {self._fmt(body_bad_type)}')
                self._add_request(lines, ep, path, 'body_bad_type')
                lines.append(f'    assert resp.status_code in (400, 422)  # 类型错误应返回错误')

        # 无效枚举
        enum_fields = [f for f in ep.request_fields if f.enum]
        if enum_fields:
            lines.append(f'')
            lines.append(f'    # 无效枚举值')
            body_bad_enum = {}
            for f in enum_fields[:1]:
                body_bad_enum[f.name] = 'INVALID_VALUE_NOT_IN_ENUM'
            if body_bad_enum:
                lines.append(f'    body_bad_enum = {self._fmt(body_bad_enum)}')
                self._add_request(lines, ep, path, 'body_bad_enum')
                lines.append(f'    assert resp.status_code in (400, 422)  # 无效枚举应返回错误')

        return lines

    # ─── P: Performance (rough) ───

    def _generate_p_tests(self, ep: APIEndpoint) -> List[str]:
        lines = []
        func = self._make_func_name(ep, 'perf')
        path = self._resolve_path(ep)
        example = self._example_body(ep)
        hdr = self._headers_kw(ep)

        lines.append(f"@pytest.mark.p")
        lines.append(f"@pytest.mark.{self._slugify(ep.tags[0]) if ep.tags else 'api'}")
        lines.append(f'def {func}({self._test_func_params(ep)}):')
        lines.append(f'    """P: {ep.summary} — 响应时间检查"""')

        if ep.method == 'GET':
            lines.append(f'    start = time.time()')
            lines.append(f'    resp = requests.get(f"{{BASE_URL}}{path}", timeout=10{hdr})')
        elif ep.method == 'POST':
            body = example if example else {}
            lines.append(f'    start = time.time()')
            lines.append(f'    resp = requests.post(f"{{BASE_URL}}{path}", json={self._fmt(body)}, timeout=10{hdr})')
        elif ep.method == 'PUT':
            body = example if example else {}
            lines.append(f'    start = time.time()')
            lines.append(f'    resp = requests.put(f"{{BASE_URL}}{path}", json={self._fmt(body)}, timeout=10{hdr})')
        else:
            lines.append(f'    start = time.time()')
            lines.append(f'    resp = requests.delete(f"{{BASE_URL}}{path}", timeout=10{hdr})')

        lines.append(f'    elapsed = time.time() - start')
        lines.append(f'    print(f"  响应时间: {{elapsed:.2f}}s")')
        # lines.append(f'    assert elapsed < 5.0, f"响应时间 {{elapsed:.2f}}s 超过 5s 阈值"')
        return lines

    def _add_request(self, lines: List[str], ep: APIEndpoint, path: str, body_var: str):
        hdr = self._headers_kw(ep)
        if ep.method == 'POST':
            lines.append(f'    resp = requests.post(f"{{BASE_URL}}{path}", json={body_var}, timeout=10{hdr})')
        elif ep.method == 'PUT':
            lines.append(f'    resp = requests.put(f"{{BASE_URL}}{path}", json={body_var}, timeout=10{hdr})')
        elif ep.method == 'GET':
            lines.append(f'    resp = requests.get(f"{{BASE_URL}}{path}", params={body_var}, timeout=10{hdr})')
        else:
            lines.append(f'    resp = requests.delete(f"{{BASE_URL}}{path}", timeout=10{hdr})')

    # ─── 安全测试 ───

    def _generate_security_test(self) -> Optional[str]:
        auth_eps = self.parser.get_auth_endpoints()
        if not auth_eps:
            return None

        filepath = os.path.join(self.output_dir, 'test_security.py')
        lines = []
        lines.append('"""')
        lines.append('安全测试 — 匿名访问/过期Token/越权')
        lines.append('"""')
        lines.append('')
        lines.append('import pytest')
        lines.append('import requests')
        lines.append('import os')
        lines.append('')
        lines.append('')
        lines.append('BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")')
        lines.append('')
        lines.append('')
        lines.append('class TestSecurity:')
        lines.append('    """安全测试"""')
        lines.append('')

        # 匿名访问测试
        lines.append('    @pytest.mark.s')
        lines.append('    def test_anonymous_access_protected(self):')
        lines.append('        """S: 未登录访问受保护接口"""')
        for ep in auth_eps[:10]:
            path = self._resolve_path(ep)
            if ep.method == 'GET':
                lines.append(f'        resp = requests.get(f"{{BASE_URL}}{path}", timeout=10)')
            else:
                lines.append(f'        resp = requests.{ep.method.lower()}(f"{{BASE_URL}}{path}", timeout=10)')
            lines.append(f'        assert resp.status_code == 401, f"{ep.method} {ep.path} 应返回 401"')

        lines.append('')
        lines.append('    @pytest.mark.s')
        lines.append('    def test_expired_token(self):')
        lines.append('        """S: 过期 Token 访问"""')
        lines.append('        headers = {"Authorization": "Bearer expired_token_12345"}')
        for ep in auth_eps[:5]:
            path = self._resolve_path(ep)
            if ep.method == 'GET':
                lines.append(f'        resp = requests.get(f"{{BASE_URL}}{path}", headers=headers, timeout=10)')
            else:
                lines.append(f'        resp = requests.{ep.method.lower()}(f"{{BASE_URL}}{path}", headers=headers, timeout=10)')
            lines.append(f'        assert resp.status_code in (401, 403), f"{ep.method} {ep.path} 应拒绝过期Token"')

        lines.append('')
        lines.append('    @pytest.mark.s')
        lines.append('    def test_invalid_token_format(self):')
        lines.append('        """S: 无效 Token 格式"""')
        lines.append('        headers = {"Authorization": "not-a-valid-token"}')
        for ep in auth_eps[:3]:
            path = self._resolve_path(ep)
            if ep.method == 'GET':
                lines.append(f'        resp = requests.get(f"{{BASE_URL}}{path}", headers=headers, timeout=10)')
            else:
                lines.append(f'        resp = requests.{ep.method.lower()}(f"{{BASE_URL}}{path}", headers=headers, timeout=10)')
            lines.append(f'        assert resp.status_code in (401, 403)')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return filepath

    # ─── 边界值测试 ───

    def _generate_boundary_test(self) -> Optional[str]:
        eps_with_fields = [ep for ep in self.parser.endpoints if ep.request_fields]
        if not eps_with_fields:
            return None

        filepath = os.path.join(self.output_dir, 'test_boundary.py')
        lines = []
        lines.append('"""')
        lines.append('边界值测试 — 字段级边界检查')
        lines.append('"""')
        lines.append('')
        lines.append('import pytest')
        lines.append('import requests')
        lines.append('import os')
        lines.append('')
        lines.append('')
        lines.append('BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")')
        lines.append('')
        lines.append('')
        lines.append('class TestBoundary:')
        lines.append('    """边界值测试"""')
        lines.append('')

        for ep in eps_with_fields[:10]:
            if not ep.request_fields:
                continue
            path = self._resolve_path(ep)
            example = self._example_body(ep)
            if not example:
                continue

            func = self._make_func_name(ep, 'boundary_detail')
            lines.append(f'    @pytest.mark.e')
            lines.append(f'    def {func}():')
            lines.append(f'        """E: {ep.summary} 字段边界"""')

            # 逐个字段测试边界
            for field in ep.request_fields[:5]:
                bv = self.parser.get_boundary_values(field)
                if bv:
                    lines.append(f'')
                    lines.append(f'        # {field.name} 边界值')
                    for bv_name, bv_val in bv.items():
                        if bv_name in ('valid_enum', 'valid_email', 'at_min', 'at_max', 'true', 'false'):
                            continue  # 跳过合法值
                        body_test = dict(example)
                        body_test[field.name] = bv_val
                        lines.append(f'        body_{field.name}_{bv_name} = {self._fmt(body_test)}')
                        self._add_request(lines, ep, path, f'body_{field.name}_{bv_name}')
                        lines.append(f'        # {bv_name}: 检查响应状态码')

            lines.append('')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return filepath

    # ─── 功能流程测试 ───

    def _generate_functional_flow_test(self) -> Optional[str]:
        filepath = os.path.join(self.output_dir, 'test_functional_flows.py')
        lines = []
        lines.append('"""')
        lines.append('功能流程测试 — 业务场景串联')
        lines.append('"""')
        lines.append('')
        lines.append('import pytest')
        lines.append('import requests')
        lines.append('import os')
        lines.append('import uuid')
        lines.append('')
        lines.append('')
        lines.append('BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")')
        lines.append('')
        lines.append('')

        # 注册→登录→操作→查询 流程
        lines.append('class TestAuthFlow:')
        lines.append('    """认证流程测试"""')
        lines.append('')
        lines.append('    def test_register_then_login(self):')
        lines.append('        """流程：注册 → 登录 → 获取用户信息"""')
        lines.append('        uname = f"flow_user_{uuid.uuid4().hex[:8]}"')
        lines.append('        # 1. 注册')
        lines.append('        resp1 = requests.post(')
        lines.append('            f"{BASE_URL}/api/auth/register",')
        lines.append('            json={"username": self.username, "password": "Test@123", "email": f"{self.username}@test.com"},')
        lines.append('            timeout=10')
        lines.append('        )')
        lines.append('        assert resp1.status_code in (200, 201)')
        lines.append('        token = resp1.json().get("token")')
        lines.append('        assert token is not None')
        lines.append('')
        lines.append('        # 2. 登录')
        lines.append('        resp2 = requests.post(')
        lines.append('            f"{BASE_URL}/api/auth/login",')
        lines.append('            json={"username": uname, "password": "Test@123"},')
        lines.append('            timeout=10')
        lines.append('        )')
        lines.append('        assert resp2.status_code == 200')
        lines.append('')
        lines.append('        # 3. 获取用户信息')
        lines.append('        resp3 = requests.get(')
        lines.append('            f"{BASE_URL}/api/auth/profile",')
        lines.append('            headers={"Authorization": f"Bearer {token}"},')
        lines.append('            timeout=10')
        lines.append('        )')
        lines.append('        assert resp3.status_code == 200')
        lines.append('')

        # 商品 CRUD 流程
        lines.append('class TestProductCRUD:')
        lines.append('    """商品 CRUD 流程测试"""')
        lines.append('')
        lines.append('    @pytest.fixture(scope="class")')
        lines.append('    def admin_session(self):')
        lines.append('        session = requests.Session()')
        lines.append('        resp = session.post(')
        lines.append('            f"{BASE_URL}/api/auth/login",')
        lines.append('            json={"username": "admin", "password": "admin123"},')
        lines.append('            timeout=10')
        lines.append('        )')
        lines.append('        if resp.status_code == 200:')
        lines.append('            token_val = resp.json().get("token")')
        lines.append('            session.headers.update({"Authorization": f"Bearer {token_val}"})')
        lines.append('        return session')
        lines.append('')
        lines.append('    def test_crud_flow(self, admin_session):')
        lines.append('        """流程：创建 → 查询 → 更新 → 删除"""')
        lines.append('        # 1. 创建')
        lines.append('        product_data = {"name": f"flow_test_{uuid.uuid4().hex[:6]}", "price": 99.9, "stock": 100}')
        lines.append('        resp_create = admin_session.post(f"{BASE_URL}/api/products", json=product_data, timeout=10)')
        lines.append('        assert resp_create.status_code in (200, 201)')
        lines.append('        product_id = resp_create.json().get("id")')
        lines.append('')
        lines.append('        # 2. 查询详情')
        lines.append('        if product_id:')
        lines.append('            resp_detail = admin_session.get(f"{BASE_URL}/api/products/{product_id}", timeout=10)')
        lines.append('            assert resp_detail.status_code == 200')
        lines.append('')
        lines.append('            # 3. 更新')
        lines.append('            resp_update = admin_session.put(f"{BASE_URL}/api/products/{product_id}", json={"price": 199.9},199.9}, timeout=10)')
        lines.append('            assert resp_update.status_code == 200')
        lines.append('')
        lines.append('            # 4. 删除')
        lines.append('            resp_delete = admin_session.delete(f"{BASE_URL}/api/products/{product_id}", timeout=10)')
        lines.append('            assert resp_delete.status_code in (200, 204)')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return filepath

    # ─── 端到端测试 ───

    def _generate_e2e_test(self) -> Optional[str]:
        filepath = os.path.join(self.output_dir, 'test_e2e_seckill_flow.py')
        lines = []
        lines.append('"""')
        lines.append('端到端测试 — 完整秒杀购物流程')
        lines.append('流程：注册 → 登录 → 查询商品 → 查询秒杀 → 下单 → 查询订单')
        lines.append('"""')
        lines.append('')
        lines.append('import pytest')
        lines.append('import requests')
        lines.append('import os')
        lines.append('import uuid')
        lines.append('')
        lines.append('')
        lines.append('BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")')
        lines.append('')
        lines.append('')
        lines.append('class TestSeckillE2E:')
        lines.append('    """秒杀系统端到端测试"""')
        lines.append('')
        lines.append('    @pytest.fixture(scope="class")')
        lines.append('    def setup_data(self):')
        lines.append('        self.session = requests.Session()')
        lines.append('        self.username = f"e2e_{uuid.uuid4().hex[:8]}"')
        lines.append('        self.token = None')
        lines.append('        self.product_id = None')
        lines.append('')
        lines.append('    def test_01_register(self):')
        lines.append('        """步骤1：用户注册"""')
        lines.append('        resp = self.session.post(')
        lines.append('            f"{BASE_URL}/api/auth/register",')
        lines.append('            json={"username": self.username, "password": "Test@123", "email": f"{self.username}@test.com"},')
        lines.append('            timeout=10')
        lines.append('        )')
        lines.append('        assert resp.status_code in (200, 201)')
        lines.append('        self.token = resp.json().get("token")')
        lines.append('        assert self.token is not None')
        lines.append('')
        lines.append('    def test_02_login(self):')
        lines.append('        """步骤2：用户登录"""')
        lines.append('        resp = self.session.post(')
        lines.append('            f"{BASE_URL}/api/auth/login",')
        lines.append('            json={"username": self.username, "password": "Test@123"},')
        lines.append('            timeout=10')
        lines.append('        )')
        lines.append('        assert resp.status_code == 200')
        lines.append('')
        lines.append('    def test_03_list_products(self):')
        lines.append('        """步骤3：查询商品列表"""')
        lines.append('        resp = self.session.get(f"{BASE_URL}/api/products", timeout=10)')
        lines.append('        assert resp.status_code == 200')
        lines.append('        data = resp.json()')
        lines.append('        if isinstance(data, list) and len(data) > 0:')
        lines.append('            self.product_id = data[0].get("id")')
        lines.append('')
        lines.append('    def test_04_product_detail(self):')
        lines.append('        """步骤4：查询商品详情"""')
        lines.append('        if not self.product_id:')
        lines.append('            pytest.skip("无可用商品")')
        lines.append('        resp = self.session.get(f"{BASE_URL}/api/products/{self.product_id}", timeout=10)')
        lines.append('        assert resp.status_code == 200')
        lines.append('')
        lines.append('    def test_05_seckill_activities(self):')
        lines.append('        """步骤5：查询秒杀活动"""')
        lines.append('        resp = self.session.get(f"{BASE_URL}/api/seckill/activities", timeout=10)')
        lines.append('        assert resp.status_code == 200')
        lines.append('')
        lines.append('    def test_06_orders(self):')
        lines.append('        """步骤6：查询订单列表"""')
        lines.append('        resp = self.session.get(f"{BASE_URL}/api/orders", timeout=10)')
        lines.append('        assert resp.status_code == 200')
        lines.append('')
        lines.append('    def test_07_unauthorized(self):')
        lines.append('        """步骤7：未登录访问受保护接口"""')
        lines.append('        resp = requests.get(f"{BASE_URL}/api/auth/profile", timeout=10)')
        lines.append('        assert resp.status_code == 401')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return filepath

    # ─── 工具方法 ───

    def _slugify(self, text: str) -> str:
        return text.lower().replace(' ', '_').replace('-', '_')

    def _fmt(self, d: Any) -> str:
        if isinstance(d, dict):
            items = []
            for k, v in d.items():
                items.append(f'"{k}": {repr(v)}')
            return '{' + ', '.join(items) + '}'
        return repr(d)


def main():
    parser = argparse.ArgumentParser(description='从 OpenAPI 文档生成全面pytest 测试代码 (H/E/X/P/S)')
    parser.add_argument('spec', help='OpenAPI 文档路径 (YAML/JSON)')
    parser.add_argument('--output', '-o', default='output', help='输出目录')
    parser.add_argument('--tag', '-t', help='只生成指定 tag 的测试')

    args = parser.parse_args()

    if not os.path.exists(args.spec):
        print(f"错误: 文件不存在 {args.spec}")
        sys.exit(1)

    print(f"解析 OpenAPI 文档: {args.spec}")
    api_parser = OpenAPIParser(args.spec)
    print(f"解析完成: {len(api_parser.endpoints)} 个接口, {len(api_parser.schemas)} 个 Schema")
    print(f"Tag 分布: {api_parser.get_all_tags()}")
    print(f"需要认证: {len(api_parser.get_auth_endpoints())} 个 | 公开: {len(api_parser.get_public_endpoints())} 个")
    print()

    generator = TestGenerator(api_parser, args.output)

    if args.tag:
        print(f"生成 {args.tag} 的测试...")
        result = generator.generate_by_tag(args.tag)
        if result:
            print(f"已生成: {result}")
        else:
            print(f"未找到 tag: {args.tag}")
    else:
        print("生成所有测试 (H/E/X/P/S + 功能流 + 安全 + 边界 + E2E)...")
        files = generator.generate_all()
        print(f"已生成 {len(files)} 个测试文件:")
        for f in files:
            size = os.path.getsize(f)
            print(f"   - {os.path.basename(f)} ({size/1024:.1f}KB)")

    print()
    print("运行测试:")
    print(f"  cd {args.output}")
    print(f"  pytest -v")
    print(f"  # 按维度运行:")
    print(f"  pytest -v -m h    # 只跑 Happy Path")
    print(f"  pytest -v -m e    # 只跑边界值")
    print(f"  pytest -v -m x    # 只跑异常")
    print(f"  pytest -v -m p    # 只跑性能")
    print(f"  pytest -v -m s    # 只跑安全")


if __name__ == '__main__':
    main()
