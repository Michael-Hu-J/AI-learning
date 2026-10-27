# 改进后的代码（示例：补齐 Header、HTTP 错误与字段提取）
def fetch_github_stars(owner: str, repo: str) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "User-Agent": "OpenClaw-Agent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 403:
            return {"success": False, "error": "API 速率限制，请稍后重试"}
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
        }
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}
