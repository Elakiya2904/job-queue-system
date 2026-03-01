from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Boolean, Text, Index, CheckConstraint
from sqlalchemy.orm import relationship
from ..db.base import Base


class Worker(Base):
    """
    Worker model representing a worker instance in the job queue system.
    
    Status values: active, idle, offline, error
    Tracks worker capabilities, performance metrics, and heartbeat status.
    """
    __tablename__ = "workers"

    # Primary fields
    id = Column(String(50), primary_key=True, index=True)
    status = Column(String(20), nullable=False, default="offline", index=True)
    
    # Worker configuration
    capabilities = Column(JSON, nullable=False, default=lambda: [])  # List of supported task types
    version = Column(String(50), nullable=True)
    api_key_hash = Column(String(255), nullable=True, index=True)  # Hashed API key for authentication
    
    # Current state
    current_task_id = Column(String(50), nullable=True, index=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=False, 
                           default=lambda: datetime.now(timezone.utc), index=True)
    
    # Performance metrics
    tasks_processed = Column(Integer, nullable=False, default=0)
    tasks_failed = Column(Integer, nullable=False, default=0)
    tasks_completed = Column(Integer, nullable=False, default=0)
    total_processing_time_ms = Column(Integer, nullable=False, default=0)
    uptime_seconds = Column(Integer, nullable=False, default=0)
    
    # Resource usage (percentages)
    memory_usage = Column(Float, nullable=True)
    cpu_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    
    # Connection info
    hostname = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # Supports IPv6
    port = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), nullable=False, 
                         default=lambda: datetime.now(timezone.utc))
    
    # Configuration
    max_concurrent_tasks = Column(Integer, nullable=False, default=1)
    heartbeat_interval = Column(Integer, nullable=False, default=30)  # seconds
    
    # Relationships
    attempts = relationship("TaskAttempt", back_populates="worker", order_by="TaskAttempt.started_at.desc()")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'idle', 'offline', 'error')",
            name="check_worker_status"
        ),
        CheckConstraint(
            "tasks_processed >= 0",
            name="check_tasks_processed_non_negative"
        ),
        CheckConstraint(
            "tasks_failed >= 0",
            name="check_tasks_failed_non_negative"
        ),
        CheckConstraint(
            "tasks_completed >= 0",
            name="check_tasks_completed_non_negative"
        ),
        CheckConstraint(
            "total_processing_time_ms >= 0",
            name="check_total_processing_time_non_negative"
        ),
        CheckConstraint(
            "uptime_seconds >= 0",
            name="check_uptime_non_negative"
        ),
        CheckConstraint(
            "memory_usage IS NULL OR (memory_usage >= 0 AND memory_usage <= 100)",
            name="check_memory_usage_percentage"
        ),
        CheckConstraint(
            "cpu_usage IS NULL OR (cpu_usage >= 0 AND cpu_usage <= 100)",
            name="check_cpu_usage_percentage"
        ),
        CheckConstraint(
            "disk_usage IS NULL OR (disk_usage >= 0 AND disk_usage <= 100)",
            name="check_disk_usage_percentage"
        ),
        CheckConstraint(
            "max_concurrent_tasks > 0",
            name="check_max_concurrent_tasks_positive"
        ),
        CheckConstraint(
            "heartbeat_interval > 0",
            name="check_heartbeat_interval_positive"
        ),
        # Indexes for common queries
        Index('idx_worker_status_heartbeat', 'status', 'last_heartbeat'),
        Index('idx_worker_capabilities', 'capabilities'),
        Index('idx_worker_current_task', 'current_task_id'),
        Index('idx_worker_performance', 'tasks_processed', 'tasks_failed'),
        Index('idx_worker_resources', 'memory_usage', 'cpu_usage'),
    )
    
    def __repr__(self) -> str:
        return f"<Worker(id='{self.id}', status='{self.status}', capabilities={self.capabilities})>"
    
    @property
    def is_online(self) -> bool:
        """Check if worker is considered online based on heartbeat."""
        if self.status == 'offline':
            return False
        
        # Consider offline if no heartbeat within 2x heartbeat interval + 30 seconds grace
        max_silence = (self.heartbeat_interval * 2) + 30
        silence_duration = (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds()
        return silence_duration <= max_silence
    
    @property
    def is_available(self) -> bool:
        """Check if worker is available to take new tasks."""
        return (
            self.is_online and
            self.status == 'idle' and
            self.current_task_id is None
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate worker success rate."""
        if self.tasks_processed == 0:
            return 0.0
        return self.tasks_completed / self.tasks_processed
    
    @property
    def failure_rate(self) -> float:
        """Calculate worker failure rate."""
        if self.tasks_processed == 0:
            return 0.0
        return self.tasks_failed / self.tasks_processed
    
    @property
    def average_processing_time_ms(self) -> float:
        """Calculate average processing time per task."""
        if self.tasks_completed == 0:
            return 0.0
        return self.total_processing_time_ms / self.tasks_completed
    
    def heartbeat(self, 
                 status: Optional[str] = None,
                 current_task_id: Optional[str] = None,
                 memory_usage: Optional[float] = None,
                 cpu_usage: Optional[float] = None,
                 disk_usage: Optional[float] = None) -> None:
        """Update worker heartbeat and status."""
        now = datetime.now(timezone.utc)
        self.last_heartbeat = now
        self.last_seen_at = now
        self.updated_at = now
        
        if status is not None:
            self.status = status
        
        if current_task_id is not None:
            self.current_task_id = current_task_id
        
        if memory_usage is not None:
            self.memory_usage = memory_usage
        
        if cpu_usage is not None:
            self.cpu_usage = cpu_usage
        
        if disk_usage is not None:
            self.disk_usage = disk_usage
    
    def start_task(self, task_id: str) -> None:
        """Mark worker as processing a task."""
        self.status = 'active'
        self.current_task_id = task_id
        self.updated_at = datetime.now(timezone.utc)
    
    def finish_task(self, success: bool, processing_time_ms: Optional[int] = None) -> None:
        """Mark worker as finished with current task."""
        self.status = 'idle'
        self.current_task_id = None
        self.tasks_processed += 1
        
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        
        if processing_time_ms is not None:
            self.total_processing_time_ms += processing_time_ms
        
        self.updated_at = datetime.now(timezone.utc)
    
    def can_handle_task_type(self, task_type: str) -> bool:
        """Check if worker can handle a specific task type."""
        return task_type in self.capabilities
    
    def add_capability(self, task_type: str) -> None:
        """Add a new capability to the worker."""
        if task_type not in self.capabilities:
            capabilities = list(self.capabilities) if self.capabilities else []
            capabilities.append(task_type)
            self.capabilities = capabilities
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_capability(self, task_type: str) -> None:
        """Remove a capability from the worker."""
        if self.capabilities and task_type in self.capabilities:
            capabilities = list(self.capabilities)
            capabilities.remove(task_type)
            self.capabilities = capabilities
            self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert worker to dictionary representation."""
        data = {
            'id': self.id,
            'status': self.status,
            'capabilities': self.capabilities or [],
            'version': self.version,
            'current_task_id': self.current_task_id,
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'tasks_processed': self.tasks_processed,
            'tasks_failed': self.tasks_failed,
            'tasks_completed': self.tasks_completed,
            'uptime_seconds': self.uptime_seconds,
            'memory_usage': self.memory_usage,
            'cpu_usage': self.cpu_usage,
            'disk_usage': self.disk_usage,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'port': self.port,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_seen_at': self.last_seen_at.isoformat(),
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'heartbeat_interval': self.heartbeat_interval,
            'is_online': self.is_online,
            'is_available': self.is_available,
            'success_rate': self.success_rate,
            'failure_rate': self.failure_rate,
            'average_processing_time_ms': self.average_processing_time_ms,
        }
        
        if include_sensitive:
            data['api_key_hash'] = self.api_key_hash
        
        return data
    
    @classmethod
    def create_worker(cls,
                     worker_id: str,
                     capabilities: List[str],
                     version: Optional[str] = None,
                     hostname: Optional[str] = None,
                     ip_address: Optional[str] = None,
                     port: Optional[int] = None,
                     api_key_hash: Optional[str] = None) -> 'Worker':
        """Create a new worker instance."""
        return cls(
            id=worker_id,
            status='idle',
            capabilities=capabilities,
            version=version,
            hostname=hostname,
            ip_address=ip_address,
            port=port,
            api_key_hash=api_key_hash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )