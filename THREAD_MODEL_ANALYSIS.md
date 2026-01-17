# Flow 和 Runtime 线程模型设计审查报告

## 执行摘要

当前系统存在**两套并行的执行机制**，导致职责不清、资源浪费和潜在的竞争条件。需要统一执行模型，明确职责划分。

## 当前架构问题

### 1. 双重执行机制

#### 机制 A: Runtime._execute_flow (简化版)
- **位置**: `routilux/runtime.py`
- **特点**:
  - 直接在 Runtime 的线程池中运行
  - 同步等待完成（使用 `time.sleep(0.1)`）
  - 使用 Runtime 的 `handle_event_emit` 路由事件
  - 没有独立的任务队列
  - 没有事件循环线程

#### 机制 B: JobExecutor + Flow.event_loop (完整版)
- **位置**: `routilux/job_executor.py` + `routilux/flow/event_loop.py`
- **特点**:
  - 每个 job 有独立的 `JobExecutor`
  - 每个 `JobExecutor` 有自己的 `event_loop_thread`
  - 每个 `JobExecutor` 有自己的 `task_queue`
  - 使用全局线程池执行任务
  - 通过 `GlobalJobManager` 管理

#### 机制 C: Flow.execute_flow_unified (混合版)
- **位置**: `routilux/flow/execution.py`
- **特点**:
  - 使用 Flow 的 `_task_queue` 和 `_execution_thread`
  - 调用 `start_event_loop(flow)` 启动 Flow 级别的事件循环
  - 与 JobExecutor 的 event loop 重复

### 2. 线程资源浪费

```
当前架构的线程层次：
┌─────────────────────────────────────┐
│ Runtime.thread_pool (共享线程池)      │
│ - 10 workers (默认)                  │
└─────────────────────────────────────┘
         │
         ├─ Runtime._execute_flow (机制A)
         │  └─ 直接执行，无独立线程
         │
         ├─ JobExecutor (机制B)
         │  ├─ event_loop_thread (每个job一个)
         │  └─ 提交任务到 Runtime.thread_pool
         │
         └─ Flow.event_loop (机制C)
            └─ _execution_thread (每个flow一个)
               └─ 提交任务到 Runtime.thread_pool
```

**问题**:
- 每个 job 有 1 个 event loop 线程
- 每个 flow 可能有 1 个 event loop 线程（如果使用 execute_flow_unified）
- 如果同时运行 10 个 jobs，就有 10-20 个额外的线程
- 这些线程大部分时间在 `time.sleep(0.1)` 中等待

### 3. 职责不清

| 组件 | 当前职责 | 应该的职责 |
|------|---------|-----------|
| Runtime | 线程池管理、事件路由、简化执行 | **仅**线程池管理和事件路由 |
| JobExecutor | 任务队列、事件循环、任务执行 | **仅**任务队列和事件循环 |
| Flow | 任务队列、事件循环（重复） | **仅**流程定义（routines + connections） |
| GlobalJobManager | JobExecutor 管理 | JobExecutor 生命周期管理 |

### 4. 竞争条件和同步问题

#### 问题 1: Flow 的 _task_queue 和 JobExecutor 的 task_queue 可能冲突
```python
# Flow 级别
flow._task_queue.put(task)  # 在 execute_flow_unified 中使用

# JobExecutor 级别  
executor.task_queue.put(task)  # 在 JobExecutor 中使用
```

#### 问题 2: 多个事件循环可能同时处理同一个 flow
- Flow.event_loop 可能在处理 flow._task_queue
- JobExecutor._event_loop 可能在处理 executor.task_queue
- 如果两者都处理同一个 flow，会导致重复执行

#### 问题 3: Runtime._execute_flow 的简化等待机制
```python
# runtime.py:249
time.sleep(0.1)  # 简化的等待，不准确
```
这不是正确的完成检测机制。

## 最佳实践分析

### ✅ 做得好的地方

1. **共享线程池**: Runtime 提供共享线程池是正确的设计
2. **非阻塞执行**: `exec()` 方法立即返回，不阻塞
3. **线程安全**: 使用了适当的锁（`_job_lock`, `_lock`, `_execution_lock`）
4. **资源清理**: 有 shutdown 机制和 context manager 支持

### ❌ 需要改进的地方

1. **单一职责原则违反**: 
   - Flow 不应该管理执行（应该只管理定义）
   - Runtime 不应该直接执行 flow（应该只管理资源）

2. **重复的事件循环**:
   - Flow.event_loop 和 JobExecutor._event_loop 功能重复
   - 应该只有一个事件循环机制

3. **不清晰的执行路径**:
   - 用户不知道应该用 Runtime.exec() 还是 Flow.execute()
   - 两套机制可能同时存在，造成混乱

## 推荐的重构方案

