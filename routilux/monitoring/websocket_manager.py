"""
WebSocket manager for real-time monitoring and debug events.

Manages WebSocket connections and broadcasts messages to connected clients.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

if TYPE_CHECKING:
    from fastapi import WebSocket

    from routilux.monitoring.breakpoint_manager import Breakpoint
    from routilux.monitoring.monitor_collector import ExecutionEvent, ExecutionMetrics
    from routilux.routine import ExecutionContext

# Optional FastAPI import for WebSocket type
try:
    from fastapi import WebSocket
except ImportError:
    # WebSocket is only used for type hints, use Any as fallback
    WebSocket = Any


class WebSocketManager:
    """Manages WebSocket connections for real-time updates.

    Thread-safe manager that maintains connections per job_id and broadcasts
    messages to all connected clients.
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        self._connections: Dict[str, Set[WebSocket]] = {}  # job_id -> Set[WebSocket]
        self._lock = asyncio.Lock()

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        """Connect a WebSocket for a job.

        Args:
            job_id: Job identifier.
            websocket: WebSocket connection.
        """
        async with self._lock:
            if job_id not in self._connections:
                self._connections[job_id] = set()
            self._connections[job_id].add(websocket)

    async def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        """Disconnect a WebSocket for a job.

        Args:
            job_id: Job identifier.
            websocket: WebSocket connection.
        """
        async with self._lock:
            if job_id in self._connections:
                self._connections[job_id].discard(websocket)
                if not self._connections[job_id]:
                    del self._connections[job_id]

    async def broadcast(self, job_id: str, message: Dict) -> None:
        """Broadcast message to all connections for a job.

        Args:
            job_id: Job identifier.
            message: Message dictionary to send.
        """
        async with self._lock:
            connections = self._connections.get(job_id, set()).copy()

        # Send to all connections (outside lock to avoid blocking)
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                # Connection closed, mark for removal
                disconnected.append(websocket)

        # Remove disconnected connections
        if disconnected:
            async with self._lock:
                if job_id in self._connections:
                    for ws in disconnected:
                        self._connections[job_id].discard(ws)

    async def send_metrics(self, job_id: str, metrics: "ExecutionMetrics") -> None:
        """Send metrics update.

        Args:
            job_id: Job identifier.
            metrics: Execution metrics.
        """
        message = {
            "type": "metrics",
            "job_id": job_id,
            "metrics": {
                "start_time": metrics.start_time.isoformat() if metrics.start_time else None,
                "end_time": metrics.end_time.isoformat() if metrics.end_time else None,
                "duration": metrics.duration,
                "total_events": metrics.total_events,
                "total_slot_calls": metrics.total_slot_calls,
                "total_event_emits": metrics.total_event_emits,
            },
        }
        await self.broadcast(job_id, message)

    async def send_breakpoint_hit(
        self,
        job_id: str,
        breakpoint: "Breakpoint",
        context: Optional["ExecutionContext"] = None,
    ) -> None:
        """Send breakpoint hit notification.

        Args:
            job_id: Job identifier.
            breakpoint: Breakpoint that was hit.
            context: Execution context where breakpoint was hit.
        """
        message = {
            "type": "breakpoint_hit",
            "job_id": job_id,
            "breakpoint": {
                "breakpoint_id": breakpoint.breakpoint_id,
                "type": breakpoint.type,
                "routine_id": breakpoint.routine_id,
                "slot_name": breakpoint.slot_name,
                "event_name": breakpoint.event_name,
            },
            "context": {
                "routine_id": context.routine_id if context else None,
            }
            if context
            else None,
        }
        await self.broadcast(job_id, message)

    async def send_execution_event(self, job_id: str, event: "ExecutionEvent") -> None:
        """Send execution event notification.

        Args:
            job_id: Job identifier.
            event: Execution event.
        """
        message = {
            "type": "execution_event",
            "job_id": job_id,
            "event": {
                "event_id": event.event_id,
                "routine_id": event.routine_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data,
            },
        }
        await self.broadcast(job_id, message)


# Global instance
ws_manager = WebSocketManager()
