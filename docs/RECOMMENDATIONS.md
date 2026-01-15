# Routilux 开发团队建议书

> 基于 Overseer 构建经验的 API 改进建议

**To**: Routilux Development Team
**From**: Routilux Overseer 开发团队
**Date**: 2025-01-15
**Version**: 1.0.0

---

## 📋 执行摘要

在构建 **Routilux Overseer**（一个基于 Web 的调试和监控工具）的过程中，我们对 Routilux API 进行了全面的分析和使用。

**总体评价：⭐⭐⭐⭐⭐ 优秀**

Routilux 提供的 API 设计清晰、功能完整、文档齐全，已经非常成熟。本文档基于实际使用经验，提供一些**可选的改进建议**，旨在进一步提升开发体验和工具生态。

**重要说明**：
- ✅ 当前 API 已经完全可以生产使用
- 💡 以下建议都是**锦上添花**，非必需
- 🎯 按优先级排序，可选择性实施

---

## 🎯 高优先级建议（建议实施）

### 1. Job 列表查询过滤

**当前状态**：
```python
GET /api/jobs
# 返回所有 Jobs，无法在服务端过滤
```

**问题分析**：
- 当 Job 数量大时（>1000），前端需要获取全部数据后再过滤
- 网络传输量大，性能不佳
- 前端内存压力大

**建议方案**：
```python
GET /api/jobs?flow_id={flow_id}&status={status}&from={time}&to={time}&limit={limit}&offset={offset}

# 参数说明：
# flow_id (str, optional): 按 Flow ID 过滤
# status (str, optional): 按状态过滤（running/completed/failed/paused/cancelled）
# from (datetime, optional): 起始时间（ISO 8601 格式）
# to (datetime, optional): 结束时间（ISO 8601 格式）
# limit (int, optional): 每页数量，默认 100，最大 1000
# offset (int, optional): 偏移量，用于分页，默认 0

# 响应：
{
  "jobs": [...],      # Job 列表
  "total": 1500,      # 总数（用于分页）
  "limit": 100,       # 当前页大小
  "offset": 0         # 当前偏移
}
```

**实现示例**（假设使用 FastAPI）：
```python
from fastapi import Query, Optional
from datetime import datetime

@app.get("/api/jobs")
async def list_jobs(
    flow_id: Optional[str] = Query(None, description="Filter by flow ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    from_time: Optional[datetime] = Query(None, alias="from", description="Start time"),
    to_time: Optional[datetime] = Query(None, alias="to", description="End time"),
    limit: int = Query(100, ge=1, le=1000, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset")
):
    """
    List jobs with optional filters and pagination.

    Returns a paginated list of jobs that match the specified criteria.
    """
    jobs = await job_service.list_jobs(
        flow_id=flow_id,
        status=status,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset
    )

    total = await job_service.count_jobs(
        flow_id=flow_id,
        status=status,
        from_time=from_time,
        to_time=to_time
    )

    return {
        "jobs": [job.dict() for job in jobs],
        "total": total,
        "limit": limit,
        "offset": offset
    }
```

**使用示例**：
```typescript
// 获取特定 Flow 的失败 Jobs
const failedJobs = await api.jobs.list({
  flow_id: "my-flow",
  status: "failed",
  limit: 50
});

// 获取最近 24 小时内完成的 Jobs
const recentJobs = await api.jobs.list({
  status: "completed",
  from: new Date(Date.now() - 24 * 3600 * 1000).toISOString(),
  limit: 100
});
```

**收益**：
- ✅ 减少网络传输（90%+ 的数据量）
- ✅ 提升响应速度（大数量集时）
- ✅ 降低前端内存消耗
- ✅ 支持大规模部署（10,000+ Jobs）

**实施成本**：低（约 2-4 小时开发 + 测试）

---

### 2. 表达式求值 API

**当前状态**：
调试时只能查看完整的变量对象，无法求值表达式。

