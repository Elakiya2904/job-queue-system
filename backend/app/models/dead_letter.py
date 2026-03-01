from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Index, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from ..db.base import Base


class DeadLetterEntry(Base):
    """
    DeadLetterEntry model representing tasks that have permanently failed.
    
    Stores failed tasks with their failure reasons and attempt history 
    for analysis and potential manual recovery.
    """
    __tablename__ = "dead_letter_queue"

    # Primary fields
    id = Column(String(50), primary_key=True, index=True)  # Original task ID
    type = Column(String(100), nullable=False, index=True)
    priority = Column(Integer, nullable=False, index=True)
    
    # Task data (preserved from original task)
    payload = Column(JSON, nullable=False)
    original_created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    original_created_by = Column(String(50), nullable=False, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    
    # Failure information
    failed_at = Column(DateTime(timezone=True), nullable=False, 
                      default=lambda: datetime.now(timezone.utc), index=True)
    failure_reason = Column(String(100), nullable=False, index=True)  # Why it was moved to DLQ
    retry_count = Column(Integer, nullable=False)
    max_retries = Column(Integer, nullable=False)
    
    # Last error details
    last_error_code = Column(String(100), nullable=True, index=True)
    last_error_message = Column(Text, nullable=True)
    last_worker_id = Column(String(50), nullable=True, index=True)
    
    # Attempt history (JSON array of attempt summaries)
    attempts_summary = Column(JSON, nullable=False)
    
    # Management fields
    reviewed = Column(String(20), nullable=False, default="pending", index=True)  # pending, reviewed, resolved
    reviewed_by = Column(String(50), nullable=True, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Recovery attempts
    recovery_attempts = Column(Integer, nullable=False, default=0)  
    last_recovery_attempt_at = Column(DateTime(timezone=True), nullable=True)
    last_recovery_attempt_by = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc))
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "failure_reason IN ('MAX_RETRIES_EXCEEDED', 'PERMANENT_ERROR', 'STALE_LOCK_TIMEOUT', 'MANUAL_MOVE')",
            name="check_dlq_failure_reason"
        ),
        CheckConstraint(
            "reviewed IN ('pending', 'reviewed', 'resolved')",
            name="check_dlq_reviewed_status"
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="check_dlq_retry_count_non_negative"
        ),
        CheckConstraint(
            "max_retries >= 0",
            name="check_dlq_max_retries_non_negative"
        ),
        CheckConstraint(
            "recovery_attempts >= 0",
            name="check_dlq_recovery_attempts_non_negative"
        ),
        CheckConstraint(
            "priority IN (1, 2, 3, 4)",
            name="check_dlq_priority"
        ),
        CheckConstraint(
            "(reviewed_by IS NULL) = (reviewed_at IS NULL)",
            name="check_dlq_reviewer_consistency"
        ),
        # Indexes for common queries
        Index('idx_dlq_type_failed_at', 'type', 'failed_at'),
        Index('idx_dlq_reviewed_status', 'reviewed', 'failed_at'),
        Index('idx_dlq_failure_reason', 'failure_reason', 'failed_at'),
        Index('idx_dlq_priority_failed_at', 'priority', 'failed_at'),
        Index('idx_dlq_creator_failed_at', 'original_created_by', 'failed_at'),
        Index('idx_dlq_error_code', 'last_error_code'),
        Index('idx_dlq_worker_failed_at', 'last_worker_id', 'failed_at'),
        Index('idx_dlq_recovery_attempts', 'recovery_attempts', 'last_recovery_attempt_at'),
    )
    
    def __repr__(self) -> str:
        return f"<DeadLetterEntry(id='{self.id}', type='{self.type}', failure_reason='{self.failure_reason}', reviewed='{self.reviewed}')>"
    
    @property
    def age_hours(self) -> float:
        """Calculate how long the task has been in the dead letter queue (in hours)."""
        return (datetime.now(timezone.utc) - self.failed_at).total_seconds() / 3600
    
    @property
    def days_in_dlq(self) -> int:
        """Calculate how many full days the task has been in the dead letter queue."""
        return int(self.age_hours / 24)
    
    @property
    def is_permanent_failure(self) -> bool:
        """Check if this was a permanent failure (not retry exhaustion)."""
        return self.failure_reason == 'PERMANENT_ERROR'
    
    @property
    def is_retry_exhausted(self) -> bool:
        """Check if this failed due to retry exhaustion."""
        return self.failure_reason == 'MAX_RETRIES_EXCEEDED'
    
    @property
    def is_stale_lock(self) -> bool:
        """Check if this failed due to stale lock timeout."""
        return self.failure_reason == 'STALE_LOCK_TIMEOUT'
    
    @property
    def can_be_retried(self) -> bool:
        """Check if this task could potentially be retried manually."""
        return self.failure_reason in ('MAX_RETRIES_EXCEEDED', 'STALE_LOCK_TIMEOUT')
    
    def mark_reviewed(self, reviewer_id: str, notes: Optional[str] = None) -> None:
        """Mark the entry as reviewed."""
        self.reviewed = 'reviewed'
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        
        if notes:
            self.review_notes = notes
    
    def mark_resolved(self, resolver_id: str, notes: Optional[str] = None) -> None:
        """Mark the entry as resolved."""
        self.reviewed = 'resolved'
        self.reviewed_by = resolver_id
        self.reviewed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        
        if notes:
            self.review_notes = notes
    
    def add_recovery_attempt(self, attempted_by: str) -> None:
        """Record a recovery attempt."""
        self.recovery_attempts += 1
        self.last_recovery_attempt_at = datetime.now(timezone.utc)
        self.last_recovery_attempt_by = attempted_by
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self, include_payload: bool = True, include_attempts: bool = True) -> Dict[str, Any]:
        """Convert dead letter entry to dictionary representation."""
        data = {
            'id': self.id,
            'type': self.type,
            'priority': self.priority,
            'original_created_at': self.original_created_at.isoformat(),
            'original_created_by': self.original_created_by,
            'correlation_id': self.correlation_id,
            'failed_at': self.failed_at.isoformat(),
            'failure_reason': self.failure_reason,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'last_error': {
                'code': self.last_error_code,
                'message': self.last_error_message
            } if self.last_error_code else None,
            'last_worker_id': self.last_worker_id,
            'reviewed': self.reviewed,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_notes': self.review_notes,
            'recovery_attempts': self.recovery_attempts,
            'last_recovery_attempt_at': self.last_recovery_attempt_at.isoformat() if self.last_recovery_attempt_at else None,
            'last_recovery_attempt_by': self.last_recovery_attempt_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'age_hours': self.age_hours,
            'days_in_dlq': self.days_in_dlq,
            'can_be_retried': self.can_be_retried,
        }
        
        if include_payload:
            data['payload'] = self.payload
        
        if include_attempts:
            data['attempts'] = self.attempts_summary
        
        return data
    
    @classmethod
    def create_from_task(cls, 
                        task,  # Task object
                        failure_reason: str,
                        last_error_code: Optional[str] = None,
                        last_error_message: Optional[str] = None,
                        last_worker_id: Optional[str] = None,
                        attempts_summary: Optional[List[Dict[str, Any]]] = None) -> 'DeadLetterEntry':
        """Create a dead letter entry from a failed task."""
        
        # Build attempts summary from task attempts if not provided
        if attempts_summary is None:
            attempts_summary = []
            for attempt in task.attempts:
                attempt_data = {
                    'id': attempt.id,
                    'worker_id': attempt.worker_id,
                    'started_at': attempt.started_at.isoformat(),
                    'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
                    'failed_at': attempt.failed_at.isoformat() if attempt.failed_at else None,
                    'processing_time_ms': attempt.processing_time_ms,
                    'error_code': attempt.error_code,
                    'error_message': attempt.error_message,
                }
                attempts_summary.append(attempt_data)
        
        return cls(
            id=task.id,
            type=task.type,
            priority=task.priority,
            payload=task.payload,
            original_created_at=task.created_at,
            original_created_by=task.created_by,
            correlation_id=task.correlation_id,
            failed_at=datetime.now(timezone.utc),
            failure_reason=failure_reason,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
            last_worker_id=last_worker_id,
            attempts_summary=attempts_summary,
            reviewed='pending',
        )
    
    @classmethod
    def get_failure_reasons(cls) -> Dict[str, str]:
        """Get all possible failure reasons with descriptions."""
        return {
            'MAX_RETRIES_EXCEEDED': 'Task exceeded maximum retry attempts',
            'PERMANENT_ERROR': 'Task failed with permanent error that cannot be retried',
            'STALE_LOCK_TIMEOUT': 'Task lock was stale for extended period (worker crash)',
            'MANUAL_MOVE': 'Task was manually moved to dead letter queue by administrator',
        }