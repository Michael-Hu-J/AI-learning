"""
security_scanner.py — 简易安全扫描器
用途：自动发现隐藏接口、测常见漏洞
"""
import requests
import re
from urllib.parse import urljoin

BASE = "http://localhost:5000"

# 1. 爬取所有页面，提取链接和表单
def crawl_pages(start_url):
    visited = set()
    to_visit = [start_url]
    found_endpoints = set()
    
    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        
        try:
            resp = requests.get(url, timeout=5)
            # 提取所有 <a href> 链接
            links = re.findall(r'href=[\'"]?([^\'" >]+)', resp.text)
            for link in links:
                full_url = urljoin(BASE, link)
                if BASE in full_url and full_url not in visited:
                    to_visit.append(full_url)
            
            # 提取所有 form action
            forms = re.findall(r'<form[^>]*action=[\'"]?([^\'" >]+)', resp.text)
            for form in forms:
                full_url = urljoin(BASE, form)
                found_endpoints.add(full_url)
                
            print(f"[爬取] {url} — 发现 {len(forms)} 个表单")
        except Exception as e:
            print(f"[失败] {url} — {e}")
    
    return found_endpoints

# 2. 对每个接口做基础安全测试
def test_sql_injection(url):
    payloads = ["' OR 1=1 --", "' AND 1=1 --", "' AND 1=2 --"]
    for payload in payloads:
        try:
            resp = requests.post(url, json={
                "username": payload,
                "password": "***"
            }, timeout=5)
            if resp.status_code == 200 and "登录成功" in resp.text:
                print(f"[高危] {url} 存在 SQL 注入！payload: {payload}")
                return True
        except:
            pass
    return False

def test_xss(url):
    payload = "<script>alert(1)</script>"
    try:
        resp = requests.get(url, params={"q": payload}, timeout=5)
        if payload in resp.text:
            print(f"[高危] {url} 存在 XSS 漏洞！")
            return True
    except:
        pass
    return False

# 3. 跑扫描
if __name__ == "__main__":
    print("="*50)
    print("🔍 安全扫描器启动")
    print("="*50)
    
    endpoints = crawl_pages(BASE)
    print(f"\n✅ 发现 {len(endpoints)} 个接口端点")
    
    print("\n--- SQL注入测试 ---")
    for ep in endpoints:
        test_sql_injection(ep)
    
    print("\n--- XSS测试 ---")
    for ep in endpoints:
        test_xss(ep)
    
    print("\n✅ 扫描完成")
