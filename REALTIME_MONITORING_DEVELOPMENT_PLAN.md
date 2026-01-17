# 实时监控与调试接口开发计划

## 概述

本计划旨在完善 Routilux 的实时监控能力，提供：
1. **实时 Routine 工作状态监控**（是否正在执行）
2. **队列压力监控**（Slot 队列状态，支持前端动画/颜色展示）
3. **Routine 元信息显示**（Activation Policy 类型和配置、Routine 参数配置）
4. **代码结构优化**（提升整体功能的完整性和成熟度）

---

## 当前状态分析

### 已有能力

1. **基础 API**：
   - `GET /api/jobs/{job_id}/state` - 获取完整 job state
   - `GET /api/jobs/{job_id}/metrics` - 获取执行指标（依赖 MonitorCollector）
   - `GET /api/jobs/{job_id}/trace` - 获取执行追踪
   - `GET /api/jobs/{job_id}/debug/*` - 调试相关接口

2. **WebSocket 支持**：
   - `WS /ws/jobs/{job_id}/monitor` - 实时监控
   - 事件推送：`job_started`, `job_completed`, `routine_started`, `routine_completed`

3. **状态追踪**：
   - `job_state.routine_states` - 存储 routine 状态
   - `job_state.current_routine_id` - 当前执行的 routine
   - `job_state.record_execution()` - 记录执行历史

4. **Slot 队列**：
   - `slot.get_unconsumed_count()` - 获取未消费数据数量
   - `slot.max_queue_length` - 最大队列长度
   - `slot.watermark` - 水位阈值

### 缺失功能

1. **实时工作状态**：
   - ❌ 无法实时知道 routine 是否正在执行
   - ❌ `current_routine_id` 可能不准确（并发执行时）

2. **队列压力监控**：
   - ❌ 没有 API 获取 slot 队列状态
   - ❌ 无法获取队列使用率、压力指标

3. **元信息显示**：
   - ❌ 无法获取 activation policy 的类型和配置
   - ❌ 无法获取 routine 的 `_config` 配置

4. **代码结构问题**：
   - ⚠️ Runtime 没有追踪正在执行的 routine
   - ⚠️ 缺少统一的监控数据模型
   - ⚠️ WebSocket 事件不够丰富

---

## 开发计划

### 阶段一：核心数据模型和状态追踪（3-4 天）

#### 1.1 在 Runtime 中追踪执行状态

**文件**：`routilux/routilux/runtime.py`

**目标**：追踪每个 job 中正在执行的 routine

**实现**：

```python
class Runtime:
    def __init__(self, ...):
        # ... 现有代码 ...
        # 新增：追踪正在执行的 routine
        # job_id -> set[routine_id] (可能并发执行多个 routine)
        self._active_routines: Dict[str, Set[str]] = {}
        self._active_routines_lock = threading.RLock()
    
    def _activate_routine(self, routine, job_state, ...):
        """激活 routine 时标记为执行中"""
        routine_id = self._get_routine_id(routine, job_state)
        
        # 标记为执行中
        with self._active_routines_lock:
            if job_state.job_id not in self._active_routines:
                self._active_routines[job_state.job_id] = set()
            self._active_routines[job_state.job_id].add(routine_id)
        
        try:
            # ... 执行逻辑 ...
        finally:
            # 标记为执行完成
            with self._active_routines_lock:
                if job_state.job_id in self._active_routines:
                    self._active_routines[job_state.job_id].discard(routine_id)
                    # 如果 job 没有活跃的 routine，清理
                    if not self._active_routines[job_state.job_id]:
                        del self._active_routines[job_state.job_id]
    
    def get_active_routines(self, job_id: str) -> Set[str]:
        """获取正在执行的 routine ID 集合"""
        with self._active_routines_lock:
            return self._active_routines.get(job_id, set()).copy()
```

**测试**：
- 单 routine 执行时状态正确
- 并发执行多个 routine 时状态正确
- Job 完成后状态清理

#### 1.2 创建统一的监控数据模型

**文件**：`routilux/routilux/api/models/monitor.py`（新增或扩展）

