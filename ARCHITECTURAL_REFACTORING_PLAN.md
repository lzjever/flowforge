# 架构重构计划：统一执行上下文管理

## 问题分析

当前实现存在以下结构性问题：

### 1. 执行上下文信息分散
- `_current_flow` 存储在 Routine 实例变量中（`routine._current_flow`）
- `_current_worker_state` 通过 ContextVar 传递
- `routine_id` 需要通过 `flow._get_routine_id(routine)` 动态查找
- `job_context` 通过另一个 ContextVar 传递

**问题**：
- 信息分散在多个地方，容易不一致
- `get_execution_context()` 需要从多个来源组装信息，效率低且容易出错
- `_current_flow` 作为实例变量，在多线程环境下可能有问题

### 2. ContextVar 管理混乱
- `routine.py` 和 `context.py` 中都有 `_current_worker_state` 的定义（已修复，但设计仍不清晰）
- 多个 ContextVar 需要分别设置，容易遗漏

### 3. 间接访问模式
- `set_job_data()` 调用 `get_execution_context()` 获取 `routine_id`
- `get_execution_context()` 需要多次检查和查找
- 增加了不必要的间接层

## 根本性重构方案

### 核心思想：统一执行上下文管理

**原则**：
1. **单一数据源**：所有执行上下文信息统一存储在 ContextVar 中
2. **在入口处设置**：WorkerExecutor 在执行 routine 时设置完整的 ExecutionContext
3. **直接访问**：Routine 方法直接从 ContextVar 获取，无需组装

### 重构步骤

#### 步骤 1: 在 context.py 中统一管理 ExecutionContext

```python
# context.py

# 统一的执行上下文 ContextVar
_current_execution_context: ContextVar[ExecutionContext | None] = ContextVar(
    "_current_execution_context", default=None
)

def get_current_execution_context() -> ExecutionContext | None:
    """Get current execution context from ContextVar."""
    return _current_execution_context.get(None)

def set_current_execution_context(ctx: ExecutionContext | None) -> None:
    """Set current execution context in ContextVar."""
    _current_execution_context.set(ctx)
```

#### 步骤 2: 将 ExecutionContext 移到 context.py

- 从 `routine.py` 移动到 `context.py`
- 这样所有上下文相关的类型都在一个地方

#### 步骤 3: 重构 WorkerExecutor 设置上下文

```python
# executor.py

def _execute_routine_task(self, ...):
    # 在执行 routine 之前，设置完整的 ExecutionContext
    from routilux.core.context import ExecutionContext, set_current_execution_context
    
    ctx = ExecutionContext(
        flow=self.flow,
        worker_state=self.worker_state,
        routine_id=routine_id,
        job_context=job_context,
    )
    
    # 统一设置执行上下文
    set_current_execution_context(ctx)
    set_current_job(job_context)
    set_current_worker_state(self.worker_state)
    
    try:
        # 执行 routine
        ...
    finally:
        # 清理
        set_current_execution_context(None)
        set_current_job(None)
        set_current_worker_state(None)
```

#### 步骤 4: 简化 Routine.get_execution_context()

```python
# routine.py

def get_execution_context(self) -> ExecutionContext | None:
    """Get execution context from ContextVar (direct access)."""
    from routilux.core.context import get_current_execution_context
    return get_current_execution_context()
```

#### 步骤 5: 简化 set_job_data/get_job_data

```python
# routine.py

def set_job_data(self, key: str, value: Any) -> None:
    """Set job-level data (direct access to execution context)."""
    from routilux.core.context import get_current_execution_context, get_current_job
    
    ctx = get_current_execution_context()
    if ctx is None:
        raise RuntimeError(
            "set_job_data requires execution context. "
            "This method must be called during routine execution."
        )
    
    job = get_current_job()
    if job is None:
        raise RuntimeError("set_job_data requires job context")
    
    # 直接从 ExecutionContext 获取 routine_id，无需查找
    full_key = f"{ctx.routine_id}_{key}"
    job.data[full_key] = value

def get_job_data(self, key: str, default: Any = None) -> Any:
    """Get job-level data (direct access to execution context)."""
    from routilux.core.context import get_current_execution_context, get_current_job
    
    ctx = get_current_execution_context()
    if ctx is None:
        return default
    
    job = get_current_job()
    if job is None:
        return default
    
    full_key = f"{ctx.routine_id}_{key}"
    return job.data.get(full_key, default)
```

#### 步骤 6: 移除 _current_flow 实例变量

- 不再需要 `routine._current_flow`
- 所有信息都从 ExecutionContext 获取
- 简化 Routine 类的状态管理

#### 步骤 7: 清理冗余代码

- 移除 `routine.py` 中不再需要的 ContextVar 定义
- 移除 `get_current_worker_state()` 和 `set_current_worker_state()` 的重复定义（如果存在）
- 统一使用 `context.py` 中的函数

## 优势

1. **单一数据源**：所有执行上下文信息统一在 ContextVar 中
2. **性能提升**：无需多次查找和组装，直接访问
3. **更安全**：在入口处统一设置，减少遗漏
4. **更清晰**：职责分离，context.py 管理所有上下文
5. **更易测试**：测试时只需设置一个 ContextVar

## 迁移影响

### 需要更新的代码

1. **WorkerExecutor**：设置 ExecutionContext
2. **Routine.get_execution_context()**：简化为直接获取
3. **所有使用 get_execution_context() 的地方**：无需改变，接口保持一致
4. **测试代码**：更新 context 设置方式

### 向后兼容性

- `get_execution_context()` 接口保持不变
- `set_job_data()` 和 `get_job_data()` 接口保持不变
- 只是内部实现更简洁高效

## 实施顺序

1. 在 `context.py` 中添加 `_current_execution_context` 和相关函数
2. 将 `ExecutionContext` 移到 `context.py`
3. 更新 `WorkerExecutor` 设置上下文的方式
4. 简化 `Routine.get_execution_context()`
5. 简化 `set_job_data/get_job_data`
6. 移除 `_current_flow` 相关代码
7. 更新测试
8. 清理冗余代码
