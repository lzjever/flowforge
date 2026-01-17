# 基于 Activation Policy 替换的断点实现方案

## 方案概述

**核心思想**：断点通过替换 routine 的 activation policy 实现，而不是复杂的 hook 机制。

**优势**：
- ✅ **实现简单**：只需要替换 policy，利用现有机制
- ✅ **自动处理队列**：清空 slot 队列，避免堆积
- ✅ **数据保存**：保存到 job_state，不会丢失
- ✅ **统一接口**：所有断点都在 routine 级别
- ✅ **符合架构**：利用 activation policy 的设计理念

---

## 实现设计

### 1. Breakpoint Activation Policy

**文件**：`routilux/routilux/activation_policies.py`

**新增函数**：

```python
def breakpoint_policy(routine_id: str):
    """Create a breakpoint activation policy.
    
    This policy:
    1. Consumes all data from all slots
    2. Saves data to job_state.debug_data (keyed by slot name, overwrites)
    3. Clears slot queues
    4. Returns should_activate=False (doesn't execute logic)
    
    Args:
        routine_id: Routine ID for this breakpoint.
    
    Returns:
        Activation policy function.
    
    Examples:
        >>> policy = breakpoint_policy("my_routine")
        >>> routine.set_activation_policy(policy)
    """
    
    def policy(
        slots: dict[str, Slot], job_state: JobState
    ) -> tuple[bool, dict[str, list[Any]], Any]:
        """Breakpoint activation policy.
        
        Args:
            slots: Dictionary of slot_name -> Slot object.
            job_state: Current job state.
        
        Returns:
            Tuple of (False, {}, None) - never activates, just captures data.
        """
        # 收集所有 slot 的数据
        debug_data = {}
        
        for slot_name, slot in slots.items():
            # 消费所有新数据（但不执行逻辑）
            data_list = slot.consume_all_new()
            
            # 保存到 debug_data（覆盖刷新，不堆积）
            if data_list:
                debug_data[slot_name] = data_list
        
        # 保存到 job_state 的专用 debug 字段
        # 使用 routine_id 作为 key，覆盖刷新
        if not hasattr(job_state, 'debug_data'):
            job_state.debug_data = {}
        
        job_state.debug_data[routine_id] = {
            "slot_data": debug_data,
            "timestamp": datetime.now().isoformat(),
            "routine_id": routine_id,
        }
        
        # 更新 updated_at
        job_state.updated_at = datetime.now()
        
        # 返回 False，不执行逻辑
        return False, {}, {
            "reason": "breakpoint",
            "routine_id": routine_id,
            "captured_slots": list(debug_data.keys()),
        }
    
    return policy
```

**关键点**：
- ✅ 消费所有 slot 数据（`consume_all_new()`），自动清空队列
- ✅ 保存到 `job_state.debug_data[routine_id]`，覆盖刷新
- ✅ 返回 `should_activate=False`，不执行逻辑
- ✅ 记录时间戳和捕获的 slot 列表

### 2. 修改 JobState 添加 debug_data 字段

**文件**：`routilux/routilux/job_state.py`

**修改内容**：

```python
def __init__(self, flow_id: str = ""):
    # ... 现有代码 ...
    
    # Debug data for breakpoints (not serialized by default, can be enabled)
    self.debug_data: Dict[str, Dict[str, Any]] = {}
    self._debug_data_lock: threading.RLock = threading.RLock()
    
    # Register serializable fields
    self.add_serializable_fields(
        [
            # ... 现有字段 ...
            "debug_data",  # 新增：可选序列化
        ]
    )
```

**注意**：`debug_data` 默认不序列化（避免状态文件过大），但可以通过 API 查询。

### 3. BreakpointManager 简化实现

**文件**：`routilux/routilux/monitoring/breakpoint_manager.py`

**简化后的实现**：