**目标**：定义统一的监控数据模型

**实现**：

```python
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

class SlotQueueStatus(BaseModel):
    """Slot 队列状态"""
    slot_name: str
    routine_id: str
    unconsumed_count: int
    total_count: int
    max_length: int
    watermark_threshold: int
    usage_percentage: float  # 使用率 (0.0-1.0)
    pressure_level: str  # "low", "medium", "high", "critical"
    is_full: bool
    is_near_full: bool  # 超过 watermark

class RoutineExecutionStatus(BaseModel):
    """Routine 执行状态"""
    routine_id: str
    is_active: bool  # 是否正在执行
    status: str  # "pending", "running", "completed", "failed"
    last_execution_time: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0

class RoutineInfo(BaseModel):
    """Routine 元信息"""
    routine_id: str
    routine_type: str  # Routine 类名
    activation_policy: Dict[str, Any]  # Policy 类型和配置
    config: Dict[str, Any]  # Routine _config
    slots: List[str]  # Slot 名称列表
    events: List[str]  # Event 名称列表

class RoutineMonitoringData(BaseModel):
    """Routine 完整监控数据"""
    routine_id: str
    execution_status: RoutineExecutionStatus
    queue_status: List[SlotQueueStatus]
    info: RoutineInfo

class JobMonitoringData(BaseModel):
    """Job 完整监控数据"""
    job_id: str
    flow_id: str
    job_status: str
    routines: Dict[str, RoutineMonitoringData]  # routine_id -> data
    updated_at: datetime
```

**测试**：
- 模型序列化/反序列化正确
- 所有字段类型正确

---

### 阶段二：队列状态 API（2-3 天）

#### 2.1 添加 Slot 队列状态获取方法

**文件**：`routilux/routilux/slot.py`

**目标**：提供队列状态查询方法

**实现**：

```python
class Slot:
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态信息
        
        Returns:
            包含队列状态的字典：
            - unconsumed_count: 未消费数量
            - total_count: 总数量
            - max_length: 最大长度
            - watermark_threshold: 水位阈值
            - usage_percentage: 使用率
            - pressure_level: 压力等级
            - is_full: 是否已满
            - is_near_full: 是否接近满
        """
        with self._lock:
            unconsumed = self.get_unconsumed_count()
            total = len(self._queue)
            usage = total / self.max_queue_length if self.max_queue_length > 0 else 0.0
            
            # 计算压力等级
            if usage >= 1.0:
                pressure = "critical"
                is_full = True
            elif usage >= self.watermark:
                pressure = "high"
                is_full = False
            elif usage >= 0.6:
                pressure = "medium"
                is_full = False
            else:
                pressure = "low"
                is_full = False
            
            is_near_full = usage >= self.watermark
            
            return {
                "unconsumed_count": unconsumed,
                "total_count": total,
                "max_length": self.max_queue_length,
                "watermark_threshold": self.watermark_threshold,
                "usage_percentage": usage,
                "pressure_level": pressure,
                "is_full": is_full,
                "is_near_full": is_near_full,
            }
```

**测试**：
- 空队列状态正确
- 满队列状态正确
- 不同使用率下的压力等级正确

#### 2.2 创建队列状态 API

**文件**：`routilux/routilux/api/routes/monitor.py`（扩展）

**目标**：提供队列状态查询端点

**实现**：