**问题分析**：
- 开发者经常需要计算表达式（如 `x + y`，`obj.attr`）
- 需要在调试会话中手动计算
- 类似 Chrome DevTools 的 Watch 功能

**建议方案**：
```python
POST /api/jobs/{job_id}/debug/evaluate

# 请求体：
{
  "expression": "x + y",           # 要求值的表达式
  "routine_id": "routine_1",       # 可选：在哪个 Routine 的上下文中求值
  "frame_index": 0                 # 可选：调用栈帧索引（默认 0 = 当前帧）
}

# 响应：
{
  "result": 15,                    # 求值结果
  "type": "int",                   # 结果类型
  "error": null                    # 如果出错，包含错误信息
}

# 错误情况：
{
  "result": null,
  "type": null,
  "error": "NameError: name 'x' is not defined"
}
```

**实现示例**：
```python
@app.post("/api/jobs/{job_id}/debug/evaluate")
async def evaluate_expression(job_id: str, request: EvalRequest):
    """
    Evaluate an expression in the context of a paused job.

    Supports Python expressions with access to local and global variables
    from the specified routine and stack frame.
    """
    try:
        # 获取调试会话
        session = debug_service.get_session(job_id)

        if session.status != "paused":
            raise HTTPException(
                status_code=400,
                detail="Job must be paused to evaluate expressions"
            )

        # 获取指定栈帧的变量
        frame = session.get_stack_frame(
            routine_id=request.routine_id,
            frame_index=request.frame_index
        )

        # 在安全的环境中求值表达式
        result = safe_eval(
            expression=request.expression,
            locals=frame.local_variables,
            globals=frame.global_variables
        )

        return {
            "result": result,
            "type": type(result).__name__,
            "error": None
        }

    except Exception as e:
        return {
            "result": None,
            "type": None,
            "error": str(e)
        }

def safe_eval(expression: str, locals: dict, globals: dict):
    """
    安全地求值表达式。

    限制可用操作，防止恶意代码执行。
    """
    # 只允许安全的内置函数
    safe_builtins = {
        "abs": abs,
        "min": min,
        "max": max,
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        # ... 其他安全的函数
    }

    # 编译表达式为 AST
    ast_node = ast.parse(expression, mode='eval')

    # 检查 AST，确保只包含安全的操作
    for node in ast.walk(ast_node):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise SecurityError("Import statements are not allowed")
        # ... 其他安全检查

    # 求值
    return eval(compile(ast_node, '<string>', 'eval'), {
        "__builtins__": safe_builtins
    }, locals)
```

**使用示例**：
```typescript
// 在调试时求值表达式
const result = await api.debug.evaluate(jobId, {
  expression: "items_processed + items_failed",
  routine_id: "process_items",
});

console.log(`Total items: ${result.result}`);  // Total items: 150

// 访问嵌套属性
const user = await api.debug.evaluate(jobId, {
  expression: "user.profile.name",
});
console.log(user.result);  // "Alice"

// 调用函数（如果允许）
const total = await api.debug.evaluate(jobId, {
  expression: "len(items)",
});
console.log(total.result);  // 42
```

**UI 展示建议**：
```typescript
// 在 Job 详情页的调试面板中添加 "Watch" 输入框
<div className="debug-watch">
  <input
    placeholder="Enter expression (e.g., x + y, obj.attr)"
    onKeyPress={async (e) => {
      if (e.key === 'Enter') {
        const result = await api.debug.evaluate(jobId, {
          expression: e.target.value
        });
        setResult(result);
      }
    }}
  />
  {result && (
    <div className="result">
      <span className="type">{result.type}</span>
      <span className="value">{JSON.stringify(result.result)}</span>
    </div>
  )}
</div>
```

**收益**：
- ✅ 大幅提升调试效率
- ✅ 支持动态计算和检查
- ✅ 类似专业调试器的体验
- ✅ 无需修改变量值就能测试假设

