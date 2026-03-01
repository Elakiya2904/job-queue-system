#!/usr/bin/env python3
"""
Task creation example script.

Demonstrates how to create tasks using the TaskService.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services import TaskService


def create_example_tasks():
    """Create various example tasks."""
    
    task_service = TaskService()
    
    print("Creating example tasks...")
    
    # Example 1: Email processing task
    email_task = task_service.create_task(
        task_type="email_processing",
        payload={
            "recipient": "user@example.com",
            "template": "welcome_email",
            "variables": {
                "name": "John Doe",
                "company": "Example Corp"
            }
        },
        created_by="admin",
        priority=2,
        correlation_id="demo_email_001"
    )
    print(f"✅ Created email task: {email_task.id}")
    
    # Example 2: File conversion task  
    file_task = task_service.create_task(
        task_type="file_conversion",
        payload={
            "input_file": "document.pdf",
            "output_format": "docx",
            "quality": "high"
        },
        created_by="admin",
        priority=3,  # High priority
        timeout=600,  # 10 minutes
        correlation_id="demo_file_001"
    )
    print(f"✅ Created file conversion task: {file_task.id}")
    
    # Example 3: Scheduled data processing task
    scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    data_task = task_service.create_task(
        task_type="data_processing",
        payload={
            "data_source": "user_analytics",
            "operation": "aggregate",
            "date_range": "2024-01-01",
            "output_format": "json"
        },
        created_by="admin",
        priority=1,  # Low priority
        scheduled_for=scheduled_time,
        max_retries=5,
        correlation_id="demo_data_001"
    )
    print(f"✅ Created scheduled data processing task: {data_task.id} (scheduled for {scheduled_time})")
    
    # Example 4: Notification task
    notification_task = task_service.create_task(
        task_type="notification",
        payload={
            "recipient": "alert@example.com",
            "message": "System maintenance completed",
            "channel": "email",
            "urgency": "low"
        },
        created_by="system",
        priority=1,
        timeout=30,  # Quick timeout for notifications
        correlation_id="demo_notification_001"
    )
    print(f"✅ Created notification task: {notification_task.id}")
    
    # Example 5: Bulk tasks with idempotency
    print("\nCreating bulk tasks with idempotency...")
    for i in range(5):
        bulk_task = task_service.create_task(
            task_type="email_processing",
            payload={
                "recipient": f"user{i+1}@example.com",
                "template": "newsletter",
                "variables": {
                    "name": f"User {i+1}",
                    "issue_number": 42
                }
            },
            created_by="bulk_system",
            priority=2,
            idempotency_key=f"newsletter_42_user_{i+1}",  # Ensures no duplicates
            correlation_id=f"newsletter_batch_001"
        )
        print(f"   📧 Bulk email task {i+1}: {bulk_task.id}")
    
    print(f"\n🎉 Successfully created example tasks!")
    
    # Show queue metrics
    metrics = task_service.get_queue_metrics()
    print(f"\n📊 Current queue metrics:")
    print(f"   - Queued tasks: {metrics['queue_length']}")
    print(f"   - Processing tasks: {metrics['processing_count']}")
    print(f"   - Total tasks: {metrics['total_tasks']}")


if __name__ == "__main__":
    # Set database URL if not in environment
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/job_queue_db"
    
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create example tasks
    try:
        create_example_tasks()
    except Exception as e:
        print(f"❌ Failed to create tasks: {e}")
        sys.exit(1)