```python
@router.get(
    "/jobs/{job_id}/routines/{routine_id}/queue-status",
    response_model=List[SlotQueueStatus],
    dependencies=[RequireAuth]
)
async def get_routine_queue_status(job_id: str, routine_id: str):
    """获取指定 routine 的所有 slot 队列状态"""
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
    
    if routine_id not in flow.routines:
        raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")
    
    routine = flow.routines[routine_id]
    
    # 收集所有 slot 的队列状态
    queue_statuses = []
    for slot_name, slot in routine.slots.items():
        status = slot.get_queue_status()
        queue_statuses.append(SlotQueueStatus(
            slot_name=slot_name,
            routine_id=routine_id,
            **status
        ))
    
    return queue_statuses


@router.get(
    "/jobs/{job_id}/queues/status",
    response_model=Dict[str, List[SlotQueueStatus]],
    dependencies=[RequireAuth]
)
async def get_job_queues_status(job_id: str):
    """获取 job 中所有 routine 的队列状态"""
    # 验证 job 存在
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    # 获取 flow
    from routilux.monitoring.flow_registry import FlowRegistry
    flow_registry = FlowRegistry.get_instance()
    flow = flow_registry.get(job_state.flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")
    
    # 收集所有 routine 的队列状态
    all_queues = {}
    for routine_id, routine in flow.routines.items():
        queue_statuses = []
        for slot_name, slot in routine.slots.items():
            status = slot.get_queue_status()
            queue_statuses.append(SlotQueueStatus(
                slot_name=slot_name,
                routine_id=routine_id,
                **status
            ))
        all_queues[routine_id] = queue_statuses
    
    return all_queues
```

**测试**：
- 单个 routine 队列状态正确
- 所有 routine 队列状态正确
- 空队列和满队列处理正确

---

### 阶段三：Routine 元信息 API（2-3 天）

#### 3.1 提取 Activation Policy 信息

**文件**：`routilux/routilux/routine.py`

**目标**：提供 policy 信息提取方法

**实现**：

```python
class Routine:
    def get_activation_policy_info(self) -> Dict[str, Any]:
        """获取 activation policy 的类型和配置信息
        
        Returns:
            包含 policy 信息的字典：
            - type: Policy 类型名称（如 "immediate", "batch_size", "time_interval"）
            - config: Policy 配置参数
            - description: Policy 描述
        """
        if self._activation_policy is None:
            return {
                "type": "none",
                "config": {},
                "description": "No activation policy set"
            }
        
        # 尝试从函数名推断类型
        policy_name = getattr(self._activation_policy, "__name__", "unknown")
        
        # 检查是否是内置 policy
        if "immediate" in policy_name.lower():
            return {
                "type": "immediate",
                "config": {},
                "description": "Activate immediately when any slot receives data"
            }
        elif "batch_size" in policy_name.lower():
            # 尝试从闭包变量获取配置
            closure_vars = self._activation_policy.__closure__
            if closure_vars:
                # 查找 min_batch_size
                for cell in closure_vars:
                    if hasattr(cell, "cell_contents"):
                        val = cell.cell_contents
                        if isinstance(val, int) and val > 0:
                            return {
                                "type": "batch_size",
                                "config": {"min_batch_size": val},
                                "description": f"Activate when all slots have at least {val} items"
                            }
            return {
                "type": "batch_size",
                "config": {},
                "description": "Activate when all slots have minimum batch size"
            }
        elif "time_interval" in policy_name.lower():
            # 类似处理 time_interval_policy
            closure_vars = self._activation_policy.__closure__
            if closure_vars:
                for cell in closure_vars:
                    if hasattr(cell, "cell_contents"):
                        val = cell.cell_contents
                        if isinstance(val, (int, float)) and val > 0:
                            return {
                                "type": "time_interval",
                                "config": {"min_interval_seconds": val},
                                "description": f"Activate at most once every {val} seconds"
                            }
            return {
                "type": "time_interval",
                "config": {},
                "description": "Activate at most once per time interval"
            }
        elif "all_slots_ready" in policy_name.lower():
            return {
                "type": "all_slots_ready",
                "config": {},
                "description": "Activate when all slots have at least 1 data point"
            }
        else:
            # 自定义 policy
            return {
                "type": "custom",
                "config": {},
                "description": f"Custom activation policy: {policy_name}"
            }
```

**注意**：这种方法可能不够准确，更好的方案是在创建 policy 时注册元信息。

**改进方案**（可选，更完善）：