**实施成本**：中等（约 1-2 天开发 + 安全审查）

**安全考虑**：
- ⚠️ 表达式求值有安全风险，需要严格限制
- 建议：使用 AST 检查 + 沙箱环境
- 可选：添加配置开关，默认关闭

---

### 3. WebSocket 事件过滤

**当前状态**：
客户端连接 WebSocket 后，会接收所有事件。

**问题分析**：
- 某些场景下客户端只关心部分事件
- 大量无用事件浪费网络带宽
- 前端需要过滤所有事件

**建议方案**：
```javascript
// 客户端连接后发送订阅消息
ws.send(JSON.stringify({
  action: "subscribe",
  events: [
    "job_started",
    "job_failed",
    "breakpoint_hit"
  ]
}));

// 可选：取消订阅
ws.send(JSON.stringify({
  action: "unsubscribe",
  events: ["routine_started"]
}));

// 可选：订阅所有事件（默认行为）
ws.send(JSON.stringify({
  action: "subscribe_all"
}));
```

**服务端实现**：
```python
# WebSocket 连接管理
class WebSocketConnection:
    def __init__(self, websocket):
        self.websocket = websocket
        self.subscriptions = set()  # 订阅的事件类型
        self.subscribed_all = False   # 是否订阅所有事件

    async def subscribe(self, events: List[str]):
        """订阅特定事件"""
        self.subscriptions.update(events)
        self.subscribed_all = False

    async def unsubscribe(self, events: List[str]):
        """取消订阅"""
        self.subscriptions.difference_update(events)

    async def subscribe_all(self):
        """订阅所有事件"""
        self.subscribed_all = True
        self.subscriptions.clear()

    def should_send_event(self, event_type: str) -> bool:
        """检查是否应该发送此事件"""
        return self.subscribed_all or event_type in self.subscriptions

# WebSocket 处理器
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conn = WebSocketConnection(websocket)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            if data.get("action") == "subscribe":
                await conn.subscribe(data.get("events", []))

            elif data.get("action") == "unsubscribe":
                await conn.unsubscribe(data.get("events", []))

            elif data.get("action") == "subscribe_all":
                await conn.subscribe_all()

    except WebSocketDisconnect:
        pass

    finally:
        # 清理连接
        websocket_manager.remove_connection(conn)

# 事件广播时过滤
async def broadcast_event(event_type: str, data: dict):
    """广播事件到所有订阅的客户端"""
    for conn in websocket_manager.get_connections():
        if conn.should_send_event(event_type):
            await conn.send_json({
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            })
```

**前端实现**：
```typescript
class RoutiluxWebSocket {
  private ws: WebSocket | null = null;
  private subscriptions: Set<string> = new Set();

  async connect(url: string) {
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');

      // 连接后订阅需要的事件
      this.subscribe(['job_started', 'job_failed', 'breakpoint_hit']);
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }

  subscribe(events: string[]) {
    this.subscriptions = new Set(events);

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        events: events
      }));
    }
  }

  unsubscribe(events: string[]) {
    events.forEach(e => this.subscriptions.delete(e));

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'unsubscribe',
        events: events
      }));
    }
  }

  handleMessage(message: any) {
    // 只处理订阅的事件
    if (this.subscriptions.has(message.type) || this.subscriptions.size === 0) {
      this.emit(message.type, message.data);
    }
  }
}
```

**收益**：
- ✅ 减少 70-90% 的无用网络传输
- ✅ 降低前端 CPU 消耗（无需过滤）
- ✅ 更精细的控制
- ✅ 支持大规模并发客户端

**实施成本**：中等（约 4-6 小时开发 + 测试）

---

## 🔧 中优先级建议（可选实施）

### 4. Flow Dry-run（空运行）

**当前状态**：
创建 Job 后才能执行 Flow，无法测试。