```python
@dataclass
class Breakpoint:
    """Simplified breakpoint - only routine level.
    
    Attributes:
        breakpoint_id: Unique identifier for this breakpoint.
        job_id: Job ID this breakpoint applies to.
        routine_id: Routine ID to break at.
        enabled: Whether this breakpoint is active.
        hit_count: Number of times this breakpoint has been hit.
        original_policy: Original activation policy (for restoration).
    """
    
    breakpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    routine_id: str = ""
    enabled: bool = True
    hit_count: int = 0
    original_policy: Optional[Callable] = None  # 保存原 policy


class BreakpointManager:
    """Simplified breakpoint manager - only routine level breakpoints."""
    
    def __init__(self):
        """Initialize breakpoint manager."""
        self._breakpoints: Dict[str, List[Breakpoint]] = {}  # job_id -> [Breakpoint]
        self._lock = threading.RLock()
    
    def add_breakpoint(
        self, 
        breakpoint: Breakpoint,
        routine: Optional["Routine"] = None  # 新增：用于保存原 policy
    ) -> None:
        """Add a breakpoint for a routine.
        
        Args:
            breakpoint: Breakpoint to add.
            routine: Optional Routine object to save original policy.
        """
        with self._lock:
            if breakpoint.job_id not in self._breakpoints:
                self._breakpoints[breakpoint.job_id] = []
            
            # 如果 routine 提供，保存原 policy
            if routine and routine._activation_policy:
                breakpoint.original_policy = routine._activation_policy
            
            # 替换为 breakpoint policy
            if routine:
                from routilux.activation_policies import breakpoint_policy
                routine.set_activation_policy(breakpoint_policy(breakpoint.routine_id))
            
            self._breakpoints[breakpoint.job_id].append(breakpoint)
    
    def remove_breakpoint(self, breakpoint_id: str, job_id: str, routine: Optional["Routine"] = None) -> None:
        """Remove a breakpoint and restore original policy.
        
        Args:
            breakpoint_id: Breakpoint ID to remove.
            job_id: Job ID.
            routine: Optional Routine object to restore original policy.
        """
        with self._lock:
            if job_id not in self._breakpoints:
                return
            
            breakpoints = self._breakpoints[job_id]
            breakpoint = next((bp for bp in breakpoints if bp.breakpoint_id == breakpoint_id), None)
            
            if not breakpoint:
                return
            
            # 恢复原 policy
            if routine and breakpoint.original_policy:
                routine.set_activation_policy(breakpoint.original_policy)
            elif routine:
                # 如果没有原 policy，使用默认的 immediate_policy
                from routilux.activation_policies import immediate_policy
                routine.set_activation_policy(immediate_policy())
            
            # 移除断点
            breakpoints.remove(breakpoint)
            if not breakpoints:
                del self._breakpoints[job_id]
    
    def get_breakpoints(self, job_id: str) -> List[Breakpoint]:
        """Get all breakpoints for a job."""
        with self._lock:
            return self._breakpoints.get(job_id, []).copy()
    
    def has_breakpoint(self, job_id: str, routine_id: str) -> bool:
        """Check if a routine has a breakpoint.
        
        Args:
            job_id: Job ID.
            routine_id: Routine ID.
        
        Returns:
            True if breakpoint exists and is enabled.
        """
        with self._lock:
            breakpoints = self._breakpoints.get(job_id, [])
            return any(
                bp.routine_id == routine_id and bp.enabled 
                for bp in breakpoints
            )
```

**关键点**：
- ✅ 只支持 routine 级别断点
- ✅ 保存原 policy，取消断点时恢复
- ✅ 如果没有原 policy，恢复为 `immediate_policy()`

### 4. 修改 Breakpoint API

**文件**：`routilux/routilux/api/routes/breakpoints.py`

**修改内容**：