```python
# 在 activation_policies.py 中
def immediate_policy():
    def policy(slots, job_state):
        # ... 实现 ...
    policy._policy_type = "immediate"
    policy._policy_config = {}
    policy._policy_description = "Activate immediately when any slot receives data"
    return policy

# 在 routine.py 中
def get_activation_policy_info(self) -> Dict[str, Any]:
    if self._activation_policy is None:
        return {"type": "none", "config": {}, "description": "No activation policy set"}
    
    # 从 policy 函数获取元信息
    policy_type = getattr(self._activation_policy, "_policy_type", "custom")
    policy_config = getattr(self._activation_policy, "_policy_config", {})
    policy_description = getattr(self._activation_policy, "_policy_description", "Custom policy")
    
    return {
        "type": policy_type,
        "config": policy_config,
        "description": policy_description
    }
```

**测试**：
- 各种 policy 类型识别正确
- 配置参数提取正确

#### 3.2 创建 Routine 元信息 API

**文件**：`routilux/routilux/api/routes/monitor.py`（扩展）

**目标**：提供 routine 元信息查询端点

**实现**：

```python
@router.get(
    "/flows/{flow_id}/routines/{routine_id}/info",
    response_model=RoutineInfo,
    dependencies=[RequireAuth]
)
async def get_routine_info(flow_id: str, routine_id: str):
    """获取 routine 的元信息（policy、config、slots、events）"""
    # 获取 flow
    from routilux.monitoring.flow_registry import FlowRegistry
    flow_registry = FlowRegistry.get_instance()
    flow = flow_registry.get(flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
    
    if routine_id not in flow.routines:
        raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")
    
    routine = flow.routines[routine_id]
    
    # 获取 policy 信息
    policy_info = routine.get_activation_policy_info()
    
    # 获取 config
    config = routine.get_all_config()
    
    # 获取 slots 和 events
    slots = list(routine.slots.keys())
    events = list(routine.events.keys())
    
    # 获取 routine 类型
    routine_type = type(routine).__name__
    
    return RoutineInfo(
        routine_id=routine_id,
        routine_type=routine_type,
        activation_policy=policy_info,
        config=config,
        slots=slots,
        events=events
    )
```

**测试**：
- Policy 信息正确
- Config 信息正确
- Slots 和 Events 列表正确

---

### 阶段四：实时状态 API（2-3 天）

#### 4.1 创建实时状态 API

**文件**：`routilux/routilux/api/routes/monitor.py`（扩展）

**目标**：提供实时 routine 状态查询端点

**实现**：

