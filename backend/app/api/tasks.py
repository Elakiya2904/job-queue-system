"""
Task management API routes.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text
from ..dependencies import get_current_user, get_db
from ..services.task_service import TaskService
from ..models.task import Task
from ..models.worker import Worker
from ..schemas.task import (
    TaskCreate, 
    TaskResponse, 
    TaskListQuery, 
    TaskListResponse,
    TaskUpdate,
    TaskActionRequest,
    TaskClaimRequest,
    TaskClaimResponse,
    TaskProgressUpdate,
    TaskCompleteRequest,
    TaskFailRequest,
    WorkerTaskListQuery,
    WorkerTaskListResponse,
    DeadLetterTaskResponse,
    DeadLetterQueueListResponse,
    RetryDeadLetterTaskRequest
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Create a new task in the queue system"
)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new task in the queue system.
    
    Args:
        task_data: Task creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created task information
        
    Raises:
        HTTPException: If task creation fails
    """
    try:
        # Initialize task service
        task_service = TaskService(db_session=db)
        
        # Create task using real service
        task = task_service.create_task(
            task_type=task_data.task_type,
            payload=task_data.payload,
            priority=task_data.priority,
            scheduled_for=task_data.scheduled_for,
            timeout=task_data.timeout,
            max_retries=task_data.max_retries,
            correlation_id=task_data.correlation_id,
            created_by=current_user["id"]
        )
        
        # Convert to response schema
        return TaskResponse(
            id=str(task.id),
            type=task.type,
            status=task.status,  # Already a string
            priority=task.priority,
            payload=task.payload,
            result=task.result,
            scheduled_for=task.scheduled_for,
            timeout=task.timeout,
            max_retries=task.max_retries,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            failed_at=task.failed_at,
            locked_by=task.locked_by,
            locked_at=task.locked_at,
            created_by=str(task.created_by),
            correlation_id=task.correlation_id,
            error_message=None  # Not available in the model yet
        )
        
    except Exception as e:
        logger.error(f"Failed to create task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="List tasks",
    description="Get a list of tasks with optional filtering and pagination"
)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    priority: Optional[int] = Query(None, ge=1, le=4, description="Filter by priority"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    locked_by: Optional[str] = Query(None, description="Filter by worker that locked the task"),
    completed_by: Optional[str] = Query(None, description="Filter by worker that completed the task"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get list of tasks with filtering and pagination.
    
    Args:
        status: Filter by task status
        task_type: Filter by task type  
        priority: Filter by priority
        created_by: Filter by creator (admins can see all, users see only their own)
        correlation_id: Filter by correlation ID
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip
        sort_by: Sort field
        sort_order: Sort order
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of tasks matching criteria
        
    Raises:
        HTTPException: If query fails
    """
    try:
        # Direct database query for listing tasks
        query = db.query(Task)

        # Role-based task visibility
        role = current_user.get("role")
        if role == "user":
            # Regular users only see queued tasks
            query = query.filter(Task.status == "queued")
        elif role == "worker":
            # Workers see queued tasks OR their own in-progress tasks
            worker_id = current_user.get("id")
            query = query.filter(
                or_(
                    Task.status == "queued",
                    and_(Task.status == "in_progress", Task.locked_by == worker_id)
                )
            )
        elif status:
            query = query.filter(Task.status == status)

        if task_type:
            query = query.filter(Task.type == task_type)
        if priority:
            query = query.filter(Task.priority == priority)
        if correlation_id:
            query = query.filter(Task.correlation_id == correlation_id)
        
        # Allow all users to see all tasks (removed role restriction)
        # Admin users can optionally filter by creator
        if created_by:
            query = query.filter(Task.created_by == created_by)
        if locked_by:
            query = query.filter(Task.locked_by == locked_by)
        if completed_by:
            query = query.filter(Task.completed_by == completed_by)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        if sort_by == "created_at":
            if sort_order.lower() == "desc":
                query = query.order_by(Task.created_at.desc())
            else:
                query = query.order_by(Task.created_at.asc())
        elif sort_by == "updated_at":
            if sort_order.lower() == "desc":
                query = query.order_by(Task.updated_at.desc())
            else:
                query = query.order_by(Task.updated_at.asc())
        elif sort_by == "priority":
            if sort_order.lower() == "desc":
                query = query.order_by(Task.priority.desc())
            else:
                query = query.order_by(Task.priority.asc())
        
        # Apply pagination
        tasks = query.offset(offset).limit(limit).all()
        
        # Convert to response models
        task_responses = []
        for task in tasks:
            task_responses.append(TaskResponse(
                id=str(task.id),
                type=task.type,
                status=task.status,  # Already a string
                priority=task.priority,
                payload=task.payload,
                result=task.result,
                scheduled_for=task.scheduled_for,
                timeout=task.timeout,
                max_retries=task.max_retries,
                retry_count=task.retry_count,
                created_at=task.created_at,
                updated_at=task.updated_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                failed_at=task.failed_at,
                locked_by=task.locked_by,
                locked_at=task.locked_at,
                completed_by=task.completed_by,
                created_by=str(task.created_by),
                correlation_id=task.correlation_id,
                error_message=task.error_message
            ))
        
        return TaskListResponse(
            tasks=task_responses,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total_count
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch tasks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tasks: {str(e)}"
        )


# Dead Letter Queue Management

@router.get(
    "/dead-letter-queue",
    response_model=DeadLetterQueueListResponse,
    summary="Get dead letter queue tasks",
    description="Get list of tasks in the dead letter queue"
)
async def list_dead_letter_tasks(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get list of tasks in the dead letter queue.
    """
    try:
        # Only admins can view dead letter queue
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view the dead letter queue"
            )
        
        query = db.query(Task).filter(Task.status == "dead_letter")
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        tasks = query.order_by(Task.failed_at.desc()).offset(offset).limit(limit).all()
        
        dead_letter_tasks = []
        for task in tasks:
            error_data = task.result or {}
            
            dead_letter_tasks.append(DeadLetterTaskResponse(
                task_id=task.id,
                original_task=TaskResponse.model_validate(task),
                failure_count=task.retry_count,
                last_error=error_data.get("error_message"),
                moved_to_dlq_at=task.failed_at or task.updated_at
            ))
        
        return DeadLetterQueueListResponse(
            tasks=dead_letter_tasks,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list dead letter tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list dead letter tasks: {str(e)}"
        )


@router.post(
    "/{task_id}/retry-from-dlq",
    response_model=TaskResponse,
    summary="Retry task from dead letter queue",
    description="Move a task from dead letter queue back to processing queue"
)
async def retry_dead_letter_task(
    task_id: str,
    retry_request: RetryDeadLetterTaskRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retry a task from the dead letter queue.
    """
    try:
        # Only admins can retry dead letter tasks
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can retry dead letter tasks"
            )
        
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.status != "dead_letter":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is not in dead letter queue"
            )
        
        # Reset task for retry
        now = datetime.now(timezone.utc)
        task.status = "queued"
        task.updated_at = now
        task.failed_at = None
        task.locked_by = None
        task.locked_at = None
        task.lock_timeout = None
        task.started_at = None
        task.completed_at = None
        
        if retry_request.reset_retry_count:
            task.retry_count = 0
        
        if retry_request.new_priority:
            task.priority = retry_request.new_priority
        
        # Clear error data
        task.result = {}
        task.error_message = None
        
        db.commit()
        
        return TaskResponse.model_validate(task)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to retry dead letter task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry dead letter task: {str(e)}"
        )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task",
    description="Get a specific task by ID"
)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get specific task by ID.
    
    Args:
        task_id: Task ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Task information
        
    Raises:
        HTTPException: If task not found or access denied
    """
    try:
        # Query task from database
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Allow all users to see tasks (removed role restriction)
        
        # Convert to response model
        return TaskResponse(
            id=task.id,
            type=task.type,
            status=task.status,
            payload=task.payload,
            priority=task.priority,
            created_by=task.created_by,
            created_at=task.created_at,
            updated_at=task.updated_at,
            scheduled_for=task.scheduled_for,
            lock_timeout=task.lock_timeout,
            timeout=task.timeout,
            max_retries=task.max_retries,
            retry_count=task.retry_count,
            correlation_id=task.correlation_id,
            progress=task.progress,
            result=task.result,
            error_message=task.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch task: {str(e)}"
        )


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description="Update a specific task"
)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update specific task.
    
    Args:
        task_id: Task ID
        task_update: Task update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated task information
        
    Raises:
        HTTPException: If task not found or access denied
    """
    try:
        # Query task from database
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Only admin or task creator can update
        if current_user.get("role") != "admin" and task.created_by != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update task data
        if task_update.status is not None:
            task.status = task_update.status
        if task_update.priority is not None:
            task.priority = task_update.priority
        if task_update.scheduled_for is not None:
            task.scheduled_for = task_update.scheduled_for
        if task_update.max_retries is not None:
            task.max_retries = task_update.max_retries
        
        task.updated_at = datetime.now(timezone.utc)
        
        # Commit changes
        db.commit()
        db.refresh(task)
        
        # Convert to response model
        return TaskResponse(
            id=task.id,
            type=task.type,
            status=task.status,
            payload=task.payload,
            priority=task.priority,
            created_by=task.created_by,
            created_at=task.created_at,
            updated_at=task.updated_at,
            scheduled_for=task.scheduled_for,
            lock_timeout=task.lock_timeout,
            timeout=task.timeout,
            max_retries=task.max_retries,
            retry_count=task.retry_count,
            correlation_id=task.correlation_id,
            progress=task.progress,
            result=task.result,
            error_message=task.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}"
        )


@router.post(
    "/{task_id}/actions",
    response_model=TaskResponse,
    summary="Perform task action",
    description="Perform an action on a specific task (cancel, retry, reschedule)"
)
async def perform_task_action(
    task_id: str,
    action_request: TaskActionRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Perform action on specific task.
    
    Args:
        task_id: Task ID
        action_request: Action request data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated task information
        
    Raises:
        HTTPException: If task not found, action invalid, or access denied
    """
    try:
        # Query task from database
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Only admin or task creator can perform actions
        if current_user.get("role") != "admin" and task.created_by != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Perform action based on type
        if action_request.action == "cancel":
            task.status = "cancelled"
        elif action_request.action == "reset":
            # Reset stuck in_progress task back to queued
            task.status = "queued"
            task.locked_by = None
            task.locked_at = None
            task.lock_timeout = None
            task.started_at = None
            task.progress = None
            task.error_message = None
        elif action_request.action == "retry":
            task.status = "queued"
            task.retry_count += 1
            task.locked_by = None
            task.locked_at = None
            task.lock_timeout = None
        elif action_request.action == "reschedule":
            if not action_request.scheduled_for:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="scheduled_for is required for reschedule action"
                )
            task.scheduled_for = action_request.scheduled_for
            task.status = "queued"
            task.lock_timeout = None  # Clear any existing lock
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action_request.action}"
            )
        
        task.updated_at = datetime.now(timezone.utc)
        
        # Commit changes
        db.commit()
        db.refresh(task)
        
        # Convert to response model
        return TaskResponse(
            id=task.id,
            type=task.type,
            status=task.status,
            payload=task.payload,
            priority=task.priority,
            created_by=task.created_by,
            created_at=task.created_at,
            updated_at=task.updated_at,
            scheduled_for=task.scheduled_for,
            lock_timeout=task.lock_timeout,
            timeout=task.timeout,
            max_retries=task.max_retries,
            retry_count=task.retry_count,
            correlation_id=task.correlation_id,
            progress=task.progress,
            result=task.result,
            error_message=task.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform action: {str(e)}"
        )


