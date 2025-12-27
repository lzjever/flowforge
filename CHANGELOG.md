# flowforge 更新日志

## [Unreleased]

### 新增功能

- ✅ **Routine 级别的错误处理**: 支持为每个 routine 设置独立的错误处理策略，优先级高于 flow 级别
- ✅ **Critical/Optional routine 标记**: 新增 `set_as_critical()` 和 `set_as_optional()` 便捷方法
- ✅ **`is_critical` 标志**: ErrorHandler 新增 `is_critical` 参数，用于标记关键 routine
- ✅ **错误处理优先级系统**: 优先级顺序为 routine-level > flow-level > default (STOP)

### 改进

- ✅ **向后兼容**: 保持对现有代码的完全兼容，flow 级别的错误处理仍然有效
- ✅ **Critical routine 重试失败处理**: Critical routine 在重试失败后会导致 flow 失败

### 文档

- ✅ 更新错误处理文档，添加 routine 级别错误处理示例
- ✅ 添加 critical 和 optional routine 使用模式文档
- ✅ 明确说明 CONTINUE 和 SKIP 策略的区别

## [0.1.2] - 2024-12-26

### 新增功能

- ✅ **ErrorHandler**: 错误处理器，支持多种错误处理策略（停止、继续、重试、跳过）
- ✅ **错误恢复策略**: 支持配置错误处理策略和重试机制
- ✅ **暂停和恢复**: Flow 支持暂停和恢复功能
- ✅ **取消功能**: Flow 支持取消执行

### 改进

- ✅ **错误处理集成**: Flow.execute 集成错误处理器
- ✅ **重试机制**: 支持自动重试，可配置重试次数和延迟
- ✅ **暂停点记录**: 记录暂停点和检查点信息
- ✅ **设计优化**: 优化 pause/resume/cancel 的职责分离
  - Flow 负责执行控制（pause/resume/cancel）
  - JobState 只负责状态记录和查询
  - 移除 JobState 的公开 pause/resume/cancel 方法，改为内部方法

## [0.1.1] - 2024-12-26

### 新增功能

- ✅ **ExecutionTracker**: 执行跟踪器，跟踪 flow 的执行状态、性能和事件流
- ✅ **执行历史记录**: 自动记录所有 emit 的事件到 JobState
- ✅ **性能指标**: 支持获取 routine 和 flow 的性能指标
- ✅ **详细状态跟踪**: 记录执行时间、开始/结束时间等详细信息

### 改进

- ✅ **错误处理**: 更完善的错误记录和处理
- ✅ **执行时间跟踪**: 自动计算和记录每个 routine 的执行时间
- ✅ **事件流跟踪**: 记录所有事件的触发和传递

## [0.1.0] - 2024-01-XX

### 新增功能

- ✅ **Routine 基类**: 支持定义 slots 和 events，提供 stats() 方法
- ✅ **Slot 类**: 输入插槽，支持连接多个 events，数据接收和处理
- ✅ **Event 类**: 输出事件，支持连接多个 slots，事件触发
- ✅ **Connection 类**: 连接对象，支持参数映射
- ✅ **Flow 类**: Flow 管理器，支持流程编排、执行和恢复
- ✅ **JobState 类**: 作业状态管理，支持状态记录和持久化
- ✅ **ExecutionRecord 类**: 执行记录

### 改进

- ✅ **事件驱动执行**: 实现了事件驱动的执行机制
- ✅ **参数映射**: 完善了 Connection 的参数映射功能
- ✅ **智能参数匹配**: Slot.receive 现在可以智能匹配 handler 参数
- ✅ **Flow 上下文**: Routine.emit 可以自动获取 Flow 上下文

### 测试

- ✅ 基本功能测试通过
- ✅ Flow 执行测试通过（线性流程、分支流程、参数映射）

### 已知问题

- ⚠️ Flow 持久化只保存结构，不保存 routine 实例
- ⚠️ 需要完善异步执行支持
- ⚠️ 需要实现完整的测试用例

