# Routilux 调试器与监控器前端开发需求文档

## 文档版本
- **版本**: 1.0
- **日期**: 2024-12-19
- **目标**: 为前端开发团队提供完整、准确、清晰的前端开发需求

---

## 目录

1. [概述](#1-概述)
2. [系统架构](#2-系统架构)
3. [API 接口规范](#3-api-接口规范)
4. [WebSocket 实时通信](#4-websocket-实时通信)
5. [数据模型](#5-数据模型)
6. [功能模块详细说明](#6-功能模块详细说明)
7. [用户界面需求](#7-用户界面需求)
8. [交互流程](#8-交互流程)
9. [错误处理](#9-错误处理)
10. [技术规范](#10-技术规范)

---

## 1. 概述

### 1.1 项目背景

Routilux 是一个事件驱动的工作流编排框架。本前端系统用于提供：
- **Flow Builder**: 可视化工作流设计器
- **Job Monitor**: 实时作业监控面板
- **Debugger**: 交互式调试器（支持断点、单步执行、变量查看）

### 1.2 核心功能

1. **Flow 管理**
   - 创建、查看、编辑、删除 Flow
   - 导入/导出 DSL（YAML/JSON）
   - Flow 结构验证

2. **Job 管理**
   - 启动、暂停、恢复、取消 Job
   - 实时监控 Job 执行状态
   - 查看 Job 历史

3. **断点调试**
   - 设置/删除断点（routine/slot/event 级别）
   - 条件断点
   - 断点命中通知

4. **调试控制**
   - 暂停/恢复执行
   - 单步执行（step over/step into）
   - 查看/修改变量
   - 查看调用栈

5. **监控指标**
   - 实时执行指标
   - 执行追踪
   - 错误日志

### 1.3 技术栈建议

- **前端框架**: React/Vue/Angular（推荐 React）
- **状态管理**: Redux/Vuex/Zustand
- **WebSocket**: 原生 WebSocket API 或 Socket.io
- **UI 组件库**: Ant Design / Material-UI / Element Plus
- **图表库**: ECharts / Chart.js / D3.js（用于监控可视化）
- **代码编辑器**: Monaco Editor / CodeMirror（用于 DSL 编辑）

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端应用                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │Flow      │  │Job       │  │Debugger  │             │
│  │Builder   │  │Monitor   │  │          │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│       │             │             │                    │
│       └─────────────┴─────────────┘                    │
│                    │                                    │
│         ┌──────────┴──────────┐                        │
│         │   API Client        │                        │
│         │   WebSocket Client  │                        │
│         └──────────┬──────────┘                        │
└────────────────────┼──────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼────┐          ┌───────▼──────┐
    │ REST API│          │  WebSocket   │
    │         │          │   Server     │
    └────┬────┘          └───────┬──────┘
         │                       │
    ┌────▼───────────────────────▼────┐
    │      Routilux Backend            │
    │  (FastAPI + Monitoring Core)     │
    └──────────────────────────────────┘
```

### 2.2 模块划分

#### 2.2.1 Flow Builder 模块
- Flow 列表视图
- Flow 编辑器（可视化 + DSL 编辑）
- Routine 管理
- Connection 管理
- DSL 导入/导出

#### 2.2.2 Job Monitor 模块
- Job 列表视图
- Job 详情面板
- 实时指标图表
- 执行追踪时间线
- 错误日志

#### 2.2.3 Debugger 模块
- 断点管理面板
- 调试控制工具栏
- 变量查看器
- 调用栈视图
- 代码/执行上下文视图

---

## 3. API 接口规范

### 3.1 基础信息

- **Base URL**: `http://localhost:8000` (开发环境)
- **API Prefix**: `/api`
- **Content-Type**: `application/json`
- **认证**: 当前版本无需认证（后续版本可能添加）

### 3.2 Flow 管理 API

#### 3.2.1 获取 Flow 列表

**请求**
```http
GET /api/flows
```

**响应** (200 OK)
```json
{
  "flows": [
    {
      "flow_id": "example_flow",
      "routines": {
        "r1": {
          "routine_id": "r1",
          "class_name": "Routine",
          "slots": ["trigger", "input"],
          "events": ["output", "error"],
          "config": {}
        }
      },
      "connections": [
        {
          "connection_id": "conn_0",
          "source_routine": "r1",
          "source_event": "output",
          "target_routine": "r2",
          "target_slot": "input",
          "param_mapping": null
        }
      ],
      "execution_strategy": "sequential",
      "max_workers": 5
    }
  ],
  "total": 1
}
```

#### 3.2.2 获取 Flow 详情

**请求**
```http
GET /api/flows/{flow_id}
```

**响应** (200 OK)
```json
{
  "flow_id": "example_flow",
  "routines": { /* 同列表接口 */ },
  "connections": [ /* 同列表接口 */ ],
  "execution_strategy": "sequential",
  "max_workers": 5
}
```

**错误响应** (404 Not Found)
```json
{
  "detail": "Flow 'example_flow' not found"
}
```

#### 3.2.3 创建 Flow

**请求**
```http
POST /api/flows
Content-Type: application/json
```

**请求体** (方式1: 空 Flow)
```json
{
  "flow_id": "new_flow"
}
```

**请求体** (方式2: 从 DSL Dict)
```json
{
  "flow_id": "new_flow",
  "dsl_dict": {
    "flow_id": "new_flow",
    "routines": {
      "r1": {
        "class": "routilux.routine.Routine"
      }
    },
    "connections": []
  }
}
```

**请求体** (方式3: 从 YAML DSL)
```json
{
  "flow_id": "new_flow",
  "dsl": "flow_id: new_flow\nroutines:\n  r1:\n    class: routilux.routine.Routine\nconnections: []"
}
```

**响应** (201 Created)
```json
{
  "flow_id": "new_flow",
  "routines": {},
  "connections": [],
  "execution_strategy": "sequential",
  "max_workers": 5
}
```

#### 3.2.4 删除 Flow

**请求**
```http
DELETE /api/flows/{flow_id}
```

**响应** (204 No Content)

#### 3.2.5 导出 Flow DSL

**请求**
```http
GET /api/flows/{flow_id}/dsl?format=yaml
GET /api/flows/{flow_id}/dsl?format=json
```

**响应** (200 OK)
```json
{
  "format": "yaml",
  "dsl": "flow_id: example_flow\nroutines:\n  r1:\n    class: routilux.routine.Routine\nconnections: []"
}
```

或
```json
{
  "format": "json",
  "dsl": "{\n  \"flow_id\": \"example_flow\",\n  \"routines\": {\n    \"r1\": {\n      \"class\": \"routilux.routine.Routine\"\n    }\n  },\n  \"connections\": []\n}"
}
```

#### 3.2.6 验证 Flow

**请求**
```http
POST /api/flows/{flow_id}/validate
```

**响应** (200 OK)
```json
{
  "valid": true,
  "issues": []
}
```

或
```json
{
  "valid": false,
  "issues": [
    "Circular dependency detected: r1 -> r2 -> r1",
    "Unconnected event: r1.output"
  ]
}
```

#### 3.2.7 获取 Flow 中的 Routines

**请求**
```http
GET /api/flows/{flow_id}/routines
```

**响应** (200 OK)
```json
{
  "r1": {
    "routine_id": "r1",
    "class_name": "Routine",
    "slots": ["trigger", "input"],
    "events": ["output"],
    "config": {}
  }
}
```

#### 3.2.8 获取 Flow 中的 Connections

**请求**
```http
GET /api/flows/{flow_id}/connections
```

**响应** (200 OK)
```json
[
  {
    "connection_id": "conn_0",
    "source_routine": "r1",
    "source_event": "output",
    "target_routine": "r2",
    "target_slot": "input",
    "param_mapping": null
  }
]
```

#### 3.2.9 添加 Routine 到 Flow

**请求**
```http
POST /api/flows/{flow_id}/routines?routine_id=r1&class_path=routilux.routine.Routine
Content-Type: application/json
```

**请求体** (可选)
```json
{
  "config": {
    "key": "value"
  }
}
```

**响应** (200 OK)
```json
{
  "routine_id": "r1",
  "status": "added"
}
```

#### 3.2.10 添加 Connection 到 Flow

**请求**
```http
POST /api/flows/{flow_id}/connections
Content-Type: application/json
```

**请求体**
```json
{
  "source_routine": "r1",
  "source_event": "output",
  "target_routine": "r2",
  "target_slot": "input",
  "param_mapping": {
    "old_param": "new_param"
  }
}
```

**响应** (200 OK)
```json
{
  "status": "connected"
}
```

#### 3.2.11 从 Flow 中删除 Routine

**请求**
```http
DELETE /api/flows/{flow_id}/routines/{routine_id}
```

**响应** (204 No Content)

#### 3.2.12 从 Flow 中删除 Connection

**请求**
```http
DELETE /api/flows/{flow_id}/connections/{connection_index}
```

**响应** (204 No Content)

### 3.3 Job 管理 API

#### 3.3.1 启动 Job

**请求**
```http
POST /api/jobs
Content-Type: application/json
```

**请求体**
```json
{
  "flow_id": "example_flow",
  "entry_routine_id": "r1",
  "entry_params": {
    "param1": "value1"
  },
  "timeout": 300.0
}
```

**响应** (201 Created)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "flow_id": "example_flow",
  "status": "running",
  "created_at": "2024-12-19T10:00:00Z",
  "started_at": "2024-12-19T10:00:00Z",
  "completed_at": null,
  "error": null
}
```

#### 3.3.2 获取 Job 列表

**请求**
```http
GET /api/jobs
```

**响应** (200 OK)
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "flow_id": "example_flow",
      "status": "completed",
      "created_at": "2024-12-19T10:00:00Z",
      "started_at": "2024-12-19T10:00:00Z",
      "completed_at": "2024-12-19T10:00:05Z",
      "error": null
    }
  ],
  "total": 1
}
```

#### 3.3.3 获取 Job 详情

**请求**
```http
GET /api/jobs/{job_id}
```

**响应** (200 OK)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "flow_id": "example_flow",
  "status": "running",
  "created_at": "2024-12-19T10:00:00Z",
  "started_at": "2024-12-19T10:00:00Z",
  "completed_at": null,
  "error": null
}
```

#### 3.3.4 暂停 Job

**请求**
```http
POST /api/jobs/{job_id}/pause
```

**响应** (200 OK)
```json
{
  "status": "paused",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 3.3.5 恢复 Job

**请求**
```http
POST /api/jobs/{job_id}/resume
```

**响应** (200 OK)
```json
{
  "status": "resumed",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 3.3.6 取消 Job

**请求**
```http
POST /api/jobs/{job_id}/cancel
```

**响应** (200 OK)
```json
{
  "status": "cancelled",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 3.3.7 获取 Job 状态

**请求**
```http
GET /api/jobs/{job_id}/status
```

**响应** (200 OK)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "flow_id": "example_flow"
}
```

**状态值说明**:
- `running`: 正在执行
- `completed`: 执行完成
- `failed`: 执行失败
- `paused`: 已暂停
- `cancelled`: 已取消

#### 3.3.8 获取 Job 完整状态

**请求**
```http
GET /api/jobs/{job_id}/state
```

**响应** (200 OK)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "flow_id": "example_flow",
  "status": "running",
  "shared_data": {},
  "routine_states": {
    "r1": {
      "status": "completed"
    }
  }
}
```

### 3.4 断点管理 API

#### 3.4.1 创建断点

**请求**
```http
POST /api/jobs/{job_id}/breakpoints
Content-Type: application/json
```

**请求体** (Routine 断点)
```json
{
  "type": "routine",
  "routine_id": "r1",
  "enabled": true
}
```

**请求体** (Slot 断点)
```json
{
  "type": "slot",
  "routine_id": "r1",
  "slot_name": "input",
  "enabled": true
}
```

**请求体** (Event 断点)
```json
{
  "type": "event",
  "routine_id": "r1",
  "event_name": "output",
  "enabled": true
}
```

**请求体** (条件断点)
```json
{
  "type": "routine",
  "routine_id": "r1",
  "condition": "data.get('value', 0) > 10",
  "enabled": true
}
```

**响应** (201 Created)
```json
{
  "breakpoint_id": "bp-123456",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "routine",
  "routine_id": "r1",
  "slot_name": null,
  "event_name": null,
  "condition": null,
  "enabled": true,
  "hit_count": 0
}
```

#### 3.4.2 获取断点列表

**请求**
```http
GET /api/jobs/{job_id}/breakpoints
```

**响应** (200 OK)
```json
{
  "breakpoints": [
    {
      "breakpoint_id": "bp-123456",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "routine",
      "routine_id": "r1",
      "slot_name": null,
      "event_name": null,
      "condition": null,
      "enabled": true,
      "hit_count": 3
    }
  ],
  "total": 1
}
```

#### 3.4.3 删除断点

**请求**
```http
DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id}
```

**响应** (204 No Content)

#### 3.4.4 更新断点

**请求**
```http
PUT /api/jobs/{job_id}/breakpoints/{breakpoint_id}
Content-Type: application/json
```

**请求体**
```json
{
  "enabled": false
}
```

**响应** (200 OK)
```json
{
  "breakpoint_id": "bp-123456",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "routine",
  "routine_id": "r1",
  "slot_name": null,
  "event_name": null,
  "condition": null,
  "enabled": false,
  "hit_count": 3
}
```

### 3.5 调试操作 API

#### 3.5.1 获取调试会话信息

**请求**
```http
GET /api/jobs/{job_id}/debug/session
```

**响应** (200 OK)
```json
{
  "session_id": "session-123456",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "paused",
  "paused_at": {
    "routine_id": "r1"
  },
  "call_stack_depth": 1
}
```

**状态值说明**:
- `running`: 正在运行
- `paused`: 已暂停（在断点处）
- `stepping`: 单步执行中

#### 3.5.2 恢复执行

**请求**
```http
POST /api/jobs/{job_id}/debug/resume
```

**响应** (200 OK)
```json
{
  "status": "resumed",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 3.5.3 单步跳过 (Step Over)

**请求**
```http
POST /api/jobs/{job_id}/debug/step-over
```

**响应** (200 OK)
```json
{
  "status": "stepping",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "step_mode": "over"
}
```

#### 3.5.4 单步进入 (Step Into)

**请求**
```http
POST /api/jobs/{job_id}/debug/step-into
```

**响应** (200 OK)
```json
{
  "status": "stepping",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "step_mode": "into"
}
```

#### 3.5.5 获取变量

**请求**
```http
GET /api/jobs/{job_id}/debug/variables?routine_id=r1
```

**响应** (200 OK)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "routine_id": "r1",
  "variables": {
    "data": {
      "value": 42
    },
    "result": "success"
  }
}
```

#### 3.5.6 设置变量

**请求**
```http
PUT /api/jobs/{job_id}/debug/variables/{variable_name}
Content-Type: application/json
```

**请求体**
```json
{
  "value": "new_value"
}
```

**响应** (200 OK)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "variable": "data",
  "value": "new_value"
}
```

#### 3.5.7 获取调用栈

**请求**
```http
GET /api/jobs/{job_id}/debug/call-stack
```

**响应** (200 OK)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "call_stack": [
    {
      "routine_id": "r1",
      "slot_name": "input",
      "event_name": null,
      "variables": ["data", "result"]
    },
    {
      "routine_id": "r2",
      "slot_name": "trigger",
      "event_name": null,
      "variables": ["param"]
    }
  ]
}
```

### 3.6 监控 API

#### 3.6.1 获取 Job 执行指标

**请求**
```http
GET /api/jobs/{job_id}/metrics
```

**响应** (200 OK)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "flow_id": "example_flow",
  "start_time": "2024-12-19T10:00:00Z",
  "end_time": null,
  "duration": null,
  "routine_metrics": {
    "r1": {
      "routine_id": "r1",
      "execution_count": 3,
      "total_duration": 1.5,
      "avg_duration": 0.5,
      "min_duration": 0.3,
      "max_duration": 0.7,
      "error_count": 0,
      "last_execution": "2024-12-19T10:00:05Z"
    }
  },
  "total_events": 10,
  "total_slot_calls": 5,
  "total_event_emits": 5,
  "errors": []
}
```

#### 3.6.2 获取 Job 执行追踪

**请求**
```http
GET /api/jobs/{job_id}/trace?limit=100
```

**响应** (200 OK)
```json
{
  "events": [
    {
      "event_id": "event-1",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "routine_id": "r1",
      "event_type": "routine_start",
      "timestamp": "2024-12-19T10:00:00Z",
      "data": {},
      "duration": null,
      "status": null
    },
    {
      "event_id": "event-2",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "routine_id": "r1",
      "event_type": "slot_call",
      "timestamp": "2024-12-19T10:00:00.1Z",
      "data": {
        "slot_name": "input",
        "data": {
          "value": 42
        }
      },
      "duration": null,
      "status": null
    },
    {
      "event_id": "event-3",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "routine_id": "r1",
      "event_type": "routine_end",
      "timestamp": "2024-12-19T10:00:00.5Z",
      "data": {},
      "duration": 0.5,
      "status": "completed"
    }
  ],
  "total": 3
}
```

**事件类型说明**:
- `routine_start`: Routine 开始执行
- `routine_end`: Routine 执行结束
- `slot_call`: Slot 被调用
- `event_emit`: Event 被触发

#### 3.6.3 获取 Job 日志

**请求**
```http
GET /api/jobs/{job_id}/logs?level=error&limit=50
```

**响应** (200 OK)
```json
{
  "logs": [
    {
      "timestamp": "2024-12-19T10:00:05Z",
      "level": "ERROR",
      "routine_id": "r1",
      "message": "ValueError: Invalid input",
      "traceback": "Traceback (most recent call last):\n  ..."
    }
  ],
  "total": 1
}
```

#### 3.6.4 获取 Flow 级别指标

**请求**
```http
GET /api/flows/{flow_id}/metrics
```

**响应** (200 OK)
```json
{
  "flow_id": "example_flow",
  "total_jobs": 10,
  "completed_jobs": 8,
  "failed_jobs": 1,
  "running_jobs": 1,
  "avg_duration": 5.2,
  "total_executions": 50
}
```

### 3.7 健康检查 API

#### 3.7.1 根端点

**请求**
```http
GET /
```

**响应** (200 OK)
```json
{
  "name": "Routilux API",
  "version": "0.10.0",
  "description": "Monitoring, debugging, and flow builder API"
}
```

#### 3.7.2 健康检查

**请求**
```http
GET /api/health
```

**响应** (200 OK)
```json
{
  "status": "healthy"
}
```

---

## 4. WebSocket 实时通信

### 4.1 WebSocket 端点

所有 WebSocket 端点使用 `ws://` 或 `wss://` 协议，路径前缀为 `/api/ws`

### 4.2 Job 监控 WebSocket

#### 4.2.1 连接

**端点**: `ws://localhost:8000/api/ws/jobs/{job_id}/monitor`

**连接流程**:
1. 客户端发起 WebSocket 连接
2. 服务器验证 job_id 是否存在
3. 如果不存在，服务器关闭连接（code: 1008）
4. 如果存在，服务器接受连接并发送初始指标

#### 4.2.2 消息格式

**服务器 → 客户端: 初始指标**
```json
{
  "type": "metrics",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "flow_id": "example_flow",
    "start_time": "2024-12-19T10:00:00Z",
    "end_time": null,
    "duration": null,
    "routine_metrics": {
      "r1": {
        "routine_id": "r1",
        "execution_count": 3,
        "total_duration": 1.5,
        "avg_duration": 0.5,
        "min_duration": 0.3,
        "max_duration": 0.7,
        "error_count": 0,
        "last_execution": "2024-12-19T10:00:05Z"
      }
    },
    "total_events": 10,
    "total_slot_calls": 5,
    "total_event_emits": 5,
    "errors": []
  }
}
```

**服务器 → 客户端: 定期更新** (每秒)
```json
{
  "type": "metrics",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": { /* 同初始指标格式 */ }
}
```

**服务器 → 客户端: Ping** (保持连接)
```json
{
  "type": "ping"
}
```

**客户端 → 服务器**: 无需发送消息（只接收）

#### 4.2.3 断开连接

- 客户端主动关闭连接
- Job 不存在时服务器关闭连接
- 网络错误自动断开

### 4.3 调试事件 WebSocket

#### 4.3.1 连接

**端点**: `ws://localhost:8000/api/ws/jobs/{job_id}/debug`

**连接流程**: 同监控 WebSocket

#### 4.3.2 消息格式

**服务器 → 客户端: 初始调试会话状态**
```json
{
  "type": "debug_session",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "paused"
}
```

**服务器 → 客户端: 断点命中**
```json
{
  "type": "breakpoint_hit",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "breakpoint_id": "bp-123456",
  "routine_id": "r1",
  "slot_name": null,
  "event_name": null,
  "timestamp": "2024-12-19T10:00:05Z"
}
```

**服务器 → 客户端: 执行事件**
```json
{
  "type": "execution_event",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": {
    "event_id": "event-1",
    "routine_id": "r1",
    "event_type": "routine_start",
    "timestamp": "2024-12-19T10:00:00Z",
    "data": {}
  }
}
```

**服务器 → 客户端: Ping**
```json
{
  "type": "ping"
}
```

### 4.4 Flow 监控 WebSocket

#### 4.4.1 连接

**端点**: `ws://localhost:8000/api/ws/flows/{flow_id}/monitor`

#### 4.4.2 消息格式

**服务器 → 客户端: Flow 指标** (每2秒)
```json
{
  "type": "flow_metrics",
  "flow_id": "example_flow",
  "total_jobs": 10,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "running"
    },
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440001",
      "status": "completed"
    }
  ]
}
```

---

## 5. 数据模型

### 5.1 Flow 数据模型

```typescript
interface Flow {
  flow_id: string;
  routines: Record<string, RoutineInfo>;
  connections: ConnectionInfo[];
  execution_strategy: "sequential" | "concurrent";
  max_workers: number;
  created_at?: string;  // ISO 8601 datetime
  updated_at?: string;  // ISO 8601 datetime
}

interface RoutineInfo {
  routine_id: string;
  class_name: string;
  slots: string[];
  events: string[];
  config: Record<string, any>;
}

interface ConnectionInfo {
  connection_id: string;
  source_routine: string;
  source_event: string;
  target_routine: string;
  target_slot: string;
  param_mapping?: Record<string, string>;
}
```

### 5.2 Job 数据模型

```typescript
interface Job {
  job_id: string;
  flow_id: string;
  status: "running" | "completed" | "failed" | "paused" | "cancelled";
  created_at: string;  // ISO 8601 datetime
  started_at?: string;  // ISO 8601 datetime
  completed_at?: string;  // ISO 8601 datetime
  error?: string;
}
```

### 5.3 断点数据模型

```typescript
interface Breakpoint {
  breakpoint_id: string;
  job_id: string;
  type: "routine" | "slot" | "event";
  routine_id?: string;
  slot_name?: string;
  event_name?: string;
  condition?: string;  // Python expression
  enabled: boolean;
  hit_count: number;
}
```

### 5.4 调试会话数据模型

```typescript
interface DebugSession {
  session_id: string;
  job_id: string;
  status: "running" | "paused" | "stepping";
  paused_at?: {
    routine_id: string;
  };
  call_stack_depth: number;
}
```

### 5.5 执行指标数据模型

```typescript
interface ExecutionMetrics {
  job_id: string;
  flow_id: string;
  start_time: string;  // ISO 8601 datetime
  end_time?: string;  // ISO 8601 datetime
  duration?: number;  // seconds
  routine_metrics: Record<string, RoutineMetrics>;
  total_events: number;
  total_slot_calls: number;
  total_event_emits: number;
  errors: ErrorRecord[];
}

interface RoutineMetrics {
  routine_id: string;
  execution_count: number;
  total_duration: number;  // seconds
  avg_duration: number;  // seconds
  min_duration?: number;  // seconds
  max_duration?: number;  // seconds
  error_count: number;
  last_execution?: string;  // ISO 8601 datetime
}

interface ErrorRecord {
  error_id: string;
  job_id: string;
  routine_id: string;
  timestamp: string;  // ISO 8601 datetime
  error_type: string;
  error_message: string;
  traceback?: string;
}
```

### 5.6 执行事件数据模型

```typescript
interface ExecutionEvent {
  event_id: string;
  job_id: string;
  routine_id: string;
  event_type: "routine_start" | "routine_end" | "slot_call" | "event_emit";
  timestamp: string;  // ISO 8601 datetime
  data: Record<string, any>;
  duration?: number;  // seconds (for end events)
  status?: string;  // for end events
}
```

### 5.7 调用栈数据模型

```typescript
interface CallFrame {
  routine_id: string;
  slot_name?: string;
  event_name?: string;
  variables: string[];  // variable names
}
```

---

## 6. 功能模块详细说明

### 6.1 Flow Builder 模块

#### 6.1.1 Flow 列表视图

**功能**:
- 显示所有 Flow 的列表
- 支持搜索和筛选
- 显示每个 Flow 的基本信息（ID、Routine 数量、Connection 数量、最后更新时间）

**UI 组件**:
- Flow 卡片/列表项
- 搜索框
- 创建 Flow 按钮
- 操作菜单（编辑、删除、导出、验证）

**交互**:
- 点击 Flow 卡片进入 Flow 编辑器
- 右键菜单提供快速操作

#### 6.1.2 Flow 编辑器

**功能**:
- 可视化 Flow 结构（节点图）
- DSL 代码编辑器（支持 YAML/JSON）
- Routine 和 Connection 管理

**UI 布局**:
```
┌─────────────────────────────────────────────────┐
│  [Flow ID]  [Save] [Validate] [Export] [Run]  │
├──────────────────┬──────────────────────────────┤
│                  │                              │
│  可视化编辑器     │    DSL 编辑器                │
│  (节点图)        │    (代码)                    │
│                  │                              │
│  [Routine 节点]  │  flow_id: example            │
│  [Connection 线] │  routines:                   │
│                  │    r1:                       │
│                  │      class: ...              │
│                  │                              │
├──────────────────┴──────────────────────────────┤
│  [Routines 面板]  [Connections 面板]            │
└─────────────────────────────────────────────────┘
```

**可视化编辑器功能**:
- 拖拽创建 Routine 节点
- 拖拽连接节点创建 Connection
- 双击节点编辑 Routine 配置
- 右键菜单：删除、编辑、查看详情
- 缩放和平移画布

**DSL 编辑器功能**:
- 语法高亮（YAML/JSON）
- 代码补全
- 实时验证
- 格式化
- 与可视化编辑器双向同步

**Routine 管理**:
- 添加 Routine（选择类路径）
- 编辑 Routine 配置
- 删除 Routine
- 查看 Routine 的 Slots 和 Events

**Connection 管理**:
- 添加 Connection（选择源和目标）
- 设置参数映射
- 删除 Connection

#### 6.1.3 DSL 导入/导出

**导入**:
- 支持 YAML 和 JSON 格式
- 文件上传或粘贴文本
- 导入后自动验证
- 显示导入结果和错误

**导出**:
- 选择格式（YAML/JSON）
- 下载文件或复制到剪贴板

#### 6.1.4 Flow 验证

**功能**:
- 实时验证 Flow 结构
- 显示验证结果和问题列表
- 高亮显示问题位置（可视化编辑器）

**验证项**:
- 循环依赖检测
- 未连接的 Event/Slot
- 无效的 Routine 类
- 无效的 Connection

### 6.2 Job Monitor 模块

#### 6.2.1 Job 列表视图

**功能**:
- 显示所有 Job 的列表
- 按状态筛选（running, completed, failed, paused, cancelled）
- 按 Flow ID 筛选
- 按时间排序
- 显示每个 Job 的基本信息

**UI 组件**:
- Job 卡片/列表项（显示状态、Flow ID、开始时间、持续时间）
- 状态标签（带颜色）
- 筛选器
- 刷新按钮

**交互**:
- 点击 Job 卡片进入 Job 详情
- 快速操作（暂停、恢复、取消）

#### 6.2.2 Job 详情面板

**功能**:
- 显示 Job 的完整信息
- 实时监控指标
- 执行追踪时间线
- 错误日志

**UI 布局**:
```
┌─────────────────────────────────────────────────┐
│  Job: {job_id}  [Pause] [Resume] [Cancel]      │
├──────────────────┬──────────────────────────────┤
│                  │                              │
│  实时指标图表     │   执行追踪时间线              │
│  - 执行时间       │   - 事件序列                  │
│  - Routine 指标   │   - 时间轴                    │
│  - 错误统计       │                              │
│                  │                              │
├──────────────────┴──────────────────────────────┤
│  错误日志                                        │
│  [筛选: All/Error/Warning]                      │
└─────────────────────────────────────────────────┘
```

**实时指标图表**:
- 执行时间趋势图（折线图）
- Routine 执行次数（柱状图）
- Routine 平均执行时间（柱状图）
- 错误统计（饼图）

**执行追踪时间线**:
- 垂直时间轴
- 事件标记（routine_start, routine_end, slot_call, event_emit）
- 点击事件查看详情
- 支持缩放和滚动

**错误日志**:
- 按级别筛选
- 显示时间、Routine ID、错误消息
- 展开查看完整 Traceback

#### 6.2.3 实时监控

**功能**:
- 通过 WebSocket 接收实时更新
- 自动刷新指标图表
- 新事件自动添加到时间线
- 状态变化通知

**实现**:
- 连接 Job 监控 WebSocket
- 每秒接收指标更新
- 更新 UI 组件

### 6.3 Debugger 模块

#### 6.3.1 断点管理面板

**功能**:
- 显示当前 Job 的所有断点
- 添加/删除/启用/禁用断点
- 设置条件断点
- 显示断点命中次数

**UI 组件**:
- 断点列表
- 添加断点对话框
- 断点项（显示类型、位置、条件、命中次数）

**添加断点对话框**:
```
┌─────────────────────────────────────┐
│  添加断点                            │
├─────────────────────────────────────┤
│  类型: [Routine ▼]                  │
│  Routine ID: [r1        ]           │
│  Slot Name:  [input     ] (可选)    │
│  Event Name: [output    ] (可选)    │
│  条件:        [data.value > 10]     │
│              (Python 表达式)        │
│  启用:        [✓]                   │
│                                     │
│  [取消]  [添加]                     │
└─────────────────────────────────────┘
```

#### 6.3.2 调试控制工具栏

**功能**:
- 暂停/恢复执行
- 单步执行（Step Over/Step Into）
- 查看当前状态

**UI 组件**:
```
[⏸ 暂停] [▶ 恢复] [⏭ Step Over] [⤵ Step Into]
```

**状态显示**:
- 当前调试状态（running/paused/stepping）
- 当前暂停位置（Routine ID）

#### 6.3.3 变量查看器

**功能**:
- 显示当前 Routine 的变量
- 修改变量值
- 支持复杂数据类型（对象、数组）的展开/折叠

**UI 组件**:
```
┌─────────────────────────────────────┐
│  变量 (Routine: r1)                  │
├─────────────────────────────────────┤
│  data                               │
│    value: 42          [编辑]        │
│    name: "test"       [编辑]        │
│  result: "success"    [编辑]        │
└─────────────────────────────────────┘
```

**交互**:
- 点击变量值进入编辑模式
- 支持 JSON 格式输入
- 保存后立即生效

#### 6.3.4 调用栈视图

**功能**:
- 显示当前调用栈
- 点击栈帧切换上下文
- 显示每个栈帧的变量

**UI 组件**:
```
┌─────────────────────────────────────┐
│  调用栈                              │
├─────────────────────────────────────┤
│  ▶ r1.input (当前)                  │
│    r2.trigger                       │
│    r3.trigger                       │
└─────────────────────────────────────┘
```

**交互**:
- 点击栈帧切换上下文
- 显示该栈帧的变量

#### 6.3.5 调试会话状态

**功能**:
- 显示调试会话信息
- 断点命中通知
- 执行事件通知

**实现**:
- 连接调试 WebSocket
- 接收断点命中事件
- 弹出通知或更新 UI

---

## 7. 用户界面需求

### 7.1 整体布局

**推荐布局**:
```
┌─────────────────────────────────────────────────────────┐
│  Logo  Routilux Debugger          [User] [Settings]    │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  侧边栏   │              主内容区                         │
│          │                                              │
│  - Flows │  [Flow Builder / Job Monitor / Debugger]    │
│  - Jobs  │                                              │
│  - Debug │                                              │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### 7.2 颜色方案

**状态颜色**:
- `running`: 蓝色 (#1890ff)
- `completed`: 绿色 (#52c41a)
- `failed`: 红色 (#ff4d4f)
- `paused`: 橙色 (#faad14)
- `cancelled`: 灰色 (#8c8c8c)

**断点颜色**:
- 启用: 红色 (#ff4d4f)
- 禁用: 灰色 (#d9d9d9)
- 命中: 黄色 (#faad14)

### 7.3 响应式设计

- 支持桌面端（推荐 1920x1080 及以上）
- 支持平板端（768px 及以上）
- 移动端支持基础查看功能

### 7.4 可访问性

- 支持键盘导航
- 支持屏幕阅读器
- 高对比度模式
- 字体大小可调节

---

## 8. 交互流程

### 8.1 Flow 创建和执行流程

```
1. 用户点击"创建 Flow"
2. 打开 Flow 编辑器
3. 用户添加 Routines 和 Connections
4. 用户点击"验证"
5. 显示验证结果
6. 如有错误，用户修复
7. 用户点击"保存"
8. Flow 保存成功
9. 用户点击"运行"
10. 弹出对话框：选择 entry_routine 和参数
11. 创建 Job
12. 自动跳转到 Job Monitor
```

### 8.2 调试流程

```
1. 用户在 Job Monitor 中查看运行中的 Job
2. 用户点击"调试"
3. 打开 Debugger 面板
4. 用户添加断点
5. 执行命中断点
6. WebSocket 接收断点命中事件
7. 显示断点命中通知
8. 自动暂停执行
9. 显示当前变量和调用栈
10. 用户可以：
    - 查看/修改变量
    - 单步执行
    - 恢复执行
11. 继续执行直到下一个断点或完成
```

### 8.3 实时监控流程

```
1. 用户打开 Job Monitor
2. 选择 Job
3. 前端连接 WebSocket: /api/ws/jobs/{job_id}/monitor
4. 接收初始指标
5. 每秒接收更新
6. 更新图表和时间线
7. Job 完成时显示最终结果
8. 断开 WebSocket 连接
```

---

## 9. 错误处理

### 9.1 API 错误处理

**HTTP 状态码**:
- `200 OK`: 成功
- `201 Created`: 创建成功
- `204 No Content`: 删除成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器错误

**错误响应格式**:
```json
{
  "detail": "Error message"
}
```

**前端处理**:
- 显示友好的错误消息
- 记录错误日志
- 提供重试机制

### 9.2 WebSocket 错误处理

**连接错误**:
- 显示连接失败消息
- 自动重连（指数退避）
- 最大重试次数限制

**消息错误**:
- 忽略无效消息
- 记录错误日志

### 9.3 用户输入验证

**前端验证**:
- Flow ID: 非空，符合命名规范
- Routine ID: 非空，符合命名规范
- 断点条件: Python 表达式语法检查
- 参数: JSON 格式验证

---

## 10. 技术规范

### 10.1 API 调用规范

**请求头**:
```http
Content-Type: application/json
Accept: application/json
```

**错误重试**:
- 网络错误: 自动重试 3 次（指数退避）
- 5xx 错误: 自动重试 3 次
- 4xx 错误: 不重试，显示错误消息

**超时设置**:
- REST API: 30 秒
- WebSocket: 保持连接，心跳检测

### 10.2 WebSocket 连接管理

**连接生命周期**:
1. 创建连接
2. 发送认证（如需要）
3. 接收消息
4. 发送心跳（可选）
5. 处理断开
6. 清理资源

**重连策略**:
- 初始重连延迟: 1 秒
- 最大重连延迟: 30 秒
- 最大重试次数: 10 次

### 10.3 状态管理

**推荐状态结构**:
```typescript
interface AppState {
  flows: {
    items: Flow[];
    current: Flow | null;
    loading: boolean;
  };
  jobs: {
    items: Job[];
    current: Job | null;
    loading: boolean;
  };
  debug: {
    session: DebugSession | null;
    breakpoints: Breakpoint[];
    variables: Record<string, any>;
    callStack: CallFrame[];
  };
  monitor: {
    metrics: ExecutionMetrics | null;
    trace: ExecutionEvent[];
    logs: LogEntry[];
  };
  websockets: {
    jobMonitor: WebSocket | null;
    debug: WebSocket | null;
    flowMonitor: WebSocket | null;
  };
}
```

### 10.4 性能优化

**建议**:
- 使用虚拟滚动处理长列表
- 图表数据采样（超过 1000 个点时）
- 防抖处理频繁更新
- 懒加载非关键组件
- 缓存 API 响应

### 10.5 测试要求

**单元测试**:
- API 客户端函数
- 数据转换函数
- 工具函数

**集成测试**:
- API 调用流程
- WebSocket 消息处理
- 用户交互流程

**E2E 测试**:
- Flow 创建和执行
- 调试流程
- 监控流程

---

## 11. 开发建议

### 11.1 项目结构

```
frontend/
├── src/
│   ├── api/              # API 客户端
│   │   ├── flows.ts
│   │   ├── jobs.ts
│   │   ├── breakpoints.ts
│   │   ├── debug.ts
│   │   └── monitor.ts
│   ├── websocket/         # WebSocket 客户端
│   │   ├── jobMonitor.ts
│   │   ├── debug.ts
│   │   └── flowMonitor.ts
│   ├── components/        # UI 组件
│   │   ├── FlowBuilder/
│   │   ├── JobMonitor/
│   │   └── Debugger/
│   ├── stores/            # 状态管理
│   ├── types/             # TypeScript 类型
│   ├── utils/             # 工具函数
│   └── App.tsx
├── package.json
└── tsconfig.json
```

### 11.2 代码示例

#### 11.2.1 API 客户端示例

```typescript
// api/flows.ts
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export async function getFlows(): Promise<FlowListResponse> {
  const response = await axios.get(`${API_BASE}/flows`);
  return response.data;
}

export async function createFlow(request: FlowCreateRequest): Promise<FlowResponse> {
  const response = await axios.post(`${API_BASE}/flows`, request);
  return response.data;
}
```

#### 11.2.2 WebSocket 客户端示例

```typescript
// websocket/jobMonitor.ts
export class JobMonitorWebSocket {
  private ws: WebSocket | null = null;
  private jobId: string;
  private onMessage: (data: any) => void;

  constructor(jobId: string, onMessage: (data: any) => void) {
    this.jobId = jobId;
    this.onMessage = onMessage;
  }

  connect(): void {
    const url = `ws://localhost:8000/api/ws/jobs/${this.jobId}/monitor`;
    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type !== 'ping') {
        this.onMessage(data);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed');
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
```

---

## 12. 附录

### 12.1 完整 API 端点列表

**Flow 管理** (12 个):
- `GET /api/flows` - 列表
- `GET /api/flows/{flow_id}` - 详情
- `POST /api/flows` - 创建
- `DELETE /api/flows/{flow_id}` - 删除
- `GET /api/flows/{flow_id}/dsl` - 导出 DSL
- `POST /api/flows/{flow_id}/validate` - 验证
- `GET /api/flows/{flow_id}/routines` - 获取 Routines
- `GET /api/flows/{flow_id}/connections` - 获取 Connections
- `POST /api/flows/{flow_id}/routines` - 添加 Routine
- `POST /api/flows/{flow_id}/connections` - 添加 Connection
- `DELETE /api/flows/{flow_id}/routines/{routine_id}` - 删除 Routine
- `DELETE /api/flows/{flow_id}/connections/{connection_index}` - 删除 Connection

**Job 管理** (8 个):
- `POST /api/jobs` - 启动
- `GET /api/jobs` - 列表
- `GET /api/jobs/{job_id}` - 详情
- `POST /api/jobs/{job_id}/pause` - 暂停
- `POST /api/jobs/{job_id}/resume` - 恢复
- `POST /api/jobs/{job_id}/cancel` - 取消
- `GET /api/jobs/{job_id}/status` - 状态
- `GET /api/jobs/{job_id}/state` - 完整状态

**断点管理** (4 个):
- `POST /api/jobs/{job_id}/breakpoints` - 创建
- `GET /api/jobs/{job_id}/breakpoints` - 列表
- `DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id}` - 删除
- `PUT /api/jobs/{job_id}/breakpoints/{breakpoint_id}` - 更新

**调试操作** (7 个):
- `GET /api/jobs/{job_id}/debug/session` - 会话信息
- `POST /api/jobs/{job_id}/debug/resume` - 恢复
- `POST /api/jobs/{job_id}/debug/step-over` - 单步跳过
- `POST /api/jobs/{job_id}/debug/step-into` - 单步进入
- `GET /api/jobs/{job_id}/debug/variables` - 获取变量
- `PUT /api/jobs/{job_id}/debug/variables/{name}` - 设置变量
- `GET /api/jobs/{job_id}/debug/call-stack` - 调用栈

**监控** (4 个):
- `GET /api/jobs/{job_id}/metrics` - 指标
- `GET /api/jobs/{job_id}/trace` - 追踪
- `GET /api/jobs/{job_id}/logs` - 日志
- `GET /api/flows/{flow_id}/metrics` - Flow 指标

**WebSocket** (3 个):
- `ws://localhost:8000/api/ws/jobs/{job_id}/monitor` - Job 监控
- `ws://localhost:8000/api/ws/jobs/{job_id}/debug` - 调试事件
- `ws://localhost:8000/api/ws/flows/{flow_id}/monitor` - Flow 监控

### 12.2 常见问题

**Q: 如何判断 Job 是否完成？**
A: 检查 `status` 字段，值为 `completed` 或 `failed` 表示完成。也可以通过 WebSocket 接收 `end_time` 不为 null 的指标。

**Q: 断点条件表达式支持哪些语法？**
A: 支持基本的 Python 表达式，包括：
- 变量访问: `data.value`
- 字典访问: `data['key']` 或 `data.get('key', 0)`
- 比较运算: `>`, `<`, `==`, `!=`, `>=`, `<=`
- 逻辑运算: `and`, `or`, `not`
- 函数调用: `len()`, `str()`, `int()`, `bool()`
- 不支持: `import`, `exec`, `eval`, 以及其他不安全操作

**Q: WebSocket 连接断开后如何处理？**
A: 实现自动重连机制，使用指数退避策略。同时显示连接状态给用户。

**Q: 如何实现 Flow 可视化编辑器？**
A: 推荐使用以下库：
- React Flow (React)
- Cytoscape.js (通用)
- D3.js (自定义)

### 12.3 联系信息

如有技术问题，请联系后端开发团队。

---

## 文档更新记录

- **v1.0** (2024-12-19): 初始版本

---

**文档结束**


