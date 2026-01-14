"""
WebSocket routes for real-time monitoring and debug events.
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from routilux.monitoring.registry import MonitoringRegistry
from routilux.monitoring.storage import flow_store, job_store
from routilux.monitoring.websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}/monitor")
async def job_monitor_websocket(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job monitoring."""
    # Verify job exists
    job_state = job_store.get(job_id)
    if not job_state:
        await websocket.close(code=1008, reason=f"Job '{job_id}' not found")
        return

    await websocket.accept()
    await ws_manager.connect(job_id, websocket)

    try:
        MonitoringRegistry.enable()
        registry = MonitoringRegistry.get_instance()
        collector = registry.monitor_collector

        # Send initial metrics
        if collector:
            metrics = collector.get_metrics(job_id)
            if metrics:
                await ws_manager.send_metrics(job_id, metrics)

        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(1)  # Update every second

            # Check if job still exists
            job_state = job_store.get(job_id)
            if not job_state:
                break

            # Send metrics update
            if collector:
                metrics = collector.get_metrics(job_id)
                if metrics:
                    await ws_manager.send_metrics(job_id, metrics)

            # Send ping to keep connection alive
            await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(job_id, websocket)


@router.websocket("/ws/jobs/{job_id}/debug")
async def job_debug_websocket(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time debug events."""
    # Verify job exists
    job_state = job_store.get(job_id)
    if not job_state:
        await websocket.close(code=1008, reason=f"Job '{job_id}' not found")
        return

    await websocket.accept()
    await ws_manager.connect(job_id, websocket)

    try:
        MonitoringRegistry.enable()
        registry = MonitoringRegistry.get_instance()
        debug_store = registry.debug_session_store

        # Send initial debug session state
        if debug_store:
            session = debug_store.get(job_id)
            if session:
                await websocket.send_json(
                    {
                        "type": "debug_session",
                        "job_id": job_id,
                        "status": session.status,
                    }
                )

        # Keep connection alive
        while True:
            await asyncio.sleep(1)

            # Check if job still exists
            job_state = job_store.get(job_id)
            if not job_state:
                break

            # Send ping to keep connection alive
            await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(job_id, websocket)


@router.websocket("/ws/flows/{flow_id}/monitor")
async def flow_monitor_websocket(websocket: WebSocket, flow_id: str):
    """WebSocket endpoint for real-time flow monitoring."""
    # Verify flow exists
    flow = flow_store.get(flow_id)
    if not flow:
        await websocket.close(code=1008, reason=f"Flow '{flow_id}' not found")
        return

    await websocket.accept()

    try:
        MonitoringRegistry.enable()
        MonitoringRegistry.get_instance()

        # Get all jobs for this flow
        jobs = job_store.get_by_flow(flow_id)

        # Send initial flow metrics
        await websocket.send_json(
            {
                "type": "flow_metrics",
                "flow_id": flow_id,
                "total_jobs": len(jobs),
            }
        )

        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(2)  # Update every 2 seconds

            # Check if flow still exists
            flow = flow_store.get(flow_id)
            if not flow:
                break

            # Get updated job list
            jobs = job_store.get_by_flow(flow_id)

            # Send update
            await websocket.send_json(
                {
                    "type": "flow_metrics",
                    "flow_id": flow_id,
                    "total_jobs": len(jobs),
                    "jobs": [
                        {
                            "job_id": job.job_id,
                            "status": str(job.status),
                        }
                        for job in jobs
                    ],
                }
            )

    except WebSocketDisconnect:
        pass
