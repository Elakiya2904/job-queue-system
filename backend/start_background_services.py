#!/usr/bin/env python3
"""
Background services launcher script.

Starts all background maintenance services including:
- Stale lock recovery
- Worker health monitoring  
- Inactive worker cleanup
- System metrics collection
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services import BackgroundServices


async def start_background_services():
    """Start all background services."""
    
    print("Starting background services...")
    print("Services:")
    print("- Stale lock recovery (every 5 minutes)")
    print("- Worker health monitoring (every 2 minutes)")
    print("- Inactive worker cleanup (every hour)")
    print("- System metrics collection (every 10 minutes)")
    print("Press Ctrl+C to stop services gracefully")
    
    services = BackgroundServices()
    
    try:
        await services.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Background services failed: {e}")
        raise
    finally:
        print("Background services stopped")


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
    
    # Start background services
    asyncio.run(start_background_services())