**建议方案**：
```python
POST /api/flows/{flow_id}/dry-run

# 请求体：
{
  "entry_routine_id": "routine_1",
  "entry_params": {...},        # 启动参数
  "timeout": 30                 # 超时时间（秒）
}

# 响应：
{
  "dry_run_id": "dry_run_abc123",
  "status": "completed",         # completed/failed/timeout
  "result": {
    "execution_path": [...],     # 执行路径（访问的 Routines）
    "estimated_duration": 2.5,   # 预估执行时间（秒）
    "validation_errors": [],     # 验证错误
    "missing_inputs": [],        # 缺失的输入
    "outputs": {...}             # 输出结果（如果有）
  }
}
```

**使用场景**：
- 测试 Flow 逻辑是否正确
- 验证参数是否完整
- 预估执行时间
- 检查是否有循环依赖

**实施成本**：高（约 2-3 天开发）

---

### 5. 条件断点文档完善

**当前状态**：
Breakpoint API 支持 `condition` 字段，但缺少文档说明。

**建议**：
在 API 文档中添加：
```python
# 创建断点时支持条件表达式
POST /api/jobs/{job_id}/breakpoints
{
  "type": "routine",
  "routine_id": "process_item",
  "condition": "item_count > 100"  # 只在条件为真时暂停
}

# 支持的运算符：
# - 比较：==, !=, <, >, <=, >=
# - 逻辑：and, or, not
# - 成员：in, not in
# - 身份：is, is not

# 示例：
condition = "status == 'error'"           # 等于
condition = "retry_count >= 3"            # 大于等于
condition = "user_id in blocked_users"    # 成员检查
condition = "not is_active"               # 布尔取反
```

**实施成本**：低（纯文档工作，约 1 小时）

---

### 6. WebSocket 连接状态事件

**当前状态**：
客户端无法得知连接状态变化。

**建议方案**：
```javascript
// 服务端主动发送连接状态
{
  "type": "connection:status",
  "status": "connected",  // connected/disconnected/reconnecting
  "timestamp": "2025-01-15T10:30:00Z",
  "server_time": "2025-01-15T10:30:00Z"
}

// 心跳包
{
  "type": "ping",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**前端处理**：
```typescript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'connection:status':
      updateConnectionStatus(message.status);
      break;
    case 'ping':
      // 回复 pong
      ws.send(JSON.stringify({ type: 'pong' }));
      break;
    // ... 其他事件
  }
};
```

**收益**：
- ✅ 客户端可以显示连接状态
- ✅ 支持自动重连
- ✅ 提升用户体验

**实施成本**：低（约 2-3 小时）

---

## 📊 低优先级建议（暂不实施）

### 7. Job 模板

**建议**：不需要在 Routilux 后端实现

**理由**：
- 可以完全在前端实现（LocalStorage 保存常用参数）
- 不涉及 Routilux 核心逻辑
- Overseer 会通过插件提供此功能

**前端实现示例**：
```typescript
// 保存为模板
const template = {
  name: "Daily Data Import",
  flow_id: "data_import_flow",
  entry_params: {
    source: "s3://my-bucket/data",
    date: "${today}"
  }
};
localStorage.setItem(`job_template:${template.name}`, JSON.stringify(template));

