"""
Production-grade Worker Runner

High-performance worker process that safely polls for tasks, executes them,
and handles all aspects of worker lifecycle including crash recovery.
"""

import asyncio
import logging
import signal
import sys
import time
import uuid
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import json

# Optional import for resource monitoring
try:
    import psutil  # type: ignore[import]
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    PSUTIL_AVAILABLE = False

from .task_service import TaskService
from .worker_service import WorkerService
from ..models import Task, TaskAttempt, Worker

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Worker configuration settings."""
    worker_id: str
    api_key: str
    capabilities: List[str]
    max_concurrent_tasks: int = 1
    heartbeat_interval: int = 30  # seconds
    poll_interval: int = 5  # seconds
    max_task_timeout: int = 3600  # 1 hour
    version: str = "1.0.0"
    
    # Resource monitoring
    enable_resource_monitoring: bool = True
    
    # Error handling
    max_consecutive_errors: int = 5
    error_backoff_seconds: int = 30


class TaskExecutor:
    """
    Base class for task execution.
    
    Override execute_task method to implement specific task logic.
    """
    
    async def execute_task(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task and return the result.
        
        Args:
            task_type: Type of task to execute
            payload: Task payload data
            
        Returns:
            Dictionary containing task result
            
        Raises:
            Exception: If task execution fails
        """
        raise NotImplementedError("Subclasses must implement execute_task method")