# Worker Task Management Endpoints

@router.get(
    "/worker/available",
    response_model=WorkerTaskListResponse,
    summary="Get available tasks for worker",
    description="Get list of tasks available for a worker to claim"
)
async def get_worker_tasks(
    task_types: Optional[str] = Query(None, description="Comma-separated task types worker can handle"),
    priority_min: Optional[int] = Query(None, ge=1, le=4, description="Minimum priority level"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of tasks to return"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get list of available tasks for workers to claim.
    
    Returns ONLY tasks with status 'queued' that are not locked or have expired locks.
    Workers should never see tasks in any other status.
    """
    try:
        # CRITICAL: Only show queued tasks available for claiming
        query = db.query(Task).filter(
            Task.status == "queued"
        )
        
        # Only filter by scheduled_for if it's set (not None)
        now = datetime.now(timezone.utc)
        query = query.filter(
            or_(
                Task.scheduled_for.is_(None),
                Task.scheduled_for <= now
            )
        )
        
        # Filter by task types if specified
        if task_types:
            type_list = [t.strip() for t in task_types.split(",")]
            query = query.filter(Task.type.in_(type_list))
        
        # Filter by minimum priority
        if priority_min:
            query = query.filter(Task.priority >= priority_min)
        
        # Exclude locked tasks (or those with non-expired locks)
        # Use database-agnostic date math by detecting the dialect
        dialect_name = db.bind.dialect.name.lower()
        
        if dialect_name == "sqlite":
            # SQLite: compare unix timestamps
            lock_check = text(
                "CAST(STRFTIME('%s', :lock_now) AS INTEGER) >= "
                "CAST(STRFTIME('%s', tasks.locked_at) AS INTEGER) + tasks.lock_timeout"
            ).bindparams(lock_now=now)
        else:
            # PostgreSQL and other databases: use EXTRACT(EPOCH FROM ...)
            lock_check = text(
                "EXTRACT(EPOCH FROM :lock_now) >= EXTRACT(EPOCH FROM tasks.locked_at) + tasks.lock_timeout"
            ).bindparams(lock_now=now)
        
        query = query.filter(
            or_(
                Task.locked_at.is_(None),
                and_(
                    Task.locked_at.isnot(None),
                    Task.lock_timeout.isnot(None),
                    lock_check
                )
            )
        )
        
        # Order by priority (highest first), then creation time
        query = query.order_by(Task.priority.desc(), Task.created_at.asc())
        
        # Get total available count
        total_available = query.count()
        
        # Apply limit
        tasks = query.limit(limit).all()
        
        return WorkerTaskListResponse(
            tasks=[TaskResponse.model_validate(task) for task in tasks],
            total_available=total_available
        )
        
    except Exception as e:
        logger.error(f"Failed to get worker tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available tasks: {str(e)}"
        )


@router.post(
    "/{task_id}/claim",
    response_model=TaskClaimResponse,
    summary="Claim a task",
    description="Claim a task for processing by a worker"
)
async def claim_task(
    task_id: str,
    claim_request: TaskClaimRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Claim a task for processing.
    
    Sets the task status to 'in_progress' and locks it to prevent other workers from claiming it.
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check if task can be claimed
        if task.status != "queued":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task cannot be claimed (current status: {task.status})"
            )
        
        # Check if task is already locked by another worker
        if task.locked_by and task.locked_by != claim_request.worker_id:
            if not task.lock_expired:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Task is already locked by worker {task.locked_by}"
                )
        
        # Only allow pre-registered workers to claim tasks — check BEFORE modifying the task
        worker = db.query(Worker).filter(Worker.id == claim_request.worker_id).first()
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Worker '{claim_request.worker_id}' is not registered. Please ask an admin to register you in Worker Management."
            )
        
        # Claim the task
        now = datetime.now(timezone.utc)
        task.status = "in_progress" 
        task.locked_by = claim_request.worker_id
        task.locked_at = now
        task.lock_timeout = claim_request.lock_timeout
        task.started_at = now
        task.updated_at = now
        worker.status = "active"
        worker.current_task_id = task.id
        worker.last_heartbeat = now
        worker.last_seen_at = now
        worker.updated_at = now
        
        db.commit()
        
        lock_expires_at = now + timedelta(seconds=claim_request.lock_timeout)
        
        return TaskClaimResponse(
            task_id=task.id,
            task=TaskResponse.model_validate(task),
            lock_expires_at=lock_expires_at
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to claim task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to claim task: {str(e)}"
        )


@router.put(
    "/{task_id}/progress",
    response_model=TaskResponse,
    summary="Update task progress",
    description="Update the progress of a task being processed by a worker"
)
async def update_task_progress(
    task_id: str,
    progress_update: TaskProgressUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update task progress information.
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify worker owns this task
        if task.locked_by != progress_update.worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Task is not claimed by this worker"
            )
        
        # Update progress information (stored in result field for now)
        progress_data = task.result or {}
        if progress_update.progress_percentage is not None:
            progress_data["progress_percentage"] = progress_update.progress_percentage
        if progress_update.status_message:
            progress_data["status_message"] = progress_update.status_message
        if progress_update.intermediate_result:
            progress_data["intermediate_result"] = progress_update.intermediate_result
        
        task.result = progress_data
        task.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return TaskResponse.model_validate(task)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update task progress {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task progress: {str(e)}"
        )


@router.post(
    "/{task_id}/complete",
    response_model=TaskResponse,
    summary="Complete a task",
    description="Mark a task as completed by a worker"
)
async def complete_task(
    task_id: str,
    complete_request: TaskCompleteRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Mark a task as completed.
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify worker owns this task
        if task.locked_by != complete_request.worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Task is not claimed by this worker"
            )
        
        # Complete the task
        now = datetime.now(timezone.utc)
        task.completed_by = task.locked_by  # preserve who did the work
        task.status = "completed"
        task.completed_at = now
        task.updated_at = now
        task.result = complete_request.result or {}
        
        # Clear lock information
        task.locked_by = None
        task.locked_at = None
        task.lock_timeout = None
        
        db.commit()
        
        return TaskResponse.model_validate(task)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to complete task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete task: {str(e)}"
        )


@router.post(
    "/{task_id}/fail",
    response_model=TaskResponse,
    summary="Mark task as failed",
    description="Mark a task as failed by a worker with retry logic"
)
async def fail_task(
    task_id: str,
    fail_request: TaskFailRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Mark a task as failed with retry logic.
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify worker owns this task
        if task.locked_by != fail_request.worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Task is not claimed by this worker"
            )
        
        # Increment retry count
        task.retry_count += 1
        now = datetime.now(timezone.utc)
        task.failed_at = now
        task.updated_at = now
        
        # Store error information
        error_data = {
            "error_message": fail_request.error_message,
            "error_details": fail_request.error_details or {},
            "failed_at": now.isoformat(),
            "retry_count": task.retry_count
        }
        task.result = error_data
        
        # Determine next status based on retry logic
        if fail_request.should_retry and task.retry_count < task.max_retries:
            # Task can be retried - reset to queued
            task.status = "queued"
            task.locked_by = None
            task.locked_at = None 
            task.lock_timeout = None
            task.started_at = None
        else:
            # Task has exhausted retries - move to dead letter queue
            task.status = "dead_letter"
            task.locked_by = None
            task.locked_at = None
            task.lock_timeout = None
        
        db.commit()
        
        return TaskResponse.model_validate(task)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to mark task as failed {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark task as failed: {str(e)}"
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Permanently delete a task (admin only)"
)
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Permanently delete a task from the database. Admin only."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        db.delete(task)
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )