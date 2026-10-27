# 比如你要从页面上爬出所有链接，验证是否404
from bs4 import BeautifulSoup
import requests

response = requests.get("http://localhost:5001")
soup = BeautifulSoup(response.text, "html.parser")

for link in soup.find_all("a"):
    href = link.get("href")
    print(f"链接：{href}")
    # 检查是否 404
    if href and href.startswith("/"):
        resp = requests.get(f"http://localhost:5001{href}")
        status = "✅" if resp.status_code == 200 else "❌"
        print(f"  {status} {resp.status_code}")
