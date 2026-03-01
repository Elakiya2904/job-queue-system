"""
Worker management API routes.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from ..dependencies import get_current_user_optional, get_current_user, get_worker_service
from ..schemas.worker import (
    WorkerRegister,
    WorkerHeartbeat,
    WorkerResponse,
    WorkerListQuery,
    WorkerListResponse,
    WorkerStats,
    WorkerRegistrationResponse
)
from ..services import WorkerService


router = APIRouter(prefix="/workers", tags=["workers"])


@router.get(
    "/",
    response_model=WorkerListResponse,
    summary="List workers",
    description="Get a list of workers with optional filtering and pagination"
)
async def list_workers(
    status: Optional[str] = Query(None, description="Filter by worker status"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of workers to return"),
    offset: int = Query(0, ge=0, description="Number of workers to skip"),
    sort_by: str = Query("last_heartbeat", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    worker_service: WorkerService = Depends(get_worker_service)
):
    # 'status' query param shadows fastapi.status — use numeric codes in exception handlers below
    """
    Get list of workers with filtering and pagination.
    
    Args:
        status: Filter by worker status
        capability: Filter by capability
        hostname: Filter by hostname  
        limit: Maximum number of workers to return
        offset: Number of workers to skip
        sort_by: Sort field
        sort_order: Sort order
        current_user: Current authenticated user (optional)
        worker_service: Worker service instance
        
    Returns:
        List of workers matching criteria
        
    Raises:
        HTTPException: If query fails
    """
    try:
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if capability:
            filters["capability"] = capability
        if hostname:
            filters["hostname"] = hostname
        
        # Get workers from service
        workers, total_count = worker_service.get_workers(
            filters=filters,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Convert to response models
        worker_responses = [WorkerResponse.from_orm(worker) for worker in workers]
        
        return WorkerListResponse(
            workers=worker_responses,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch workers: {str(e)}"
        )


@router.post(
    "/register",
    response_model=WorkerRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register worker",
    description="Register a new worker or update existing worker configuration"
)
async def register_worker(
    worker_data: WorkerRegister,
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Register a new worker.
    
    Args:
        worker_data: Worker registration data
        worker_service: Worker service instance
        
    Returns:
        Worker registration response
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        worker = worker_service.register_worker(
            worker_id=worker_data.worker_id,
            capabilities=worker_data.capabilities,
            api_key=worker_data.api_key,
            version=worker_data.version,
            hostname=worker_data.hostname,
            ip_address=worker_data.ip_address,
            port=worker_data.port,
            max_concurrent_tasks=worker_data.max_concurrent_tasks,
            heartbeat_interval=worker_data.heartbeat_interval
        )
        
        return WorkerRegistrationResponse(
            worker_id=worker.id,
            status="registered",
            message="Worker registered successfully",
            worker=WorkerResponse.from_orm(worker)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register worker: {str(e)}"
        )


@router.post(
    "/heartbeat",
    response_model=Dict[str, Any],
    summary="Worker heartbeat",
    description="Update worker heartbeat and status information"
)
async def worker_heartbeat(
    heartbeat_data: WorkerHeartbeat,
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Update worker heartbeat.
    
    Args:
        heartbeat_data: Worker heartbeat data
        worker_service: Worker service instance
        
    Returns:
        Heartbeat acknowledgment
        
    Raises:
        HTTPException: If heartbeat update fails
    """
    try:
        success = worker_service.update_heartbeat(
            worker_id=heartbeat_data.worker_id,
            status=heartbeat_data.status,
            current_task_id=heartbeat_data.current_task_id,
            memory_usage=heartbeat_data.memory_usage,
            cpu_usage=heartbeat_data.cpu_usage,
            disk_usage=heartbeat_data.disk_usage,
            tasks_processed=heartbeat_data.tasks_processed,
            tasks_failed=heartbeat_data.tasks_failed,
            uptime_seconds=heartbeat_data.uptime_seconds
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker not found"
            )
        
        return {
            "status": "acknowledged",
            "timestamp": worker_service._get_current_timestamp(),
            "message": "Heartbeat received successfully"
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update heartbeat: {str(e)}"
        )


@router.get(
    "/{worker_id}",
    response_model=WorkerResponse,
    summary="Get worker",
    description="Get a specific worker by ID"
)
async def get_worker(
    worker_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Get specific worker by ID.
    
    Args:
        worker_id: Worker ID
        current_user: Current authenticated user (optional)
        worker_service: Worker service instance
        
    Returns:
        Worker information
        
    Raises:
        HTTPException: If worker not found
    """
    try:
        worker = worker_service.get_worker_by_id(worker_id)
        
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker not found"
            )
        
        return WorkerResponse.from_orm(worker)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch worker: {str(e)}"
        )


@router.get(
    "/stats/summary",
    response_model=WorkerStats,
    summary="Get worker statistics",
    description="Get aggregated worker statistics"
)
async def get_worker_stats(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Get worker statistics summary.
    
    Args:
        current_user: Current authenticated user (optional)
        worker_service: Worker service instance
        
    Returns:
        Worker statistics
        
    Raises:
        HTTPException: If stats retrieval fails
    """
    try:
        stats = worker_service.get_worker_statistics()
        
        return WorkerStats(
            total_workers=stats["total_workers"],
            active_workers=stats["active_workers"],
            idle_workers=stats["idle_workers"],
            offline_workers=stats["offline_workers"],
            error_workers=stats["error_workers"],
            avg_cpu_usage=stats["avg_cpu_usage"],
            avg_memory_usage=stats["avg_memory_usage"],
            total_tasks_processed=stats["total_tasks_processed"],
            total_tasks_failed=stats["total_tasks_failed"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch worker stats: {str(e)}"
        )


@router.delete(
    "/{worker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister worker",
    description="Unregister a worker (admin only)"
)
async def unregister_worker(
    worker_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Unregister a worker (admin only).
    
    Args:
        worker_id: Worker ID
        current_user: Current authenticated user
        worker_service: Worker service instance
        
    Raises:
        HTTPException: If worker not found or access denied
    """
    # Only admin users can unregister workers
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        success = worker_service.unregister_worker(worker_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister worker: {str(e)}"
        )