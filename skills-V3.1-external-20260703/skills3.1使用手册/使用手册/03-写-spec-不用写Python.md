# 不会写 Python？先学会写这一种 Markdown

专业版里有一种文件，叫 **spec**：Markdown 正文 + 文首一段 **YAML**。

你改的是「测什么」，不是 `def test_xxx`。保存后跑 `./generate.sh`，`output/` 里会自动出现 pytest 脚本。

---

## spec 长什么样

最小结构：

```markdown
---
kind: api_pytest
base_url: http://你的服务地址:端口
cases:
  - id: TC-001
    method: POST
    path: /api/login
    json_body:
      username: "admin"
      password: "123456"
    expect_status: 200
---

# 可选说明

这里写给人看的备注，不影响生成。
```

要点：

- **`---` 之间是 YAML**，机器读  
- **`kind`** 决定生成哪种脚本  
- **`cases`** 里一条就是一个测试用例（API 场景）

把 `base_url`、路径、请求体改成你们系统的，再：

```bash
./generate.sh my_login.md
cd output && python3 -m pytest my_login.py -v
```

---

## 六种 kind（能测什么）

| kind | 测什么 | 大致要装什么 |
|------|--------|----------------|
| `api_pytest` | HTTP 接口 | pytest、requests |
| `ui_pytest_playwright` | 浏览器页面 | pytest-playwright、chromium |
| `appium_pytest` | 手机 App | Appium-Python-Client、Appium 服务 |
| `data_factory` | 造测试数据 | pymysql 等（按模板） |
| `perf_test` | 接口压测 | locust |
| `visual_regression` | UI 截图对比 | playwright、pillow 等 |

不用一次装全。做接口就先 `api_pytest`；做页面再装 Playwright。

---

## 从模板抄，比从空白写快

```bash
cp templates/api_smoke.md my_api.md
# 用记事本 / VS Code / Cursor 改 base_url 和 cases
./generate.sh my_api.md
```

`templates/` 里有多份现成例子：冒烟、登录、表单、秒杀相关命名等。  
**建议流程**：复制最接近的 → 只改变动的字段 → 生成 → `collect-only` → 再接真实环境跑全量。

---

## 和 AI 怎么配合

1. 让 AI 根据 OpenAPI 或接口列表**起草** spec（@ `api-skills` 相关 SKILL，见第 7 篇）  
2. **你审** base_url、path、鉴权字段  
3. `./generate.sh` 出脚本，进仓库、进 CI  

同一份 spec，换机器、换 CI 节点，生成结果一致——这是声明式的价值。

---

## 进阶：字段写全了吗

模板不够用时，包内提供：

```bash
python codegen/run_spec.py --print-schema
```

会打印各 kind 支持的字段说明。本手册不展开全表，**以你本机该命令输出为准**。

发版前维护者可在包根跑自检（你只需知道有这回事）：

```bash
python codegen/selftest_bundle.py
```

通过表示一批内置 spec 能校验、能生成、能 `collect-only`。

---

## 三个新手易错点

1. **`base_url` 末尾不要多写路径** —— 路径在每条 case 的 `path` 里拼。  
2. **字段名和服务端不一致** —— 例如 `username` vs `userName`，接口 400 看起来像脚本 bug。  
3. **改 spec 忘了重新 generate** —— `output/*.py` 是生成物，改 spec 后要再跑 `./generate.sh`。

---

## UI spec 一句话区别

`ui_pytest_playwright` 的 cases 里是步骤、选择器、断言 URL 等（具体字段见模板 `templates/ui_login.md`）。  
专业版 **主交付是 Python + Playwright + pytest**，不是 MidScene、也不是 `.spec.ts`。第 8 篇单独讲 UI 线。

---

## 本篇作业

```bash
cp templates/api_smoke.md homework_api.md
# 把 base_url 改成你们测试环境（或保持占位）
./generate.sh homework_api.md
cd output && python3 -m pytest homework_api.py --collect-only -q
```

---

## 下一步

要用 AI 从 PRD / OpenAPI 起草 spec，见 **`04-AI编辑器-怎么引用.md`**、**`07-接口自动化.md`**。

---

