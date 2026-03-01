"""
Task schemas for request and response models.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class TaskCreate(BaseModel):
    """Task creation request schema."""
    task_type: str = Field(..., description="Type of task to execute")
    payload: Dict[str, Any] = Field(..., description="Task payload data")
    priority: int = Field(default=2, ge=1, le=4, description="Task priority (1=low, 2=normal, 3=high, 4=critical)")
    scheduled_for: Optional[datetime] = Field(None, description="When to execute task (ISO format)")
    timeout: int = Field(default=300, gt=0, description="Task timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key for duplicate prevention")


class TaskResponse(BaseModel):
    """Task response schema."""
    id: str = Field(..., description="Task ID")
    type: str = Field(..., description="Task type")
    status: str = Field(..., description="Task status")
    priority: int = Field(..., description="Task priority")
    payload: Dict[str, Any] = Field(..., description="Task payload")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled execution time")
    timeout: int = Field(..., description="Task timeout in seconds")
    max_retries: int = Field(..., description="Maximum retry attempts")
    retry_count: int = Field(..., description="Current retry count")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    failed_at: Optional[datetime] = Field(None, description="Task failure timestamp")
    locked_by: Optional[str] = Field(None, description="Worker ID that locked the task")
    locked_at: Optional[datetime] = Field(None, description="Task lock timestamp")
    created_by: str = Field(..., description="User who created the task")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        from_attributes = True


class TaskListQuery(BaseModel):
    """Task list query parameters."""
    status: Optional[str] = Field(None, description="Filter by task status")
    task_type: Optional[str] = Field(None, description="Filter by task type")
    priority: Optional[int] = Field(None, ge=1, le=4, description="Filter by priority")
    created_by: Optional[str] = Field(None, description="Filter by creator")
    correlation_id: Optional[str] = Field(None, description="Filter by correlation ID")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of tasks to return")
    offset: int = Field(default=0, ge=0, description="Number of tasks to skip")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")


class TaskListResponse(BaseModel):
    """Task list response schema."""
    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks matching criteria")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")
    has_more: bool = Field(..., description="Whether more tasks are available")


class TaskUpdate(BaseModel):
    """Task update request schema."""
    status: Optional[str] = Field(None, description="New task status")
    priority: Optional[int] = Field(None, ge=1, le=4, description="New task priority")
    scheduled_for: Optional[datetime] = Field(None, description="New scheduled time")
    max_retries: Optional[int] = Field(None, ge=0, description="New max retries")


class TaskActionRequest(BaseModel):
    """Task action request schema."""
    action: str = Field(..., description="Action to perform (cancel, retry, reschedule)")
    reason: Optional[str] = Field(None, description="Reason for action")
    scheduled_for: Optional[datetime] = Field(None, description="New scheduled time for reschedule action")


# Worker Task Management Schemas
class TaskClaimRequest(BaseModel):
    """Schema for worker claiming a task."""
    worker_id: str = Field(..., description="Worker ID claiming the task")
    lock_timeout: int = Field(default=300, gt=0, description="Task lock timeout in seconds")


class TaskClaimResponse(BaseModel):
    """Response schema when worker claims a task."""
    task_id: str = Field(..., description="ID of claimed task")
    task: TaskResponse = Field(..., description="Full task details")
    lock_expires_at: datetime = Field(..., description="When the task lock expires") 


class TaskProgressUpdate(BaseModel):
    """Schema for worker to update task progress."""
    worker_id: str = Field(..., description="Worker ID updating the task")
    progress_percentage: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage (0-100)")
    status_message: Optional[str] = Field(None, description="Status message for the task")
    intermediate_result: Optional[Dict[str, Any]] = Field(None, description="Intermediate results")


class TaskCompleteRequest(BaseModel):
    """Schema for worker to complete a task."""
    worker_id: str = Field(..., description="Worker ID completing the task")
    result: Optional[Dict[str, Any]] = Field(None, description="Task completion result")
    execution_time: Optional[float] = Field(None, gt=0, description="Task execution time in seconds")


class TaskFailRequest(BaseModel):
    """Schema for worker to mark task as failed."""
    worker_id: str = Field(..., description="Worker ID reporting failure")
    error_message: str = Field(..., description="Error message describing the failure")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    should_retry: bool = Field(default=True, description="Whether task should be retried")


class WorkerTaskListQuery(BaseModel):
    """Query parameters for worker to list available tasks."""
    task_types: Optional[List[str]] = Field(None, description="Task types worker can handle")
    priority_min: Optional[int] = Field(None, ge=1, le=4, description="Minimum priority level")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of tasks to return")


class WorkerTaskListResponse(BaseModel):
    """Response schema for worker task list."""
    tasks: List[TaskResponse] = Field(..., description="Available tasks for worker")
    total_available: int = Field(..., description="Total available tasks for this worker")


# Dead Letter Queue Schemas
class DeadLetterTaskResponse(BaseModel):
    """Schema for dead letter queue tasks."""
    task_id: str = Field(..., description="ID of the task")
    original_task: TaskResponse = Field(..., description="Original task details")
    failure_count: int = Field(..., description="Number of times task failed")
    last_error: Optional[str] = Field(None, description="Last error message")
    moved_to_dlq_at: datetime = Field(..., description="When task was moved to dead letter queue")


class DeadLetterQueueListResponse(BaseModel):
    """Response schema for dead letter queue list."""
    tasks: List[DeadLetterTaskResponse] = Field(..., description="Tasks in dead letter queue")
    total: int = Field(..., description="Total number of dead letter tasks")


class RetryDeadLetterTaskRequest(BaseModel):
    """Schema for retrying a dead letter task."""
    reset_retry_count: bool = Field(default=True, description="Whether to reset retry count")
    new_priority: Optional[int] = Field(None, ge=1, le=4, description="New priority for retry")