// 使用模板启动 Job
const savedTemplate = JSON.parse(localStorage.getItem('job_template:...'));
await api.jobs.start({
  ...savedTemplate,
  entry_params: {
    ...savedTemplate.entry_params,
    date: new Date().toISOString().split('T')[0]
  }
});
```

---

### 8. 版本管理

**建议**：不需要在 Routilux 后端实现

**理由**：
- 可以通过前端插件实现
- 插件在 Flow 更新时保存 DSL 到 IndexedDB
- 不需要在 Routilux 增加存储负担

**插件实现示例**：
```typescript
// 版本管理插件
const versionPlugin = {
  install(context) {
    // 监听 Flow 更新事件
    context.events.on('flow:updated', async (flow) => {
      const dsl = await context.api.flows.export(flow.flow_id);
      context.storage.indexedDB.set('flow_versions', `${flow.flow_id}_${Date.now()}`, {
        flow_id: flow.flow_id,
        dsl,
        timestamp: new Date().toISOString(),
        version: generateVersion()
      });
    });
  }
};
```

---

### 9. 批量操作

**建议**：不需要在 Routilux 后端实现

**理由**：
- 前端可以循环调用单个操作 API
- 批量操作不是核心需求
- 减少后端复杂度

**前端实现**：
```typescript
// 批量取消 Jobs
async function batchCancelJobs(jobIds: string[]) {
  const results = await Promise.allSettled(
    jobIds.map(id => api.jobs.cancel(id))
  );

  const succeeded = results.filter(r => r.status === 'fulfilled').length;
  const failed = results.filter(r => r.status === 'rejected').length;

  console.log(`Cancelled: ${succeeded}, Failed: ${failed}`);
}
```

---

## 🎨 API 设计最佳实践

基于 Routilux API 的优秀设计，总结一些最佳实践：

### 1. RESTful 风格 ✅

Routilux 已经很好地遵循了 RESTful 原则：
```python
GET    /api/jobs           # 列表
GET    /api/jobs/{id}      # 详情
POST   /api/jobs           # 创建
POST   /api/jobs/{id}/pause  # 动作
```

**建议**：继续保持这种风格 ✅

### 2. 一致的响应格式 ✅

```python
{
  "job_id": "...",
  "flow_id": "...",
  "status": "...",
  # ... 其他字段
}
```

**建议**：添加统一的错误响应格式：
```python
# 成功
{ "data": {...} }

# 错误
{
  "error": {
    "code": "JOB_NOT_FOUND",
    "message": "Job not found",
    "details": {...}
  }
}
```

### 3. 版本控制

**建议**：考虑添加 API 版本：
```python
/api/v1/jobs
/api/v2/jobs  # 未来如果有破坏性变更
```

### 4. 速率限制

**建议**：添加速率限制保护：
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.get("/api/jobs", dependencies=[Depends(RateLimiter(times=100, seconds=60))])
async def list_jobs():
    ...
```

---

## 📚 文档改进建议

### 1. OpenAPI/Swagger 规范

**建议**：提供 OpenAPI 3.0 规范文件

**收益**：
- 自动生成交互式 API 文档
- 支持多种语言的 SDK 自动生成
- 便于前端集成

**示例**：
```yaml
openapi: 3.0.0
info:
  title: Routilux API
  version: 1.0.0
paths:
  /api/jobs:
    get:
      summary: List jobs
      parameters:
        - name: flow_id
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/JobListResponse'
```

### 2. 使用示例

在文档中添加更多实际使用示例：
```python
# 官方文档示例
from routilux import Client

# 连接到 Routilux
client = Client("http://localhost:20555")

# 启动 Job
job = client.jobs.start(
    flow_id="my_flow",
    entry_routine_id="start",
    entry_params={"user_id": 123}
)

# 监控 Job
while job.status in ["pending", "running"]:
    job.refresh()
    print(f"Progress: {job.progress}%")
    time.sleep(1)

print(f"Job completed: {job.result}")
```

### 3. WebSocket 文档

创建专门的 WebSocket 事件文档：
```markdown
## WebSocket Events

### Connection

Connect to: `ws://localhost:20555/ws`

### Event Types

#### job_started
Sent when a job is started.

```json
{
  "type": "job_started",
  "job_id": "job_123",
  "flow_id": "my_flow",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "entry_routine": "start",
    "params": {...}
  }
}
```

...
```

---

## 🔒 安全建议

### 1. CORS 配置

**建议**：提供可配置的 CORS 设置：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 可配置
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. API Key 认证（可选）

如果需要多租户或权限控制：
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not await validate_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

@app.get("/api/jobs", dependencies=[Depends(verify_api_key)])
async def list_jobs():
    ...
```

### 3. 表达式求值安全

如果实施表达式求值 API：
```python
# 使用受限的环境
SAFE_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    # ... 只包含安全的函数
}

# 禁止危险的 AST 节点
FORBIDDEN_NODES = (ast.Import, ast.ImportFrom, ast.Exec, ast.Eval)

def safe_eval(expr: str, locals: dict):
    tree = ast.parse(expr, mode='eval')

    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            raise SecurityError("Operation not allowed")

    return eval(compile(tree, '<string>', 'eval'),
                {"__builtins__": SAFE_BUILTINS}, locals)
```

---

## 🧪 测试建议

### 1. API 测试套件

提供官方的 API 测试套件：
```python
# tests/test_api.py
def test_list_jobs(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert "jobs" in response.json()

def test_start_job(client):
    response = client.post("/api/jobs", json={
        "flow_id": "test_flow",
        "entry_routine_id": "start"
    })
    assert response.status_code == 200
    assert "job_id" in response.json()
```

### 2. WebSocket 测试

```python
from fastapi.testclient import TestClient

def test_websocket_events(client):
    with client.websocket_connect("/ws") as websocket:
        # 发送订阅消息
        websocket.send_json({
            "action": "subscribe",
            "events": ["job_started"]
        })

        # 启动一个 Job
        client.post("/api/jobs", json={...})

        # 接收事件
        data = websocket.receive_json()
        assert data["type"] == "job_started"
```

---

## 📊 性能优化建议

### 1. 分页响应

对于列表 API，始终支持分页：
```python
@app.get("/api/jobs")
async def list_jobs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    return {
        "jobs": jobs[offset:offset+limit],
        "total": len(jobs),
        "limit": limit,
        "offset": offset
    }
```

### 2. 字段过滤

允许客户端指定返回的字段：
```python
@app.get("/api/jobs/{job_id}")
async def get_job(
    job_id: str,
    fields: Optional[str] = Query(None)  # "job_id,status,created_at"
):
    job = await job_service.get(job_id)

    if fields:
        field_list = fields.split(",")
        return {k: v for k, v in job.items() if k in field_list}

    return job
```

### 3. 压缩响应

启用响应压缩：
```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 🚀 实施优先级总结

### 立即实施（1-2 周）
1. ✅ Job 查询过滤 - 高价值，低成本
2. ✅ WebSocket 连接状态事件 - 用户体验提升

### 短期实施（1-2 个月）
3. ✅ 表达式求值 API - 调试体验大幅提升
4. ✅ WebSocket 事件过滤 - 性能优化
5. ✅ 条件断点文档 - 纯文档工作

### 中期考虑（3-6 个月）
6. ⏸️ Flow Dry-run - 需要更多设计
7. ⏸️ OpenAPI 规范 - 文档工具链

### 不建议实施
- ❌ Job 模板 - 前端实现即可
- ❌ 版本管理 - 前端插件实现
- ❌ 批量操作 - 前端循环即可
- ❌ 时间旅行调试 - 过于复杂

---

## 📝 反馈渠道

如果有任何问题或需要进一步讨论：
- GitHub Issues: [Routilux Issues](https://github.com/lzjever/routilux/issues)
- Email: [your-email@example.com]

---

## 🎉 结语

Routilux 是一个优秀的项目，API 设计清晰、功能完整。以上建议都是基于实际使用经验的**可选改进**，旨在让优秀的工具变得更好。

**再次强调**：
- ✅ 当前 API 已经完全可以生产使用
- 💡 所有建议都是锦上添花
- 🎯 可以根据优先级选择性实施

感谢 Routilux 团队的出色工作！

---

**文档版本**: 1.0.0
**创建日期**: 2025-01-15
**作者**: Routilux Overseer Team
