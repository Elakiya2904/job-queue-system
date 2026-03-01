# Distributed Job Queue System - API Specification

## Overview
This document defines the complete API contract for the Distributed Job Queue & Background Task Processing System.

**Base URL**: `https://api.jobqueue.system/v1`

---

## 🔐 Authentication

### POST /auth/login
**Description**: Authenticate user and receive JWT token  
**Authentication**: None  
**Content-Type**: `application/json`

**Request Body**:
```json
{
  "email": "john.doe@example.com",
  "password": "securePassword123"
}
```

**Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "usr_1234567890",
    "email": "john.doe@example.com",
    "role": "user",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Invalid credentials
- `429 Too Many Requests`: Rate limit exceeded

### POST /auth/signup
**Description**: Register new user account  
**Authentication**: None  
**Content-Type**: `application/json`

**Request Body**:
```json
{
  "email": "jane.smith@example.com",
  "password": "securePassword456",
  "full_name": "Jane Smith"
}
```

**Response (201 Created)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "usr_0987654321",
    "email": "jane.smith@example.com",
    "role": "user",
    "created_at": "2024-01-15T10:35:00Z"
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request format or validation errors
- `409 Conflict`: Email already exists

---

## 📋 Task APIs (Public)

### POST /tasks
**Description**: Create a new task for processing  
**Authentication**: Bearer JWT  
**Content-Type**: `application/json`  
**Headers**: 
- `Authorization: Bearer {jwt_token}`
- `Idempotency-Key: {unique_key}` (optional)
- `X-Correlation-ID: {unique_request_id}` (optional, auto-generated if not provided)

**Request Body**:
```json
{
  "type": "email_processing",
  "payload": {
    "recipient": "customer@example.com",
    "template": "welcome_email",
    "variables": {
      "name": "John Doe",
      "company": "Example Corp"
    }
  },
  "priority": 2,
  "scheduled_for": "2024-01-15T15:00:00Z",
  "timeout": 300,
  "max_retries": 3
}
```

**Priority Levels**:
- `1`: Low priority
- `2`: Normal priority (default)
- `3`: High priority  
- `4`: Critical priority

