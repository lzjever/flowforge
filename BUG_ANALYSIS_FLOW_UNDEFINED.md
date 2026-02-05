# Bug 分析：runtime.py 中 flow 变量未定义

## 问题描述

在 `routilux/core/runtime.py` 的 `_check_routine_activation()` 方法中，第559行使用了 `flow` 变量，但该变量未定义。

**问题代码**（修复前）：
```python
ctx = get_current_execution_context()
routine_id = ctx.routine_id if ctx else None
# flow 变量未定义！

# ... 执行 logic ...

except Exception as e:
    # ...
    # Handle error via error handler
    if routine_id and flow:  # ❌ flow 未定义，会抛出 NameError
        error_handler = flow._get_error_handler_for_routine(routine, routine_id)
```

## Bug 触发条件

这个 bug 只有在以下**所有条件同时满足**时才会触发：

1. ✅ Routine logic 执行时抛出异常（进入 `except Exception as e:` 块）
2. ✅ `routine_id` 不为 `None`（从 `ExecutionContext` 中成功获取）
3. ✅ 此时 `flow` 变量未定义

## 为什么测试没有发现？

### 原因 1: Python 条件短路

在 Python 中，`if routine_id and flow:` 会先检查 `routine_id`：
- 如果 `routine_id` 是 `None` 或 `False`，会**短路**，不会检查 `flow`
- 只有当 `routine_id` 有值时，才会检查 `flow`，这时才会触发 `NameError`

**测试场景**：
```python
# 场景 1: routine_id 是 None（短路，不会检查 flow）
routine_id = None
if routine_id and flow:  # ✅ 短路，不会抛出错误
    pass

# 场景 2: routine_id 有值（会检查 flow，触发 NameError）
routine_id = 'test'
if routine_id and flow:  # ❌ NameError: name 'flow' is not defined
    pass
```

### 原因 2: 测试覆盖不足

可能的情况：
1. **测试用例中的错误场景，`routine_id` 是 `None`**
   - ExecutionContext 没有正确设置
   - 或者测试用例没有设置 ExecutionContext
   - 导致条件短路，不会检查 `flow`

2. **测试用例没有覆盖到这个错误处理路径**
   - 测试用例可能没有触发 routine logic 异常
   - 或者异常在更早的地方被捕获了

3. **测试用例中的错误场景，错误在更早的地方被处理**
   - 错误可能在 `WorkerExecutor` 或其他地方被处理
   - 没有到达 `_check_routine_activation()` 的错误处理代码

## 修复方案

**修复代码**：
```python
ctx = get_current_execution_context()
routine_id = ctx.routine_id if ctx else None
flow = ctx.flow if ctx else None  # ✅ 从 ExecutionContext 获取 flow
```

## 影响分析

### 潜在影响

如果这个 bug 被触发，会导致：
- `NameError: name 'flow' is not defined`
- 错误处理逻辑无法执行
- 可能导致错误无法被正确处理

### 实际影响（可能较小）

由于条件短路的存在，这个 bug 只在特定条件下才会触发：
- 需要 routine logic 抛出异常
- 需要 `routine_id` 有值
- 需要 `flow` 未定义

在实际使用中，如果 ExecutionContext 正确设置，`flow` 应该总是可以从 `ctx.flow` 获取。

## 结论

1. **这是一个真实的 bug**：`flow` 变量确实未定义
2. **测试没有发现的原因**：
   - Python 条件短路保护了大部分情况
   - 测试覆盖可能不足
   - 或者测试场景中 `routine_id` 是 `None`，导致短路
3. **修复是必要的**：虽然可能不会经常触发，但修复后可以确保错误处理逻辑正常工作

## 建议

1. ✅ **已修复**：从 `ExecutionContext` 获取 `flow`
2. 🔍 **建议**：添加测试用例覆盖这个错误处理路径
3. 🔍 **建议**：确保测试用例中 ExecutionContext 正确设置