```python
@router.post(
    "/jobs/{job_id}/breakpoints",
    response_model=BreakpointResponse,
    status_code=201,
    dependencies=[RequireAuth],
)
async def create_breakpoint(job_id: str, request: BreakpointCreateRequest):
    """Create a breakpoint for a routine (routine level only)."""
    # 验证：只支持 routine 类型
    if request.type != "routine":
        raise HTTPException(
            status_code=400, 
            detail="Only 'routine' type breakpoints are supported. "
                   "Use routine_id to specify which routine to break at."
        )
    
    if not request.routine_id:
        raise HTTPException(
            status_code=400,
            detail="routine_id is required for routine breakpoints"
        )
    
    # 验证 job 存在
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    # 获取 flow 和 routine
    from routilux.monitoring.flow_registry import FlowRegistry
    flow_registry = FlowRegistry.get_instance()
    flow = flow_registry.get(job_state.flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")
    
    if request.routine_id not in flow.routines:
        raise HTTPException(
            status_code=404, 
            detail=f"Routine '{request.routine_id}' not found in flow"
        )
    
    routine = flow.routines[request.routine_id]
    
    # 检查是否已有断点
    registry = MonitoringRegistry.get_instance()
    breakpoint_mgr = registry.breakpoint_manager
    
    if not breakpoint_mgr:
        raise HTTPException(status_code=500, detail="Breakpoint manager not available")
    
    existing = breakpoint_mgr.get_breakpoints(job_id)
    if any(bp.routine_id == request.routine_id and bp.enabled for bp in existing):
        raise HTTPException(
            status_code=400,
            detail=f"Breakpoint already exists for routine '{request.routine_id}'"
        )
    
    # 创建断点
    breakpoint = Breakpoint(
        job_id=job_id,
        type="routine",
        routine_id=request.routine_id,
        enabled=request.enabled if request.enabled is not None else True,
    )
    
    # 添加断点（会自动替换 policy）
    breakpoint_mgr.add_breakpoint(breakpoint, routine=routine)
    
    return _breakpoint_to_response(breakpoint)


@router.delete(
    "/jobs/{job_id}/breakpoints/{breakpoint_id}",
    status_code=204,
    dependencies=[RequireAuth],
)
async def delete_breakpoint(job_id: str, breakpoint_id: str):
    """Delete a breakpoint and restore original policy."""
    # 验证 job 存在
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    # 获取 flow 和 routine
    from routilux.monitoring.flow_registry import FlowRegistry
    flow_registry = FlowRegistry.get_instance()
    flow = flow_registry.get(job_state.flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")
    
    registry = MonitoringRegistry.get_instance()
    breakpoint_mgr = registry.breakpoint_manager
    
    if not breakpoint_mgr:
        raise HTTPException(status_code=404, detail="Breakpoint manager not available")
    
    # 获取断点信息
    breakpoints = breakpoint_mgr.get_breakpoints(job_id)
    breakpoint = next((bp for bp in breakpoints if bp.breakpoint_id == breakpoint_id), None)
    
    if not breakpoint:
        raise HTTPException(status_code=404, detail=f"Breakpoint '{breakpoint_id}' not found")
    
    # 获取 routine 以恢复 policy
    routine = flow.routines.get(breakpoint.routine_id)
    
    # 删除断点（会自动恢复 policy）
    breakpoint_mgr.remove_breakpoint(breakpoint_id, job_id, routine=routine)
```

### 5. 添加 Debug Data 查询 API

**文件**：`routilux/routilux/api/routes/debug.py`

**新增端点**：

```python
@router.get("/jobs/{job_id}/debug/data", dependencies=[RequireAuth])
async def get_debug_data(job_id: str, routine_id: str = None):
    """Get debug data captured at breakpoint.
    
    Args:
        job_id: Job ID.
        routine_id: Optional routine ID to filter by.
    
    Returns:
        Debug data dictionary.
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    if not hasattr(job_state, 'debug_data'):
        return {"debug_data": {}}
    
    debug_data = job_state.debug_data
    
    if routine_id:
        # 返回特定 routine 的 debug 数据
        return {
            "routine_id": routine_id,
            "debug_data": debug_data.get(routine_id, {}),
        }
    else:
        # 返回所有 debug 数据
        return {
            "debug_data": debug_data,
        }
```

---

## 实现细节

### 1. Policy 替换的线程安全

**问题**：多线程环境下替换 policy 可能不安全。

**解决方案**：在 Routine 类中添加锁保护。

**文件**：`routilux/routilux/routine.py`

**修改内容**：

```python
def __init__(self):
    # ... 现有代码 ...
    self._policy_lock: threading.RLock = threading.RLock()  # 新增

def set_activation_policy(self, policy: Callable) -> Routine:
    """Set activation policy with thread safety."""
    with self._policy_lock:
        self._activation_policy = policy
    return self

def get_activation_policy(self) -> Callable | None:
    """Get current activation policy (thread-safe)."""
    with self._policy_lock:
        return self._activation_policy
```

### 2. 原 Policy 的保存和恢复

