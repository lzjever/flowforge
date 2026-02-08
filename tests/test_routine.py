"""
Routine 测试用例
"""

import pytest

from routilux import Routine


class TestRoutineBasic:
    """Routine 基本功能测试"""

    def test_create_routine(self):
        """测试用例 1: 创建 Routine 对象"""
        routine = Routine()
        assert routine._id is not None
        assert isinstance(routine._config, dict)
        assert len(routine._config) == 0

    def test_define_slot(self):
        """测试用例 2: 定义 Slot"""
        routine = Routine()

        def handler(data):
            pass

        slot = routine.define_slot("input", handler=handler)
        assert slot.name == "input"
        assert slot.routine == routine
        assert slot.handler == handler
        assert "input" in routine._slots

    def test_define_event(self):
        """测试用例 3: 定义 Event"""
        routine = Routine()

        event = routine.define_event("output", ["result", "status"])
        assert event.name == "output"
        assert event.routine == routine
        assert event.output_params == ["result", "status"]
        assert "output" in routine._events

    def test_emit_event(self):
        """测试用例 4: 触发 Event"""
        routine = Routine()

        # 定义事件
        event = routine.define_event("output", ["data"])

        # 触发事件（没有连接时不应该报错）
        routine.emit("output", data="test")

        # 验证事件已定义
        assert "output" in routine._events
        assert routine.get_event("output") == event

    def test_config_method(self):
        """测试用例 5: Config 方法"""
        routine = Routine()

        # 初始状态为空
        config = routine.config()
        assert isinstance(config, dict)
        assert len(config) == 0

        # 更新配置
        routine.set_config(count=1, result="success")

        # 验证 config() 返回副本
        config = routine.config()
        assert config["count"] == 1
        assert config["result"] == "success"

        # 修改返回的字典不应影响内部状态
        config["new_key"] = "new_value"
        assert "new_key" not in routine._config


class TestRoutineEdgeCases:
    """Routine 边界情况测试"""

    def test_empty_routine(self):
        """测试用例 6: 空 Routine"""
        routine = Routine()

        # 没有 slots 和 events 的 routine 应该可以正常工作
        assert len(routine._slots) == 0
        assert len(routine._events) == 0

        # Note: Direct calling via __call__ has been removed.
        # Routines are now executed through Flow.execute() with slot handlers.

    def test_duplicate_slot_name(self):
        """测试用例 7: 重复定义 Slot"""
        routine = Routine()

        routine.define_slot("input")

        # 重复定义同名 slot 应该报错
        with pytest.raises(ValueError):
            routine.define_slot("input")

    def test_duplicate_event_name(self):
        """测试用例 7: 重复定义 Event"""
        routine = Routine()

        routine.define_event("output")

        # 重复定义同名 event 应该报错
        with pytest.raises(ValueError):
            routine.define_event("output")


class TestRoutineIntegration:
    """Routine 集成测试"""

    def test_routine_lifecycle(self):
        """测试 Routine 完整生命周期"""
        routine = Routine()

        # 1. 定义 slots 和 events
        received_data = []

        def handler(data):
            received_data.append(data)

        routine.define_slot("input", handler=handler)
        routine.define_event("output", ["result"])

        # 2. 更新配置
        routine.set_config(initialized=True)

        # 3. 触发事件
        routine.emit("output", result="test")

        # 4. 查询配置
        config = routine.config()
        assert config["initialized"] is True
        assert "output" in routine._events
        assert "input" in routine._slots


class TestRoutineExecutionContext:
    """Routine ExecutionContext 集成测试"""

    def test_emit_uses_execution_context(self):
        """Test that emit() can access worker_state through ExecutionContext."""
        from routilux.core import Flow, Runtime
        from routilux.core.context import ExecutionContext, set_current_execution_context

        # Create test routines
        class TestSourceRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.output = self.add_event("output", ["data"])

        class TestDestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input = self.add_slot("input")
                self.last_input = None

        # Create flow with routines
        flow = Flow("test_flow")
        runtime = Runtime()

        source = TestSourceRoutine()
        dest = TestDestRoutine()
        flow.add_routine(source, "source")
        flow.add_routine(dest, "dest")
        flow.connect("source", "output", "dest", "input")

        # Register flow
        from routilux.core.registry import FlowRegistry
        FlowRegistry.get_instance().register(flow)

        # Create worker state
        worker_state = runtime.exec("test_flow")

        # Set execution context
        ctx = ExecutionContext(
            flow=flow,
            worker_state=worker_state,
            routine_id="source",
            job_context=None
        )
        set_current_execution_context(ctx)

        # Emit should work without explicit runtime parameter
        # It should get worker_state from ExecutionContext
        source.emit("output", data="test")

        # Give some time for the event to be processed
        import time
        time.sleep(0.1)

        # Verify dest received the data in its slot
        assert len(dest.input._queue) > 0
        assert dest.input._queue[0].data.get("data") == "test"

        # Cleanup
        runtime.shutdown(wait=False)
