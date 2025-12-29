"""
集成测试用例
"""

from routilux import Flow, Routine


class TestCompleteFlow:
    """完整流程测试"""

    def test_data_processing_flow(self):
        """测试用例 1: 数据处理流程 InputProcessor -> Validator -> Processor -> OutputFormatter"""
        flow = Flow()
        results = []

        class InputProcessor(Routine):
            def __init__(self):
                super().__init__()
                # Define trigger slot for entry routine
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, input_data=None, **kwargs):
                input_data = input_data or kwargs.get("input_data", "default")
                processed = f"Processed: {input_data}"
                self._stats["input_processed"] = True
                # Get flow from routine context
                flow = getattr(self, "_current_flow", None)
                self.emit("output", flow=flow, data=processed)

        class Validator(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self.validate)
                self.output_event = self.define_event("output", ["data"])

            def validate(self, data=None, **kwargs):
                if data and len(str(data)) > 0:
                    self._stats["validated"] = True
                    # Get flow from routine context
                    flow = getattr(self, "_current_flow", None)
                    self.emit("output", flow=flow, data=data)

        class Processor(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self.process)
                self.output_event = self.define_event("output", ["data"])

            def process(self, data=None, **kwargs):
                result = f"Final: {data}"
                self._stats["processed"] = True
                # Get flow from routine context
                flow = getattr(self, "_current_flow", None)
                self.emit("output", flow=flow, data=result)

        class OutputFormatter(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self.format)

            def format(self, data):
                formatted = f"[FORMATTED] {data}"
                results.append(formatted)
                self._stats["formatted"] = True

        # 创建 routines
        input_proc = InputProcessor()
        validator = Validator()
        processor = Processor()
        formatter = OutputFormatter()

        # 添加到 flow
        id1 = flow.add_routine(input_proc, "input")
        id2 = flow.add_routine(validator, "validator")
        id3 = flow.add_routine(processor, "processor")
        id4 = flow.add_routine(formatter, "formatter")

        # 连接
        flow.connect(id1, "output", id2, "input")
        flow.connect(id2, "output", id3, "input")
        flow.connect(id3, "output", id4, "input")

        # 执行
        job_state = flow.execute(id1, entry_params={"input_data": "test"})
        flow.wait_for_completion(timeout=2.0)

        # 验证
        assert job_state.status == "completed"
        assert len(results) > 0
        assert input_proc.stats().get("input_processed") is True

    def test_error_handling_flow(self):
        """测试用例 2: 错误处理流程"""
        flow = Flow()
        success_results = []
        error_results = []

        class Processor(Routine):
            def __init__(self):
                super().__init__()
                # Define trigger slot for entry routine
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])
                self.error_event = self.define_event("error", ["error"])

            def _handle_trigger(self, should_fail=False, **kwargs):
                should_fail = should_fail or kwargs.get("should_fail", False)
                # Get flow from routine context
                flow = getattr(self, "_current_flow", None)
                if should_fail:
                    self.emit("error", flow=flow, error="Test error")
                else:
                    self.emit("output", flow=flow, data="success")

        class SuccessHandler(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self.handle)

            def handle(self, data=None, **kwargs):
                success_results.append(data)

        class ErrorHandler(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self.handle)

            def handle(self, error=None, **kwargs):
                error_results.append(error)

        processor = Processor()
        success_handler = SuccessHandler()
        error_handler = ErrorHandler()

        id_proc = flow.add_routine(processor, "processor")
        id_success = flow.add_routine(success_handler, "success")
        id_error = flow.add_routine(error_handler, "error")

        flow.connect(id_proc, "output", id_success, "input")
        flow.connect(id_proc, "error", id_error, "input")

        # 测试成功路径
        job_state = flow.execute(id_proc, entry_params={"should_fail": False})
        flow.wait_for_completion(timeout=2.0)
        assert job_state.status == "completed"
        assert len(success_results) > 0

        # 测试错误路径 - 创建新的flow实例以避免状态冲突
        success_results.clear()
        error_results.clear()

        # Create new flow for error path test
        flow2 = Flow()
        processor2 = Processor()
        error_handler2 = ErrorHandler()
        id_proc2 = flow2.add_routine(processor2, "processor")
        id_error2 = flow2.add_routine(error_handler2, "error")
        flow2.connect(id_proc2, "error", id_error2, "input")

        job_state2 = flow2.execute(id_proc2, entry_params={"should_fail": True})
        flow2.wait_for_completion(timeout=2.0)
        assert len(error_results) > 0

    def test_parallel_processing_flow(self):
        """测试用例 3: 并行处理流程"""
        flow = Flow()
        aggregated_data = []

        class MultiSourceRoutine(Routine):
            """Source routine that emits multiple messages."""

            def __init__(self):
                super().__init__()
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                # Get flow from routine context
                flow = getattr(self, "_current_flow", None)
                # Emit multiple messages
                for data in ["A", "B", "C"]:
                    self.emit("output", flow=flow, data=data)

        class Aggregator(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot(
                    "input", handler=self.aggregate, merge_strategy="append"
                )

            def aggregate(self, data=None, **kwargs):
                if data is not None:
                    aggregated_data.append(data)

        multi_source = MultiSourceRoutine()
        agg = Aggregator()

        source_id = flow.add_routine(multi_source, "multi_source")
        id_agg = flow.add_routine(agg, "aggregator")

        flow.connect(source_id, "output", id_agg, "input")

        # 执行单个源，它会发出多个消息
        job_state = flow.execute(source_id)

        # 等待所有任务完成
        flow.wait_for_completion(timeout=2.0)

        # 验证聚合器收到了数据
        assert len(aggregated_data) >= 3


class TestComplexScenarios:
    """复杂场景测试"""

    def test_nested_flow(self):
        """测试嵌套流程"""
        flow = Flow()

        class RoutineA(Routine):
            def __init__(self):
                super().__init__()
                # Define trigger slot for entry routine
                self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
                self.output_event = self.define_event("output", ["data"])

            def _handle_trigger(self, **kwargs):
                # Get flow from routine context
                flow = getattr(self, "_current_flow", None)
                self.emit("output", flow=flow, data="A")

        class RoutineB(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self.process)
                self.output_event = self.define_event("output", ["data"])

            def process(self, data=None, **kwargs):
                # Get flow from routine context
                flow = getattr(self, "_current_flow", None)
                self.emit("output", flow=flow, data=f"B({data})")

        class RoutineC(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self.process)
                self.output_event = self.define_event("output", ["data"])

            def process(self, data=None, **kwargs):
                # Get flow from routine context
                flow = getattr(self, "_current_flow", None)
                self.emit("output", flow=flow, data=f"C({data})")

        class RoutineD(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=self.process)
                self.final_result = None

            def process(self, data):
                self.final_result = f"D({data})"

        a = RoutineA()
        b = RoutineB()
        c = RoutineC()
        d = RoutineD()

        id_a = flow.add_routine(a, "A")
        id_b = flow.add_routine(b, "B")
        id_c = flow.add_routine(c, "C")
        id_d = flow.add_routine(d, "D")

        flow.connect(id_a, "output", id_b, "input")
        flow.connect(id_b, "output", id_c, "input")
        flow.connect(id_c, "output", id_d, "input")

        # 执行
        job_state = flow.execute(id_a)
        flow.wait_for_completion(timeout=2.0)

        # 验证
        assert job_state.status == "completed"
        assert d.final_result is not None
