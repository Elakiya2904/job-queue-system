"""
Production-grade Worker Service Layer

Handles worker registration, heartbeat management, and worker lifecycle
with proper concurrency control and health monitoring.
"""

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from contextlib import contextmanager

from ..models import Worker, TaskAttempt
from ..db.base import SessionLocal

logger = logging.getLogger(__name__)


class WorkerService:
    """
    Production-grade worker management service.
    
    Handles worker registration, heartbeat tracking, and health monitoring
    with proper database transactions and concurrency control.
    """
    
    # Worker health thresholds
    HEARTBEAT_TIMEOUT_MULTIPLIER = 2.5  # Consider offline after 2.5x interval
    HEARTBEAT_GRACE_PERIOD = 30  # Additional grace period in seconds
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize service with optional database session."""
        self._db_session = db_session
    
    @contextmanager
    def get_session(self):
        """Get database session with proper cleanup."""
        if self._db_session:
            yield self._db_session
        else:
            session = SessionLocal()
            try:
                yield session
            finally:
                session.close()
    
    def register_worker(
        self,
        worker_id: str,
        capabilities: List[str],
        api_key: str,
        version: Optional[str] = None,
        hostname: Optional[str] = None,
        ip_address: Optional[str] = None,
        port: Optional[int] = None,
        max_concurrent_tasks: int = 1,
        heartbeat_interval: int = 30
    ) -> Worker:
        """
        Register a new worker or update existing worker configuration.
        
        Args:
            worker_id: Unique worker identifier
            capabilities: List of task types this worker can handle
            api_key: Worker API key for authentication
            version: Worker version string
            hostname: Worker hostname
            ip_address: Worker IP address
            port: Worker port number
            max_concurrent_tasks: Maximum concurrent tasks worker can handle
            heartbeat_interval: Heartbeat interval in seconds
            
        Returns:
            Worker instance
            
        Raises:
            ValueError: Invalid parameters
        """
        # Validation
        if not worker_id or not worker_id.strip():
            raise ValueError("worker_id is required")
        
        if not capabilities or len(capabilities) == 0:
            raise ValueError("capabilities list cannot be empty")
        
        if not api_key or len(api_key) < 32:
            raise ValueError("api_key must be at least 32 characters")
        
        if max_concurrent_tasks <= 0:
            raise ValueError("max_concurrent_tasks must be positive")
        
        if heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval must be positive")
        
        # Hash API key for storage
        api_key_hash = self._hash_api_key(api_key)
        
        with self.get_session() as session:
            try:
                # Check if worker already exists
                existing_worker = session.query(Worker).filter(
                    Worker.id == worker_id
                ).first()
                
                now = datetime.now(timezone.utc)
                
                if existing_worker:
                    # Update existing worker
                    existing_worker.capabilities = capabilities
                    existing_worker.api_key_hash = api_key_hash
                    existing_worker.version = version
                    existing_worker.hostname = hostname
                    existing_worker.ip_address = ip_address
                    existing_worker.port = port
                    existing_worker.max_concurrent_tasks = max_concurrent_tasks
                    existing_worker.heartbeat_interval = heartbeat_interval
                    existing_worker.status = "idle"
                    existing_worker.last_heartbeat = now
                    existing_worker.last_seen_at = now
                    existing_worker.updated_at = now
                    
                    session.commit()
                    session.refresh(existing_worker)
                    
                    logger.info(f"Updated worker registration: {worker_id}")
                    return existing_worker
                else:
                    # Create new worker
                    worker = Worker.create_worker(
                        worker_id=worker_id,
                        capabilities=capabilities,
                        version=version,
                        hostname=hostname,
                        ip_address=ip_address,
                        port=port,
                        api_key_hash=api_key_hash
                    )
                    
                    worker.max_concurrent_tasks = max_concurrent_tasks
                    worker.heartbeat_interval = heartbeat_interval
                    
                    session.add(worker)
                    session.commit()
                    session.refresh(worker)
                    
                    logger.info(f"Registered new worker: {worker_id} with capabilities {capabilities}")
                    return worker
                    
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to register worker {worker_id}: {e}")
                raise
    
    def authenticate_worker(self, worker_id: str, api_key: str) -> bool:
        """
        Authenticate worker using API key.
        
        Args:
            worker_id: Worker identifier
            api_key: Worker API key
            
        Returns:
            True if authentication successful, False otherwise
        """
        api_key_hash = self._hash_api_key(api_key)
        
        with self.get_session() as session:
            try:
                worker = session.query(Worker).filter(
                    and_(
                        Worker.id == worker_id,
                        Worker.api_key_hash == api_key_hash
                    )
                ).first()
                
                return worker is not None
                
            except Exception as e:
                logger.error(f"Failed to authenticate worker {worker_id}: {e}")
                return False
    
    def update_heartbeat(
        self,
        worker_id: str,
        status: str = "active",
        current_task_id: Optional[str] = None,
        memory_usage: Optional[float] = None,
        cpu_usage: Optional[float] = None,
        disk_usage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update worker heartbeat and status information.
        
        Args:
            worker_id: Worker identifier
            status: Worker status (active, idle, error)
            current_task_id: Currently processing task ID
            memory_usage: Memory usage percentage
            cpu_usage: CPU usage percentage
            disk_usage: Disk usage percentage
            
        Returns:
            Dict with heartbeat acknowledgment and next heartbeat interval
        """
        if status not in ("active", "idle", "error"):
            raise ValueError("status must be 'active', 'idle', or 'error'")
        
        with self.get_session() as session:
            try:
                worker = session.query(Worker).filter(
                    Worker.id == worker_id
                ).with_for_update().first()
                
                if not worker:
                    logger.warning(f"Worker {worker_id} not found for heartbeat update")
                    return {"error": "Worker not found"}
                
                # Update worker information
                worker.heartbeat(
                    status=status,
                    current_task_id=current_task_id,
                    memory_usage=memory_usage,
                    cpu_usage=cpu_usage,
                    disk_usage=disk_usage
                )
                
                session.commit()
                
                logger.debug(f"Updated heartbeat for worker {worker_id}: {status}")
                
                return {
                    "acknowledged": True,
                    "next_heartbeat_in": worker.heartbeat_interval,
                    "status": worker.status
                }
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to update heartbeat for worker {worker_id}: {e}")
                raise
    
    def start_task(self, worker_id: str, task_id: str) -> bool:
        """
        Mark worker as starting a task.
        
        Args:
            worker_id: Worker identifier
            task_id: Task being started
            
        Returns:
            True if updated successfully, False if worker not found
        """
        with self.get_session() as session:
            try:
                worker = session.query(Worker).filter(
                    Worker.id == worker_id
                ).with_for_update().first()
                
                if not worker:
                    return False
                
                worker.start_task(task_id)
                session.commit()
                
                logger.debug(f"Worker {worker_id} started task {task_id}")
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to mark task start for worker {worker_id}: {e}")
                raise
    
    def finish_task(
        self,
        worker_id: str,
        success: bool,
        processing_time_ms: Optional[int] = None
    ) -> bool:
        """
        Mark worker as finished with current task.
        
        Args:
            worker_id: Worker identifier
            success: Whether task completed successfully
            processing_time_ms: Task processing time
            
        Returns:
            True if updated successfully, False if worker not found
        """
        with self.get_session() as session:
            try:
                worker = session.query(Worker).filter(
                    Worker.id == worker_id
                ).with_for_update().first()
                
                if not worker:
                    return False
                
                worker.finish_task(success, processing_time_ms)
                session.commit()
                
                logger.debug(f"Worker {worker_id} finished task (success: {success})")
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to mark task finish for worker {worker_id}: {e}")
                raise
    
    def get_worker_status(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current worker status and information.
        
        Args:
            worker_id: Worker identifier
            
        Returns:
            Worker information dict or None if not found
        """
        with self.get_session() as session:
            try:
                worker = session.query(Worker).filter(
                    Worker.id == worker_id
                ).first()
                
                if not worker:
                    return None
                
                return worker.to_dict()
                
            except Exception as e:
                logger.error(f"Failed to get worker status for {worker_id}: {e}")
                raise
    
    def get_online_workers(self) -> List[Dict[str, Any]]:
        """
        Get list of currently online workers.
        
        Returns:
            List of online worker information dicts
        """
        with self.get_session() as session:
            try:
                now = datetime.now(timezone.utc)
                
                # Calculate cutoff time for considering workers offline
                workers = session.query(Worker).all()
                
                online_workers = []
                for worker in workers:
                    # Check if worker is considered online
                    max_silence = (worker.heartbeat_interval * self.HEARTBEAT_TIMEOUT_MULTIPLIER) + self.HEARTBEAT_GRACE_PERIOD
                    silence_duration = (now - worker.last_heartbeat).total_seconds()
                    
                    if silence_duration <= max_silence:
                        worker_data = worker.to_dict()
                        worker_data["silence_duration"] = silence_duration
                        online_workers.append(worker_data)
                
                return online_workers
                
            except Exception as e:
                logger.error(f"Failed to get online workers: {e}")
                raise
    
    def mark_workers_offline(self, max_silence_seconds: Optional[int] = None) -> int:
        """
        Mark workers as offline based on missed heartbeats.
        
        Args:
            max_silence_seconds: Maximum silence before marking offline
                               (defaults to calculated threshold)
            
        Returns:
            Number of workers marked offline
        """
        with self.get_session() as session:
            try:
                now = datetime.now(timezone.utc)
                marked_offline = 0
                
                # Get all workers that might need status updates
                workers = session.query(Worker).filter(
                    Worker.status.in_(["active", "idle"])
                ).with_for_update().all()
                
                for worker in workers:
                    # Calculate timeout for this specific worker
                    if max_silence_seconds is None:
                        worker_timeout = (worker.heartbeat_interval * self.HEARTBEAT_TIMEOUT_MULTIPLIER) + self.HEARTBEAT_GRACE_PERIOD
                    else:
                        worker_timeout = max_silence_seconds
                    
                    silence_duration = (now - worker.last_heartbeat).total_seconds()
                    
                    if silence_duration > worker_timeout:
                        worker.status = "offline"
                        worker.current_task_id = None  # Clear any assigned task
                        worker.updated_at = now
                        marked_offline += 1
                        
                        logger.warning(f"Marked worker {worker.id} offline (silent for {silence_duration:.0f}s)")
                
                session.commit()
                
                if marked_offline > 0:
                    logger.info(f"Marked {marked_offline} workers offline")
                
                return marked_offline
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to mark workers offline: {e}")
                raise
    
    def get_worker_metrics(self) -> Dict[str, Any]:
        """Get worker metrics for monitoring."""
        with self.get_session() as session:
            try:
                now = datetime.now(timezone.utc)
                
                # Get worker counts by status
                status_counts = dict(
                    session.query(Worker.status, func.count(Worker.id))
                    .group_by(Worker.status)
                    .all()
                )
                
                # Get performance metrics
                performance_metrics = (
                    session.query(
                        func.avg(Worker.tasks_processed).label("avg_tasks_processed"),
                        func.avg(Worker.success_rate).label("avg_success_rate"),
                        func.avg(Worker.memory_usage).label("avg_memory_usage"),
                        func.avg(Worker.cpu_usage).label("avg_cpu_usage")
                    )
                    .filter(Worker.status.in_(["active", "idle"]))
                    .first()
                )
                
                # Calculate online workers
                online_workers = self.get_online_workers()
                online_count = len(online_workers)
                
                # Get capability distribution  
                capability_counts = {}
                workers = session.query(Worker).all()
                for worker in workers:
                    if worker.capabilities:
                        for capability in worker.capabilities:
                            capability_counts[capability] = capability_counts.get(capability, 0) + 1
                
                return {
                    "timestamp": now.isoformat(),
                    "total_workers": sum(status_counts.values()),
                    "online_workers": online_count,
                    "active_workers": status_counts.get("active", 0),
                    "idle_workers": status_counts.get("idle", 0),
                    "offline_workers": status_counts.get("offline", 0),
                    "error_workers": status_counts.get("error", 0),
                    "avg_tasks_processed": float(performance_metrics.avg_tasks_processed or 0),
                    "avg_success_rate": float(performance_metrics.avg_success_rate or 0),
                    "avg_memory_usage": float(performance_metrics.avg_memory_usage or 0),
                    "avg_cpu_usage": float(performance_metrics.avg_cpu_usage or 0),
                    "capability_distribution": capability_counts
                }
                
            except Exception as e:
                logger.error(f"Failed to get worker metrics: {e}")
                raise
    
    def get_workers(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "last_heartbeat",
        sort_order: str = "desc"
    ):
        """
        Get list of workers with optional filtering and pagination.

        Returns:
            Tuple of (list of Worker ORM objects, total count)
        """
        with self.get_session() as session:
            try:
                query = session.query(Worker)

                if filters:
                    if "status" in filters:
                        query = query.filter(Worker.status == filters["status"])
                    if "hostname" in filters:
                        query = query.filter(Worker.hostname == filters["hostname"])
                    if "capability" in filters:
                        # JSON contains check — works for SQLite JSON columns
                        query = query.filter(
                            Worker.capabilities.contains(filters["capability"])
                        )

                total = query.count()

                sort_col = getattr(Worker, sort_by, Worker.last_heartbeat)
                if sort_order == "asc":
                    query = query.order_by(sort_col.asc())
                else:
                    query = query.order_by(sort_col.desc())

                workers = query.offset(offset).limit(limit).all()
                return workers, total

            except Exception as e:
                logger.error(f"Failed to get workers: {e}")
                raise

    def get_worker_by_id(self, worker_id: str) -> Optional[Worker]:
        """Get a specific worker by ID."""
        with self.get_session() as session:
            try:
                return session.query(Worker).filter(Worker.id == worker_id).first()
            except Exception as e:
                logger.error(f"Failed to get worker {worker_id}: {e}")
                raise

    def get_worker_statistics(self) -> Dict[str, Any]:
        """Get aggregated worker statistics."""
        with self.get_session() as session:
            try:
                status_counts = dict(
                    session.query(Worker.status, func.count(Worker.id))
                    .group_by(Worker.status)
                    .all()
                )
                perf = session.query(
                    func.avg(Worker.cpu_usage).label("avg_cpu"),
                    func.avg(Worker.memory_usage).label("avg_mem"),
                    func.sum(Worker.tasks_processed).label("total_processed"),
                    func.sum(Worker.tasks_failed).label("total_failed"),
                ).first()
                return {
                    "total_workers": sum(status_counts.values()),
                    "active_workers": status_counts.get("active", 0),
                    "idle_workers": status_counts.get("idle", 0),
                    "offline_workers": status_counts.get("offline", 0),
                    "error_workers": status_counts.get("error", 0),
                    "avg_cpu_usage": float(perf.avg_cpu or 0),
                    "avg_memory_usage": float(perf.avg_mem or 0),
                    "total_tasks_processed": int(perf.total_processed or 0),
                    "total_tasks_failed": int(perf.total_failed or 0),
                }
            except Exception as e:
                logger.error(f"Failed to get worker statistics: {e}")
                raise

    def unregister_worker(self, worker_id: str) -> bool:
        """Delete a worker record. Returns True if deleted, False if not found."""
        with self.get_session() as session:
            try:
                worker = session.query(Worker).filter(Worker.id == worker_id).first()
                if not worker:
                    return False
                session.delete(worker)
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to unregister worker {worker_id}: {e}")
                raise

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def cleanup_inactive_workers(self, max_offline_hours: int = 24) -> int:
        """
        Remove workers that have been offline for an extended period.
        
        Args:
            max_offline_hours: Hours offline before cleanup
            
        Returns:
            Number of workers removed
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_offline_hours)
        
        with self.get_session() as session:
            try:
                # Find workers offline for extended period
                inactive_workers = session.query(Worker).filter(
                    and_(
                        Worker.status == "offline",
                        Worker.last_seen_at < cutoff_time
                    )
                ).all()
                
                count = len(inactive_workers)
                
                for worker in inactive_workers:
                    logger.info(f"Removing inactive worker: {worker.id} (offline since {worker.last_seen_at})")
                    session.delete(worker)
                
                session.commit()
                
                if count > 0:
                    logger.info(f"Cleaned up {count} inactive workers")
                
                return count
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to cleanup inactive workers: {e}")
                raise