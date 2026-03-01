from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from ..db.base import Base


class TaskAttempt(Base):
    """
    TaskAttempt model representing individual execution attempts of a task.
    
    Tracks the execution history including timing, worker assignment, and error details.
    """
    __tablename__ = "task_attempts"

    # Primary fields
    id = Column(String(50), primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(50), ForeignKey("workers.id"), nullable=False, index=True)
    
    # Execution timing
    started_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Error information
    error_code = Column(String(100), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    task = relationship("Task", back_populates="attempts")
    worker = relationship("Worker", back_populates="attempts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(completed_at IS NULL) OR (failed_at IS NULL)",
            name="check_attempt_completion_xor_failure"
        ),
        CheckConstraint(
            "processing_time_ms >= 0",
            name="check_processing_time_non_negative"
        ),
        CheckConstraint(
            "(failed_at IS NULL) OR (error_code IS NOT NULL)",
            name="check_error_code_required_on_failure"
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="check_completed_after_started"
        ),
        CheckConstraint(
            "failed_at IS NULL OR failed_at >= started_at",
            name="check_failed_after_started"
        ),
        # Indexes for common queries
        Index('idx_task_attempt_task_started', 'task_id', 'started_at'),
        Index('idx_task_attempt_worker_started', 'worker_id', 'started_at'),
        Index('idx_task_attempt_status', 'completed_at', 'failed_at'),
        Index('idx_task_attempt_error', 'error_code'),
        Index('idx_task_attempt_duration', 'processing_time_ms'),
    )
    
    def __repr__(self) -> str:
        status = "completed" if self.completed_at else "failed" if self.failed_at else "in_progress"
        return f"<TaskAttempt(id='{self.id}', task_id='{self.task_id}', worker_id='{self.worker_id}', status='{status}')>"
    
    @property
    def status(self) -> str:
        """Get the current status of the attempt."""
        if self.completed_at:
            return "completed"
        elif self.failed_at:
            return "failed"
        else:
            return "in_progress"
    
    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate duration in milliseconds if attempt is finished."""
        if self.processing_time_ms is not None:
            return self.processing_time_ms
        
        end_time = self.completed_at or self.failed_at
        if end_time:
            duration = (end_time - self.started_at).total_seconds() * 1000
            return int(duration)
        
        return None
    
    @property
    def is_finished(self) -> bool:
        """Check if the attempt has finished (either completed or failed)."""
        return self.completed_at is not None or self.failed_at is not None
    
    @property
    def is_successful(self) -> bool:
        """Check if the attempt completed successfully."""
        return self.completed_at is not None
    
    @property
    def is_failed(self) -> bool:
        """Check if the attempt failed."""
        return self.failed_at is not None
    
    def complete(self, processing_time_ms: Optional[int] = None) -> None:
        """Mark the attempt as completed."""
        now = datetime.now(timezone.utc)
        self.completed_at = now
        self.failed_at = None
        self.error_code = None
        self.error_message = None
        
        if processing_time_ms is not None:
            self.processing_time_ms = processing_time_ms
        elif self.processing_time_ms is None:
            # Calculate processing time if not provided
            duration = (now - self.started_at).total_seconds() * 1000
            self.processing_time_ms = int(duration)
    
    def fail(self, error_code: str, error_message: str, processing_time_ms: Optional[int] = None) -> None:
        """Mark the attempt as failed."""
        now = datetime.now(timezone.utc)
        self.failed_at = now
        self.completed_at = None
        self.error_code = error_code
        self.error_message = error_message
        
        if processing_time_ms is not None:
            self.processing_time_ms = processing_time_ms
        elif self.processing_time_ms is None:
            # Calculate processing time if not provided
            duration = (now - self.started_at).total_seconds() * 1000
            self.processing_time_ms = int(duration)
    
    def to_dict(self, include_task_details: bool = False) -> Dict[str, Any]:
        """Convert attempt to dictionary representation."""
        data = {
            'id': self.id,
            'task_id': self.task_id,
            'worker_id': self.worker_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'processing_time_ms': self.processing_time_ms,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'status': self.status,
            'duration_ms': self.duration_ms,
        }
        
        if include_task_details and self.task:
            data['task'] = self.task.to_dict(include_payload=False, include_result=False)
        
        return data
    
    @classmethod
    def create_for_task(cls, task_id: str, worker_id: str, attempt_id: Optional[str] = None) -> 'TaskAttempt':
        """Create a new attempt for a task."""
        if attempt_id is None:
            # Generate attempt ID based on task and timestamp
            timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
            attempt_id = f"attempt_{task_id}_{timestamp}"
        
        return cls(
            id=attempt_id,
            task_id=task_id,
            worker_id=worker_id,
            started_at=datetime.now(timezone.utc)
        )