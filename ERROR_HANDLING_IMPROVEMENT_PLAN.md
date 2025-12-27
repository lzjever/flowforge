# Error Handling 改进方案

## 当前问题分析

### 1. 错误处理层级问题

**现状**：
- 错误处理只在 Flow 层面，所有 routines 共享同一个 `error_handler`
- 无法为不同的 routine 设置不同的错误处理策略
- 无法区分 critical routine（必须成功）和 optional routine（失败可容忍）

**问题场景**：
```python
flow = Flow()

# 添加一个 optional routine（失败可容忍）
optional_routine = OptionalRoutine()
optional_id = flow.add_routine(optional_routine, "optional")

# 添加一个 critical routine（必须成功，可重试）
critical_routine = CriticalRoutine()
critical_id = flow.add_routine(critical_routine, "critical")

# 当前只能设置一个全局错误处理策略
flow.set_error_handler(ErrorHandler(strategy=ErrorStrategy.CONTINUE))
# 问题：无法区分 optional 和 critical routine 的错误处理需求
```

### 2. SKIP vs CONTINUE 策略区别分析

**当前实现**：

**CONTINUE 策略**：
- 记录错误到 `execution_history`，action 为 `"error_continued"`
- Routine 状态标记为 `"error_continued"`
- Flow 状态标记为 `"completed"`
- 继续执行下游 routines

**SKIP 策略**：
- Routine 状态标记为 `"skipped"`
- Flow 状态标记为 `"completed"`
- 继续执行下游 routines

**区别**：
- **语义区别**：CONTINUE 表示"尝试执行但失败了，继续流程"；SKIP 表示"跳过这个 routine"
- **状态标记**：CONTINUE 使用 `"error_continued"`，SKIP 使用 `"skipped"`
- **实际行为**：两者都继续执行，区别主要在状态记录上

**结论**：
- 两者确实很相似，但语义上有区别
- CONTINUE 更适合"执行失败但继续"的场景
- SKIP 更适合"主动跳过"的场景
- 建议保留两者，但需要更清晰的文档说明

## 改进方案

### 方案 1：Routine 级别的错误处理（推荐）

#### 1.1 设计思路

- 在 Routine 类中添加 `error_handler` 属性
- Flow 层面的 `error_handler` 作为默认值
- 执行时优先使用 routine 级别的 error_handler，如果没有则使用 flow 级别的

#### 1.2 实现步骤

**步骤 1：在 Routine 类中添加 error_handler 支持**

```python
# flowforge/routine.py
class Routine(Serializable):
    def __init__(self):
        super().__init__()
        # ... existing code ...
        self._error_handler: Optional['ErrorHandler'] = None
    
    def set_error_handler(self, error_handler: 'ErrorHandler') -> None:
        """Set error handler for this routine.
        
        Args:
            error_handler: ErrorHandler instance.
        """
        self._error_handler = error_handler
    
    def get_error_handler(self) -> Optional['ErrorHandler']:
        """Get error handler for this routine.
        
        Returns:
            ErrorHandler instance if set, None otherwise.
        """
        return self._error_handler
```

**步骤 2：修改 Flow 的错误处理逻辑**

```python
# flowforge/flow.py
def _get_error_handler_for_routine(self, routine: 'Routine', routine_id: str) -> Optional['ErrorHandler']:
    """Get error handler for a routine.
    
    Priority:
    1. Routine-level error handler (if set)
    2. Flow-level error handler (if set)
    3. None (default STOP behavior)
    
    Args:
        routine: Routine object.
        routine_id: Routine ID.
    
    Returns:
        ErrorHandler instance or None.
    """
    # Priority 1: Routine-level error handler
    if routine.get_error_handler() is not None:
        return routine.get_error_handler()
    
    # Priority 2: Flow-level error handler
    return self.error_handler
```

**步骤 3：更新错误处理调用点**

在 `_execute_sequential` 和 `_execute_concurrent` 中，将：
```python
if self.error_handler:
    should_continue = self.error_handler.handle_error(...)
```

改为：
```python
error_handler = self._get_error_handler_for_routine(entry_routine, entry_routine_id)
if error_handler:
    should_continue = error_handler.handle_error(...)
```

**步骤 4：更新序列化支持**

