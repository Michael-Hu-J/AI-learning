# RAG 知识库与缺陷同步：让 AI 引用历史，让缺陷自动流转

专业版除了生成和执行测试，还有两个"基础设施"模块：

- **RAG 引擎**（`rag-engine`）：让 AI 生成用例时引用团队历史经验，而不是从零开始
- **缺陷同步**（`defect-sync`）：把 Markdown 缺陷草稿推送到禅道、云效或自研平台，打通最后一环

这两个模块不依赖后端，但需要你们先有"历史知识"和"工单系统"。

---

## RAG 引擎（rag-engine）

**什么时候用**：团队积累了大量历史用例、缺陷报告、最佳实践，希望 AI 生成新用例时能参考这些经验。

**它不干什么**：不管理知识库（走独立系统），不执行测试（走 api-skills）。

### 检索流水线

```
需求文本
  → BM25 关键词检索（关键词匹配）
  → 向量语义检索（FAISS 轻量级 / Milvus 生产级）
  → RRF 融合（两路排名加权）
  → Rerank 精排（多信号打分）
  → ContextOptimizer 裁剪（~3000 token）
  → 注入 Prompt
```

### 快速使用

**方式一：命令行**

```bash
cd rag-engine/scripts
python service.py
```

**方式二：Python 调用**

```python
from service import create_rag_service

rag = create_rag_service()

# 添加知识
rag.add_knowledge(
    texts=["登录功能测试", "Token 鉴权机制"],
    metadatas=[
        {"type": "case", "title": "登录测试"},
        {"type": "best_practice", "title": "鉴权设计"}
    ]
)

# 检索
results = rag.search("登录模块测试", top_k=3)
for r in results:
    print(f"- {r['text']} (relevance={r['relevance']:.3f})")

# 获取上下文（注入 Prompt）
context = rag.get_context("Token 鉴权", top_k=3)
print(context)
```

### 知识类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `case` | 历史测试用例 | "登录测试：用户登录功能需要支持用户名密码登录、手机号验证码登录" |
| `bug` | 历史缺陷报告 | "改密未踢下线：修改密码后旧会话应踢下线，调用 /api/profile 返回 401" |
| `best_practice` | 最佳实践 | "Token 鉴权机制，每次请求需要携带 Bearer Token" |

### 和 testcase-skills 的集成

testcase-skills/生成 的 Step 0a 会自动调用 RAG 检索：

```bash
python testcase-skills/生成/scripts/rag_prefetch.py <需求.md> --top-k 5 \
  --out output/rag_context_<模块>.md
```

生成的输出会包含：

```markdown
## 知识库检索摘要
RAG 命中 3 条：
1. [case] 登录测试：用户登录功能需要支持用户名密码登录
2. [best_practice] 鉴权设计：Token 鉴权机制，每次请求需要携带 Bearer Token
3. [bug] 改密未踢下线：修改密码后旧会话应踢下线
```

AI 在写测试点时会引用这些历史经验，补充纯 PRD 分析可能遗漏的检查项。

### 降级策略

| 情况 | 降级方式 |
|------|----------|
| Milvus 未安装 | 降级到 FAISS（轻量级） |
| FAISS 索引为空 | 降级到 BM25 关键词检索 |
| 完全无知识库 | 跳过 RAG，纯靠 LLM 生成 |

**不阻塞生成**。即使没有知识库，testcase-skills 也能正常工作，只是少了历史经验参考。

---

## 缺陷同步（defect-sync）

**什么时候用**：自动化测试失败后，需要把 Markdown 缺陷草稿推送到禅道、云效或自研平台。

**它不干什么**：不写缺陷内容（走 bug-reporter），不做 AI 根因分析（走 defect-analysis）。

### 架构位置

```
pytest 失败 → defect_drafts.py → output/bugs/*.md
                                      ↓
                            defect-analysis（根因 + 指纹）
                                      ↓
                            defect-sync（本模块）
                                      ↓
                ┌──────────┬──────────┬──────────┐
                │  禅道    │  云效    │  自研    │
                └──────────┴──────────┴──────────┘
```

### 快速使用

**1. 配置环境变量**

复制根目录 `.env.example` 中缺陷同步段落，填入真实值。

**2. 预览映射（不推送）**