```python
@router.get(
    "/jobs/{job_id}/routines/status",
    response_model=Dict[str, RoutineExecutionStatus],
    dependencies=[RequireAuth]
)
async def get_routines_status(job_id: str):
    """获取 job 中所有 routine 的执行状态"""
    # 验证 job 存在
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    # 获取 flow
    from routilux.monitoring.flow_registry import FlowRegistry
    flow_registry = FlowRegistry.get_instance()
    flow = flow_registry.get(job_state.flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")
    
    # 获取正在执行的 routine（从 Runtime）
    from routilux.runtime import Runtime
    # 需要获取 Runtime 实例（可能需要通过 registry 或全局实例）
    runtime = get_runtime_instance()  # 需要实现
    active_routines = runtime.get_active_routines(job_id)
    
    # 获取 metrics（用于执行次数、错误次数等）
    registry = MonitoringRegistry.get_instance()
    collector = registry.monitor_collector
    
    routines_status = {}
    for routine_id in flow.routines.keys():
        # 检查是否正在执行
        is_active = routine_id in active_routines
        
        # 获取 routine state
        routine_state = job_state.get_routine_state(routine_id)
        
        # 获取状态
        if routine_state:
            status = routine_state.get("status", "pending")
        elif is_active:
            status = "running"
        else:
            status = "pending"
        
        # 获取 metrics
        execution_count = 0
        error_count = 0
        last_execution_time = None
        
        if collector:
            metrics = collector.get_metrics(job_id)
            if metrics and routine_id in metrics.routine_metrics:
                rm = metrics.routine_metrics[routine_id]
                execution_count = rm.execution_count
                error_count = rm.error_count
                last_execution_time = rm.last_execution
        
        routines_status[routine_id] = RoutineExecutionStatus(
            routine_id=routine_id,
            is_active=is_active,
            status=status,
            last_execution_time=last_execution_time,
            execution_count=execution_count,
            error_count=error_count
        )
    
    return routines_status


@router.get(
    "/jobs/{job_id}/monitoring",
    response_model=JobMonitoringData,
    dependencies=[RequireAuth]
)
async def get_job_monitoring_data(job_id: str):
    """获取 job 的完整监控数据（状态 + 队列 + 元信息）"""
    # 验证 job 存在
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    # 获取 flow
    from routilux.monitoring.flow_registry import FlowRegistry
    flow_registry = FlowRegistry.get_instance()
    flow = flow_registry.get(job_state.flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")
    
    # 获取正在执行的 routine
    runtime = get_runtime_instance()
    active_routines = runtime.get_active_routines(job_id)
    
    # 获取 metrics
    registry = MonitoringRegistry.get_instance()
    collector = registry.monitor_collector
    
    # 构建每个 routine 的监控数据
    routines_data = {}
    for routine_id, routine in flow.routines.items():
        # 执行状态
        is_active = routine_id in active_routines
        routine_state = job_state.get_routine_state(routine_id)
        status = routine_state.get("status", "pending") if routine_state else ("running" if is_active else "pending")
        
        execution_count = 0
        error_count = 0
        last_execution_time = None
        if collector:
            metrics = collector.get_metrics(job_id)
            if metrics and routine_id in metrics.routine_metrics:
                rm = metrics.routine_metrics[routine_id]
                execution_count = rm.execution_count
                error_count = rm.error_count
                last_execution_time = rm.last_execution
        
        execution_status = RoutineExecutionStatus(
            routine_id=routine_id,
            is_active=is_active,
            status=status,
            last_execution_time=last_execution_time,
            execution_count=execution_count,
            error_count=error_count
        )
        
        # 队列状态
        queue_statuses = []
        for slot_name, slot in routine.slots.items():
            status = slot.get_queue_status()
            queue_statuses.append(SlotQueueStatus(
                slot_name=slot_name,
                routine_id=routine_id,
                **status
            ))
        
        # 元信息
        policy_info = routine.get_activation_policy_info()
        config = routine.get_all_config()
        routine_type = type(routine).__name__
        
        info = RoutineInfo(
            routine_id=routine_id,
            routine_type=routine_type,
            activation_policy=policy_info,
            config=config,
            slots=list(routine.slots.keys()),
            events=list(routine.events.keys())
        )
        
        routines_data[routine_id] = RoutineMonitoringData(
            routine_id=routine_id,
            execution_status=execution_status,
            queue_status=queue_statuses,
            info=info
        )
    
    return JobMonitoringData(
        job_id=job_id,
        flow_id=job_state.flow_id,
        job_status=str(job_state.status),
        routines=routines_data,
        updated_at=job_state.updated_at
    )
```

**注意**：需要实现 `get_runtime_instance()` 来获取 Runtime 实例。可以通过以下方式：

```python
# 在 runtime.py 中
_runtime_instance: Optional[Runtime] = None

def get_runtime_instance() -> Runtime:
    """获取全局 Runtime 实例（用于 API）"""
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = Runtime(thread_pool_size=10)
    return _runtime_instance
```

**测试**：
- 单个 routine 状态正确
- 所有 routine 状态正确
- 正在执行的 routine 标记正确
- 完整监控数据正确

---

### 阶段五：WebSocket 实时推送（2-3 天）

#### 5.1 扩展 WebSocket 事件

**文件**：`routilux/routilux/monitoring/hooks.py`

**目标**：推送更丰富的实时事件

**实现**：

```python
def on_routine_start(self, routine, routine_id, job_state):
    """Routine 开始执行时推送事件"""
    # ... 现有代码 ...
    
    # 推送队列状态更新
    queue_updates = {}
    for slot_name, slot in routine.slots.items():
        status = slot.get_queue_status()
        queue_updates[slot_name] = status
    
    _publish_event_via_manager(
        job_state.job_id,
        {
            "type": "routine_queue_update",
            "job_id": job_state.job_id,
            "routine_id": routine_id,
            "queues": queue_updates,
        }
    )

def on_slot_data_received(self, slot, routine_id, job_state, data):
    """Slot 接收数据时推送队列状态更新"""
    # ... 现有代码 ...
    
    # 推送队列状态更新
    status = slot.get_queue_status()
    _publish_event_via_manager(
        job_state.job_id,
        {
            "type": "slot_queue_update",
            "job_id": job_state.job_id,
            "routine_id": routine_id,
            "slot_name": slot.name,
            "queue_status": status,
        }
    )
```

