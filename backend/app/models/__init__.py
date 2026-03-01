"""
SQLAlchemy models for the Distributed Job Queue System.

This package contains all database models that match the API specification:
- Task: Main job/task model with status, priority, scheduling, and retry logic
- TaskAttempt: Individual execution attempts with worker assignment and timing
- Worker: Worker instance model with capabilities, status, and performance metrics  
- DeadLetterEntry: Permanently failed tasks for analysis and recovery

All models include proper relationships, constraints, indexes, and utility methods.
"""

# Import Base first to ensure proper initialization
from ..db.base import Base

# Import all models to register them with SQLAlchemy
from .task import Task
from .task_attempt import TaskAttempt
from .worker import Worker
from .dead_letter import DeadLetterEntry

# Export all models and Base
__all__ = [
    'Base',
    'Task',
    'TaskAttempt', 
    'Worker',
    'DeadLetterEntry',
]

# Model relationships summary:
# - Task has many TaskAttempts (one-to-many)
# - Worker has many TaskAttempts (one-to-many)  
# - TaskAttempt belongs to Task and Worker (many-to-one)
# - DeadLetterEntry is independent (stores task data as JSON)