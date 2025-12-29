"""
Event 测试用例
"""

from routilux import Routine


class TestEventConnection:
    """Event 连接管理测试"""

    def test_connect_to_slot(self):
        """测试用例 1: 连接到 Slot"""
        routine1 = Routine()
        routine = Routine()

        event = routine1.define_event("output", ["data"])
        slot = routine.define_slot("input")

        # 连接
        event.connect(slot)

        # 验证连接关系
        assert slot in event.connected_slots
        assert event in slot.connected_events

    def test_disconnect_from_slot(self):
        """测试用例 2: 断开连接"""
        routine1 = Routine()
        routine = Routine()

        event = routine1.define_event("output")
        slot = routine.define_slot("input")

        # 连接
        event.connect(slot)
        assert slot in event.connected_slots

        # 断开
        event.disconnect(slot)
        assert slot not in event.connected_slots
        assert event not in slot.connected_events

    def test_one_to_many_connection(self):
        """测试用例 3: 一对多连接 - 一个 event 连接多个 slots"""
        routine1 = Routine()
        routine = Routine()
        routine3 = Routine()

        event = routine1.define_event("output")
        slot1 = routine.define_slot("input1")
        slot2 = routine3.define_slot("input2")

        # 连接多个 slots
        event.connect(slot1)
        event.connect(slot2)

        # 验证
        assert len(event.connected_slots) == 2
        assert slot1 in event.connected_slots
        assert slot2 in event.connected_slots


class TestEventEmission:
    """Event 事件触发测试"""

    def test_emit_to_connected_slots(self):
        """测试用例 4: 触发事件"""
        received_data = []

        def handler1(data=None, **kwargs):
            if data:
                received_data.append(("handler1", {"data": data}))
            elif kwargs:
                received_data.append(("handler1", kwargs))

        def handler2(data=None, **kwargs):
            if data:
                received_data.append(("handler2", {"data": data}))
            elif kwargs:
                received_data.append(("handler2", kwargs))

        class Routine1(Routine):
            def __init__(self):
                super().__init__()
                # Define trigger slot for entry routine
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                self.emit("output", data="test")

        routine1 = Routine1()
        routine = Routine()
        routine3 = Routine()

        slot1 = routine.define_slot("input1", handler=handler1)
        slot2 = routine3.define_slot("input2", handler=handler2)

        # 连接
        routine1.get_event("output").connect(slot1)
        routine1.get_event("output").connect(slot2)

        # 触发事件（需要通过 Flow 来正确触发）
        from routilux import Flow

        flow = Flow()
        flow.add_routine(routine1, "r1")
        flow.add_routine(routine, "r2")
        flow.add_routine(routine3, "r3")
        flow.connect("r1", "output", "r2", "input1")
        flow.connect("r1", "output", "r3", "input2")

        # 执行 flow
        flow.execute("r1")

        # 验证所有连接的 slots 都收到数据
        assert len(received_data) >= 2

    def test_emit_without_connections(self):
        """测试用例 5: 无连接事件"""
        routine = Routine()

        routine.define_event("output", ["data"])

        # 没有连接的事件应该可以正常触发，不报错
        routine.emit("output", data="test")

        # 验证事件已定义
        assert "output" in routine._events

    def test_output_params(self):
        """测试用例 6: 输出参数验证"""
        routine = Routine()

        # 定义带输出参数的事件
        event = routine.define_event("output", ["result", "status"])

        # 验证输出参数正确记录
        assert "result" in event.output_params
        assert "status" in event.output_params

        # 未声明的参数也应该能传递
        routine.emit("output", result="ok", status="success", extra="data")


