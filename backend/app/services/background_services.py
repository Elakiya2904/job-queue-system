"""
Background Services for Job Queue System

Handles periodic cleanup tasks, monitoring, and maintenance operations
that keep the system healthy and performant.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from .task_service import TaskService
from .worker_service import WorkerService

logger = logging.getLogger(__name__)


class BackgroundServices:
    """
    Background service manager for periodic cleanup and monitoring tasks.
    
    Runs essential maintenance operations:
    - Stale lock recovery
    - Worker health monitoring  
    - Inactive worker cleanup
    - System metrics collection
    """
    
    def __init__(self):
        self.task_service = TaskService()
        self.worker_service = WorkerService()
        self.running = False
        self._tasks = []
        self._shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start all background services."""
        if self.running:
            logger.warning("Background services already running")
            return
        
        self.running = True
        logger.info("Starting background services...")
        
        # Setup signal handlers for graceful shutdown
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._stale_lock_recovery_loop()),
            asyncio.create_task(self._worker_health_monitor_loop()),
            asyncio.create_task(self._inactive_worker_cleanup_loop()),
            asyncio.create_task(self._metrics_collection_loop())
        ]
        
        logger.info("Background services started successfully")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        await self.stop()
    
    async def stop(self):
        """Stop all background services gracefully."""
        if not self.running:
            return
        
        logger.info("Stopping background services...")
        self.running = False
        
        # Cancel all running tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        logger.info("Background services stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._shutdown_event.set()
    
    async def _stale_lock_recovery_loop(self):
        """
        Periodic stale lock recovery.
        
        Runs every 5 minutes to recover tasks from crashed workers.
        """
        interval_seconds = 300  # 5 minutes
        
        logger.info("Started stale lock recovery loop")
        
        while self.running:
            try:
                start_time = datetime.now(timezone.utc)
                
                # Recover stale locks (tasks locked for > 1 hour)
                recovered_count = self.task_service.recover_stale_locks(max_age_hours=1)
                
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if recovered_count > 0:
                    logger.info(f"Stale lock recovery: {recovered_count} tasks recovered in {duration:.2f}s")
                else:
                    logger.debug(f"Stale lock recovery: no stale locks found ({duration:.2f}s)")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Stale lock recovery loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in stale lock recovery: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _worker_health_monitor_loop(self):
        """
        Periodic worker health monitoring.
        
        Runs every 2 minutes to mark offline workers and update status.
        """
        interval_seconds = 120  # 2 minutes
        
        logger.info("Started worker health monitor loop")
        
        while self.running:
            try:
                start_time = datetime.now(timezone.utc)
                
                # Mark workers offline based on missed heartbeats
                offline_count = self.worker_service.mark_workers_offline()
                
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if offline_count > 0:
                    logger.info(f"Worker health check: {offline_count} workers marked offline in {duration:.2f}s")
                else:
                    logger.debug(f"Worker health check: all workers healthy ({duration:.2f}s)")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Worker health monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in worker health monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _inactive_worker_cleanup_loop(self):
        """
        Periodic inactive worker cleanup.
        
        Runs every hour to remove workers offline for > 24 hours.
        """
        interval_seconds = 3600  # 1 hour
        
        logger.info("Started inactive worker cleanup loop")
        
        while self.running:
            try:
                start_time = datetime.now(timezone.utc)
                
                # Clean up workers offline for > 24 hours
                cleaned_count = self.worker_service.cleanup_inactive_workers(max_offline_hours=24)
                
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if cleaned_count > 0:
                    logger.info(f"Worker cleanup: {cleaned_count} inactive workers removed in {duration:.2f}s")
                else:
                    logger.debug(f"Worker cleanup: no inactive workers found ({duration:.2f}s)")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Inactive worker cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in inactive worker cleanup: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _metrics_collection_loop(self):
        """
        Periodic metrics collection and logging.
        
        Runs every 10 minutes to collect and log system metrics.
        """
        interval_seconds = 600  # 10 minutes
        
        logger.info("Started metrics collection loop")
        
        while self.running:
            try:
                start_time = datetime.now(timezone.utc)
                
                # Collect queue metrics
                queue_metrics = self.task_service.get_queue_metrics()
                
                # Collect worker metrics
                worker_metrics = self.worker_service.get_worker_metrics()
                
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                # Log key metrics
                logger.info(
                    f"System Metrics - "
                    f"Queue: {queue_metrics['queue_length']} queued, "
                    f"{queue_metrics['processing_count']} processing | "
                    f"Workers: {worker_metrics['online_workers']} online, "
                    f"{worker_metrics['active_workers']} active | "
                    f"Collection time: {duration:.2f}s"
                )
                
                # Log detailed metrics at debug level
                logger.debug(f"Queue metrics: {queue_metrics}")
                logger.debug(f"Worker metrics: {worker_metrics}")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Metrics collection loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            Dict containing current system status and metrics
        """
        try:
            queue_metrics = self.task_service.get_queue_metrics()
            worker_metrics = self.worker_service.get_worker_metrics()
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "background_services_running": self.running,
                "queue": queue_metrics,
                "workers": worker_metrics,
                "health": {
                    "queue_healthy": queue_metrics["queue_length"] < 10000,  # Alert if > 10k queued
                    "workers_healthy": worker_metrics["online_workers"] > 0,
                    "processing_healthy": queue_metrics["processing_count"] > 0 or queue_metrics["queue_length"] == 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "background_services_running": self.running,
                "error": str(e)
            }


# Background service runner script
async def main():
    """Main entry point for background services."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start background services
    services = BackgroundServices()
    
    try:
        await services.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Background services failed: {e}")
        sys.exit(1)
    else:
        logger.info("Background services completed")


if __name__ == "__main__":
    asyncio.run(main())