```python
# flowforge/routine.py
class Routine(Serializable):
    def __init__(self):
        # ... existing code ...
        self.add_serializable_fields([..., "_error_handler"])
```

#### 1.3 使用示例

```python
from flowforge import Flow, Routine, ErrorHandler, ErrorStrategy

class OptionalRoutine(Routine):
    def __call__(self):
        # 可能失败，但可以容忍
        if random.random() < 0.5:
            raise ValueError("Optional operation failed")

class CriticalRoutine(Routine):
    def __call__(self):
        # 必须成功
        if random.random() < 0.3:
            raise ConnectionError("Critical operation failed")

flow = Flow()

# 添加 optional routine，设置 CONTINUE 策略
optional_routine = OptionalRoutine()
optional_routine.set_error_handler(
    ErrorHandler(strategy=ErrorStrategy.CONTINUE)
)
optional_id = flow.add_routine(optional_routine, "optional")

# 添加 critical routine，设置 RETRY 策略
critical_routine = CriticalRoutine()
critical_routine.set_error_handler(
    ErrorHandler(
        strategy=ErrorStrategy.RETRY,
        max_retries=5,
        retry_delay=1.0
    )
)
critical_id = flow.add_routine(critical_routine, "critical")

# Flow 级别的错误处理作为默认值（可选）
flow.set_error_handler(ErrorHandler(strategy=ErrorStrategy.STOP))

# 执行
flow.connect(optional_id, "output", critical_id, "input")
job_state = flow.execute(optional_id)
```

### 方案 2：增强 ErrorHandler 支持 critical/optional 标记

#### 2.1 设计思路

- 在 ErrorHandler 中添加 `is_critical` 标记
- 如果 `is_critical=True`，失败后必须重试，重试失败则 flow 失败
- 如果 `is_critical=False`，失败后可以容忍（使用 CONTINUE 或 SKIP）

#### 2.2 实现步骤

**步骤 1：扩展 ErrorHandler**

```python
# flowforge/error_handler.py
class ErrorHandler(Serializable):
    def __init__(
        self,
        strategy: str = "stop",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
        retryable_exceptions: Optional[tuple] = None,
        is_critical: bool = False  # 新增
    ):
        # ... existing code ...
        self.is_critical: bool = is_critical
```

**步骤 2：修改错误处理逻辑**

```python
def handle_error(...) -> bool:
    # ... existing code ...
    
    # 如果是 critical routine，重试失败后必须停止
    if self.is_critical and self.strategy == ErrorStrategy.RETRY:
        if self.retry_count >= self.max_retries:
            # Critical routine 重试失败，flow 必须失败
            return False
    
    # ... rest of the code ...
```

#### 2.3 使用示例

```python
# Optional routine
optional_handler = ErrorHandler(
    strategy=ErrorStrategy.CONTINUE,
    is_critical=False
)
optional_routine.set_error_handler(optional_handler)

# Critical routine
critical_handler = ErrorHandler(
    strategy=ErrorStrategy.RETRY,
    max_retries=5,
    is_critical=True  # 重试失败后 flow 失败
)
critical_routine.set_error_handler(critical_handler)
```

### 方案 3：组合方案（推荐）

结合方案 1 和方案 2：
- 支持 routine 级别的错误处理（方案 1）
- 支持 critical/optional 标记（方案 2）
- 提供便捷方法设置 common patterns

#### 3.1 便捷方法

```python
# flowforge/routine.py
class Routine(Serializable):
    def set_as_optional(self, strategy: ErrorStrategy = ErrorStrategy.CONTINUE) -> None:
        """Mark this routine as optional (failures are tolerated).
        
        Args:
            strategy: Error handling strategy for optional routine.
        """
        self.set_error_handler(ErrorHandler(
            strategy=strategy,
            is_critical=False
        ))
    
    def set_as_critical(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> None:
        """Mark this routine as critical (must succeed, retry on failure).
        
        Args:
            max_retries: Maximum number of retries.
            retry_delay: Initial retry delay.
        """
        self.set_error_handler(ErrorHandler(
            strategy=ErrorStrategy.RETRY,
            max_retries=max_retries,
            retry_delay=retry_delay,
            is_critical=True
        ))
```

#### 3.2 使用示例

