# 第 8 篇：前端集成：SSE 实时日志 + 轮询兜底的双通道设计
> **代码说明**：本文中的代码示例来自完整版系统，配套代码（`配套代码/` 目录）提供了功能一致的简化版——去掉了 LLM API、LangGraph、数据库等外部依赖，替换为纯规则实现 + JSON 文件 + 内置演示应用。文章讲原理，配套代码可本地跑通，两相对照效果更好。

文中的 `apiBaseUrl` 表示 **AI测试执行平台 / 管理前端** 的后端地址，与被测系统（默认 `http://127.0.0.1:5000`，见 `WEB_BASE_URL`）是两条线：前者调度与展示日志，后者是 Playwright 实际打开的页面。

测试跑了 5 分钟，前端页面一片空白——用户不知道是卡住了还是在跑。这是我们在第一个版本里犯的错误：只有轮询，没有实时推送。后来加上了 SSE 主通道 + 轮询兜底，用户终于能在测试执行时看到日志一条条跳出来。

## 一、为什么需要实时日志？

### 1.1 传统轮询的问题

```javascript
// 反模式：纯轮询
setInterval(async () => {
  const response = await fetch(`${this.apiBaseUrl}/api/ui/scripts/status/` + execId)
  const result = await response.json()
  updateUI(result.logs)
}, 1000)  // 每秒请求一次
```

**问题**：
- 延迟高：最多 1 秒延迟
- 服务器压力大：每秒请求一次
- 带宽浪费：大部分请求没有新日志
- 用户体验差：日志不是实时显示

### 1.2 SSE 的优势

```javascript
// SSE：服务器主动推送
const es = new EventSource(`${this.apiBaseUrl}/api/ui/scripts/stream/` + execId)
es.onmessage = (event) => {
  const payload = JSON.parse(event.data)
  if (payload.type === 'log') {
    addLog(payload.log)  // 实时显示
  }
}
```

**优势**：
- 实时性：日志产生即推送
- 低开销：长连接，无需频繁请求
- 简单：浏览器原生支持
- 自动重连：浏览器内置重连机制

## 二、SSE 主通道

### 2.1 后端实现

```python
# ui_fastapi.py - SSE 端点
@router.get("/scripts/stream/{exec_id}")

async def stream_execution_logs(exec_id: str):
    """SSE 输出 UI 执行日志，前端可配合轮询兜底。"""
    store = ui_execution_service._cache.get(exec_id, {})
    if not store:
        return {"code": 404, "message": "执行任务不存在"}
    
    async def event_generator():
        cursor = 0
        while True:
            store = ui_execution_service._cache.get(exec_id, {})
            if not store:
                yield "event: error\ndata: {\"message\":\"执行任务不存在\"}\n\n"
                break
            
            logs = store.get("logs", [])
            while cursor < len(logs):
                log_item = logs[cursor]
                payload = {
                    "type": "log",
                    "status": store.get("status"),
                    "log": log_item,
                    "id": cursor,  # 用于 SSE 重连后去重
                }
                yield f"id: {cursor}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                cursor += 1
            
            status = store.get("status")
            if status in ["completed", "failed", "stopped"]:
                payload = {"type": "done", "status": status, "exec_id": exec_id}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 2.2 SSE 协议格式

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

id: 0
data: {"type":"log","status":"running","log":{"time":"16:30:01","message":" Worker 启动","level":"info"}}

id: 1
data: {"type":"log","status":"running","log":{"time":"16:30:02","message":" [步骤 1] 打开页面 成功","level":"success"}}

data: {"type":"done","status":"completed","exec_id":"ui_exec_20260504163001_abc123"}
```

> `id:` 字段是 SSE 协议的一部分，浏览器会自动记录最后收到的 event ID。连接断开重连后，浏览器会在请求头中带上 `Last-Event-ID`，服务端据此跳过已发送的事件，避免重复。

### 2.3 前端实现

```javascript
// frontend/src/views/uitest/index.vue
startUiExecutionStream(execId) {
  try {
    const es = new EventSource(`${this.apiBaseUrl}/api/ui/scripts/stream/${encodeURIComponent(execId)}`)
    this.activeSse = es
    this.lastEventId = -1  // 记录最后收到的 event ID，初始为 -1 避免跳过第一条
    
    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data || '{}')
        
        // SSE 重连去重：如果 event.id <= lastEventId，跳过
        if (payload.type === 'log' && event.lastEventId !== undefined) {
          const eventId = parseInt(event.lastEventId, 10)
          if (eventId <= this.lastEventId) return  // 重连后重复的事件，跳过
          this.lastEventId = eventId
        }
        
        if (payload.type === 'log' && payload.log) {
          const log = payload.log
          this.addHealerLog({
            time: log.time || new Date().toLocaleTimeString(),
            message: log.message || '',
            level: log.level || 'info'
          })
        }
        
        if (payload.type === 'done') {
          this.stopUiExecutionChannels()
          this.clearUiExecutionSession()
        }
      } catch (e) {
        // ignore parse errors
      }
    }
    
    es.onerror = () => {
      // 浏览器会自动重连，不需要手动 close()
      // 轮询兜底在此期间保证日志不中断
      console.warn('SSE 连接断开，浏览器将自动重连')
    }
  } catch (error) {
    console.warn('SSE 建连失败，将使用轮询兜底', error)
  }
}
```