### 方案 1: 统一使用 JobExecutor（推荐）

```
架构层次：
┌─────────────────────────────────────┐
│ Runtime                              │
│ - thread_pool (共享)                  │
│ - handle_event_emit (事件路由)        │
│ - _check_routine_activation           │
└─────────────────────────────────────┘
         │
         └─ GlobalJobManager
            └─ JobExecutor (每个job一个)
               ├─ task_queue (独立)
               ├─ event_loop_thread (独立)
               └─ 提交任务到 Runtime.thread_pool
```

**关键改进**:
1. **移除 Runtime._execute_flow**: 不再直接执行 flow
2. **移除 Flow.event_loop**: Flow 不再管理执行
3. **统一使用 JobExecutor**: 所有执行都通过 JobExecutor
4. **Runtime.exec() 改为**: 创建 JobExecutor 并启动

### 方案 2: 简化 JobExecutor（备选）

如果 JobExecutor 的事件循环线程是性能瓶颈，可以考虑：
- 移除 JobExecutor 的 event_loop_thread
- 直接在 Runtime.thread_pool 中轮询 task_queue
- 但这会增加线程池的负载

## 具体改进建议

### 1. 明确职责划分

```python
# Runtime: 仅资源管理
class Runtime:
    - thread_pool: ThreadPoolExecutor  # 共享线程池
    - handle_event_emit()              # 事件路由
    - _check_routine_activation()      # 激活检查
    
# JobExecutor: 仅执行管理
class JobExecutor:
    - task_queue: Queue                # 任务队列
    - event_loop_thread: Thread         # 事件循环
    - global_thread_pool: ThreadPoolExecutor  # 引用 Runtime 的线程池
    
# Flow: 仅流程定义
class Flow:
    - routines: dict                    # 流程定义
    - connections: list                  # 连接定义
    # 移除: _task_queue, _execution_thread, _running 等执行相关属性
```

### 2. 统一执行入口

```python
# 推荐: 统一通过 Runtime
runtime = Runtime()
job_state = runtime.exec("flow_name", entry_params={...})

# 内部实现:
def exec(self, flow_name: str, ...):
    flow = self._get_flow(flow_name)
    executor = JobExecutor(flow, job_state, self.thread_pool)
    executor.start(...)
    return job_state
```

### 3. 移除重复机制

- [ ] 删除 `Runtime._execute_flow` 方法
- [ ] 删除 `Flow.event_loop` 相关代码
- [ ] 删除 `Flow._task_queue`, `Flow._execution_thread` 等执行属性
- [ ] 删除 `execute_flow_unified` 中的 `start_event_loop(flow)` 调用

### 4. 改进完成检测

当前的问题：
```python
# runtime.py:249 - 不准确的等待
time.sleep(0.1)
```

应该改为：
```python
# JobExecutor 中已经有正确的完成检测
def _is_complete(self) -> bool:
    with self._lock:
        if not self.task_queue.empty():
            return False
        active = [f for f in self.active_tasks if not f.done()]
        return len(active) == 0
```

### 5. 线程模型优化

**当前**: 每个 job = 1 个 event loop 线程 + N 个 worker 线程（共享）

**优化后**: 保持相同，但移除重复的 Flow.event_loop

**进一步优化**（可选）:
- 考虑使用 `asyncio` 替代线程池 + 事件循环
- 或者使用更轻量级的协程机制

## 风险评估

### 高风险
- 移除 Runtime._execute_flow 可能破坏现有代码
- 需要确保所有执行路径都迁移到 JobExecutor

### 中风险
- 移除 Flow.event_loop 需要更新所有调用点
- 需要确保序列化/反序列化不依赖 Flow 的执行状态

### 低风险
- 性能改进（减少线程数）
- 代码简化（移除重复逻辑）

## 实施步骤

1. **Phase 1: 分析依赖**
   - 找出所有使用 Runtime._execute_flow 的地方
   - 找出所有使用 Flow.event_loop 的地方
   - 找出所有直接访问 Flow._task_queue 的地方

2. **Phase 2: 迁移到 JobExecutor**
   - 更新 Runtime.exec() 使用 JobExecutor
   - 移除 Runtime._execute_flow
   - 更新所有调用点

3. **Phase 3: 清理 Flow**
   - 移除 Flow 的执行相关属性
   - 移除 Flow.event_loop 相关代码
   - 更新序列化逻辑

4. **Phase 4: 测试和验证**
   - 确保所有测试通过
   - 性能测试（线程数、内存使用）
   - 并发测试（多个 jobs 同时运行）

## 结论

当前线程模型存在**职责不清**和**重复机制**的问题。推荐统一使用 **JobExecutor** 作为唯一的执行机制，移除 Runtime 和 Flow 中的重复执行逻辑。这将使架构更清晰、更易维护，并减少资源浪费。