class DefaultTaskExecutor(TaskExecutor):
    """
    Default task executor with basic implementations.
    
    Add your custom task handlers here or subclass TaskExecutor.
    """
    
    async def execute_task(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task based on type."""
        
        if task_type == "email_processing":
            return await self._execute_email_task(payload)
        elif task_type == "file_conversion":
            return await self._execute_file_conversion(payload)
        elif task_type == "data_processing":
            return await self._execute_data_processing(payload)
        elif task_type == "notification":
            return await self._execute_notification(payload)
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
    
    async def _execute_email_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email processing task."""
        # Simulate email processing
        recipient = payload.get("recipient")
        template = payload.get("template")
        
        logger.info(f"Processing email to {recipient} using template {template}")
        
        # Simulate processing time
        await asyncio.sleep(1)
        
        return {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "recipient": recipient,
            "status": "sent"
        }
    
    async def _execute_file_conversion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file conversion task."""
        input_file = payload.get("input_file")
        output_format = payload.get("output_format")
        
        logger.info(f"Converting {input_file} to {output_format}")
        
        # Simulate conversion time
        await asyncio.sleep(3)
        
        return {
            "output_file": f"converted_{uuid.uuid4().hex[:8]}.{output_format}",
            "size_bytes": 1024 * 1024,  # 1MB
            "conversion_time_ms": 3000,
            "status": "completed"
        }
    
    async def _execute_data_processing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data processing task."""
        data_source = payload.get("data_source")
        operation = payload.get("operation", "transform")
        
        logger.info(f"Processing data from {data_source} with operation {operation}")
        
        # Simulate processing time
        await asyncio.sleep(2)
        
        return {
            "processed_records": 1000,
            "output_location": f"processed_{uuid.uuid4().hex[:8]}.json",
            "operation": operation,
            "status": "completed"
        }
    
    async def _execute_notification(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute notification task."""
        recipient = payload.get("recipient")
        message = payload.get("message")
        channel = payload.get("channel", "push")
        
        logger.info(f"Sending {channel} notification to {recipient}")
        
        # Simulate notification time
        await asyncio.sleep(0.5)
        
        return {
            "notification_id": f"notif_{uuid.uuid4().hex[:8]}",
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "channel": channel,
            "status": "delivered"
        }


class WorkerRunner:
    """
    Production-grade worker runner with comprehensive error handling,
    resource monitoring, and graceful shutdown capabilities.
    """
    
    def __init__(self, config: WorkerConfig, task_executor: TaskExecutor):
        self.config = config
        self.task_executor = task_executor
        self.task_service = TaskService()
        self.worker_service = WorkerService()
        
        # State management
        self.running = False
        self.current_tasks: Dict[str, asyncio.Task] = {}
        self.consecutive_errors = 0
        self.last_heartbeat = datetime.now(timezone.utc)
        
        # Asyncio events
        self._shutdown_event = asyncio.Event()
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Resource monitoring
        self.process = None
        if config.enable_resource_monitoring and PSUTIL_AVAILABLE:
            try:
                self.process = psutil.Process()
            except Exception as e:
                logger.warning(f"Failed to initialize psutil process: {e}")
        elif config.enable_resource_monitoring and not PSUTIL_AVAILABLE:
            logger.warning("Resource monitoring enabled but psutil not available. Install psutil for resource monitoring.")
    
    async def start(self):
        """Start the worker runner."""
        logger.info(f"Starting worker {self.config.worker_id}")
        
        try:
            # Register worker
            await self._register_worker()
            
            # Setup signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
            
            # Start background tasks
            self.running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"Worker {self.config.worker_id} started successfully")
            
            # Main polling loop
            await self._polling_loop()
            
        except Exception as e:
            logger.error(f"Fatal error in worker {self.config.worker_id}: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Gracefully stop the worker."""
        if not self.running:
            return
        
        logger.info(f"Stopping worker {self.config.worker_id}")
        self.running = False
        
        # Wait for current tasks to complete (with timeout)
        if self.current_tasks:
            logger.info(f"Waiting for {len(self.current_tasks)} tasks to complete...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.current_tasks.values(), return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some tasks didn't complete within timeout, cancelling...")
                for task in self.current_tasks.values():
                    task.cancel()
        
        # Stop heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Mark worker as offline
        try:
            await self._update_worker_status("offline")
        except Exception as e:
            logger.error(f"Failed to update worker status to offline: {e}")
        
        logger.info(f"Worker {self.config.worker_id} stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Worker {self.config.worker_id} received signal {signum}")
        self._shutdown_event.set()
    
    async def _register_worker(self):
        """Register worker with the system."""
        # Get system info
        hostname = None
        ip_address = None
        
        try:
            import socket
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
        except Exception:
            pass
        
        # Register worker
        worker = self.worker_service.register_worker(
            worker_id=self.config.worker_id,
            capabilities=self.config.capabilities,
            api_key=self.config.api_key,
            version=self.config.version,
            hostname=hostname,
            ip_address=ip_address,
            max_concurrent_tasks=self.config.max_concurrent_tasks,
            heartbeat_interval=self.config.heartbeat_interval
        )
        
        logger.info(f"Registered worker {self.config.worker_id} with capabilities: {self.config.capabilities}")
    
    async def _polling_loop(self):
        """Main polling loop for claiming and processing tasks."""
        logger.info(f"Starting polling loop for worker {self.config.worker_id}")
        
        while self.running:
            try:
                # Check for shutdown
                if self._shutdown_event.is_set():
                    break
                
                # Check if we can take more tasks
                if len(self.current_tasks) >= self.config.max_concurrent_tasks:
                    await asyncio.sleep(1)
                    continue
                
                # Try to claim a task
                task_info = self.task_service.claim_next_task(
                    worker_id=self.config.worker_id,
                    capabilities=self.config.capabilities,
                    max_timeout=self.config.max_task_timeout
                )
                
                if task_info:
                    task, attempt = task_info
                    
                    # Start processing task
                    task_coroutine = self._process_task(task, attempt)
                    task_future = asyncio.create_task(task_coroutine)
                    self.current_tasks[task.id] = task_future
                    
                    # Reset consecutive error count on successful claim
                    self.consecutive_errors = 0
                    
                    logger.info(f"Claimed and started task {task.id} (type: {task.type})")
                else:
                    # No tasks available, wait before polling again
                    await asyncio.sleep(self.config.poll_interval)
                
            except Exception as e:
                self.consecutive_errors += 1
                logger.error(f"Error in polling loop: {e}")
                
                # Implement exponential backoff for consecutive errors
                if self.consecutive_errors >= self.config.max_consecutive_errors:
                    backoff_time = self.config.error_backoff_seconds * (2 ** min(self.consecutive_errors - self.config.max_consecutive_errors, 5))
                    logger.error(f"Too many consecutive errors ({self.consecutive_errors}), backing off for {backoff_time}s")
                    await asyncio.sleep(backoff_time)
                else:
                    await asyncio.sleep(5)  # Short wait on error
    
    async def _process_task(self, task: Task, attempt: TaskAttempt):
        """Process a single task."""
        start_time = time.time()
        task_id = task.id
        attempt_id = attempt.id
        
        try:
            # Update worker status
            self.worker_service.start_task(self.config.worker_id, task_id)
            await self._update_worker_status("active", task_id)
            
            logger.info(f"Processing task {task_id} (type: {task.type})")
            
            # Execute the task
            result = await asyncio.wait_for(
                self.task_executor.execute_task(task.type, task.payload),
                timeout=task.timeout
            )
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Mark task as successful
            success = self.task_service.mark_task_success(
                task_id=task_id,
                attempt_id=attempt_id,
                worker_id=self.config.worker_id,
                result=result,
                processing_time_ms=processing_time_ms
            )
            
            if success:
                logger.info(f"Task {task_id} completed successfully in {processing_time_ms}ms")
                
                # Update worker metrics
                self.worker_service.finish_task(
                    worker_id=self.config.worker_id,
                    success=True,
                    processing_time_ms=processing_time_ms
                )
            else:
                logger.error(f"Failed to mark task {task_id} as successful - task may have been reassigned")
            
        except asyncio.TimeoutError:
            # Task timeout
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_message = f"Task timed out after {task.timeout} seconds"
            
            logger.error(f"Task {task_id} timed out after {task.timeout}s")
            
            self.task_service.mark_task_failed(
                task_id=task_id,
                attempt_id=attempt_id,
                worker_id=self.config.worker_id,
                error_code="TIMEOUT",
                error_message=error_message,
                processing_time_ms=processing_time_ms
            )
            
            # Update worker metrics
            self.worker_service.finish_task(
                worker_id=self.config.worker_id,
                success=False,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            # Task execution error
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_code = type(e).__name__.upper()
            error_message = str(e)
            
            logger.error(f"Task {task_id} failed with error: {error_message}")
            logger.debug(f"Task {task_id} error traceback: {traceback.format_exc()}")
            
            self.task_service.mark_task_failed(
                task_id=task_id,
                attempt_id=attempt_id,
                worker_id=self.config.worker_id,
                error_code=error_code,
                error_message=error_message,
                processing_time_ms=processing_time_ms
            )
            
            # Update worker metrics
            self.worker_service.finish_task(
                worker_id=self.config.worker_id,
                success=False,
                processing_time_ms=processing_time_ms
            )
            
        finally:
            # Clean up task from current tasks
            self.current_tasks.pop(task_id, None)
            
            # Update worker status back to idle
            await self._update_worker_status("idle")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain worker health status."""
        logger.info(f"Starting heartbeat loop for worker {self.config.worker_id}")
        
        while self.running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                
                if not self.running:
                    break
                
                # Determine current status
                if self.current_tasks:
                    status = "active"
                    current_task_id = list(self.current_tasks.keys())[0] if len(self.current_tasks) == 1 else None
                else:
                    status = "idle"
                    current_task_id = None
                
                # Get resource usage if monitoring enabled
                memory_usage = None
                cpu_usage = None
                
                if self.process and PSUTIL_AVAILABLE:
                    try:
                        memory_info = self.process.memory_info()
                        # Calculate memory usage as percentage of system memory
                        system_memory = psutil.virtual_memory().total
                        memory_usage = (memory_info.rss / system_memory) * 100
                        cpu_usage = self.process.cpu_percent(interval=None)
                    except Exception as e:
                        logger.debug(f"Failed to get resource usage: {e}")
                
                # Send heartbeat
                result = self.worker_service.update_heartbeat(
                    worker_id=self.config.worker_id,
                    status=status,
                    current_task_id=current_task_id,
                    memory_usage=memory_usage,
                    cpu_usage=cpu_usage
                )
                
                if result.get("error"):
                    logger.error(f"Heartbeat failed: {result['error']}")
                else:
                    self.last_heartbeat = datetime.now(timezone.utc)
                    logger.debug(f"Heartbeat sent successfully (status: {status})")
                
            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _update_worker_status(self, status: str, current_task_id: Optional[str] = None):
        """Update worker status (convenience method)."""
        try:
            self.worker_service.update_heartbeat(
                worker_id=self.config.worker_id,
                status=status,
                current_task_id=current_task_id
            )
        except Exception as e:
            logger.error(f"Failed to update worker status to {status}: {e}")


# Worker runner script
async def main():
    """Main entry point for worker runner."""
    import os
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Job Queue Worker Runner")
    parser.add_argument("--worker-id", default=f"worker-{uuid.uuid4().hex[:8]}", help="Unique worker ID")
    parser.add_argument("--api-key", required=True, help="Worker API key")
    parser.add_argument("--capabilities", required=True, help="Comma-separated list of capabilities")
    parser.add_argument("--max-concurrent-tasks", type=int, default=1, help="Maximum concurrent tasks")
    parser.add_argument("--heartbeat-interval", type=int, default=30, help="Heartbeat interval in seconds")
    parser.add_argument("--poll-interval", type=int, default=5, help="Poll interval in seconds")
    parser.add_argument("--max-task-timeout", type=int, default=3600, help="Maximum task timeout in seconds")
    parser.add_argument("--version", default="1.0.0", help="Worker version")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - [%(worker_id)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"worker-{args.worker_id}.log")
        ]
    )
    
    # Add worker_id to all log records
    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.worker_id = args.worker_id
        return record
    logging.setLogRecordFactory(record_factory)
    
    # Create worker config
    capabilities = [cap.strip() for cap in args.capabilities.split(",")]
    config = WorkerConfig(
        worker_id=args.worker_id,
        api_key=args.api_key,
        capabilities=capabilities,
        max_concurrent_tasks=args.max_concurrent_tasks,
        heartbeat_interval=args.heartbeat_interval,
        poll_interval=args.poll_interval,
        max_task_timeout=args.max_task_timeout,
        version=args.version
    )
    
    # Create task executor
    task_executor = DefaultTaskExecutor()
    
    # Create and start worker
    worker = WorkerRunner(config, task_executor)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
    else:
        logger.info("Worker completed")


if __name__ == "__main__":
    asyncio.run(main())