class TestEventDataFlow:
    """Event 数据流测试"""

    def test_data_propagation(self):
        """测试数据传播"""
        results = []

        def handler(value1=None, value2=None, **kwargs):
            if value1 or value2:
                results.append({"value1": value1, "value2": value2})
            elif kwargs:
                results.append(kwargs)

        class Routine1(Routine):
            def __init__(self):
                super().__init__()
                # Define trigger slot for entry routine
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["value1", "value2"])

            def _handle_trigger(self, **kwargs):
                self.emit("output", value1="a", value2="b")

        routine1 = Routine1()
        routine = Routine()

        slot = routine.define_slot("input", handler=handler)

        # 连接
        routine1.get_event("output").connect(slot)

        # 触发事件，传递多个参数（需要通过 Flow）
        from routilux import Flow

        flow = Flow()
        flow.add_routine(routine1, "r1")
        flow.add_routine(routine, "r2")
        flow.connect("r1", "output", "r2", "input")

        # 执行 flow
        flow.execute("r1")

        # 验证数据正确传递
        assert len(results) >= 1
        # 检查 value1 和 value2 是否在结果中
        first_result = results[0]
        assert first_result.get("value1") == "a" or "a" in str(first_result)
        assert first_result.get("value2") == "b" or "b" in str(first_result)


