# Routilux API Redesign Documentation

## Executive Summary

This document provides a complete redesign of the Routilux HTTP API based on REST best practices and the actual capabilities of the core implementation. The redesign eliminates the debug and monitor categories, redistributes endpoints to resource-oriented categories, and ensures each component provides comprehensive self-information queries.

**Key Principles**:
- Resource-oriented design (nouns, not verbs)
- Hierarchical organization (related resources nested)
- Self-contained components (each resource provides its own information)
- No backward compatibility (clean break for better design)

---

## Table of Contents

1. [API Design Principles](#api-design-principles)
2. [Resource Categories](#resource-categories)
3. [Complete API Reference](#complete-api-reference)
4. [Additional Improvements](#additional-improvements)
5. [Implementation Guide](#implementation-guide)

---

## API Design Principles

### 1. Resource-Oriented Design

**Principle**: Resources are nouns, actions are HTTP methods.

✅ **Good**:
- `GET /api/jobs/{job_id}/metrics` - Get metrics for a job
- `POST /api/jobs` - Create a new job
- `PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id}` - Update breakpoint

❌ **Bad** (removed):
- `GET /api/monitor/jobs/{job_id}/metrics` - Action-oriented category
- `GET /api/debug/{job_id}/session` - Action-oriented category

### 2. Hierarchical Organization

**Principle**: Related resources are nested under their parent.

```
/api/jobs/{job_id}/metrics          ✅ Job metrics belong to job
/api/jobs/{job_id}/routines/{routine_id}/queue-status  ✅ Routine queue belongs to job+routine
/api/flows/{flow_id}/routines/{routine_id}/info  ✅ Routine info belongs to flow+routine
/api/workers/{worker_id}/breakpoints/{breakpoint_id}  ✅ Breakpoint belongs to worker
```

### 3. Self-Contained Components

**Principle**: Each resource category provides all information about itself.

- **Jobs**: All job-related information (status, metrics, trace, logs, data, routines)
- **Workers**: All worker-related information (status, statistics, breakpoints, history)
- **Flows**: All flow-related information (structure, routines, connections, metrics)
- **Routines**: Routine information nested under flows (info, queue status)

### 4. HTTP Method Semantics

- `GET`: Retrieve resource information (idempotent, safe)
- `POST`: Create new resource or trigger action
- `PUT`: Update entire resource or specific attribute
- `PATCH`: Partial update (if needed)
- `DELETE`: Remove resource

---

## Resource Categories

### 1. Jobs (`/api/jobs`)

**Purpose**: Manage and monitor individual job executions.

**Core Data** (from `JobContext`):
- `job_id`, `worker_id`, `flow_id`
- `status` (pending, running, completed, failed)
- `created_at`, `completed_at`
- `metadata`, `data`, `trace_log`
- `error`

**Endpoints**:
- CRUD operations
- Status and lifecycle management
- Execution information (metrics, trace, logs)
- Routine-level information within job context

### 2. Workers (`/api/workers`)

**Purpose**: Manage long-running worker instances.

**Core Data** (from `WorkerState`):
- `worker_id`, `flow_id`, `status`
- `routine_states`, `execution_history`
- `jobs_processed`, `jobs_failed`
- `created_at`, `started_at`, `completed_at`
- `error`, `error_traceback`
- `pause_points`, `deferred_events`, `pending_tasks`

**Endpoints**:
- CRUD operations
- Lifecycle control (pause, resume, stop)
- Statistics and history
- Breakpoint management (enable/disable)

### 3. Flows (`/api/flows`)

**Purpose**: Manage workflow definitions and structure.

**Core Data** (from `Flow`):
- `flow_id`
- `routines` (dict of Routine objects)
- `connections` (list of Connection objects)
- `error_handler`
- `execution_timeout`

**Endpoints**:
- CRUD operations
- Routine and connection management
- Flow-level metrics
- Routine information (nested under flows)

### 4. Breakpoints (`/api/jobs/{job_id}/breakpoints`)

**Purpose**: Manage breakpoints for debugging (creation, listing, deletion).

**Note**: Breakpoint enable/disable moved to workers category.

**Core Data** (from `Breakpoint`):
- `breakpoint_id`, `job_id`
- `type` (routine, slot, event, connection)
- `routine_id`, `slot_name`, `event_name`
- `condition`, `enabled`, `hit_count`

**Endpoints**:
- Create breakpoint
- List breakpoints
- Delete breakpoint
- (Enable/disable moved to workers)

---

## Complete API Reference

### Jobs API

#### List Jobs
```http
GET /api/jobs
Query Parameters:
  - worker_id (optional): Filter by worker
  - flow_id (optional): Filter by flow
  - status (optional): Filter by status (pending, running, completed, failed)
  - limit (default: 100, max: 1000): Maximum results
  - offset (default: 0): Pagination offset

Response: 200 OK
{
  "jobs": [
    {
      "job_id": "job-123",
      "worker_id": "worker-456",
      "flow_id": "data_processing_flow",
      "status": "running",
      "created_at": "2025-01-15T10:00:00Z",
      "completed_at": null,
      "metadata": {"user_id": "user-789"},
      "error": null
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

#### Get Job
```http
GET /api/jobs/{job_id}

Response: 200 OK
{
  "job_id": "job-123",
  "worker_id": "worker-456",
  "flow_id": "data_processing_flow",
  "status": "running",
  "created_at": "2025-01-15T10:00:00Z",
  "completed_at": null,
  "metadata": {"user_id": "user-789"},
  "data": {"processed": true, "count": 42},
  "error": null
}
```

#### Submit Job
```http
POST /api/jobs
Content-Type: application/json

{
  "flow_id": "data_processing_flow",
  "routine_id": "data_source",
  "slot_name": "input",
  "data": {"value": 42},
  "worker_id": "worker-456",  // optional
  "job_id": "job-123",  // optional (auto-generated)
  "metadata": {"user_id": "user-789"}  // optional
}

Response: 201 Created
{
  "job_id": "job-123",
  "worker_id": "worker-456",
  "flow_id": "data_processing_flow",
  "status": "running",
  "created_at": "2025-01-15T10:00:00Z",
  "completed_at": null,
  "metadata": {"user_id": "user-789"},
  "error": null
}
```

#### Get Job Status
```http
GET /api/jobs/{job_id}/status

Response: 200 OK
{
  "job_id": "job-123",
  "status": "running",
  "worker_id": "worker-456",
  "flow_id": "data_processing_flow"
}
```

#### Get Job Metrics
```http
GET /api/jobs/{job_id}/metrics

Response: 200 OK
{
  "job_id": "job-123",
  "flow_id": "data_processing_flow",
  "start_time": "2025-01-15T10:00:00Z",
  "end_time": "2025-01-15T10:05:30Z",
  "duration": 330.5,
  "routine_metrics": {
    "data_source": {
      "routine_id": "data_source",
      "execution_count": 100,
      "total_duration": 50.2,
      "avg_duration": 0.502,
      "min_duration": 0.1,
      "max_duration": 2.5,
      "error_count": 0,
      "last_execution": "2025-01-15T10:05:25Z"
    }
  },
  "total_events": 195,
  "total_slot_calls": 195,
  "total_event_emits": 195,
  "errors": [
    {
      "error_id": "err-001",
      "job_id": "job-123",
      "routine_id": "processor",
      "timestamp": "2025-01-15T10:03:15Z",
      "error_type": "ValueError",
      "error_message": "Invalid data format",
      "traceback": "Traceback..."
    }
  ]
}
```

#### Get Job Trace
```http
GET /api/jobs/{job_id}/trace
Query Parameters:
  - limit (optional, 1-10000): Maximum events to return

Response: 200 OK
{
  "events": [
    {
      "event_id": "evt-001",
      "job_id": "job-123",
      "routine_id": "data_source",
      "event_type": "routine_start",
      "timestamp": "2025-01-15T10:00:00.100Z",
      "data": {"input": {"data": "item_1"}},
      "duration": null,
      "status": null
    }
  ],
  "total": 195
}
```

#### Get Job Logs
```http
GET /api/jobs/{job_id}/logs

Response: 200 OK
{
  "job_id": "job-123",
  "logs": [
    {
      "timestamp": "2025-01-15T10:00:00Z",
      "routine_id": "data_source",
      "action": "slot_activated",
      "details": {"slot": "trigger", "data": {"value": 42}}
    }
  ],
  "total": 10
}
```

#### Get Job Data
```http
GET /api/jobs/{job_id}/data

Response: 200 OK
{
  "job_id": "job-123",
  "data": {
    "processed": true,
    "count": 42,
    "result": "success"
  }
}
```

#### Get Job Output
```http
GET /api/jobs/{job_id}/output
Query Parameters:
  - incremental (default: false): Return only new output since last call

Response: 200 OK
{
  "job_id": "job-123",
  "output": "Processing started...\nProcessing complete.\n",
  "is_complete": false,
  "truncated": false
}
```

#### Get Job Monitoring Data
```http
GET /api/jobs/{job_id}/monitoring

Response: 200 OK
{
  "job_id": "job-123",
  "flow_id": "data_processing_flow",
  "job_status": "running",
  "routines": {
    "data_source": {
      "routine_id": "data_source",
      "execution_status": {
        "routine_id": "data_source",
        "is_active": true,
        "status": "running",
        "last_execution_time": "2025-01-15T10:05:25Z",
        "execution_count": 100,
        "error_count": 0,
        "active_thread_count": 2
      },
      "queue_status": [
        {
          "slot_name": "trigger",
          "routine_id": "data_source",
          "unconsumed_count": 0,
          "usage_percentage": 0.0,
          "pressure_level": "low",
          "is_full": false,
          "is_near_full": false
        }
      ],
      "info": {
        "routine_id": "data_source",
        "routine_type": "DataSource",
        "activation_policy": {
          "type": "immediate",
          "config": {},
          "description": "Activate immediately when any slot receives data"
        },
        "config": {"name": "DataSource"},
        "slots": ["trigger"],
        "events": ["output"]
      }
    }
  },
  "updated_at": "2025-01-15T10:05:30Z"
}
```

#### Get Job Routine Status
```http
GET /api/jobs/{job_id}/routines/status

Response: 200 OK
{
  "data_source": {
    "routine_id": "data_source",
    "is_active": true,
    "status": "running",
    "last_execution_time": "2025-01-15T10:05:25Z",
    "execution_count": 100,
    "error_count": 0,
    "active_thread_count": 2
  }
}
```

#### Get Job Routine Queue Status
```http
GET /api/jobs/{job_id}/routines/{routine_id}/queue-status

Response: 200 OK
[
  {
    "slot_name": "input",
    "routine_id": "data_processor",
    "unconsumed_count": 5,
    "total_count": 100,
    "max_length": 1000,
    "watermark_threshold": 800,
    "usage_percentage": 0.1,
    "pressure_level": "low",
    "is_full": false,
    "is_near_full": false
  }
]
```

#### Get All Job Queue Statuses
```http
GET /api/jobs/{job_id}/queues/status

Response: 200 OK
{
  "data_processor": [
    {
      "slot_name": "input",
      "routine_id": "data_processor",
      "unconsumed_count": 5,
      "usage_percentage": 0.1,
      "pressure_level": "low",
      "is_full": false,
      "is_near_full": false
    }
  ]
}
```

#### Complete Job
```http
POST /api/jobs/{job_id}/complete

Response: 200 OK
{
  "job_id": "job-123",
  "status": "completed",
  "completed_at": "2025-01-15T10:05:30Z"
}
```

#### Fail Job
```http
POST /api/jobs/{job_id}/fail
Content-Type: application/json

{
  "error": "Processing failed: Invalid input"
}

Response: 200 OK
{
  "job_id": "job-123",
  "status": "failed",
  "error": "Processing failed: Invalid input",
  "completed_at": "2025-01-15T10:05:30Z"
}
```

#### Wait for Job
```http
POST /api/jobs/{job_id}/wait
Query Parameters:
  - timeout (default: 60.0, max: 3600.0): Timeout in seconds

Response: 200 OK
{
  "status": "completed",
  "job_id": "job-123",
  "final_status": "completed",
  "waited_seconds": 45.2
}
```

---

### Workers API

#### List Workers
```http
GET /api/workers
Query Parameters:
  - flow_id (optional): Filter by flow
  - status (optional): Filter by status
  - limit (default: 100, max: 1000): Maximum results
  - offset (default: 0): Pagination offset

Response: 200 OK
{
  "workers": [
    {
      "worker_id": "worker-456",
      "flow_id": "data_processing_flow",
      "status": "running",
      "created_at": "2025-01-15T09:00:00Z",
      "started_at": "2025-01-15T09:00:05Z",
      "jobs_processed": 150,
      "jobs_failed": 2
    }
  ],
  "total": 10,
  "limit": 100,
  "offset": 0
}
```

#### Get Worker
```http
GET /api/workers/{worker_id}

Response: 200 OK
{
  "worker_id": "worker-456",
  "flow_id": "data_processing_flow",
  "status": "running",
  "created_at": "2025-01-15T09:00:00Z",
  "started_at": "2025-01-15T09:00:05Z",
  "completed_at": null,
  "jobs_processed": 150,
  "jobs_failed": 2,
  "error": null,
  "error_traceback": null
}
```

#### Create Worker
```http
POST /api/workers
Content-Type: application/json

{
  "flow_id": "data_processing_flow"
}

Response: 201 Created
{
  "worker_id": "worker-456",
  "flow_id": "data_processing_flow",
  "status": "running",
  "created_at": "2025-01-15T09:00:00Z",
  "started_at": "2025-01-15T09:00:05Z",
  "jobs_processed": 0,
  "jobs_failed": 0
}
```

#### Stop Worker
```http
DELETE /api/workers/{worker_id}

Response: 204 No Content
```

#### Pause Worker
```http
POST /api/workers/{worker_id}/pause

Response: 200 OK
{
  "worker_id": "worker-456",
  "status": "paused",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

#### Resume Worker
```http
POST /api/workers/{worker_id}/resume

Response: 200 OK
{
  "worker_id": "worker-456",
  "status": "running",
  "updated_at": "2025-01-15T10:00:05Z"
}
```

#### Get Worker Statistics
```http
GET /api/workers/{worker_id}/statistics

Response: 200 OK
{
  "worker_id": "worker-456",
  "flow_id": "data_processing_flow",
  "jobs_processed": 150,
  "jobs_failed": 2,
  "success_rate": 0.9867,
  "average_job_duration": 45.2,
  "total_execution_time": 6780.0,
  "routine_statistics": {
    "data_source": {
      "execution_count": 1500,
      "total_duration": 750.0,
      "avg_duration": 0.5,
      "error_count": 0
    }
  }
}
```

#### Get Worker Execution History
```http
GET /api/workers/{worker_id}/history
Query Parameters:
  - routine_id (optional): Filter by routine
  - limit (default: 100, max: 1000): Maximum records
  - offset (default: 0): Pagination offset

Response: 200 OK
{
  "worker_id": "worker-456",
  "history": [
    {
      "routine_id": "data_source",
      "event_name": "output",
      "data": {"result": "success"},
      "timestamp": "2025-01-15T10:05:25Z"
    }
  ],
  "total": 1500,
  "limit": 100,
  "offset": 0
}
```

#### Get Worker Routine States
```http
GET /api/workers/{worker_id}/routines/states

Response: 200 OK
{
  "data_source": {
    "status": "running",
    "execution_count": 1500,
    "last_execution": "2025-01-15T10:05:25Z"
  },
  "processor": {
    "status": "idle",
    "execution_count": 1450,
    "last_execution": "2025-01-15T10:05:20Z"
  }
}
```

#### List Worker Jobs
```http
GET /api/workers/{worker_id}/jobs
Query Parameters:
  - status (optional): Filter by job status
  - limit (default: 100, max: 1000): Maximum results
  - offset (default: 0): Pagination offset

Response: 200 OK
{
  "jobs": [
    {
      "job_id": "job-123",
      "worker_id": "worker-456",
      "flow_id": "data_processing_flow",
      "status": "running",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

#### Enable Breakpoint
```http
PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id}
Content-Type: application/json

{
  "enabled": true
}

Response: 200 OK
{
  "breakpoint_id": "bp-789",
  "enabled": true,
  "updated_at": "2025-01-15T10:00:00Z"
}
```

#### Disable Breakpoint
```http
PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id}
Content-Type: application/json

{
  "enabled": false
}

Response: 200 OK
{
  "breakpoint_id": "bp-789",
  "enabled": false,
  "updated_at": "2025-01-15T10:00:05Z"
}
```

---

### Flows API

#### List Flows
```http
GET /api/flows

Response: 200 OK
{
  "flows": [
    {
      "flow_id": "data_processing_flow",
      "routines": {
        "data_source": {
          "routine_id": "data_source",
          "class_name": "DataSource",
          "slots": ["trigger"],
          "events": ["output"],
          "config": {"name": "Source"}
        }
      },
      "connections": [
        {
          "connection_id": "conn_0",
          "source_routine": "data_source",
          "source_event": "output",
          "target_routine": "processor",
          "target_slot": "input"
        }
      ]
    }
  ],
  "total": 10
}
```

#### Get Flow
```http
GET /api/flows/{flow_id}

Response: 200 OK
{
  "flow_id": "data_processing_flow",
  "routines": {
    "data_source": {
      "routine_id": "data_source",
      "class_name": "DataSource",
      "slots": ["trigger"],
      "events": ["output"],
      "config": {"name": "Source"}
    }
  },
  "connections": [
    {
      "connection_id": "conn_0",
      "source_routine": "data_source",
      "source_event": "output",
      "target_routine": "processor",
      "target_slot": "input"
    }
  ],
  "execution_timeout": 300.0,
  "error_handler": null
}
```

#### Create Flow
```http
POST /api/flows
Content-Type: application/json

{
  "flow_id": "my_new_flow",
  "dsl": "flow_id: my_new_flow\nroutines:\n  source:\n    class: data_source\n    config:\n      name: Source"
}

// OR

{
  "flow_id": "my_new_flow",
  "dsl_dict": {
    "flow_id": "my_new_flow",
    "routines": {
      "source": {
        "class": "data_source",
        "config": {"name": "Source"}
      }
    },
    "connections": []
  }
}

// OR (empty flow)

{
  "flow_id": "my_new_flow"
}

Response: 201 Created
{
  "flow_id": "my_new_flow",
  "routines": {},
  "connections": []
}
```

#### Delete Flow
```http
DELETE /api/flows/{flow_id}

Response: 204 No Content
```

#### Get Flow Metrics
```http
GET /api/flows/{flow_id}/metrics

Response: 200 OK
{
  "flow_id": "data_processing_flow",
  "total_jobs": 150,
  "completed_jobs": 145,
  "failed_jobs": 5,
  "success_rate": 0.9667,
  "average_duration": 45.2,
  "job_metrics": [
    {
      "job_id": "job-123",
      "duration": 42.5,
      "status": "completed"
    }
  ]
}
```

#### Get Flow Routines
```http
GET /api/flows/{flow_id}/routines

Response: 200 OK
{
  "data_source": {
    "routine_id": "data_source",
    "class_name": "DataSource",
    "slots": ["trigger"],
    "events": ["output"],
    "config": {"name": "Source"}
  },
  "processor": {
    "routine_id": "processor",
    "class_name": "DataTransformer",
    "slots": ["input"],
    "events": ["output"],
    "config": {"name": "Processor"}
  }
}
```

#### Get Flow Routine Info
```http
GET /api/flows/{flow_id}/routines/{routine_id}/info

Response: 200 OK
{
  "routine_id": "data_source",
  "routine_type": "DataSource",
  "activation_policy": {
    "type": "immediate",
    "config": {},
    "description": "Activate immediately when any slot receives data"
  },
  "config": {"name": "DataSource"},
  "slots": ["trigger"],
  "events": ["output"]
}
```

#### Get Flow Connections
```http
GET /api/flows/{flow_id}/connections

Response: 200 OK
[
  {
    "connection_id": "conn_0",
    "source_routine": "data_source",
    "source_event": "output",
    "target_routine": "processor",
    "target_slot": "input"
  }
]
```

#### Add Routine to Flow
```http
POST /api/flows/{flow_id}/routines
Content-Type: application/json

{
  "routine_id": "data_processor",
  "object_name": "data_transformer",
  "config": {
    "name": "MyProcessor",
    "transformation": "uppercase"
  }
}

Response: 200 OK
{
  "routine_id": "data_processor",
  "status": "added"
}
```

#### Remove Routine from Flow
```http
DELETE /api/flows/{flow_id}/routines/{routine_id}

Response: 204 No Content
```

#### Add Connection to Flow
```http
POST /api/flows/{flow_id}/connections
Content-Type: application/json

{
  "source_routine": "data_source",
  "source_event": "output",
  "target_routine": "data_processor",
  "target_slot": "input"
}

Response: 200 OK
{
  "status": "connected"
}
```

#### Remove Connection from Flow
```http
DELETE /api/flows/{flow_id}/connections/{connection_index}

Response: 204 No Content
```

#### Validate Flow
```http
POST /api/flows/{flow_id}/validate

Response: 200 OK
{
  "valid": true,
  "issues": [],
  "errors": [],
  "warnings": []
}
```

#### Export Flow DSL
```http
GET /api/flows/{flow_id}/dsl
Query Parameters:
  - format (default: yaml): Export format (yaml or json)

Response: 200 OK
{
  "format": "yaml",
  "dsl": "flow_id: data_processing_flow\nroutines:\n  source:\n    class: data_source\n    config:\n      name: Source"
}
```

---

### Breakpoints API

#### Create Breakpoint
```http
POST /api/jobs/{job_id}/breakpoints
Content-Type: application/json

{
  "type": "routine",
  "routine_id": "data_processor",
  "condition": "data.get('value') > 100",
  "enabled": true
}

Response: 201 Created
{
  "breakpoint_id": "bp-789",
  "job_id": "job-123",
  "type": "routine",
  "routine_id": "data_processor",
  "condition": "data.get('value') > 100",
  "enabled": true,
  "hit_count": 0
}
```

#### List Breakpoints
```http
GET /api/jobs/{job_id}/breakpoints

Response: 200 OK
{
  "breakpoints": [
    {
      "breakpoint_id": "bp-789",
      "job_id": "job-123",
      "type": "routine",
      "routine_id": "data_processor",
      "condition": "data.get('value') > 100",
      "enabled": true,
      "hit_count": 5
    }
  ],
  "total": 1
}
```

#### Delete Breakpoint
```http
DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id}

Response: 204 No Content
```

---

## Additional Improvements

### 1. Consistent Response Format

All list endpoints return:
```json
{
  "items": [...],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

All single resource endpoints return the resource object directly.

### 2. Error Response Format

All errors follow consistent format:
```json
{
  "error": {
    "code": "JOB_NOT_FOUND",
    "message": "Job 'job-123' not found",
    "details": {}
  }
}
```

### 3. Pagination

All list endpoints support:
- `limit`: Maximum items per page (1-1000)
- `offset`: Number of items to skip
- Response includes `total` for client-side pagination

### 4. Filtering

List endpoints support filtering via query parameters:
- Jobs: `worker_id`, `flow_id`, `status`
- Workers: `flow_id`, `status`
- Consistent parameter naming

### 5. Resource Links (HATEOAS)

Consider adding resource links for discoverability:
```json
{
  "job_id": "job-123",
  "worker_id": "worker-456",
  "_links": {
    "self": "/api/jobs/job-123",
    "worker": "/api/workers/worker-456",
    "flow": "/api/flows/data_processing_flow",
    "metrics": "/api/jobs/job-123/metrics",
    "trace": "/api/jobs/job-123/trace"
  }
}
```

### 6. Field Selection

Add support for field selection to reduce payload size:
```http
GET /api/jobs/{job_id}?fields=job_id,status,created_at
```

### 7. Bulk Operations

Consider adding bulk operations for efficiency:
```http
POST /api/jobs/bulk
Content-Type: application/json

{
  "jobs": [
    {"flow_id": "flow-1", "routine_id": "source", "slot_name": "input", "data": {}},
    {"flow_id": "flow-1", "routine_id": "source", "slot_name": "input", "data": {}}
  ]
}
```

### 8. WebSocket Endpoints

Keep WebSocket endpoints for real-time monitoring:
- `WS /api/ws/jobs/{job_id}/monitor` - Real-time job monitoring
- `WS /api/ws/workers/{worker_id}/monitor` - Real-time worker monitoring
- `WS /api/ws/flows/{flow_id}/monitor` - Real-time flow monitoring

### 9. Health Check

Add comprehensive health check:
```http
GET /api/health

Response: 200 OK
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "runtime": "healthy",
    "monitoring": "healthy",
    "storage": "healthy"
  },
  "uptime": 3600.5
}
```

### 10. API Versioning

Use URL versioning for future changes:
- Current: `/api/jobs/{job_id}`
- Future: `/api/v2/jobs/{job_id}`

---

## Implementation Guide

### Phase 1: Route File Reorganization

**New Structure**:
```
routilux/server/routes/
  ├── jobs.py          (all job-related endpoints)
  ├── workers.py       (all worker-related endpoints)
  ├── flows.py         (all flow-related endpoints)
  └── breakpoints.py   (breakpoint CRUD only)
```

**Removed Files**:
- `debug.py` (all endpoints removed)
- `monitor.py` (endpoints moved to jobs/flows)

### Phase 2: Endpoint Migration

**Jobs Route** (`jobs.py`):
- Existing: CRUD, status, output, trace, wait
- **Added from monitor**: metrics, logs, data, monitoring, routines/status, routines/{routine_id}/queue-status, queues/status

**Workers Route** (`workers.py`):
- Existing: CRUD, pause, resume, jobs
- **Added**: statistics, history, routines/states
- **Added from breakpoints**: breakpoints/{breakpoint_id} (PUT for enable/disable)

**Flows Route** (`flows.py`):
- Existing: CRUD, routines, connections, validate, dsl
- **Added from monitor**: metrics, routines/{routine_id}/info

**Breakpoints Route** (`breakpoints.py`):
- Existing: create, list, delete
- **Removed**: update (enable/disable moved to workers)

### Phase 3: Model Updates

Update response models to match new structure:
- `JobResponse`: Add all job-related fields
- `WorkerResponse`: Add statistics, history fields
- `FlowResponse`: Add metrics fields
- Remove `DebugResponse` models
- Update `MonitorResponse` models (move to appropriate categories)

### Phase 4: Documentation

- Update OpenAPI/Swagger spec
- Update user guide
- Create migration guide (for reference, not backward compatibility)
- Update code examples

### Phase 5: Testing

- Update all API tests
- Add tests for new endpoint locations
- Remove tests for deleted endpoints
- Test error handling

---

## Summary

This redesign provides:

1. ✅ **Resource-Oriented Design**: All endpoints organized by resource type
2. ✅ **Hierarchical Organization**: Related resources nested appropriately
3. ✅ **Self-Contained Components**: Each resource provides comprehensive information
4. ✅ **Clean API Surface**: Removed debug category, eliminated monitor category
5. ✅ **Consistent Patterns**: Uniform response formats, error handling, pagination
6. ✅ **Better Discoverability**: Related endpoints grouped together
7. ✅ **Improved Security**: Removed risky debug endpoints (expression evaluation)
8. ✅ **Future-Proof**: Support for versioning, field selection, bulk operations

The API is now cleaner, more intuitive, and follows REST best practices while accurately reflecting the capabilities of the core implementation.

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-15  
**Status**: Ready for Implementation