## 三、轮询兜底通道

### 3.1 为什么需要兜底？

**SSE 的局限性**：
- 某些网络环境（公司代理、防火墙）可能拦截 SSE
- 浏览器兼容性问题（旧版浏览器不支持）
- 连接不稳定时可能断开

**轮询的优势**：
- 兼容性最好（所有浏览器支持）
- 防火墙友好（标准 HTTP 请求）
- 实现简单

### 3.2 轮询实现

```javascript
// frontend/src/views/uitest/index.vue
async pollExecutionStatus(execId) {
  this.activePollTimer = setInterval(async () => {
    try {
      const response = await fetch(`${this.apiBaseUrl}/api/ui/scripts/status/${execId}`)
      const result = await response.json()
      
      if (result.code === 200) {
        const status = result.data.status
        const logs = result.data.logs || []
        
        // 增量推送新日志
        const newLogs = logs.slice(this.lastUiLogCount)
        for (const log of newLogs) {
          this.addHealerLog({
            time: log.time,
            message: log.message,
            level: log.level
          })
        }
        this.lastUiLogCount = logs.length
        
        if (status === 'completed' || status === 'failed') {
          this.stopUiExecutionChannels()
          this.clearUiExecutionSession()
          this.addHealerLog({
            time: new Date().toLocaleTimeString(),
            message: ` 执行完成！状态：${status}`,
            level: status === 'completed' ? 'success' : 'error'
          })
        }
      }
    } catch (error) {
      console.error('轮询状态失败:', error)
    }
  }, 2000)  // 轮询间隔拉长到 2 秒，减少资源消耗
}
```

### 3.3 `get_status` 实现（指向第 7 篇的缓存）

轮询接口 `/api/ui/scripts/status/{exec_id}` 需要返回当前执行状态和日志。实现上直接读取第 7 篇的内存缓存 `_cache`：

```python
# ui_fastapi.py - 状态查询端点
@router.get("/scripts/status/{exec_id}")
async def get_execution_status(exec_id: str):
    """返回执行状态和日志（供轮询使用）"""
    store = ui_execution_service._cache.get(exec_id, {})
    if not store:
        return {"code": 404, "message": "执行任务不存在"}
    
    return {
        "code": 200,
        "data": {
            "exec_id": exec_id,
            "status": store.get("status", "unknown"),
            "logs": store.get("logs", []),
            "stats": store.get("stats", {}),
        }
    }
```

`ui_execution_service._cache.get(exec_id, {})` 的实现见第 7 篇的内存缓存 `_cache`，本质上是 `self._cache.get(exec_id)`，包含 `status`、`logs`、`stats` 等字段。

## 四、双通道协同

### 4.1 协同设计

