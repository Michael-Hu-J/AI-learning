---
kind: ui_pytest_playwright
base_url: http://127.0.0.1:5000
viewport:
  width: 1280
  height: 720
steps:
  - action: goto
    path: /login
  - action: fill
    l1_label: "用户名"
    value: "admin"
  - action: fill
    l1_label: "密码"
    value: "&lt;PASSWORD&gt;"
  - action: click
    l1_role: button
    l1_name: "登录"
expect:
  - type: visible_text
    text: "商品"
    exact: false
---

# UI 登录冒烟（教学用声明式 spec）

本文件是 **第 2 篇路径二** 的最小示例，说明 `kind: ui_pytest_playwright` 如何描述步骤与期望。

本示例不包含 `generate.sh`。渲染为 `test_*.py` 及完整模板（`ui_form`、`ui_e2e`、`visual_regression` 等）需自行实现。

与路径一（`worker/ui_worker.py` 的 JSON `action/target/value`）对比：

| 维度 | 路径一 JSON 步骤 | 路径二 ui_pytest spec |
|------|------------------|------------------------|
| 维护 | 偏运行时编排、前端可编辑 | 偏版本库评审、CI 增量 |
| 定位 | `target` 常为 CSS | `l1_label` / `l1_role` 等契约字段 |
| 本课代码 | `配套代码/worker/` | 本示例仅结构说明 |