**Response (201 Created)**:
```json
{
  "id": "task_abc123def456",
  "type": "email_processing",
  "status": "queued",
  "priority": 2,
  "payload": {
    "recipient": "customer@example.com",
    "template": "welcome_email",
    "variables": {
      "name": "John Doe",
      "company": "Example Corp"
    }
  },
  "scheduled_for": "2024-01-15T15:00:00Z",
  "timeout": 300,
  "max_retries": 3,
  "retry_count": 0,
  "created_at": "2024-01-15T10:45:00Z",
  "updated_at": "2024-01-15T10:45:00Z",
  "created_by": "usr_1234567890",
  "correlation_id": "req_abc123def456"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request format or validation errors
- `401 Unauthorized`: Invalid or missing JWT token

**Note**: If an `Idempotency-Key` header is provided with a duplicate key, the API returns the existing task with `200 OK` status instead of creating a new task.

### GET /tasks
**Description**: List tasks with pagination and filtering  
**Authentication**: Bearer JWT  
**Query Parameters**:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)
- `status`: Filter by status (`queued`, `processing`, `completed`, `failed`, `failed_permanent`)
- `type`: Filter by task type
- `sort`: Sort field (`created_at`, `updated_at`, `priority`)
- `order`: Sort order (`asc`, `desc`, default: `desc`)

**Example Request**:
```
GET /tasks?page=1&page_size=10&status=queued&sort=created_at&order=desc
```

**Response (200 OK)**:
```json
{
  "items": [
    {
      "id": "task_abc123def456",
      "type": "email_processing",
      "status": "queued",
      "priority": 2,
      "retry_count": 0,
      "max_retries": 3,
      "created_at": "2024-01-15T10:45:00Z",
      "updated_at": "2024-01-15T10:45:00Z",
      "scheduled_for": "2024-01-15T15:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 10,
  "total_pages": 15
}
```

### GET /tasks/{id}
**Description**: Get detailed task information including attempt history  
**Authentication**: Bearer JWT

**Response (200 OK)**:
```json
{
  "id": "task_abc123def456",
  "type": "email_processing",
  "status": "completed",
  "priority": 2,
  "payload": {
    "recipient": "customer@example.com",
    "template": "welcome_email",
    "variables": {
      "name": "John Doe",
      "company": "Example Corp"
    }
  },
  "result": {
    "message_id": "msg_xyz789",
    "delivered_at": "2024-01-15T15:01:23Z"
  },
  "scheduled_for": "2024-01-15T15:00:00Z",
  "timeout": 300,
  "max_retries": 3,
  "retry_count": 1,
  "created_at": "2024-01-15T10:45:00Z",
  "updated_at": "2024-01-15T15:01:30Z",
  "completed_at": "2024-01-15T15:01:30Z",
  "created_by": "usr_1234567890",
  "attempts": [
    {
      "id": "attempt_111",
      "started_at": "2024-01-15T15:00:15Z",
      "completed_at": null,
      "failed_at": "2024-01-15T15:00:45Z",
      "worker_id": "worker-001",
      "error_message": "Connection timeout",
      "error_code": "CONNECTION_TIMEOUT"
    },
    {
      "id": "attempt_222", 
      "started_at": "2024-01-15T15:01:00Z",
      "completed_at": "2024-01-15T15:01:30Z",
      "failed_at": null,
      "worker_id": "worker-002",
      "error_message": null,
      "error_code": null
    }
  ]
}
```

**Error Responses**:
- `404 Not Found`: Task not found or access denied

---

## 🤖 Worker Internal APIs

### POST /internal/poll
**Description**: Poll for next available task (atomic operation)  
**Authentication**: API Key  
**Headers**: `X-API-Key: {worker_api_key}`

**Request Body**:
```json
{
  "capabilities": ["email_processing", "file_conversion"],
  "max_timeout": 600
}
```

**Response (200 OK)** - Task Available:
```json
{
  "id": "task_abc123def456",
  "type": "email_processing",
  "payload": {
    "recipient": "customer@example.com",
    "template": "welcome_email",
    "variables": {
      "name": "John Doe",
      "company": "Example Corp"
    }
  },
  "timeout": 300,
  "attempt_id": "attempt_333",
  "locked_at": "2024-01-15T15:01:00Z",
  "lock_timeout": 300
}
```

**Response (204 No Content)** - No Tasks Available

**Error Responses**:
- `401 Unauthorized`: Invalid API key
- `403 Forbidden`: Worker not authorized

### POST /internal/heartbeat
**Description**: Update worker heartbeat and status  
**Authentication**: API Key

**Request Body**:
```json
{
  "status": "active",
  "current_task_id": "task_abc123def456",
  "memory_usage": 75.5,
  "cpu_usage": 45.2
}
```

**Response (200 OK)**:
```json
{
  "acknowledged": true,
  "next_heartbeat_in": 30
}
```

### POST /internal/complete
**Description**: Mark task as completed with result  
**Authentication**: API Key

**Request Body**:
```json
{
  "task_id": "task_abc123def456",
  "attempt_id": "attempt_333",
  "result": {
    "message_id": "msg_xyz789",
    "delivered_at": "2024-01-15T15:01:23Z"
  },
  "processing_time_ms": 2300
}
```

**Response (200 OK)**:
```json
{
  "acknowledged": true,
  "task_status": "completed"
}
```

**Error Responses**:
- `404 Not Found`: Task or attempt not found
- `409 Conflict`: Task not locked by this worker

### POST /internal/fail
**Description**: Mark task attempt as failed  
**Authentication**: API Key

**Request Body**:
```json
{
  "task_id": "task_abc123def456",
  "attempt_id": "attempt_333",
  "error_code": "CONNECTION_TIMEOUT",
  "error_message": "Failed to connect to email service after 3 attempts",
  "processing_time_ms": 30000
}
```

**Response (200 OK)**:
```json
{
  "acknowledged": true,
  "task_status": "queued",
  "retry_scheduled_for": "2024-01-15T15:08:00Z",
  "retry_count": 2,
  "backoff_seconds": 480
}
```

**Response (200 OK)** - Max Retries Exceeded:
```json
{
  "acknowledged": true,
  "task_status": "failed_permanent",
  "moved_to_dead_letter": true
}
```

---

## 👑 Admin APIs

### GET /admin/metrics
**Description**: Get system-wide metrics and statistics  
**Authentication**: Bearer JWT (admin role required)

**Query Parameters**:
- `period`: Time period (`1h`, `24h`, `7d`, `30d`, default: `24h`)

**Response (200 OK)**:
```json
{
  "timestamp": "2024-01-15T15:30:00Z",
  "period": "24h",
  "queue_length": 342,
  "processing_count": 28,
  "completed_count": 1247,
  "failed_count": 43,
  "failed_permanent_count": 5,
  "avg_processing_time_ms": 2340,
  "p95_processing_time_ms": 5200,
  "active_workers": 12,
  "idle_workers": 3,
  "offline_workers": 1,
  "throughput": {
    "tasks_per_hour": 156,
    "tasks_per_minute": 2.6
  },
  "error_rate": 0.034,
  "success_rate": 0.966,
  "top_task_types": [
    {
      "type": "email_processing",
      "count": 567,
      "avg_duration_ms": 1200
    },
    {
      "type": "file_conversion", 
      "count": 234,
      "avg_duration_ms": 4500
    }
  ]
}
```

### GET /admin/dead-letter
**Description**: Get tasks in dead letter queue  
**Authentication**: Bearer JWT (admin role required)

**Query Parameters**:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `type`: Filter by task type

**Response (200 OK)**:
```json
{
  "items": [
    {
      "id": "task_def456ghi789",
      "type": "file_conversion",
      "payload": {
        "input_file": "document.pdf",
        "output_format": "docx"
      },
      "failed_at": "2024-01-15T14:30:00Z",
      "retry_count": 3,
      "last_error": {
        "code": "FILE_CORRUPTION",
        "message": "Input file appears to be corrupted"
      },
      "attempts": [
        {
          "worker_id": "worker-003",
          "failed_at": "2024-01-15T14:15:00Z",
          "error_code": "FILE_CORRUPTION"
        }
      ]
    }
  ],
  "total": 23,
  "page": 1,
  "page_size": 20,
  "total_pages": 2
}
```

### POST /admin/retry/{task_id}
**Description**: Manually retry a failed task  
**Authentication**: Bearer JWT (admin role required)

**Request Body** (optional):
```json
{
  "reset_retry_count": true,
  "priority": 3
}
```

**Response (200 OK)**:
```json
{
  "task_id": "task_def456ghi789",
  "status": "queued",
  "retry_count": 0,
  "scheduled_for": "2024-01-15T15:35:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Task not found
- `409 Conflict`: Task not in failed state

---

## 🔄 Dead Letter Queue & Stale Lock Handling

### Stale Lock Requeue Process
When a task lock expires (task is `locked_at` + `lock_timeout` seconds ago), the system automatically:

1. **Detect Stale Locks**: Background process identifies tasks locked beyond their timeout
2. **Reset Lock State**: Clear `locked_by`, `locked_at`, and `lock_timeout` fields  
3. **Increment Retry Count**: If retry count < max_retries
4. **Apply Exponential Backoff**: Calculate next retry time using: `base_delay * (2 ^ retry_count)` 
5. **Requeue or Dead Letter**: 
   - If retries available: Schedule for retry with backoff delay
   - If max retries exceeded: Move to dead letter queue

### Dead Letter Queue Criteria
Tasks are moved to dead letter queue when:
- Max retry attempts exceeded (`retry_count >= max_retries`)
- Task fails with permanent error codes: `FILE_CORRUPTION`, `INVALID_PAYLOAD`
- Task lock is stale for more than 6 hours (indicates worker crash)

### Backoff Strategy
The server controls retry timing using exponential backoff:
```
retry_delay = min(base_delay * (2 ^ retry_count), max_delay)
```
- `base_delay`: 60 seconds (configurable)
- `max_delay`: 1800 seconds (30 minutes)
- Jitter: ±25% random variation to prevent thundering herd

---

## ❌ Error Handling Standard

All API errors return the following format:

```json
{
  "error_code": "STRING_CODE",
  "message": "Human readable error message",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "req_abc123def456",
  "timestamp": "2024-01-15T15:30:00Z",
  "details": {
    "field": "Optional additional context"
  }
}
```

### Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `TASK_LOCKED` | Task is currently locked by another worker | 409 |
| `TASK_NOT_FOUND` | Task does not exist or access denied | 404 |
| `WORKER_UNAUTHORIZED` | Worker API key invalid or expired | 401 |
| `INVALID_IDEMPOTENCY_KEY` | Malformed idempotency key | 400 |
| `STALE_LOCK_DETECTED` | Task lock has expired and been reassigned | 409 |
| `MAX_RETRIES_EXCEEDED` | Task exceeded maximum retry attempts | 409 |
| `UNAUTHORIZED` | Authentication required or invalid | 401 |
| `FORBIDDEN` | Insufficient permissions | 403 |
| `VALIDATION_ERROR` | Request validation failed | 400 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `INTERNAL_SERVER_ERROR` | Unexpected server error | 500 |
| `SERVICE_UNAVAILABLE` | System temporarily unavailable | 503 |
| `CONNECTION_TIMEOUT` | External service timeout | 408 |
| `FILE_CORRUPTION` | File processing error | 422 |
| `INSUFFICIENT_RESOURCES` | System resource constraints | 507 |

---

## 📄 Pagination Format

All paginated endpoints use this standard format:

```json
{
  "items": [],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "has_next": true,
  "has_previous": false
}
```

---

## 📊 Data Models

### Task
```json
{
  "id": "string",
  "type": "string", 
  "status": "queued|processing|completed|failed|failed_permanent",
  "priority": "integer (1=low, 2=normal, 3=high, 4=critical)",
  "payload": "object",
  "result": "object|null",
  "scheduled_for": "string (ISO 8601)|null",
  "timeout": "integer (seconds)",
  "max_retries": "integer",
  "retry_count": "integer",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "started_at": "string (ISO 8601)|null",
  "completed_at": "string (ISO 8601)|null",
  "failed_at": "string (ISO 8601)|null",
  "locked_by": "string|null",
  "locked_at": "string (ISO 8601)|null",
  "lock_timeout": "integer (seconds)|null",
  "created_by": "string"
}
```

### TaskAttempt
```json
{
  "id": "string",
  "task_id": "string",
  "worker_id": "string",
  "started_at": "string (ISO 8601)",
  "completed_at": "string (ISO 8601)|null",
  "failed_at": "string (ISO 8601)|null", 
  "processing_time_ms": "integer|null",
  "error_code": "string|null",
  "error_message": "string|null"
}
```

### Worker
```json
{
  "id": "string",
  "status": "active|idle|offline|error",
  "capabilities": ["string"],
  "last_heartbeat": "string (ISO 8601)",
  "current_task_id": "string|null",
  "tasks_processed": "integer",
  "uptime": "integer (seconds)",
  "memory_usage": "number (percentage)",
  "cpu_usage": "number (percentage)",
  "version": "string",
  "created_at": "string (ISO 8601)"
}
```

### Metrics
```json
{
  "timestamp": "string (ISO 8601)",
  "period": "string",
  "queue_length": "integer",
  "processing_count": "integer", 
  "completed_count": "integer",
  "failed_count": "integer",
  "failed_permanent_count": "integer",
  "avg_processing_time_ms": "integer",
  "p95_processing_time_ms": "integer",
  "active_workers": "integer",
  "idle_workers": "integer", 
  "offline_workers": "integer",
  "throughput": {
    "tasks_per_hour": "number",
    "tasks_per_minute": "number"
  },
  "error_rate": "number (0-1)",
  "success_rate": "number (0-1)"
}
```

### DeadLetterEntry
```json
{
  "id": "string",
  "type": "string",
  "payload": "object",
  "failed_at": "string (ISO 8601)",
  "retry_count": "integer",
  "last_error": {
    "code": "string",
    "message": "string"
  },
  "attempts": ["TaskAttempt"],
  "created_at": "string (ISO 8601)"
}
```

---

## � Observability & Correlation

All API requests support an optional `X-Correlation-ID` header for request tracing:
- If not provided, server auto-generates a unique correlation ID
- Returned in all responses (success and error) for end-to-end tracing
- Used for distributed tracing across microservices
- Helps correlate logs, metrics, and traces for debugging

**Example Headers**:
```
X-Correlation-ID: req_abc123def456
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response Headers**:
```
X-Correlation-ID: req_abc123def456
X-Request-ID: internal_trace_xyz789
```

---

## �🔒 Authentication Summary

| Endpoint Type | Authentication | Header |
|---------------|----------------|---------|
| Auth | None | - |
| Public Tasks | JWT Bearer | `Authorization: Bearer {token}` |
| Worker Internal | API Key | `X-API-Key: {api_key}` |
| Admin | JWT Bearer (admin role) | `Authorization: Bearer {token}` |

---

## 📈 Rate Limits

| Endpoint Group | Limit | Window |
|----------------|--------|---------|
| Auth | 10 requests | 1 minute |
| Public Tasks | 100 requests | 1 minute |
| Worker Internal | 1000 requests | 1 minute | 
| Admin | 200 requests | 1 minute |

---

## 🏷️ HTTP Status Codes Summary

| Status | Usage |
|--------|--------|
| 200 | Successful GET, PUT, PATCH |
| 201 | Successful POST (resource created) |
| 204 | Successful request with no content |
| 400 | Bad request / validation error |
| 401 | Authentication required |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate, locked resource) |
| 422 | Unprocessable entity |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service unavailable |