# 禁止输出（api-spec Skill）

本 Skill 产出 **仅** 下列形式：

✅ 带 YAML frontmatter 的 `.md` 文件  
✅ Markdown 正文中的 case 说明列表  

❌ 下列一律禁止：

| 禁止项 | 原因 |
|--------|------|
| `def test_xxx` Python 函数 | 交给 generate.sh |
| `import requests` 代码块 | 同上 |
| `playwright` / `page.click` | 属于 UI-skills |
| 无 frontmatter 的纯 Markdown 用例表 | CI 无法 generate |

若用户要求「直接给 pytest」：回复应引导先出 spec，再 `./generate.sh`。