**文件**：`routilux/routilux/runtime.py`

**实现**：

```python
def _activate_routine(self, ...):
    """激活 routine 时推送状态更新"""
    # ... 现有代码 ...
    
    # 推送 routine 状态更新
    from routilux.monitoring.hooks import execution_hooks
    execution_hooks.on_routine_status_change(
        routine, routine_id, job_state, "running"
    )
    
    try:
        # ... 执行逻辑 ...
    finally:
        # 推送 routine 状态更新（完成）
        execution_hooks.on_routine_status_change(
            routine, routine_id, job_state, "idle"
        )
```

**文件**：`routilux/routilux/monitoring/hooks.py`（扩展）

```python
def on_routine_status_change(self, routine, routine_id, job_state, status: str):
    """Routine 状态变化时推送事件"""
    if not MonitoringRegistry.is_enabled():
        return
    
    _publish_event_via_manager(
        job_state.job_id,
        {
            "type": "routine_status_change",
            "job_id": job_state.job_id,
            "routine_id": routine_id,
            "status": status,
            "is_active": status == "running",
        }
    )
```

**测试**：
- 事件推送正确
- 队列状态更新及时
- 状态变化事件准确

---

### 阶段六：代码结构优化（2-3 天）

#### 6.1 统一监控数据访问

**文件**：`routilux/routilux/monitoring/monitor_service.py`（新建）

**目标**：提供统一的监控数据访问服务

**实现**：

```python
class MonitorService:
    """统一的监控数据访问服务"""
    
    def __init__(self):
        self._runtime = None
        self._registry = MonitoringRegistry.get_instance()
    
    def get_runtime(self) -> Runtime:
        """获取 Runtime 实例"""
        if self._runtime is None:
            from routilux.runtime import get_runtime_instance
            self._runtime = get_runtime_instance()
        return self._runtime
    
    def get_job_monitoring_data(self, job_id: str) -> JobMonitoringData:
        """获取 job 的完整监控数据"""
        # 整合所有监控数据获取逻辑
        # ... 实现 ...
    
    def get_routine_monitoring_data(
        self, job_id: str, routine_id: str
    ) -> RoutineMonitoringData:
        """获取 routine 的完整监控数据"""
        # ... 实现 ...
```

#### 6.2 优化 API 路由结构

**文件**：`routilux/routilux/api/routes/monitor.py`

**目标**：重构 API 路由，使用 MonitorService

**实现**：

```python
# 创建 MonitorService 实例
_monitor_service = MonitorService()

@router.get("/jobs/{job_id}/monitoring", ...)
async def get_job_monitoring_data(job_id: str):
    """使用 MonitorService 获取数据"""
    return _monitor_service.get_job_monitoring_data(job_id)
```

#### 6.3 添加 API 文档和类型定义

**文件**：`routilux/routilux/api/models/monitor.py`

**目标**：完善所有监控相关的 Pydantic 模型

**实现**：
- 确保所有模型都有完整的字段说明
- 添加示例值
- 添加验证规则

---

## 实施时间表

| 阶段 | 任务 | 预计时间 | 优先级 |
|------|------|----------|--------|
| 阶段一 | 核心数据模型和状态追踪 | 3-4 天 | P0 |
| 阶段二 | 队列状态 API | 2-3 天 | P0 |
| 阶段三 | Routine 元信息 API | 2-3 天 | P1 |
| 阶段四 | 实时状态 API | 2-3 天 | P0 |
| 阶段五 | WebSocket 实时推送 | 2-3 天 | P1 |
| 阶段六 | 代码结构优化 | 2-3 天 | P2 |

**总计**：13-19 天（约 2.5-3.5 周）

---

## 测试计划

### 单元测试

