"""
Services Package

Production-grade business logic layer for the distributed job queue system.

This package contains:
- TaskService: Core task lifecycle management with PostgreSQL optimizations
- WorkerService: Worker registration, authentication, and health monitoring  
- BackgroundServices: Periodic cleanup and system maintenance tasks
- WorkerRunner: Production worker process with comprehensive error handling

Key features:
- Proper transaction management and concurrency control
- PostgreSQL-specific optimizations (FOR UPDATE SKIP LOCKED)
- Exponential backoff retry logic with jitter
- Comprehensive error handling and recovery
- Resource monitoring and health checks
- Graceful shutdown and crash recovery
"""

from .task_service import TaskService
from .worker_service import WorkerService
from .background_services import BackgroundServices
from .worker_runner import WorkerRunner, WorkerConfig, TaskExecutor, DefaultTaskExecutor

__all__ = [
    'TaskService',
    'WorkerService', 
    'BackgroundServices',
    'WorkerRunner',
    'WorkerConfig',
    'TaskExecutor',
    'DefaultTaskExecutor'
]