```javascript
// 启动执行时，同时启动两个通道
async runScript(script) {
  if (!script) return
  if (!script.steps) {
    this.addHealerLog({ time: new Date().toLocaleTimeString(), message: `脚本 ${script.name} 没有可执行的步骤`, level: 'warn' })
    return
  }

  script.status = 'pending'
  
  // 切换到执行测试视图
  this.subView = 'execute'
  
  try {
    // 1. 启动执行
    const response = await fetch(`${this.apiBaseUrl}/api/ui/scripts/${script.id}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        browser: this.browser,
        headless: true,
        steps: script.steps
      })
    })
    
    const result = await response.json()
    if (!response.ok || result.code !== 200) {
      throw new Error(result.message || '启动执行失败')
    }
    
    const execId = result.data.exec_id
    
    // 2. 启动 SSE 主通道
    this.startUiExecutionStream(execId)
    
    // 3. 启动轮询兜底通道
    this.pollExecutionStatus(execId)
    
  } catch (error) {
    script.status = 'fail'
    this.addHealerLog({
      time: new Date().toLocaleTimeString(),
      message: `执行失败: ${script.name} - ${error.message}`,
      level: 'error'
    })
  }
}
```

### 4.2 如果 SSE 正常，轮询会不会浪费资源？

会浪费，但代价可控。实际运行中：

- **SSE 正常时**：轮询每 2 秒请求一次 `/status` 接口，返回的数据量很小（只返回 status + logs 数组长度），单次请求约 100-200 字节。10 个并发任务 × 2 秒间隔 ≈ 每秒 5 次请求，对 FastAPI 来说毫无压力。
- **SSE 断开时**：轮询立即兜底，用户不会看到日志中断。
- **优化方案**：可以在 SSE 正常工作时降低轮询频率（如 5 秒 → 10 秒），或者在 SSE 连接建立后暂停轮询、SSE 断开时恢复。但考虑到实现复杂度，我们选择了简单的"双通道同时跑"方案——资源浪费有，但不影响系统稳定性。

### 4.3 去重逻辑

由于两个通道可能推送相同的日志，需要去重：

```javascript
addHealerLog(logData) {
  // 去重：相同时间 + 相同消息不重复添加
  const lastLog = this.healerLogs[this.healerLogs.length - 1]
  if (lastLog && lastLog.time === logData.time && lastLog.message === logData.message) {
    return  // 重复，跳过
  }
  
  this.healerLogs.push({
    time: logData.time,
    message: logData.message,
    level: logData.level
  })
  
  // 限制日志数量
  if (this.healerLogs.length > 100) {
    this.healerLogs.shift()
  }
  
  // 滚动到底部
  this.$nextTick(() => {
    const container = this.$refs.logContainer
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}
```

### 4.4 通道管理

```javascript
stopUiExecutionChannels() {
  // 关闭 SSE
  if (this.activeSse) {
    this.activeSse.close()
    this.activeSse = null
  }
  
  // 停止轮询
  if (this.activePollTimer) {
    clearInterval(this.activePollTimer)
    this.activePollTimer = null
  }
}

clearUiExecutionSession() {
  sessionStorage.removeItem('ui_running_execution')
  this.activeExecId = ''
  this.lastUiLogCount = 0
  this.lastEventId = 0
}
```

## 五、状态恢复

### 5.1 为什么需要状态恢复？

**场景**：用户刷新页面后，需要恢复正在执行的测试状态。

**解决**：使用 localStorage 持久化执行会话。

```javascript
// 保存执行会话
persistUiExecutionSession() {
  if (!this.activeExecId) return
  sessionStorage.setItem('ui_running_execution', JSON.stringify({
    exec_id: this.activeExecId,
    started_at: Date.now()
  }))
}

// 恢复执行会话
restoreUiExecutionSession() {
  try {
    const raw = sessionStorage.getItem('ui_running_execution')
    if (!raw) return
    const session = JSON.parse(raw)
    if (!session || !session.exec_id) return
    
    this.activeExecId = session.exec_id
    this.addHealerLog({
      time: new Date().toLocaleTimeString(),
      message: `检测到未完成执行，恢复跟踪: ${session.exec_id}`,
      level: 'info'
    })
    
    // 重新启动双通道
    this.startUiExecutionStream(session.exec_id)
    this.pollExecutionStatus(session.exec_id)
  } catch (error) {
    this.clearUiExecutionSession()
  }
}
```

## 六、UI 展示

### 6.1 自愈日志面板

```vue
<template>
  <div class="panel">
    <div class="panel-header">
      <h3>Healer 自愈日志</h3>
      <span class="log-count">{{ healerLogs.length }} 条</span>
    </div>
    <div class="healer-log" ref="logContainer">
      <div v-for="(log, index) in healerLogs" :key="index" :class="['log-entry', 'log-' + log.level]">
        <span class="log-time">{{ log.time }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>
```

### 6.2 日志样式

```css
.log-entry {
  padding: 4px 8px;
  font-family: monospace;
  font-size: 12px;
  border-bottom: 1px solid #eee;
}

.log-info {
  background-color: #f0f9ff;
  color: #1e40af;
}

.log-success {
  background-color: #f0fdf4;
  color: #166534;
}

.log-error {
  background-color: #fef2f2;
  color: #991b1b;
}

.log-warning {
  background-color: #fffbeb;
  color: #92400e;
}
```

### 6.3 执行统计

```vue
<template>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="value">{{ stats_ui.total }}</div>
      <div class="label">总测试数</div>
    </div>
    <div class="stat-card success">
      <div class="value">{{ stats_ui.passed }}</div>
      <div class="label">通过</div>
    </div>
    <div class="stat-card failure">
      <div class="value">{{ stats_ui.failed }}</div>
      <div class="label">失败</div>
    </div>
    <div class="stat-card warning">
      <div class="value">{{ stats_ui.repaired }}</div>
      <div class="label">已自愈</div>
    </div>
    <div class="stat-card">
      <div class="value">{{ stats_ui.rate }}%</div>
      <div class="label">成功率</div>
    </div>
  </div>
</template>
```

## 七、踩坑经验

### 7.1 坑 1：SSE 跨域问题

**问题**：前端和后端不在同一域名时，SSE 请求被拦截。

**解决**：后端配置 CORS。

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5566"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 7.2 坑 2：SSE 连接断开

**问题**：网络不稳定时，SSE 连接可能断开。

**解决**：浏览器自动重连 + 轮询兜底 + `lastEventId` 去重。

```javascript
es.onerror = () => {
  console.warn('SSE 连接断开，浏览器将自动重连')
  // 浏览器会自动重连，轮询也会兜底
  // 重连后通过 event.lastEventId 去重，避免重复日志
}
```

### 7.3 坑 3：日志重复

**问题**：SSE 和轮询可能推送相同的日志。

**解决**：去重逻辑（相同时间 + 相同消息）+ SSE `lastEventId` 去重。

```javascript
// 前端去重
const lastLog = this.healerLogs[this.healerLogs.length - 1]
if (lastLog && lastLog.time === logData.time && lastLog.message === logData.message) {
  return  // 重复，跳过
}

// SSE 重连去重
if (payload.type === 'log' && event.lastEventId !== undefined) {
  const eventId = parseInt(event.lastEventId, 10)
  if (eventId <= this.lastEventId) return  // 重连后重复的事件，跳过
  this.lastEventId = eventId
}
```

### 7.4 坑 4：内存泄漏

**问题**：日志数组无限增长，导致内存泄漏。

**解决**：限制日志数量。

```javascript
if (this.healerLogs.length > 100) {
  this.healerLogs.shift()
}
```

## 八、总结

SSE + 轮询双通道的设计思路很简单：SSE 负责实时性，轮询负责兜底。两个通道同时跑，前端去重，后端加 `id` 字段支持 SSE 重连后跳过已发送的事件。资源上轮询确实有额外开销，但 2 秒间隔 + 小 payload 的代价远小于用户看到空白页面的体验损失。

API 地址统一使用 `this.apiBaseUrl`，避免硬编码 `localhost:8888` 导致的环境切换问题。

### 8.1 实战：双通道在项目中的实际效果

上线双通道之前，用户最常抱怨的是"不知道测试卡在哪了"。纯轮询方案下，日志是"一波一波"刷新的——用户点执行，页面空白，3 秒后才看到第一条日志。如果测试在中间卡住了，用户要等到 timeout 才知道。

**上线后**：用户点执行 → 1 秒内就看到第一条日志。每次浏览器操作、每次选择器尝试、每次自愈诊断，都是实时显示。卡在哪了、为什么卡了，用户一清二楚。

**用户反馈**：这个功能是用户"最直接能感知到的改进"，没有之一。相比三层定位、自愈系统这些后台能力，SSE 实时日志是用户每天都会看到的界面变化。

### 8.2 实战：为什么不用 WebSocket？

很多人问我为什么要用 SSE 而不是 WebSocket。区别很简单：

| 特性 | SSE | WebSocket |
|------|-----|-----------|
| 方向 | 服务端→客户端单向 | 双向 |
| 协议 | HTTP | 独立协议（ws://） |
| 实现 | 3 行代码 | 需要一个 WebSocket 库 |
| 自动重连 | 浏览器原生支持 | 需要自己实现 |
| 兼容性 | 所有现代浏览器 | 所有现代浏览器 |
| 适用场景 | 日志推送、状态更新 | 聊天、协同编辑 |

对于"日志推送"这种纯单向的场景，SSE 是最合适的选择——浏览器原生支持自动重连，不需要额外协议和库。我们的日志通道只用 SSE，完全够用。

### 8.3 实战：Session 恢复机制

用户刷新页面后，之前执行的日志丢了怎么办？我们在 `localStorage` 里缓存了最近执行的 session 信息：

```javascript
// 会话持久化
const sessionKey = `exec_session_${execId}`
sessionStorage.setItem(sessionKey, JSON.stringify({
  status: 'running',
  startTime: Date.now(),
  logs: []
}))

// 页面加载时恢复
document.addEventListener('DOMContentLoaded', () => {
  Object.keys(sessionStorage).forEach(key => {
    if (key.startsWith('exec_session_')) {
      const session = JSON.parse(sessionStorage.getItem(key))
      restoreSession(session)
    }
  })
})
```

用户刷新页面后，正在执行的测试 session 被恢复，日志继续追加。不是 100% 完美（如果浏览器缓存被清掉就丢了），但覆盖了 95% 以上的场景。

---

