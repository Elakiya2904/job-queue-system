#!/usr/bin/env python3
"""
Example worker launcher script with authentication.

This script demonstrates how to start a production worker with
proper configuration, authentication, and error handling.
"""

import asyncio
import sys
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services import WorkerRunner, WorkerConfig, DefaultTaskExecutor


# Worker authentication token (will be set after login)
WORKER_TOKEN = None
TOKEN_EXPIRY = None


def authenticate_worker(worker_id: str, api_key: str, api_url: str = "http://localhost:8002") -> dict:
    """
    Authenticate worker with backend API and get JWT token.
    
    Args:
        worker_id: Worker identifier
        api_key: Worker API key
        api_url: Backend API base URL
        
    Returns:
        Authentication response with token and worker info
        
    Raises:
        Exception: If authentication fails
    """
    print(f"🔐 Authenticating worker {worker_id}...")
    
    try:
        response = requests.post(
            f"{api_url}/api/v1/auth/worker/login",
            json={"worker_id": worker_id, "api_key": api_key},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Authentication successful!")
            print(f"   Worker ID: {data['worker']['worker_id']}")
            print(f"   Capabilities: {', '.join(data['worker']['capabilities'])}")
            print(f"   Token expires in: {data['expires_in']} seconds ({data['expires_in']//3600} hours)")
            return data
        else:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to connect to API: {e}")


async def start_worker():
    """Start a worker with authentication and example configuration."""
    
    global WORKER_TOKEN, TOKEN_EXPIRY
    
    # Get credentials from environment variables or use defaults
    worker_id = os.environ.get("WORKER_ID", "worker_01")
    api_key = os.environ.get("WORKER_API_KEY", "worker_key_123456_secure_token_abcdefghijklmnop")
    api_url = os.environ.get("API_URL", "http://localhost:8002")
    
    # Authenticate before starting
    try:
        auth_data = authenticate_worker(worker_id, api_key, api_url)
        WORKER_TOKEN = auth_data["access_token"]
        TOKEN_EXPIRY = datetime.now() + timedelta(seconds=auth_data["expires_in"])
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("Cannot start worker without valid authentication.")
        return
    
    # Worker configuration
    config = WorkerConfig(
        worker_id=worker_id,
        api_key=api_key,  # Still needed for internal operations
        capabilities=["email_processing", "data_processing", "notification"],
        max_concurrent_tasks=2,
        heartbeat_interval=30,
        poll_interval=5,
        max_task_timeout=600,  # 10 minutes
        version="1.0.0"
    )
    
    # Create task executor (use DefaultTaskExecutor or create custom)
    executor = DefaultTaskExecutor()
    
    # Create and start worker
    worker = WorkerRunner(config, executor)
    
    print(f"Starting worker {config.worker_id}...")
    print(f"Capabilities: {config.capabilities}")
    print(f"Max concurrent tasks: {config.max_concurrent_tasks}")
    print("Press Ctrl+C to stop the worker gracefully")
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Worker failed: {e}")
        raise
    finally:
        print("Worker stopped")


if __name__ == "__main__":
    # Use SQLite configuration from .env file instead
    # if "DATABASE_URL" not in os.environ:
    #     os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/job_queue_db"
    
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start the worker
    asyncio.run(start_worker())