"""
Worker schemas for request and response models.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class WorkerRegister(BaseModel):
    """Worker registration request schema."""
    worker_id: str = Field(..., description="Unique worker identifier")
    capabilities: List[str] = Field(..., min_items=1, description="List of task types this worker can handle")
    api_key: str = Field(..., min_length=32, description="Worker API key for authentication")
    version: Optional[str] = Field(None, description="Worker version string")
    hostname: Optional[str] = Field(None, description="Worker hostname")
    ip_address: Optional[str] = Field(None, description="Worker IP address")
    port: Optional[int] = Field(None, gt=0, le=65535, description="Worker port number")
    max_concurrent_tasks: int = Field(default=1, gt=0, description="Maximum concurrent tasks")
    heartbeat_interval: int = Field(default=30, gt=0, description="Heartbeat interval in seconds")


class WorkerHeartbeat(BaseModel):
    """Worker heartbeat request schema."""
    worker_id: str = Field(..., description="Worker ID")
    status: str = Field(..., description="Worker status (active, idle, error)")
    current_task_id: Optional[str] = Field(None, description="Currently processing task ID")
    memory_usage: Optional[float] = Field(None, ge=0, le=100, description="Memory usage percentage")
    cpu_usage: Optional[float] = Field(None, ge=0, le=100, description="CPU usage percentage")
    disk_usage: Optional[float] = Field(None, ge=0, le=100, description="Disk usage percentage")
    tasks_processed: int = Field(default=0, ge=0, description="Total tasks processed")
    tasks_failed: int = Field(default=0, ge=0, description="Total tasks failed")
    uptime_seconds: int = Field(default=0, ge=0, description="Worker uptime in seconds")


class WorkerResponse(BaseModel):
    """Worker response schema."""
    id: str = Field(..., description="Worker ID")
    status: str = Field(..., description="Worker status")
    capabilities: List[str] = Field(..., description="Worker capabilities")
    version: Optional[str] = Field(None, description="Worker version")
    current_task_id: Optional[str] = Field(None, description="Current task ID")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")
    tasks_processed: int = Field(..., description="Total tasks processed")
    tasks_failed: int = Field(..., description="Total tasks failed")
    tasks_completed: int = Field(..., description="Total tasks completed")
    total_processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    uptime_seconds: int = Field(..., description="Worker uptime in seconds")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    disk_usage: Optional[float] = Field(None, description="Disk usage percentage")
    hostname: Optional[str] = Field(None, description="Worker hostname")
    ip_address: Optional[str] = Field(None, description="Worker IP address")
    port: Optional[int] = Field(None, description="Worker port")
    created_at: datetime = Field(..., description="Worker registration timestamp")

    class Config:
        from_attributes = True


class WorkerListQuery(BaseModel):
    """Worker list query parameters."""
    status: Optional[str] = Field(None, description="Filter by worker status")
    capability: Optional[str] = Field(None, description="Filter by capability")
    hostname: Optional[str] = Field(None, description="Filter by hostname")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of workers to return")
    offset: int = Field(default=0, ge=0, description="Number of workers to skip")
    sort_by: str = Field(default="last_heartbeat", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")


class WorkerListResponse(BaseModel):
    """Worker list response schema."""
    workers: List[WorkerResponse] = Field(..., description="List of workers")
    total: int = Field(..., description="Total number of workers matching criteria")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")
    has_more: bool = Field(..., description="Whether more workers are available")


class WorkerStats(BaseModel):
    """Worker statistics schema."""
    total_workers: int = Field(..., description="Total number of workers")
    active_workers: int = Field(..., description="Number of active workers")
    idle_workers: int = Field(..., description="Number of idle workers")
    offline_workers: int = Field(..., description="Number of offline workers")
    error_workers: int = Field(..., description="Number of workers in error state")
    avg_cpu_usage: float = Field(..., description="Average CPU usage across workers")
    avg_memory_usage: float = Field(..., description="Average memory usage across workers")
    total_tasks_processed: int = Field(..., description="Total tasks processed by all workers")
    total_tasks_failed: int = Field(..., description="Total tasks failed by all workers")


class WorkerRegistrationResponse(BaseModel):
    """Worker registration response schema."""
    worker_id: str = Field(..., description="Registered worker ID")
    status: str = Field(..., description="Registration status")
    message: str = Field(..., description="Registration message")
    worker: WorkerResponse = Field(..., description="Worker details")