1. **Runtime 状态追踪**：
   - 测试 `_active_routines` 正确更新
   - 测试并发执行时状态正确
   - 测试 job 完成后状态清理

2. **Slot 队列状态**：
   - 测试 `get_queue_status()` 各种场景
   - 测试压力等级计算正确

3. **Policy 信息提取**：
   - 测试各种 policy 类型识别
   - 测试配置参数提取

### 集成测试

1. **API 端点**：
   - 测试所有新增 API 端点
   - 测试错误处理
   - 测试并发访问

2. **WebSocket**：
   - 测试事件推送
   - 测试连接管理
   - 测试多客户端

### 端到端测试

1. **完整监控流程**：
   - 启动 job
   - 监控 routine 状态变化
   - 监控队列状态变化
   - 验证前端显示

---

## 前端集成建议

### 1. 实时状态显示

```typescript
// 使用 WebSocket 接收实时更新
const ws = new WebSocket(`ws://localhost:20555/ws/jobs/${jobId}/monitor`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === "routine_status_change") {
    // 更新 routine 状态
    updateRoutineStatus(data.routine_id, data.status, data.is_active);
  } else if (data.type === "slot_queue_update") {
    // 更新队列状态（动画/颜色）
    updateQueueStatus(data.routine_id, data.slot_name, data.queue_status);
  }
};
```

### 2. 队列压力可视化

```typescript
// 根据压力等级设置颜色
function getQueueColor(pressureLevel: string): string {
  switch (pressureLevel) {
    case "low": return "#4CAF50";      // 绿色
    case "medium": return "#FFC107";  // 黄色
    case "high": return "#FF9800";    // 橙色
    case "critical": return "#F44336"; // 红色
    default: return "#9E9E9E";        // 灰色
  }
}

// 根据使用率设置动画速度
function getAnimationSpeed(usagePercentage: number): number {
  if (usagePercentage >= 0.9) return "fast";  // 快速闪烁
  if (usagePercentage >= 0.7) return "medium";
  return "slow";
}
```

### 3. Routine 元信息显示

```typescript
// 显示 activation policy 信息
function displayPolicyInfo(policy: ActivationPolicyInfo) {
  return (
    <div>
      <strong>Policy:</strong> {policy.type}
      {policy.config && (
        <div>
          {Object.entries(policy.config).map(([key, value]) => (
            <span key={key}>{key}: {value}</span>
          ))}
        </div>
      )}
      <p>{policy.description}</p>
    </div>
  );
}
```

---

## 代码质量要求

1. **类型安全**：
   - 所有 API 使用 Pydantic 模型
   - TypeScript 前端使用生成的类型

2. **错误处理**：
   - 所有 API 端点都有错误处理
   - 返回明确的错误信息

3. **线程安全**：
   - 所有共享状态使用锁保护
   - 避免死锁

4. **性能**：
   - 监控数据获取不阻塞执行
   - WebSocket 事件推送异步

5. **文档**：
   - API 端点有完整文档
   - 代码有必要的注释

---

## 风险评估

### 高风险

1. **Runtime 状态追踪**：
   - 风险：并发执行时状态可能不准确
   - 缓解：使用线程安全的 Set，仔细测试并发场景

2. **Policy 信息提取**：
   - 风险：自定义 policy 可能无法识别
   - 缓解：提供 fallback，允许手动注册元信息

### 中风险

1. **WebSocket 性能**：
   - 风险：大量事件推送可能影响性能
   - 缓解：事件合并、限流

2. **API 性能**：
   - 风险：获取完整监控数据可能较慢
   - 缓解：缓存、异步获取

---

## 后续优化建议

1. **监控数据缓存**：
   - 缓存 routine 状态和队列状态
   - 定期刷新

2. **批量 API**：
   - 支持批量获取多个 job 的监控数据
   - 减少请求次数

3. **监控指标聚合**：
   - 提供 flow 级别的聚合指标
   - 支持时间序列数据

4. **告警机制**：
   - 队列满时告警
   - Routine 错误率过高时告警

---

*文档版本：1.0*  
*创建日期：2024年*  
*最后更新：2024年*
