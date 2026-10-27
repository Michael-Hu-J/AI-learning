@app.post('/api/login')
def login(username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password == password:
        return {"token": generate_token(user.id)}
    return {"error": "Invalid credentials"}

import re

def detect_security_vulnerabilities(code: str) -> dict:
    """基于规则的安全漏洞检测"""
    vulnerabilities = []
    
    # SQL注入检测
    sql_patterns = [
        r'filter\s*\(\s*\w+\.\w+\s*==\s*\w+',
        r'WHERE\s+\w+\s*=\s*["\']?\s*\+',
        r'f["\'].*SELECT.*\{',
    ]
    for p in sql_patterns:
        if re.search(p, code, re.IGNORECASE):
            vulnerabilities.append({
                'type': 'SQL注入',
                'severity': 'high',
                'fix': '使用参数化查询'
            })
    
    # 密码明文比较
    if re.search(r'password\s*==\s*\w+', code, re.IGNORECASE):
        vulnerabilities.append({
            'type': '密码明文比较',
            'severity': 'high',
            'fix': '使用bcrypt哈希比较'
        })
    
    # XSS漏洞
    if re.search(r'return\s+.*\+.*request', code, re.IGNORECASE):
        vulnerabilities.append({
            'type': 'XSS',
            'severity': 'medium',
            'fix': '对用户输入进行HTML转义'
        })
    
    # 硬编码密钥
    if re.search(r'(api_key|secret|token)\s*=\s*["\'][^"\']{8,}["\']', code, re.IGNORECASE):
        vulnerabilities.append({
            'type': '硬编码密钥',
            'severity': 'high',
            'fix': '使用环境变量'
        })
    
    # 命令注入
    if re.search(r'os\.system\s*\(\s*\w+', code):
        vulnerabilities.append({
            'type': '命令注入',
            'severity': 'critical',
            'fix': '使用subprocess.run()限制参数'
        })
    
    # 代码注入
    if re.search(r'\beval\s*\(', code) or re.search(r'\bexec\s*\(', code):
        vulnerabilities.append({
            'type': '代码注入',
            'severity': 'critical',
            'fix': '禁止使用 eval/exec'
        })
    
    return {'vulnerabilities': vulnerabilities, 'safe': len(vulnerabilities) == 0}

def test_code_correctness(generated_code: str, test_cases: list) -> dict:
    """代码正确性测试：生成测试并执行"""
    import tempfile, subprocess, os, shutil
    
    temp_dir = tempfile.mkdtemp()
    code_file = os.path.join(temp_dir, 'gen.py')
    with open(code_file, 'w') as f:
        f.write(generated_code)
    
    test_file = os.path.join(temp_dir, 'test_gen.py')
    with open(test_file, 'w') as f:
        f.write("import pytest\nfrom gen import *\n\n")
        for i, tc in enumerate(test_cases):
            f.write(f"def test_{i}():\n    assert {tc['assertion']}\n")
    
    result = subprocess.run(
        ['python', '-m', 'pytest', test_file, '-v'],
        capture_output=True, text=True, timeout=60, cwd=temp_dir
    )
    shutil.rmtree(temp_dir)
    
    return {'passed': result.returncode == 0, 'output': result.stdout}

def test_context_retrieval(project_dir: str, query: str) -> dict:
    """上下文检索测试"""
    from code_context import CodeContext
    
    ctx = CodeContext(project_dir)
    related_files = ctx.retrieve(query, top_k=5)
    
    return {
        'query': query,
        'related_files': related_files,
        'passed': len(related_files) > 0 and all(
            not f.startswith('.') for f in related_files
        )
    }

def run_pipeline(requirement: str, project_dir: str) -> dict:
    """端到端流水线，任一阶段失败则整体失败"""
    context = retrieve_context(project_dir, requirement)
    code = generate_code(requirement, context)
    
    syntax = check_syntax(code)
    security = detect_security_vulnerabilities(code)
    quality_score = compute_quality_score(syntax, security)
    
    tests = generate_and_run_tests(code)
    
    success = (
        syntax['valid'] and
        security['safe'] and
        quality_score >= 0.6 and
        tests['passed']
    )
    
    return {
        'success': success,
        'syntax': syntax,
        'security': security,
        'quality_score': quality_score,
        'tests': tests
    }

import subprocess

def run_bandit(code_file: str) -> dict:
    """使用bandit扫描Python代码"""
    result = subprocess.run(
        ['bandit', '-r', code_file, '-f', 'json'],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        return {'safe': True, 'issues': []}
    
    import json
    data = json.loads(result.stdout)
    issues = []
    for issue in data.get('results', []):
        issues.append({
            'type': issue.get('test_name', 'unknown'),
            'severity': issue.get('issue_severity', 'MEDIUM'),
            'confidence': issue.get('issue_confidence', 'MEDIUM'),
            'line': issue.get('line_number', 0),
            'message': issue.get('issue_text', '')
        })
    
    return {'safe': len(issues) == 0, 'issues': issues}

def analyze_with_sonarqube(project_key: str) -> dict:
    """调用SonarQube API获取代码质量报告"""
    import requests
    
    response = requests.get(
        f'http://sonarqube.example.com/api/measures/component',
        params={
            'component': project_key,
            'metricKeys': [
                'code_smells', 'bugs', 'vulnerabilities',
                'security_rating', 'reliability_rating'
            ]
        },
        auth=('token', 'your-token'),
        timeout=30
    )
    
    data = response.json()
    measures = {m['metric']: m['value'] for m in data['component']['measures']}
    
    return {
        'code_smells': int(measures.get('code_smells', 0)),
        'bugs': int(measures.get('bugs', 0)),
        'vulnerabilities': int(measures.get('vulnerabilities', 0)),
        'security_rating': measures.get('security_rating', 'A'),
        'reliability_rating': measures.get('reliability_rating', 'A'),
        'quality_gate': measures.get('security_rating', 'A') == 'A'
    }

# 为AI生成的代码自动生成pytest测试
def generate_pytest_tests(generated_code: str, requirements: list) -> str:
    """生成pytest测试代码"""
    test_lines = [
        "import pytest",
        "from gen import *",
        "",
    ]
    
    for i, req in enumerate(requirements):
        test_lines.append(f"@pytest.mark.parametrize('input_val,expected', [")
        for case in req['cases']:
            test_lines.append(f"    ({case['input']}, {case['expected']}),")
        test_lines.append("])")
        test_lines.append(f"def test_{req['name']}(input_val, expected):")
        test_lines.append(f"    assert {req['function']}(input_val) == expected")
        test_lines.append("")
    
    return "\n".join(test_lines)