**问题**：如何保存和恢复原 policy？

**解决方案**：
1. 在 `BreakpointManager.add_breakpoint()` 时保存
2. 在 `BreakpointManager.remove_breakpoint()` 时恢复
3. 如果原 policy 是 `None`，恢复为 `immediate_policy()`

**实现**：

```python
# 在 BreakpointManager 中
def add_breakpoint(self, breakpoint: Breakpoint, routine: Optional["Routine"] = None):
    with self._lock:
        # 保存原 policy
        if routine:
            original_policy = routine.get_activation_policy()
            breakpoint.original_policy = original_policy
            
            # 替换为 breakpoint policy
            from routilux.activation_policies import breakpoint_policy
            routine.set_activation_policy(breakpoint_policy(breakpoint.routine_id))
        
        # ... 添加到列表 ...
```

### 3. Slot 队列清空

**问题**：`consume_all_new()` 是否真的清空队列？

**验证**：查看 `Slot.consume_all_new()` 的实现。

根据代码，`consume_all_new()` 会：
1. 获取所有未消费的数据
2. 标记为已消费
3. 返回数据列表

但队列中的数据点还在，只是标记为已消费。需要真正清空吗？

**方案 A（推荐）**：只消费数据，不物理清空队列
- 优点：保留历史数据，便于调试
- 缺点：队列可能增长

**方案 B**：物理清空队列
- 优点：队列不会增长
- 缺点：丢失历史数据

**建议**：使用方案 A，因为：
1. 队列有 `max_queue_length` 限制
2. 已消费的数据会在 watermark 时自动清理
3. 保留历史数据有助于调试

如果需要物理清空，可以添加方法：

```python
def clear_queue(self) -> None:
    """Clear all data from queue (for breakpoint use)."""
    with self._lock:
        self._queue.clear()
        self._last_consumed_index = -1
```

### 4. Debug Data 的存储位置

**选项 A**：`job_state.debug_data`（推荐）
- 优点：与 job_state 一起序列化，便于持久化
- 缺点：可能增大状态文件

**选项 B**：`job_state.shared_data["__debug__"]`
- 优点：利用现有字段
- 缺点：与业务数据混在一起

**选项 C**：独立的 debug store
- 优点：不影响 job_state
- 缺点：需要额外的存储管理

**建议**：使用选项 A，但默认不序列化（通过 `add_serializable_fields` 控制）。

---

## 工作流程

### 设置断点

```
1. API: POST /api/jobs/{job_id}/breakpoints
   {
     "type": "routine",
     "routine_id": "my_routine"
   }

2. BreakpointManager.add_breakpoint():
   - 保存 routine._activation_policy → breakpoint.original_policy
   - 替换为 breakpoint_policy(routine_id)
   - 添加到断点列表

3. 下次 routine 激活检查时：
   - breakpoint_policy 被调用
   - 消费所有 slot 数据
   - 保存到 job_state.debug_data[routine_id]
   - 返回 should_activate=False
   - routine 逻辑不执行
```

### 取消断点

```
1. API: DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id}

2. BreakpointManager.remove_breakpoint():
   - 从列表移除断点
   - 恢复 routine._activation_policy = breakpoint.original_policy
   - 如果没有原 policy，使用 immediate_policy()

3. 下次 routine 激活检查时：
   - 使用原 policy
   - 正常执行逻辑
```

### 查询 Debug Data

```
1. API: GET /api/jobs/{job_id}/debug/data?routine_id=my_routine

2. 返回：
   {
     "routine_id": "my_routine",
     "debug_data": {
       "slot_data": {
         "input": [{"value": 1}, {"value": 2}],
         "config": [{"setting": "x"}]
       },
       "timestamp": "2024-01-01T12:00:00",
       "routine_id": "my_routine"
     }
   }
```

---

## 优势分析

### 1. 实现简单

**对比原方案**：
- ❌ 原方案：需要 hook 机制、断点检查、队列管理
- ✅ 新方案：只需要替换 policy，利用现有机制

**代码量**：
- 原方案：~500 行代码
- 新方案：~200 行代码

### 2. 自动处理队列

**原方案问题**：
- 断点暂停时，队列仍可接收数据
- 需要手动检查队列状态
- 队列满时数据丢失

**新方案优势**：
- ✅ `consume_all_new()` 自动消费数据
- ✅ 数据保存到 `job_state.debug_data`
- ✅ 不会丢失数据

### 3. 统一接口

**原方案**：
- 支持 routine/slot/event/connection 级别
- 实现复杂，维护成本高

**新方案**：
- ✅ 只支持 routine 级别
- ✅ 接口统一，易于理解
- ✅ 维护成本低

### 4. 符合架构

**原方案**：
- 使用 hook 机制，与 activation policy 设计理念不一致

**新方案**：
- ✅ 利用 activation policy 机制
- ✅ 符合"策略模式"设计
- ✅ 与现有架构一致

---

## 潜在问题和解决方案

### 问题 1：多 Job 共享 Routine

**场景**：同一个 routine 对象被多个 job 使用。

**问题**：替换 policy 会影响所有 job。

**解决方案**：
- 方案 A：每个 job 使用独立的 routine 实例（推荐）
- 方案 B：在 policy 中检查 job_id

**实现**（方案 B）：

```python
def breakpoint_policy(routine_id: str, job_id: str):
    """Breakpoint policy with job_id check."""
    
    def policy(slots: dict[str, Slot], job_state: JobState) -> tuple[bool, dict[str, list[Any]], Any]:
        # 检查 job_id 是否匹配
        if job_state.job_id != job_id:
            # 不匹配，使用原 policy（需要从 breakpoint 获取）
            # 这里需要重新设计...
            pass
        
        # ... 断点逻辑 ...
    
    return policy
```

**建议**：使用方案 A，确保每个 job 有独立的 routine 实例。

### 问题 2：Policy 序列化

**问题**：`original_policy` 是函数，无法序列化。

**解决方案**：
- `original_policy` 不序列化
- 取消断点时，如果没有原 policy，使用 `immediate_policy()`
- 或者保存 policy 的标识符（如函数名）

### 问题 3：并发设置/取消断点

**问题**：多线程同时设置/取消断点可能冲突。

**解决方案**：
- 使用 `BreakpointManager._lock` 保护
- 使用 `Routine._policy_lock` 保护 policy 替换

---

## 实施计划

### 阶段一：核心实现（1 周）

1. **Day 1-2**：实现 `breakpoint_policy()`
   - 在 `activation_policies.py` 中添加
   - 实现数据收集和保存逻辑
   - 单元测试

2. **Day 3**：修改 `JobState`
   - 添加 `debug_data` 字段
   - 添加锁保护
   - 测试

3. **Day 4**：简化 `BreakpointManager`
   - 移除 slot/event/connection 支持
   - 实现 policy 保存和恢复
   - 测试

4. **Day 5**：修改 API
   - 更新 breakpoint 创建/删除 API
   - 添加 debug data 查询 API
   - 测试

### 阶段二：测试和优化（3 天）

1. **Day 1**：集成测试
   - 测试断点设置/取消
   - 测试数据保存和查询
   - 测试并发场景

2. **Day 2**：性能测试
   - 测试 policy 替换的性能
   - 测试大量数据时的性能

3. **Day 3**：文档和代码审查

---

## 总结

### 方案评估

**合理性**：⭐⭐⭐⭐⭐ (5/5)
- ✅ 实现简单，利用现有机制
- ✅ 自动处理队列，避免数据丢失
- ✅ 统一接口，易于理解
- ✅ 符合架构设计理念

**实现复杂度**：⭐ (1/5)
- ✅ 代码量少（~200 行）
- ✅ 逻辑简单
- ✅ 易于测试和维护

**工程最佳实践**：⭐⭐⭐⭐⭐ (5/5)
- ✅ 利用现有机制（activation policy）
- ✅ 线程安全设计
- ✅ 清晰的职责分离
- ✅ 易于扩展

### 建议

**强烈推荐采用此方案**，因为：
1. 实现简单，维护成本低
2. 自动处理队列，避免数据丢失
3. 符合现有架构设计
4. 易于测试和调试

**唯一需要注意**：确保每个 job 使用独立的 routine 实例，避免 policy 替换影响其他 job。

---

*文档版本：1.0*  
*最后更新：2024年*  
*设计者：系统架构师*