```bash
cd defect-sync/scripts
python defect_sync.py preview ../../output/bugs/ --platform zentao
python defect_sync.py push ../../output/bugs/ --platform zentao --dry-run
```

**3. 确认后推送**

```bash
# 推送到禅道
python defect_sync.py push ../../output/bugs/ --platform zentao --confirm

# 推送到自研平台 Webhook
python defect_sync.py push ../../output/bugs/BUG-xxx.md --platform custom --confirm

# 仅推送 High/Critical
python defect_sync.py push ../../output/bugs/ --platform custom --confirm --severity High,Critical

# 推送 + 飞书通知
python defect_sync.py push ../../output/bugs/ --platform zentao --confirm --notify
```

**4. 检查配置**

```bash
python defect_sync.py check --platform zentao
python defect_sync.py status
```

### 平台配置

| 平台 | `--platform` | 必需环境变量 |
|------|-------------|-------------|
| 禅道 | `zentao` | `ZENTAO_BASE_URL` `ZENTAO_ACCOUNT` `ZENTAO_PASSWORD` `ZENTAO_PRODUCT_ID` |
| 云效 | `yunxiao` | `YUNXIAO_ORG_ID` `YUNXIAO_PROJECT_ID` `YUNXIAO_PAT` |
| 自研/Webhook | `custom` | `DEFECT_WEBHOOK_URL`（可选 `DEFECT_WEBHOOK_TOKEN`） |
| 飞书通知 | — | `FEISHU_WEBHOOK_URL`（配合 `--notify`） |

### pytest 自动同步（可选）

```bash
export DEFECT_SYNC=1
export DEFECT_SYNC_PLATFORM=custom      # zentao | yunxiao | custom
export DEFECT_SYNC_CONFIRM=1            # 允许推送 Draft 草稿
export DEFECT_SYNC_SEVERITY=High,Critical
export DEFECT_SYNC_NOTIFY=1             # 推送后发飞书

./run_pytest.sh output/api_smoke.py -v
```

默认行为：

- "环境"分流缺陷不自动推送
- 已同步过的指纹跳过（见 `output/bugs/sync_state.json`）
- 未设 `DEFECT_SYNC_CONFIRM=1` 时 Draft 草稿不推送

### 推送规则

| 规则 | 说明 |
|------|------|
| Draft → Confirm | 草稿默认不推送，需 `--confirm` 或人工改状态 |
| 指纹去重 | MD5(nodeid + 状态码 + 错误摘要)；同批 push 仅首条；历史见 sync_state.json |
| 环境分流跳过 | triage=「环境」的缺陷默认跳过 |
| 分析 enrichment | 读取 `output/reports/failure_analysis.json`，按 nodeid/指纹合并 category/confidence |
| sync_state.json | 记录 fingerprint → 远端 ID，防重复 |

### 自研平台对接

1. 让后端提供 `POST /api/defects` Webhook，接收 JSON
2. 复制 `config/platforms/custom.json`，按字段名改 `field_map`
3. 设置 `DEFECT_WEBHOOK_URL` 和 `DEFECT_WEBHOOK_TOKEN`
4. `python defect_sync.py preview ... --platform custom` 验证映射
5. 确认后 `--confirm` 推送

若平台 API 与 Webhook 不同，可新增 `adapters/your_platform.py` 并在 `adapters/__init__.py` 注册。

### 和 bug-reporter 的分工

| 模块 | 职责 |
|------|------|
| `bug-reporter` | 缺陷**怎么写**（模板、严重级别、字段规范） |
| `defect-analysis` | 缺陷**怎么判**（根因、指纹、置信度） |
| `defect-sync` | 缺陷**怎么推**（对接外部工单系统） |

---

## 两个模块的协作关系

```
需求文档 → RAG 检索（引用历史经验）→ 生成用例 → 执行测试
                                                    ↓
                                            失败 → 缺陷草稿
                                                    ↓
                                            defect-analysis（根因分析）
                                                    ↓
                                            defect-sync（推送到工单系统）
```

RAG 让 AI "知道团队踩过什么坑"，defect-sync 让"踩坑的记录自动流转"。两者配合，形成知识积累 → 用例生成 → 缺陷记录的闭环。

---
