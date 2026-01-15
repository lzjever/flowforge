# WebSocket Events

## Overview

Routilux provides real-time event streaming through WebSocket connections. This allows clients to receive updates as they occur, without the need for polling.

## Connection

### Monitor Job Events

```javascript
const ws = new WebSocket('ws://localhost:20555/api/ws/jobs/{job_id}/monitor');
```

### Monitor Debug Events

```javascript
const ws = new WebSocket('ws://localhost:20555/api/ws/jobs/{job_id}/debug');
```

### Monitor Flow Events

```javascript
const ws = new WebSocket('ws://localhost:20555/api/ws/flows/{flow_id}/monitor');
```

## Event Types

### Connection Status Events

#### `connection:status`

Sent when the connection status changes.

```json
{
  "type": "connection:status",
  "status": "connected",  // connected | disconnected | reconnecting
  "timestamp": "2025-01-15T10:30:00Z",
  "server_time": "2025-01-15T10:30:00Z"
}
```

**Possible values:**
- `connected`: Connection established
- `disconnected`: Connection closed
- `reconnecting`: Attempting to reconnect

---

### Heartbeat Events

#### `ping`

Sent periodically (every 30 seconds) to keep the connection alive.

```json
{
  "type": "ping",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Client Response:**
```json
{
  "type": "pong"
}
```

---

### Job Events

#### `job_started`

Sent when a job starts execution.

```json
{
  "type": "job_started",
  "job_id": "job_123",
  "flow_id": "my_flow",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "entry_routine": "start",
    "params": {
      "user_id": 123,
      "data": "example"
    }
  }
}
```

#### `job_completed`

Sent when a job completes successfully.

```json
{
  "type": "job_completed",
  "job_id": "job_123",
  "flow_id": "my_flow",
  "timestamp": "2025-01-15T10:35:00Z",
  "data": {
    "duration": 5.2,
    "total_events": 42
  }
}
```

#### `job_failed`

Sent when a job fails.

```json
{
  "type": "job_failed",
  "job_id": "job_123",
  "flow_id": "my_flow",
  "timestamp": "2025-01-15T10:32:00Z",
  "data": {
    "error": "ValueError: Invalid input",
    "error_type": "ValueError",
    "routine_id": "process_data"
  }
}
```

#### `job_paused`

Sent when a job is paused.

```json
{
  "type": "job_paused",
  "job_id": "job_123",
  "timestamp": "2025-01-15T10:33:00Z",
  "data": {
    "reason": "Paused via API"
  }
}
```

#### `job_resumed`

Sent when a paused job is resumed.

```json
{
  "type": "job_resumed",
  "job_id": "job_123",
  "timestamp": "2025-01-15T10:34:00Z"
}
```

#### `job_cancelled`

Sent when a job is cancelled.

```json
{
  "type": "job_cancelled",
  "job_id": "job_123",
  "timestamp": "2025-01-15T10:35:00Z",
  "data": {
    "reason": "Cancelled via API"
  }
}
```

---

### Routine Events

#### `routine_started`

Sent when a routine starts execution.

```json
{
  "type": "routine_started",
  "job_id": "job_123",
  "routine_id": "process_data",
  "timestamp": "2025-01-15T10:30:05Z",
  "data": {
    "slot_name": "input",
    "event_data": {...}
  }
}
```

#### `routine_completed`

Sent when a routine completes execution.

```json
{
  "type": "routine_completed",
  "job_id": "job_123",
  "routine_id": "process_data",
  "timestamp": "2025-01-15T10:30:10Z",
  "data": {
    "duration": 0.5,
    "events_emitted": 2
  }
}
```

#### `routine_failed`

Sent when a routine fails.

```json
{
  "type": "routine_failed",
  "job_id": "job_123",
  "routine_id": "process_data",
  "timestamp": "2025-01-15T10:30:08Z",
  "data": {
    "error": "ValueError: Invalid data format",
    "error_type": "ValueError",
    "slot_name": "input"
  }
}
```

---

### Breakpoint Events

#### `breakpoint_hit`

Sent when a breakpoint is hit during execution.

```json
{
  "type": "breakpoint_hit",
  "job_id": "job_123",
  "timestamp": "2025-01-15T10:31:00Z",
  "breakpoint": {
    "breakpoint_id": "bp_abc123",
    "type": "routine",
    "routine_id": "process_data",
    "slot_name": "input",
    "event_name": "output"
  },
  "context": {
    "routine_id": "process_data",
    "variables": {
      "data": "example",
      "count": 42
    }
  }
}
```

#### `breakpoint_resumed`

Sent when execution resumes from a breakpoint.

```json
{
  "type": "breakpoint_resumed",
  "job_id": "job_123",
  "breakpoint_id": "bp_abc123",
  "timestamp": "2025-01-15T10:31:05Z",
  "data": {
    "step_mode": "over"  // over | into | continue
  }
}
```

---

### Execution Events

#### `execution_event`

Sent for various execution events (slot calls, event emissions, etc.).

```json
{
  "type": "execution_event",
  "job_id": "job_123",
  "timestamp": "2025-01-15T10:30:06Z",
  "event": {
    "event_id": "evt_xyz789",
    "routine_id": "process_data",
    "event_type": "slot_call",
    "timestamp": "2025-01-15T10:30:06Z",
    "data": {
      "slot_name": "input",
      "arguments": {...}
    }
  }
}
```

**Possible `event_type` values:**
- `slot_call`: A slot was called
- `event_emit`: An event was emitted
- `error`: An error occurred

---

### Metrics Events

#### `metrics`

Sent periodically with execution metrics.

```json
{
  "type": "metrics",
  "job_id": "job_123",
  "timestamp": "2025-01-15T10:31:00Z",
  "metrics": {
    "start_time": "2025-01-15T10:30:00Z",
    "end_time": null,
    "duration": 60.0,
    "total_events": 150,
    "total_slot_calls": 75,
    "total_event_emits": 75
  }
}
```

---

### Subscription Events

#### `subscription:confirmed`

Sent when a subscription request is processed.

```json
{
  "type": "subscription:confirmed",
  "action": "subscribe",  // subscribe | unsubscribe | subscribe_all
  "events": ["job_started", "job_failed", "breakpoint_hit"]
}
```

---

## Event Filtering

You can subscribe to specific event types to reduce bandwidth:

### Subscribe to Specific Events

```javascript
// After connection is established
ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    events: ['job_started', 'job_failed', 'breakpoint_hit']
  }));
};
```

### Unsubscribe from Events

```javascript
ws.send(JSON.stringify({
  action: 'unsubscribe',
  events: ['routine_started']
}));
```

### Subscribe to All Events (Default)

```javascript
ws.send(JSON.stringify({
  action: 'subscribe_all'
}));
```

---

## Client Implementation

### Basic WebSocket Client

```javascript
class RoutiluxWebSocket {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.subscriptions = new Set();
    this.eventHandlers = new Map();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.emit('connected');
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected');
    };
  }

  subscribe(events) {
    events.forEach(e => this.subscriptions.add(e));

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        events: events
      }));
    }
  }

  unsubscribe(events) {
    events.forEach(e => this.subscriptions.delete(e));

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'unsubscribe',
        events: events
      }));
    }
  }

  handleMessage(message) {
    // Handle ping
    if (message.type === 'ping') {
      this.ws.send(JSON.stringify({ type: 'pong' }));
      return;
    }

    // Check if we're subscribed to this event
    if (this.subscriptions.size === 0 || this.subscriptions.has(message.type)) {
      this.emit(message.type, message);
    }
  }

  on(event, handler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event).push(handler);
  }

  emit(event, data) {
    const handlers = this.eventHandlers.get(event) || [];
    handlers.forEach(handler => handler(data));
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const client = new RoutiluxWebSocket('ws://localhost:20555/api/ws/jobs/job_123/monitor');

client.on('connected', () => {
  // Subscribe to specific events
  client.subscribe(['job_started', 'job_failed', 'breakpoint_hit']);
});

client.on('job_failed', (event) => {
  console.log('Job failed:', event.data.error);
});

client.on('breakpoint_hit', (event) => {
  console.log('Breakpoint hit at', event.breakpoint.routine_id);
});

client.connect();
```

### Auto-Reconnecting Client

```javascript
class ReconnectingWebSocket {
  constructor(url, options = {}) {
    this.url = url;
    this.reconnectInterval = options.reconnectInterval || 5000;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    this.reconnectAttempts = 0;
    this.ws = null;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected, attempting to reconnect...');
      this.scheduleReconnect();
    };
  }

  scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnection attempt ${this.reconnectAttempts}`);
        this.connect();
      }, this.reconnectInterval);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  handleMessage(message) {
    // Handle messages
  }
}
```

---

## Error Handling

### Connection Errors

```javascript
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
  // Attempt to reconnect
};
```

### Message Parse Errors

```javascript
ws.onmessage = (event) => {
  try {
    const message = JSON.parse(event.data);
    handleMessage(message);
  } catch (error) {
    console.error('Failed to parse message:', error);
  }
};
```

---

## Best Practices

### 1. Always Handle Connection States

```javascript
ws.onopen = () => {
  console.log('Connected');
  // Send subscription messages
};

ws.onclose = () => {
  console.log('Disconnected');
  // Implement reconnection logic
};
```

### 2. Use Event Filtering

Only subscribe to events you need to reduce bandwidth:

```javascript
client.subscribe(['job_started', 'job_failed', 'breakpoint_hit']);
```

### 3. Implement Heartbeat Detection

Monitor ping messages to detect connection issues:

```javascript
let lastPingTime = Date.now();

client.on('ping', () => {
  lastPingTime = Date.now();
});

// Check for stale connection
setInterval(() => {
  if (Date.now() - lastPingTime > 60000) { // 60 seconds
    console.warn('Connection may be stale');
    client.disconnect();
    client.connect();
  }
}, 10000);
```

### 4. Graceful Shutdown

Always close WebSocket connections when done:

```javascript
window.addEventListener('beforeunload', () => {
  client.disconnect();
});
```

---

## Security Considerations

1. **Use WSS for Production**: Always use `wss://` (WebSocket Secure) in production
2. **Authentication**: Include authentication tokens in connection URL
3. **Validation**: Validate all incoming messages on the client side
4. **Rate Limiting**: Implement rate limiting for reconnection attempts

## Related Features

- [REST API](../api_reference.md) - HTTP endpoints for job management
- [Debugging](conditional_breakpoints.md) - Breakpoint debugging
- [Expression Evaluation](expression_evaluation.md) - Runtime expression evaluation

## API Reference

See the [API Documentation](../api_reference.md) for complete endpoint details.
