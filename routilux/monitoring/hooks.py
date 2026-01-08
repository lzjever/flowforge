"""
Execution hooks for monitoring and debugging.

These hooks are called at key execution points and have zero overhead
when monitoring is disabled.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from routilux.flow.flow import Flow
    from routilux.job_state import JobState
    from routilux.routine import Routine, ExecutionContext
    from routilux.slot import Slot
    from routilux.event import Event


class ExecutionHooks:
    """Execution hooks for monitoring and debugging.
    
    All methods return immediately if monitoring is disabled, ensuring
    zero overhead for existing applications.
    """
    
    def on_flow_start(self, flow: "Flow", job_state: "JobState") -> None:
        """Hook called when flow execution starts.
        
        Args:
            flow: Flow being executed.
            job_state: Job state for this execution.
        """
        from routilux.monitoring.registry import MonitoringRegistry
        
        if not MonitoringRegistry.is_enabled():
            return
        
        registry = MonitoringRegistry.get_instance()
        collector = registry.monitor_collector
        
        if collector:
            collector.record_flow_start(flow.flow_id, job_state.job_id)
            
            # Broadcast via WebSocket (non-blocking)
            try:
                from routilux.monitoring.websocket_manager import ws_manager
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(ws_manager.broadcast(job_state.job_id, {
                        "type": "flow_start",
                        "job_id": job_state.job_id,
                        "flow_id": flow.flow_id,
                    }))
                else:
                    loop.run_until_complete(ws_manager.broadcast(job_state.job_id, {
                        "type": "flow_start",
                        "job_id": job_state.job_id,
                        "flow_id": flow.flow_id,
                    }))
            except (RuntimeError, AttributeError):
                # No event loop, skip WebSocket notification
                pass
    
    def on_flow_end(self, flow: "Flow", job_state: "JobState", status: str = "completed") -> None:
        """Hook called when flow execution ends.
        
        Args:
            flow: Flow that was executed.
            job_state: Job state for this execution.
            status: Final execution status.
        """
        from routilux.monitoring.registry import MonitoringRegistry
        
        if not MonitoringRegistry.is_enabled():
            return
        
        registry = MonitoringRegistry.get_instance()
        collector = registry.monitor_collector
        
        if collector:
            collector.record_flow_end(job_state.job_id, status)
            
            # Get final metrics and broadcast
            metrics = collector.get_metrics(job_state.job_id)
            if metrics:
                try:
                    from routilux.monitoring.websocket_manager import ws_manager
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(ws_manager.send_metrics(job_state.job_id, metrics))
                    else:
                        loop.run_until_complete(ws_manager.send_metrics(job_state.job_id, metrics))
                except (RuntimeError, AttributeError):
                    # No event loop, skip WebSocket notification
                    pass
    
    def on_routine_start(
        self,
        routine: "Routine",
        routine_id: str,
        job_state: Optional["JobState"] = None,
    ) -> None:
        """Hook called when routine execution starts.
        
        Args:
            routine: Routine being executed.
            routine_id: Routine identifier.
            job_state: Optional job state.
        """
        from routilux.monitoring.registry import MonitoringRegistry
        
        if not MonitoringRegistry.is_enabled() or not job_state:
            return
        
        registry = MonitoringRegistry.get_instance()
        collector = registry.monitor_collector
        
        if collector:
            collector.record_routine_start(routine_id, job_state.job_id)
            
            # Broadcast execution event via WebSocket (non-blocking)
            try:
                from routilux.monitoring.websocket_manager import ws_manager
                from routilux.monitoring.monitor_collector import ExecutionEvent
                from datetime import datetime
                import asyncio
                
                event = ExecutionEvent(
                    event_id=f"event_{id(self)}",
                    job_id=job_state.job_id,
                    routine_id=routine_id,
                    event_type="routine_start",
                    timestamp=datetime.now(),
                )
                
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(ws_manager.send_execution_event(job_state.job_id, event))
                else:
                    loop.run_until_complete(ws_manager.send_execution_event(job_state.job_id, event))
            except (RuntimeError, AttributeError):
                # No event loop, skip WebSocket notification
                pass
    
    def on_routine_end(
        self,
        routine: "Routine",
        routine_id: str,
        job_state: Optional["JobState"] = None,
        status: str = "completed",
        error: Optional[Exception] = None,
    ) -> None:
        """Hook called when routine execution ends.
        
        Args:
            routine: Routine that was executed.
            routine_id: Routine identifier.
            job_state: Optional job state.
            status: Execution status.
            error: Optional error that occurred.
        """
        from routilux.monitoring.registry import MonitoringRegistry
        
        if not MonitoringRegistry.is_enabled() or not job_state:
            return
        
        registry = MonitoringRegistry.get_instance()
        collector = registry.monitor_collector
        
        if collector:
            collector.record_routine_end(routine_id, job_state.job_id, status, error)
    
    def on_slot_call(
        self,
        slot: "Slot",
        routine_id: str,
        job_state: Optional["JobState"] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Hook called when slot handler is called.
        
        Args:
            slot: Slot being called.
            routine_id: Routine identifier.
            job_state: Optional job state.
            data: Data being passed to slot.
            
        Returns:
            True if execution should continue, False if should pause.
        """
        from routilux.monitoring.registry import MonitoringRegistry
        
        if not MonitoringRegistry.is_enabled() or not job_state:
            return True
        
        registry = MonitoringRegistry.get_instance()
        
        # Record slot call
        collector = registry.monitor_collector
        if collector:
            collector.record_slot_call(slot.name, routine_id, job_state.job_id, data)
        
        # Check breakpoint
        breakpoint_mgr = registry.breakpoint_manager
        if breakpoint_mgr:
            context = slot.routine.get_execution_context() if hasattr(slot, 'routine') and slot.routine else None
            breakpoint = breakpoint_mgr.check_breakpoint(
                job_state.job_id, routine_id, "slot",
                slot_name=slot.name, context=context, variables=data
            )
            if breakpoint:
                debug_store = registry.debug_session_store
                if debug_store:
                    session = debug_store.get_or_create(job_state.job_id)
                    session.pause(context, reason=f"Breakpoint at {routine_id}.{slot.name}")
                    # Notify via WebSocket
                    from routilux.monitoring.websocket_manager import ws_manager
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(ws_manager.send_breakpoint_hit(job_state.job_id, breakpoint, context))
                        else:
                            loop.run_until_complete(ws_manager.send_breakpoint_hit(job_state.job_id, breakpoint, context))
                    except RuntimeError:
                        # No event loop, skip WebSocket notification
                        pass
                    return False
        
        return True
    
    def on_event_emit(
        self,
        event: "Event",
        routine_id: str,
        job_state: Optional["JobState"] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Hook called when event is emitted.
        
        Args:
            event: Event being emitted.
            routine_id: Routine identifier.
            job_state: Optional job state.
            data: Data being emitted with event.
            
        Returns:
            True if execution should continue, False if should pause.
        """
        from routilux.monitoring.registry import MonitoringRegistry
        
        if not MonitoringRegistry.is_enabled() or not job_state:
            return True
        
        registry = MonitoringRegistry.get_instance()
        
        # Record event emission
        collector = registry.monitor_collector
        if collector:
            collector.record_event_emit(event.name, routine_id, job_state.job_id, data)
        
        # Check breakpoint
        breakpoint_mgr = registry.breakpoint_manager
        if breakpoint_mgr:
            context = event.routine.get_execution_context() if hasattr(event, 'routine') and event.routine else None
            breakpoint = breakpoint_mgr.check_breakpoint(
                job_state.job_id, routine_id, "event",
                event_name=event.name, context=context, variables=data
            )
            if breakpoint:
                debug_store = registry.debug_session_store
                if debug_store:
                    session = debug_store.get_or_create(job_state.job_id)
                    session.pause(context, reason=f"Breakpoint at {routine_id}.{event.name}")
                    # Notify via WebSocket
                    from routilux.monitoring.websocket_manager import ws_manager
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(ws_manager.send_breakpoint_hit(job_state.job_id, breakpoint, context))
                        else:
                            loop.run_until_complete(ws_manager.send_breakpoint_hit(job_state.job_id, breakpoint, context))
                    except RuntimeError:
                        # No event loop, skip WebSocket notification
                        pass
                    return False
        
        return True
    
    def should_pause_routine(
        self,
        routine_id: str,
        job_state: Optional["JobState"] = None,
        context: Optional["ExecutionContext"] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if execution should pause at routine start.
        
        Args:
            routine_id: Routine identifier.
            job_state: Optional job state.
            context: Optional execution context.
            variables: Optional local variables.
            
        Returns:
            True if execution should pause.
        """
        from routilux.monitoring.registry import MonitoringRegistry
        
        if not MonitoringRegistry.is_enabled() or not job_state:
            return False
        
        registry = MonitoringRegistry.get_instance()
        breakpoint_mgr = registry.breakpoint_manager
        
        if breakpoint_mgr:
            return breakpoint_mgr.should_pause_routine(job_state.job_id, routine_id, context, variables)
        
        return False
    
    def pause_execution(self, job_id: str, context: Optional["ExecutionContext"] = None, reason: str = "") -> None:
        """Pause execution at current point.
        
        Args:
            job_id: Job identifier.
            context: Execution context.
            reason: Reason for pause.
        """
        from routilux.monitoring.registry import MonitoringRegistry
        
        if not MonitoringRegistry.is_enabled():
            return
        
        registry = MonitoringRegistry.get_instance()
        debug_store = registry.debug_session_store
        
        if debug_store:
            session = debug_store.get_or_create(job_id)
            session.pause(context, reason)


# Global instance
execution_hooks = ExecutionHooks()

