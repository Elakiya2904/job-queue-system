"""
Admin and metrics schemas for request and response models.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional


class SystemMetrics(BaseModel):
    """System-wide metrics schema."""
    total_tasks: int = Field(..., description="Total number of tasks")
    queued_tasks: int = Field(..., description="Number of queued tasks")
    processing_tasks: int = Field(..., description="Number of processing tasks")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    failed_tasks: int = Field(..., description="Number of failed tasks")
    failed_permanent_tasks: int = Field(..., description="Number of permanently failed tasks")
    
    success_rate: float = Field(..., description="Overall success rate percentage")
    avg_processing_time: float = Field(..., description="Average processing time in seconds")
    
    total_workers: int = Field(..., description="Total number of workers")
    active_workers: int = Field(..., description="Number of active workers")
    idle_workers: int = Field(..., description="Number of idle workers")
    offline_workers: int = Field(..., description="Number of offline workers")
    
    queue_length: int = Field(..., description="Current queue length")
    tasks_processed_last_hour: int = Field(..., description="Tasks processed in last hour")
    tasks_processed_last_24h: int = Field(..., description="Tasks processed in last 24 hours")
    
    avg_cpu_usage: float = Field(..., description="Average CPU usage across workers")
    avg_memory_usage: float = Field(..., description="Average memory usage across workers")
    
    timestamp: datetime = Field(..., description="Metrics timestamp")


class TaskTypeMetrics(BaseModel):
    """Task type metrics schema."""
    task_type: str = Field(..., description="Task type name")
    total_count: int = Field(..., description="Total tasks of this type")
    success_count: int = Field(..., description="Successful tasks of this type")
    failed_count: int = Field(..., description="Failed tasks of this type")
    avg_processing_time: float = Field(..., description="Average processing time for this type")
    success_rate: float = Field(..., description="Success rate for this type")


class WorkerMetrics(BaseModel):
    """Individual worker metrics schema."""
    worker_id: str = Field(..., description="Worker ID")
    status: str = Field(..., description="Worker status")
    tasks_processed: int = Field(..., description="Total tasks processed")
    tasks_completed: int = Field(..., description="Tasks completed successfully")
    tasks_failed: int = Field(..., description="Tasks failed")
    success_rate: float = Field(..., description="Worker success rate")
    avg_processing_time: float = Field(..., description="Average processing time")
    cpu_usage: Optional[float] = Field(None, description="Current CPU usage")
    memory_usage: Optional[float] = Field(None, description="Current memory usage")
    uptime_seconds: int = Field(..., description="Worker uptime")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")


class QueueMetrics(BaseModel):
    """Queue metrics schema."""
    total_queued: int = Field(..., description="Total queued tasks")
    high_priority: int = Field(..., description="High priority tasks in queue")
    normal_priority: int = Field(..., description="Normal priority tasks in queue")
    low_priority: int = Field(..., description="Low priority tasks in queue")
    scheduled_future: int = Field(..., description="Tasks scheduled for future execution")
    oldest_task_age_minutes: Optional[int] = Field(None, description="Age of oldest queued task in minutes")
    avg_wait_time_minutes: float = Field(..., description="Average wait time in minutes")


class ErrorMetrics(BaseModel):
    """Error metrics schema."""
    total_errors: int = Field(..., description="Total number of errors")
    error_rate: float = Field(..., description="Error rate percentage")
    common_errors: List[Dict[str, Any]] = Field(..., description="Most common error types and counts")
    recent_errors: List[Dict[str, Any]] = Field(..., description="Recent error details")


class PerformanceMetrics(BaseModel):
    """Performance metrics schema."""
    throughput_per_hour: float = Field(..., description="Tasks processed per hour")
    throughput_per_minute: float = Field(..., description="Tasks processed per minute")
    avg_response_time: float = Field(..., description="Average API response time")
    p95_processing_time: float = Field(..., description="95th percentile processing time")
    p99_processing_time: float = Field(..., description="99th percentile processing time")


class HealthStatus(BaseModel):
    """System health status schema."""
    status: str = Field(..., description="Overall system status")
    database_connected: bool = Field(..., description="Database connection status")
    workers_healthy: bool = Field(..., description="Worker health status")
    queue_healthy: bool = Field(..., description="Queue health status")
    alerts: List[str] = Field(..., description="Active alerts")
    timestamp: datetime = Field(..., description="Health check timestamp")


class MetricsResponse(BaseModel):
    """Complete metrics response schema."""
    system: SystemMetrics = Field(..., description="System-wide metrics")
    task_types: List[TaskTypeMetrics] = Field(..., description="Per task type metrics")
    workers: List[WorkerMetrics] = Field(..., description="Worker metrics")
    queue: QueueMetrics = Field(..., description="Queue metrics")
    errors: ErrorMetrics = Field(..., description="Error metrics")
    performance: PerformanceMetrics = Field(..., description="Performance metrics")
    health: HealthStatus = Field(..., description="System health status")


class MetricsQuery(BaseModel):
    """Metrics query parameters."""
    time_range: str = Field(default="1h", description="Time range for metrics (1h, 24h, 7d, 30d)")
    include_task_types: bool = Field(default=True, description="Include task type breakdown")
    include_workers: bool = Field(default=True, description="Include worker metrics")
    include_errors: bool = Field(default=True, description="Include error details")
    worker_id: Optional[str] = Field(None, description="Specific worker ID to filter by")
    task_type: Optional[str] = Field(None, description="Specific task type to filter by")