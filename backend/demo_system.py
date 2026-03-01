#!/usr/bin/env python3
"""
Complete system demonstration script.

This script demonstrates the entire job queue system working together:
1. Creates tasks
2. Shows tasks being processed by workers
3. Displays system metrics
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services import (
    TaskService, 
    WorkerService, 
    WorkerRunner, 
    WorkerConfig, 
    DefaultTaskExecutor,
    BackgroundServices
)


class DemoTaskExecutor(DefaultTaskExecutor):
    """Demo task executor with visible progress."""
    
    async def execute_task(self, task_type: str, payload: dict) -> dict:
        print(f"    🔄 Executing {task_type} task...")
        
        # Add some visible delay
        await asyncio.sleep(2)
        
        result = await super().execute_task(task_type, payload)
        print(f"    ✅ Completed {task_type} task")
        
        return result


async def demo_system():
    """Run a complete system demonstration."""
    
    print("🚀 Job Queue System Demonstration")
    print("=" * 50)
    
    # Initialize services
    task_service = TaskService()
    worker_service = WorkerService()
    
    print("\n1️⃣ Creating demonstration tasks...")
    
    # Create various types of tasks
    tasks = []
    
    # Email tasks
    for i in range(3):
        task = task_service.create_task(
            task_type="email_processing",
            payload={
                "recipient": f"user{i+1}@example.com",
                "template": "demo_email",
                "variables": {"name": f"User {i+1}"}
            },
            created_by="demo",
            priority=2,
            correlation_id=f"demo_email_{i+1}"
        )
        tasks.append(task)
        print(f"   📧 Created email task: {task.id}")
    
    # File conversion tasks
    for i in range(2):
        task = task_service.create_task(
            task_type="file_conversion",
            payload={
                "input_file": f"document{i+1}.pdf",
                "output_format": "docx"
            },
            created_by="demo",
            priority=3,  # Higher priority
            correlation_id=f"demo_file_{i+1}"
        )
        tasks.append(task)
        print(f"   📄 Created file conversion task: {task.id}")
    
    # Data processing task
    task = task_service.create_task(
        task_type="data_processing",
        payload={
            "data_source": "demo_analytics",
            "operation": "aggregate"
        },
        created_by="demo",
        priority=1,  # Lower priority
        correlation_id="demo_data_1"
    )
    tasks.append(task)
    print(f"   📊 Created data processing task: {task.id}")
    
    print(f"\n✅ Created {len(tasks)} demonstration tasks")
    
    # Show initial metrics
    print("\n2️⃣ Initial system metrics...")
    queue_metrics = task_service.get_queue_metrics()
    print(f"   Queue length: {queue_metrics['queue_length']}")
    print(f"   Processing: {queue_metrics['processing_count']}")
    print(f"   Total tasks: {queue_metrics['total_tasks']}")
    
    print("\n3️⃣ Starting demo worker...")
    
    # Configure demo worker
    config = WorkerConfig(
        worker_id="demo-worker",
        api_key="demo-api-key-32-characters-long",
        capabilities=["email_processing", "file_conversion", "data_processing"],
        max_concurrent_tasks=2,
        heartbeat_interval=10,
        poll_interval=2
    )
    
    # Create worker with demo executor
    executor = DemoTaskExecutor()
    worker = WorkerRunner(config, executor)
    
    # Start worker in background
    worker_task = asyncio.create_task(worker.start())
    
    print(f"   🤖 Started worker: {config.worker_id}")
    print(f"   📋 Capabilities: {config.capabilities}")
    print(f"   🔀 Max concurrent tasks: {config.max_concurrent_tasks}")
    
    # Monitor progress
    print("\n4️⃣ Monitoring task processing...")
    
    completed_tasks = set()
    start_time = time.time()
    max_wait_time = 60  # Maximum wait time in seconds
    
    while len(completed_tasks) < len(tasks) and (time.time() - start_time) < max_wait_time:
        await asyncio.sleep(3)
        
        # Check task status
        for task in tasks:
            if task.id not in completed_tasks:
                # Refresh task from database
                with task_service.get_session() as session:
                    updated_task = session.query(type(task)).filter_by(id=task.id).first()
                    if updated_task and updated_task.status in ("completed", "failed_permanent"):
                        completed_tasks.add(task.id)
                        print(f"   ✅ Task {task.id} completed: {updated_task.status}")
        
        # Show progress
        queue_metrics = task_service.get_queue_metrics()
        worker_metrics = worker_service.get_worker_metrics()
        
        print(f"   📊 Progress: {len(completed_tasks)}/{len(tasks)} completed, "
              f"queue: {queue_metrics['queue_length']}, "
              f"processing: {queue_metrics['processing_count']}, "
              f"workers online: {worker_metrics['online_workers']}")
    
    print("\n5️⃣ Final system metrics...")
    
    # Get final metrics
    queue_metrics = task_service.get_queue_metrics()
    worker_metrics = worker_service.get_worker_metrics()
    
    print(f"   Queue metrics:")
    print(f"     - Queued: {queue_metrics['queue_length']}")
    print(f"     - Processing: {queue_metrics['processing_count']}")
    print(f"     - Completed: {queue_metrics['completed_count']}")
    print(f"     - Failed: {queue_metrics['failed_count']}")
    print(f"     - Total: {queue_metrics['total_tasks']}")
    
    print(f"   Worker metrics:")
    print(f"     - Online workers: {worker_metrics['online_workers']}")
    print(f"     - Active workers: {worker_metrics['active_workers']}")
    print(f"     - Average success rate: {worker_metrics['avg_success_rate']:.2%}")
    
    # Show task details
    print(f"\n6️⃣ Task completion details...")
    for task in tasks:
        with task_service.get_session() as session:
            updated_task = session.query(type(task)).filter_by(id=task.id).first()
            if updated_task:
                print(f"   Task {task.id[:12]}... ({task.type}): {updated_task.status}")
                if updated_task.result:
                    print(f"     Result keys: {list(updated_task.result.keys())}")
    
    print("\n7️⃣ Stopping worker...")
    
    # Stop worker gracefully
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    
    await worker.stop()
    print("   🛑 Worker stopped gracefully")
    
    print(f"\n🎉 Demonstration completed successfully!")
    print(f"   📈 Processed {len(completed_tasks)} tasks in {time.time() - start_time:.1f} seconds")
    print(f"   🏆 System demonstrated: task creation, worker processing, metrics collection")


if __name__ == "__main__":
    # Set database URL if not in environment
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/job_queue_db"
    
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise for demo
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🔧 Make sure PostgreSQL is running and database is set up!")
    print("   Run: python setup_db.py")
    print("   Or:  alembic upgrade head")
    print("")
    
    try:
        asyncio.run(demo_system())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print(f"💡 Make sure your database is running and properly configured")
        sys.exit(1)