"""
Admin API routes for metrics and system monitoring.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from ..dependencies import get_current_admin_user, get_task_service, get_worker_service
from ..schemas.admin import (
    MetricsResponse,
    MetricsQuery,
    SystemMetrics,
    TaskTypeMetrics,
    WorkerMetrics,
    QueueMetrics,
    ErrorMetrics,
    PerformanceMetrics,
    HealthStatus
)
from ..services import TaskService, WorkerService


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get system metrics",
    description="Get comprehensive system metrics and statistics (admin only)"
)
async def get_metrics(
    time_range: str = Query("1h", description="Time range for metrics (1h, 24h, 7d, 30d)"),
    include_task_types: bool = Query(True, description="Include task type breakdown"),
    include_workers: bool = Query(True, description="Include worker metrics"),
    include_errors: bool = Query(True, description="Include error details"),
    worker_id: Optional[str] = Query(None, description="Specific worker ID to filter by"),
    task_type: Optional[str] = Query(None, description="Specific task type to filter by"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    task_service: TaskService = Depends(get_task_service),
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Get comprehensive system metrics.
    
    Args:
        time_range: Time range for metrics
        include_task_types: Include task type breakdown
        include_workers: Include worker metrics
        include_errors: Include error details
        worker_id: Specific worker ID to filter by
        task_type: Specific task type to filter by
        current_user: Current admin user
        task_service: Task service instance
        worker_service: Worker service instance
        
    Returns:
        Comprehensive system metrics
        
    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        # Parse time range
        time_delta_map = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        if time_range not in time_delta_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time range. Use: 1h, 24h, 7d, 30d"
            )
        
        since = datetime.now(timezone.utc) - time_delta_map[time_range]
        
        # Get system metrics
        system_metrics = await _get_system_metrics(task_service, worker_service, since)
        
        # Get task type metrics
        task_type_metrics = []
        if include_task_types:
            task_type_metrics = await _get_task_type_metrics(task_service, since, task_type)
        
        # Get worker metrics
        worker_metrics = []
        if include_workers:
            worker_metrics = await _get_worker_metrics(worker_service, since, worker_id)
        
        # Get queue metrics
        queue_metrics = await _get_queue_metrics(task_service)
        
        # Get error metrics
        error_metrics = ErrorMetrics(
            total_errors=0,
            error_rate=0.0,
            common_errors=[],
            recent_errors=[]
        )
        if include_errors:
            error_metrics = await _get_error_metrics(task_service, since)
        
        # Get performance metrics
        performance_metrics = await _get_performance_metrics(task_service, since)
        
        # Get health status
        health_status = await _get_health_status(task_service, worker_service)
        
        return MetricsResponse(
            system=system_metrics,
            task_types=task_type_metrics,
            workers=worker_metrics,
            queue=queue_metrics,
            errors=error_metrics,
            performance=performance_metrics,
            health=health_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )


async def _get_system_metrics(
    task_service: TaskService, 
    worker_service: WorkerService, 
    since: datetime
) -> SystemMetrics:
    """Get system-wide metrics."""
    
    # Get task statistics
    task_stats = task_service.get_task_statistics()
    
    # Get worker statistics
    worker_stats = worker_service.get_worker_statistics()
    
    # Calculate success rate
    total_completed = task_stats.get("completed_tasks", 0)
    total_failed = task_stats.get("failed_tasks", 0)
    total_processed = total_completed + total_failed
    success_rate = (total_completed / total_processed * 100) if total_processed > 0 else 100.0
    
    # Get tasks processed in time windows
    tasks_last_hour = task_service.get_tasks_count_since(
        datetime.now(timezone.utc) - timedelta(hours=1)
    )
    tasks_last_24h = task_service.get_tasks_count_since(
        datetime.now(timezone.utc) - timedelta(hours=24)
    )
    
    return SystemMetrics(
        total_tasks=task_stats.get("total_tasks", 0),
        queued_tasks=task_stats.get("queued_tasks", 0),
        processing_tasks=task_stats.get("processing_tasks", 0),
        completed_tasks=total_completed,
        failed_tasks=total_failed,
        failed_permanent_tasks=task_stats.get("failed_permanent_tasks", 0),
        success_rate=success_rate,
        avg_processing_time=task_stats.get("avg_processing_time", 0.0),
        total_workers=worker_stats["total_workers"],
        active_workers=worker_stats["active_workers"],
        idle_workers=worker_stats["idle_workers"],
        offline_workers=worker_stats["offline_workers"],
        queue_length=task_stats.get("queued_tasks", 0),
        tasks_processed_last_hour=tasks_last_hour,
        tasks_processed_last_24h=tasks_last_24h,
        avg_cpu_usage=worker_stats["avg_cpu_usage"],
        avg_memory_usage=worker_stats["avg_memory_usage"],
        timestamp=datetime.now(timezone.utc)
    )


async def _get_task_type_metrics(
    task_service: TaskService, 
    since: datetime, 
    task_type_filter: Optional[str]
) -> list[TaskTypeMetrics]:
    """Get task type metrics."""
    
    # Get task type statistics from service
    task_type_stats = task_service.get_task_type_statistics(since=since)
    
    metrics = []
    for task_type, stats in task_type_stats.items():
        if task_type_filter and task_type != task_type_filter:
            continue
            
        total = stats.get("total_count", 0)
        success = stats.get("success_count", 0)
        failed = stats.get("failed_count", 0)
        success_rate = (success / total * 100) if total > 0 else 100.0
        
        metrics.append(TaskTypeMetrics(
            task_type=task_type,
            total_count=total,
            success_count=success,
            failed_count=failed,
            avg_processing_time=stats.get("avg_processing_time", 0.0),
            success_rate=success_rate
        ))
    
    return metrics


async def _get_worker_metrics(
    worker_service: WorkerService, 
    since: datetime, 
    worker_id_filter: Optional[str]
) -> list[WorkerMetrics]:
    """Get worker metrics."""
    
    # Get all workers
    workers, _ = worker_service.get_workers(
        filters={"worker_id": worker_id_filter} if worker_id_filter else {},
        limit=1000,
        offset=0
    )
    
    metrics = []
    for worker in workers:
        total_tasks = worker.tasks_processed + worker.tasks_failed
        success_rate = (
            worker.tasks_completed / total_tasks * 100 
            if total_tasks > 0 else 100.0
        )
        
        avg_processing_time = (
            worker.total_processing_time_ms / worker.tasks_processed / 1000.0
            if worker.tasks_processed > 0 else 0.0
        )
        
        metrics.append(WorkerMetrics(
            worker_id=worker.id,
            status=worker.status,
            tasks_processed=worker.tasks_processed,
            tasks_completed=worker.tasks_completed,
            tasks_failed=worker.tasks_failed,
            success_rate=success_rate,
            avg_processing_time=avg_processing_time,
            cpu_usage=worker.cpu_usage,
            memory_usage=worker.memory_usage,
            uptime_seconds=worker.uptime_seconds,
            last_heartbeat=worker.last_heartbeat
        ))
    
    return metrics


async def _get_queue_metrics(task_service: TaskService) -> QueueMetrics:
    """Get queue metrics."""
    
    queue_stats = task_service.get_queue_statistics()
    
    return QueueMetrics(
        total_queued=queue_stats.get("total_queued", 0),
        high_priority=queue_stats.get("high_priority", 0),
        normal_priority=queue_stats.get("normal_priority", 0),
        low_priority=queue_stats.get("low_priority", 0),
        scheduled_future=queue_stats.get("scheduled_future", 0),
        oldest_task_age_minutes=queue_stats.get("oldest_task_age_minutes"),
        avg_wait_time_minutes=queue_stats.get("avg_wait_time_minutes", 0.0)
    )


async def _get_error_metrics(task_service: TaskService, since: datetime) -> ErrorMetrics:
    """Get error metrics."""
    
    error_stats = task_service.get_error_statistics(since=since)
    
    return ErrorMetrics(
        total_errors=error_stats.get("total_errors", 0),
        error_rate=error_stats.get("error_rate", 0.0),
        common_errors=error_stats.get("common_errors", []),
        recent_errors=error_stats.get("recent_errors", [])
    )


async def _get_performance_metrics(task_service: TaskService, since: datetime) -> PerformanceMetrics:
    """Get performance metrics."""
    
    perf_stats = task_service.get_performance_statistics(since=since)
    
    return PerformanceMetrics(
        throughput_per_hour=perf_stats.get("throughput_per_hour", 0.0),
        throughput_per_minute=perf_stats.get("throughput_per_minute", 0.0),
        avg_response_time=perf_stats.get("avg_response_time", 0.0),
        p95_processing_time=perf_stats.get("p95_processing_time", 0.0),
        p99_processing_time=perf_stats.get("p99_processing_time", 0.0)
    )


async def _get_health_status(task_service: TaskService, worker_service: WorkerService) -> HealthStatus:
    """Get system health status."""
    
    alerts = []
    
    # Check database connection
    database_connected = True
    try:
        task_service.get_task_statistics()
    except Exception:
        database_connected = False
        alerts.append("Database connection failed")
    
    # Check worker health
    worker_stats = worker_service.get_worker_statistics()
    workers_healthy = worker_stats["active_workers"] > 0
    if not workers_healthy:
        alerts.append("No active workers available")
    
    # Check queue health
    queue_stats = task_service.get_queue_statistics()
    queue_length = queue_stats.get("total_queued", 0)
    queue_healthy = queue_length < 10000  # Threshold for unhealthy queue
    if not queue_healthy:
        alerts.append(f"Queue length too high: {queue_length}")
    
    # Determine overall status
    if database_connected and workers_healthy and queue_healthy:
        status = "healthy"
    elif database_connected and (workers_healthy or queue_healthy):
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthStatus(
        status=status,
        database_connected=database_connected,
        workers_healthy=workers_healthy,
        queue_healthy=queue_healthy,
        alerts=alerts,
        timestamp=datetime.now(timezone.utc)
    )


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Get system health",
    description="Get current system health status"
)
async def get_health(
    task_service: TaskService = Depends(get_task_service),
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Get system health status.
    
    Args:
        task_service: Task service instance
        worker_service: Worker service instance
        
    Returns:
        System health status
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        health_status = await _get_health_status(task_service, worker_service)
        return health_status
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )