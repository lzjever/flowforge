# RetryHandler 设计问题分析与改进建议

## 问题分析

### 1. RetryHandler 的设计问题

#### ❌ 不符合 FlowForge 设计理念

**当前设计：**
- `RetryHandler` 接收一个 `callable` 并执行它
- 这更像是**包装器模式**，而不是一个独立的业务逻辑 routine
- FlowForge 的设计理念是：**每个 Routine 有自己的业务逻辑，通过 slots 接收数据，通过 events 发送数据**

**问题：**
1. **执行逻辑不在 Routine 内部**：真正的业务逻辑（callable）是从外部传入的，Routine 本身没有自己的业务逻辑
2. **违反设计原则**：违反了"所有 routine 都有自己内部实际的逻辑"的原则
3. **序列化问题**：callable 无法很好地序列化，反序列化后可能无法恢复
4. **不符合 FlowForge 架构**：FlowForge 的设计是通过 Flow 连接多个 Routine，数据在 Routine 之间流动，而不是在一个 Routine 内部执行外部函数

#### ✅ 正确的设计应该是：

1. **业务逻辑在自己的 Routine 中实现**
   - 需要重试的业务逻辑应该在自己的 Routine 中实现
   - 这个 Routine 有自己的输入 slot 和输出 events（success/failure）

2. **重试逻辑通过 Flow 的连接实现**
   - 使用 `ConditionalRouter` 或类似的路由器来判断成功/失败
   - 失败时，路由器发送 retry 事件回业务 Routine
   - 成功时，路由器透传给下游

3. **或者，每个需要重试的 Routine 自己实现重试逻辑**
   - 在 Routine 内部实现重试逻辑
   - 通过配置控制重试次数和策略

### 2. 使用 ConditionalRouter 实现 retry 的可行性

#### ✅ 用户的理解是合理的

**用户的理解：**
```
R1 -> cond1 (R1失败发给cond1, cond1再发消息给R1重试，若干次之后失败。
或者R1成功，cond1透传成功给下面的routine)
```

**这个理解完全正确！** 这正是 FlowForge 设计理念的体现。

#### 实现方式

1. **业务 Routine (R1)**：
   - 有自己的业务逻辑
   - 成功时发送 `success` 事件
   - 失败时发送 `failure` 事件（包含 `retry_count`）

2. **重试路由器（类似 ConditionalRouter）**：
   - 接收业务 Routine 的结果（成功或失败）
   - 如果成功 → 透传给下游
   - 如果失败且 `retry_count < max_retries` → 发送 `retry` 事件回业务 Routine
   - 如果失败且 `retry_count >= max_retries` → 发送 `final_failure` 事件

3. **Flow 连接**：
   ```
   business.success -> router.input
   business.failure -> router.input
   router.retry -> business.input
   router.final_success -> downstream.input
   router.final_failure -> downstream.input
   ```

#### 优势

1. ✅ **符合 FlowForge 设计理念**：每个 Routine 有自己的逻辑，通过事件和槽连接
2. ✅ **可序列化**：所有逻辑都在 Routine 内部，可以正常序列化
3. ✅ **灵活**：可以轻松调整重试策略，甚至使用不同的路由器
4. ✅ **可测试**：每个 Routine 可以独立测试
5. ✅ **可组合**：可以与其他 Routine 组合使用

## 建议

### 1. 删除或废弃 RetryHandler

**理由：**
- 不符合 FlowForge 设计理念
- 可以通过 ConditionalRouter 模式实现
- 维护成本高，且容易误导用户

**替代方案：**
- 提供示例代码展示如何使用 ConditionalRouter 实现 retry
- 在文档中说明最佳实践

### 2. 增强 ConditionalRouter 或创建 RetryRouter

**选项 A：增强 ConditionalRouter**
- 添加重试相关的配置选项
- 提供重试计数和状态管理

**选项 B：创建专门的 RetryRouter**
- 基于 ConditionalRouter 模式
- 专门处理重试逻辑
- 提供更友好的 API

### 3. 更新文档

**需要更新的内容：**
1. 说明 RetryHandler 已废弃，推荐使用 ConditionalRouter 模式
2. 提供完整的示例代码（见 `examples/retry_with_router_demo.py`）
3. 在最佳实践文档中说明如何实现重试逻辑

## 示例代码

完整示例见：`examples/retry_with_router_demo.py`

**核心代码结构：**

```python
# 业务 Routine
class BusinessRoutine(Routine):
    def _handle_input(self, data, retry_count=0, **kwargs):
        try:
            # 业务逻辑
            result = process(data)
            self.emit("success", result=result, data=data, retry_count=retry_count)
        except Exception as e:
            self.emit("failure", error=str(e), data=data, retry_count=retry_count)

# 重试路由器
class RetryRouter(Routine):
    def _handle_input(self, result=None, error=None, data=None, retry_count=0, **kwargs):
        if result:
            # 成功：透传给下游
            self.emit("final_success", result=result, data=data, total_attempts=retry_count+1)
        elif error:
            if retry_count < max_retries:
                # 重试
                self.emit("retry", data=data, retry_count=retry_count+1)
            else:
                # 最终失败
                self.emit("final_failure", error=error, data=data, total_attempts=retry_count+1)

# Flow 连接
flow.connect(business_id, "success", router_id, "input")
flow.connect(business_id, "failure", router_id, "input")
flow.connect(router_id, "retry", business_id, "input")
```

## 结论

1. ✅ **RetryHandler 的设计不符合 FlowForge 设计理念**
2. ✅ **使用 ConditionalRouter 模式可以实现 retry，且更符合设计理念**
3. ✅ **建议删除或废弃 RetryHandler**
4. ✅ **提供示例和文档说明最佳实践**