```python
# 简洁的 API
optional_routine.set_as_optional()
critical_routine.set_as_critical(max_retries=5)

# 或者使用完整的 API
optional_routine.set_error_handler(
    ErrorHandler(strategy=ErrorStrategy.CONTINUE, is_critical=False)
)
critical_routine.set_error_handler(
    ErrorHandler(strategy=ErrorStrategy.RETRY, max_retries=5, is_critical=True)
)
```

## 关于 SKIP vs CONTINUE 的建议

### 建议保留两者，但明确区分：

**CONTINUE**：
- 适用于：routine 执行失败，但希望继续流程
- 语义：尝试执行但失败了，记录错误但继续
- 状态：`"error_continued"`
- 使用场景：非关键操作失败，但流程可以继续

**SKIP**：
- 适用于：主动跳过某个 routine（可能因为条件不满足）
- 语义：跳过这个 routine，不执行
- 状态：`"skipped"`
- 使用场景：条件性执行，或者明确知道要跳过

### 改进建议：

1. **文档说明**：在文档中明确两者的区别和使用场景
2. **状态区分**：保持不同的状态标记，便于监控和调试
3. **可选合并**：如果确实不需要区分，可以考虑在后续版本中合并

## 实施计划

### Phase 1: Routine 级别的错误处理
1. 在 Routine 类中添加 `_error_handler` 属性
2. 添加 `set_error_handler()` 和 `get_error_handler()` 方法
3. 修改 Flow 的错误处理逻辑，支持 routine 级别优先
4. 更新序列化支持
5. 添加测试用例

### Phase 2: Critical/Optional 标记
1. 在 ErrorHandler 中添加 `is_critical` 属性
2. 修改错误处理逻辑，支持 critical routine 的重试失败处理
3. 添加便捷方法 `set_as_optional()` 和 `set_as_critical()`
4. 更新文档
5. 添加测试用例

### Phase 3: 文档和示例
1. 更新错误处理文档
2. 添加使用示例
3. 更新 CHANGELOG

## 测试用例设计

```python
def test_routine_level_error_handler():
    """测试 routine 级别的错误处理"""
    flow = Flow()
    
    # Optional routine with CONTINUE
    optional = OptionalRoutine()
    optional.set_error_handler(ErrorHandler(strategy=ErrorStrategy.CONTINUE))
    optional_id = flow.add_routine(optional, "optional")
    
    # Critical routine with RETRY
    critical = CriticalRoutine()
    critical.set_error_handler(
        ErrorHandler(strategy=ErrorStrategy.RETRY, max_retries=3, is_critical=True)
    )
    critical_id = flow.add_routine(critical, "critical")
    
    flow.connect(optional_id, "output", critical_id, "input")
    job_state = flow.execute(optional_id)
    
    # Optional routine 失败应该被容忍
    assert job_state.status == "completed"  # 或根据 critical routine 的结果
    
    # Critical routine 如果重试失败，flow 应该失败
    # 需要根据实际实现调整断言

def test_critical_routine_retry_failure():
    """测试 critical routine 重试失败后 flow 失败"""
    flow = Flow()
    
    critical = AlwaysFailingRoutine()
    critical.set_as_critical(max_retries=2)
    critical_id = flow.add_routine(critical, "critical")
    
    job_state = flow.execute(critical_id)
    
    # 重试失败后，flow 应该失败
    assert job_state.status == "failed"

def test_optional_routine_failure_tolerated():
    """测试 optional routine 失败被容忍"""
    flow = Flow()
    
    optional = FailingRoutine()
    optional.set_as_optional()
    optional_id = flow.add_routine(optional, "optional")
    
    job_state = flow.execute(optional_id)
    
    # Optional routine 失败应该被容忍
    assert job_state.status == "completed"
    assert job_state.get_routine_state("optional")["status"] == "error_continued"
```

## 向后兼容性

- Flow 级别的 `error_handler` 仍然有效，作为默认值
- 如果没有设置 routine 级别的 error_handler，使用 flow 级别的
- 现有代码不需要修改即可工作
- 新功能是可选的增强

## 总结

推荐采用**方案 3（组合方案）**：
1. 支持 routine 级别的错误处理，满足不同 routine 的不同需求
2. 支持 critical/optional 标记，明确区分关键和非关键操作
3. 提供便捷方法，简化常见场景的使用
4. 保持向后兼容，不影响现有代码
5. 保留 SKIP 和 CONTINUE 策略，但明确区分使用场景

