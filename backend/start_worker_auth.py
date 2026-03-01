#!/usr/bin/env python3
"""
Authenticated worker launcher script.

This worker authenticates with the backend API before claiming tasks.
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


# Worker authentication token
WORKER_TOKEN = None
TOKEN_EXPIRY = None


def authenticate_worker(worker_id: str, api_key: str, api_url: str = "http://localhost:8001") -> dict:
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
    """Start an authenticated worker."""
    
    global WORKER_TOKEN, TOKEN_EXPIRY
    
    # Get credentials from environment  variables or use defaults
    worker_id = os.environ.get("WORKER_ID", "worker_01")
    api_key = os.environ.get("WORKER_API_KEY", "worker_key_123456")
    api_url = os.environ.get("API_URL", "http://localhost:8001")
    
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
        api_key=api_key,
        capabilities=["email_processing", "data_processing", "notification"],
        max_concurrent_tasks=2,
        heartbeat_interval=30,
        poll_interval=5,
        max_task_timeout=600,
        version="1.0.0"
    )
    
    # Create task executor
    executor = DefaultTaskExecutor()
    
    # Create and start worker
    worker = WorkerRunner(config, executor)
    
    # Store token in worker for API requests
    worker.auth_token = WORKER_TOKEN
    
    print(f"\n🚀 Starting worker {config.worker_id}...")
    print(f"   Capabilities: {', '.join(config.capabilities)}")
    print(f"   Max concurrent tasks: {config.max_concurrent_tasks}")
    print(f"   Polling interval: {config.poll_interval}s")
    print(f"   Authenticated: ✅")
    print("\nPress Ctrl+C to stop the worker gracefully\n")
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\n⚠️  Shutdown requested by user")
    except Exception as e:
        print(f"❌ Worker failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("👋 Worker stopped")


if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*60)
    print("🔧 Job Queue System - Authenticated Worker")
    print("="*60)
    print()
    
    # Display configuration
    worker_id = os.environ.get("WORKER_ID", "worker_01")
    api_url = os.environ.get("API_URL", "http://localhost:8001")
    
    print(f"Configuration:")
    print(f"  Worker ID: {worker_id}")
    print(f"  API URL: {api_url}")
    print(f"  Database: {os.environ.get('DATABASE_URL', 'Using default')}")
    print()
    
    # Start the worker
    try:
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nFailed to start worker: {e}")
        sys.exit(1)
