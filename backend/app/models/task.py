from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Boolean, Index, CheckConstraint
from sqlalchemy.orm import relationship
from ..db.base import Base


class Task(Base):
    """
    Task model representing a job in the queue system.
    
    Status values: queued, processing, completed, failed, failed_permanent
    Priority levels: 1=low, 2=normal, 3=high, 4=critical
    """
    __tablename__ = "tasks"

    # Primary fields
    id = Column(String(50), primary_key=True, index=True)
    type = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="queued", index=True)
    priority = Column(Integer, nullable=False, default=2, index=True)
    
    # Task data
    payload = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    
    # Scheduling and timing
    scheduled_for = Column(DateTime(timezone=True), nullable=True, index=True)
    timeout = Column(Integer, nullable=False, default=300)  # seconds
    
    # Retry configuration
    max_retries = Column(Integer, nullable=False, default=3)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Lock management
    locked_by = Column(String(50), nullable=True, index=True)
    locked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    lock_timeout = Column(Integer, nullable=True)  # seconds
    
    # Ownership and tracing
    created_by = Column(String(50), nullable=False, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    idempotency_key = Column(String(255), nullable=True, unique=True)
    
    # Progress and error tracking
    progress = Column(Integer, nullable=False, default=0)  # 0-100 percentage
    error_message = Column(Text, nullable=True)  # Error message if failed
    
    # Relationships
    attempts = relationship("TaskAttempt", back_populates="task", 
                          cascade="all, delete-orphan", order_by="TaskAttempt.started_at")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'failed_permanent', 'in_progress', 'dead_letter')",
            name="check_task_status"
        ),
        CheckConstraint(
            "priority IN (1, 2, 3, 4)",
            name="check_task_priority"
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="check_retry_count_non_negative"
        ),
        CheckConstraint(
            "max_retries >= 0",
            name="check_max_retries_non_negative"
        ),
        CheckConstraint(
            "timeout > 0",
            name="check_timeout_positive"
        ),
        CheckConstraint(
            "(locked_by IS NULL AND locked_at IS NULL AND lock_timeout IS NULL) OR "
            "(locked_by IS NOT NULL AND locked_at IS NOT NULL AND lock_timeout IS NOT NULL)",
            name="check_lock_fields_consistency"
        ),
        # Indexes for common queries
        Index('idx_task_status_priority', 'status', 'priority'),
        Index('idx_task_type_status', 'type', 'status'),
        Index('idx_task_scheduled_status', 'scheduled_for', 'status'),
        Index('idx_task_created_by_status', 'created_by', 'status'),
        Index('idx_task_lock_expiry', 'locked_at', 'lock_timeout'),
        Index('idx_task_correlation', 'correlation_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Task(id='{self.id}', type='{self.type}', status='{self.status}', priority={self.priority})>"
    
    @property
    def is_locked(self) -> bool:
        """Check if task is currently locked."""
        if not self.locked_at or not self.lock_timeout:
            return False
        
        lock_expiry = self.locked_at.timestamp() + self.lock_timeout
        return datetime.now(timezone.utc).timestamp() < lock_expiry
    
    @property
    def lock_expired(self) -> bool:
        """Check if task lock has expired."""
        if not self.locked_at or not self.lock_timeout:
            return False
        
        lock_expiry = self.locked_at.timestamp() + self.lock_timeout
        return datetime.now(timezone.utc).timestamp() >= lock_expiry
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (
            self.status in ('failed', 'queued') and
            self.retry_count < self.max_retries
        )
    
    @property
    def should_execute(self) -> bool:
        """Check if task is ready for execution."""
        if self.status != 'queued':
            return False
        
        if self.scheduled_for and self.scheduled_for > datetime.now(timezone.utc):
            return False
        
        return not self.is_locked
    
    def to_dict(self, include_payload: bool = True, include_result: bool = True) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        data = {
            'id': self.id,
            'type': self.type,
            'status': self.status,
            'priority': self.priority,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'created_by': self.created_by,
            'correlation_id': self.correlation_id,
        }
        
        if include_payload:
            data['payload'] = self.payload
        
        if include_result:
            data['result'] = self.result
        
        return data