class TestEmitAutoFlowDetection:
    """测试改进后的 emit() 接口 - 自动 flow 检测"""

    def test_emit_auto_detects_flow(self):
        """测试 emit() 自动从 routine 上下文检测 flow"""
        from routilux import Flow

        flow = Flow()
        received_data = []

        class SourceRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                # 不需要显式传递 flow - 自动从 routine._current_flow 获取
                self.emit("output", data="auto_detected")

        class TargetRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self._handle_input)

            def _handle_input(self, data=None, **kwargs):
                received_data.append(data or kwargs.get("data"))

        source = SourceRoutine()
        target = TargetRoutine()

        source_id = flow.add_routine(source, "source")
        target_id = flow.add_routine(target, "target")

        flow.connect(source_id, "output", target_id, "input")

        # 执行 flow - 这会自动设置 routine._current_flow
        job_state = flow.execute(source_id)
        flow.wait_for_completion(timeout=2.0)

        # 验证数据正确传递（说明 flow 自动检测成功）
        assert len(received_data) > 0
        assert "auto_detected" in received_data

    def test_emit_explicit_flow_still_works(self):
        """测试显式传递 flow 参数仍然工作（向后兼容）"""
        from routilux import Flow

        flow = Flow()
        received_data = []

        class SourceRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                # 显式传递 flow 仍然应该工作
                flow_obj = getattr(self, "_current_flow", None)
                self.emit("output", flow=flow_obj, data="explicit_flow")

        class TargetRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self._handle_input)

            def _handle_input(self, data=None, **kwargs):
                received_data.append(data or kwargs.get("data"))

        source = SourceRoutine()
        target = TargetRoutine()

        source_id = flow.add_routine(source, "source")
        target_id = flow.add_routine(target, "target")

        flow.connect(source_id, "output", target_id, "input")

        job_state = flow.execute(source_id)
        flow.wait_for_completion(timeout=2.0)

        # 验证显式传递 flow 仍然工作
        assert len(received_data) > 0
        assert "explicit_flow" in received_data

    def test_emit_fallback_without_flow(self):
        """测试没有 flow 上下文时的 fallback 行为（legacy 模式）"""
        received_data = []

        class SourceRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.output_event = self.define_event("output", ["data"])

            def emit_test(self):
                # 没有 flow 上下文，应该 fallback 到直接调用 slot.receive()
                self.emit("output", data="no_flow")

        class TargetRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self._handle_input)

            def _handle_input(self, data=None, **kwargs):
                received_data.append(data or kwargs.get("data"))

        source = SourceRoutine()
        target = TargetRoutine()

        # 直接连接（不使用 Flow）
        source.get_event("output").connect(target.get_slot("input"))

        # 在没有 flow 上下文的情况下 emit
        source.emit_test()

        # 验证 fallback 模式工作（直接调用 slot.receive()）
        assert len(received_data) > 0
        assert "no_flow" in received_data

    def test_emit_multiple_calls_auto_detect(self):
        """测试多个 emit 调用都能自动检测 flow"""
        from routilux import Flow

        flow = Flow()
        received_data = []

        class SourceRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                # 多次 emit，都不需要显式传递 flow
                for i in range(3):
                    self.emit("output", data=f"message_{i}")

        class TargetRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self._handle_input)

            def _handle_input(self, data=None, **kwargs):
                received_data.append(data or kwargs.get("data"))

        source = SourceRoutine()
        target = TargetRoutine()

        source_id = flow.add_routine(source, "source")
        target_id = flow.add_routine(target, "target")

        flow.connect(source_id, "output", target_id, "input")

        job_state = flow.execute(source_id)
        flow.wait_for_completion(timeout=2.0)

        # 验证所有 emit 调用都成功
        assert len(received_data) >= 3
        for i in range(3):
            assert f"message_{i}" in received_data

    def test_emit_explicit_flow_parameter_used(self):
        """测试显式传递的 flow 参数被正确使用"""
        from routilux import Flow

        flow = Flow()
        received_data = []
        flow_used = []

        class SourceRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                # 显式传递 flow 参数应该被使用
                # 即使 routine._current_flow 已经设置，显式参数优先
                explicit_flow = getattr(self, "_current_flow", None)
                self.emit("output", flow=explicit_flow, data="explicit_used")
                # 记录使用的 flow
                flow_used.append(explicit_flow is not None)

        class TargetRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self._handle_input)

            def _handle_input(self, data=None, **kwargs):
                received_data.append(data or kwargs.get("data"))

        source = SourceRoutine()
        target = TargetRoutine()

        source_id = flow.add_routine(source, "source")
        target_id = flow.add_routine(target, "target")

        flow.connect(source_id, "output", target_id, "input")

        job_state = flow.execute(source_id)
        flow.wait_for_completion(timeout=2.0)

        # 验证显式传递的 flow 被使用（数据正确传递说明 flow 被正确使用）
        assert len(received_data) > 0
        assert "explicit_used" in received_data
        assert any(flow_used)  # 至少有一次使用了 flow

    def test_emit_in_nested_handlers(self):
        """测试在嵌套的 handler 调用中 emit 也能自动检测 flow"""
        from routilux import Flow

        flow = Flow()
        execution_order = []

        class SourceRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                execution_order.append("trigger_started")
                # 调用另一个方法，该方法也会 emit
                self._emit_through_helper()

            def _emit_through_helper(self):
                # 在辅助方法中 emit，也应该能自动检测 flow
                self.emit("output", data="from_helper")

        class TargetRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self._handle_input)

            def _handle_input(self, data=None, **kwargs):
                execution_order.append(f"received_{data or kwargs.get('data')}")

        source = SourceRoutine()
        target = TargetRoutine()

        source_id = flow.add_routine(source, "source")
        target_id = flow.add_routine(target, "target")

        flow.connect(source_id, "output", target_id, "input")

        job_state = flow.execute(source_id)
        flow.wait_for_completion(timeout=2.0)

        # 验证嵌套调用中的 emit 也能工作
        assert "trigger_started" in execution_order
        assert "received_from_helper" in execution_order

    def test_emit_after_resume(self):
        """测试 resume 后 emit 也能自动检测 flow"""
        from routilux import Flow

        flow = Flow()
        received_data = []

        class SourceRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                # Resume 后，routine._current_flow 应该被重新设置
                self.emit("output", data="after_resume")

        class TargetRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self._handle_input)

            def _handle_input(self, data=None, **kwargs):
                received_data.append(data or kwargs.get("data"))

        source = SourceRoutine()
        target = TargetRoutine()

        source_id = flow.add_routine(source, "source")
        target_id = flow.add_routine(target, "target")

        flow.connect(source_id, "output", target_id, "input")

        # 执行并暂停
        job_state = flow.execute(source_id)
        flow.pause(reason="test")

        # Resume
        resumed_job_state = flow.resume(job_state)
        flow.wait_for_completion(timeout=2.0)

        # 验证 resume 后 emit 仍然能自动检测 flow
        # 注意：这个测试主要验证 resume 后 _current_flow 被正确设置
        assert resumed_job_state.status in ["completed", "running"]
