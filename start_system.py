#!/usr/bin/env python3
"""
System startup script for the Job Queue System.
This script starts all necessary services in the correct order.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Set up paths
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

def setup_environment():
    """Set up environment variables for the backend."""
    os.environ["DATABASE_URL"] = "sqlite:///./data/job_queue.db"
    os.environ["PYTHONPATH"] = str(BACKEND_DIR)
    
    # Set a default SECRET_KEY for development only
    if not os.environ.get("SECRET_KEY"):
        print("⚠️  WARNING: Using default SECRET_KEY for development. Set SECRET_KEY environment variable in production!")
        os.environ["SECRET_KEY"] = "dev-secret-key-change-in-production"
    
    os.environ["DEBUG"] = "true"

def create_data_dir():
    """Ensure the data directory exists."""
    data_dir = BACKEND_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"[OK] Data directory ready: {data_dir}")

def test_backend_import():
    """Test if the backend can be imported successfully."""
    print("Testing backend import...")
    try:
        # Change to backend directory for import test
        original_cwd = os.getcwd()
        os.chdir(BACKEND_DIR)
        
        # Test import
        result = subprocess.run([
            str(VENV_PYTHON), "-c", 
            "from app.main import app; print('[OK] Backend import successful')"
        ], capture_output=True, text=True, timeout=10)
        
        os.chdir(original_cwd)
        
        if result.returncode == 0:
            print(result.stdout.strip())
            return True
        else:
            print(f"[ERROR] Backend import failed: {result.stderr}")
            return False
            
    except Exception as e:
        if os.getcwd() != original_cwd:
            os.chdir(original_cwd)
        print(f"[ERROR] Error testing backend import: {e}")
        return False

def start_backend():
    """Start the FastAPI backend server."""
    print("Starting backend server...")
    try:
        # Change to backend directory
        os.chdir(BACKEND_DIR)
        
        # Start uvicorn server
        cmd = [
            str(VENV_PYTHON), "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8001", 
            "--reload"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        
        # Give it a moment to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("[OK] Backend server started successfully!")
            print("  - API available at: http://localhost:8001")
            print("  - API docs: http://localhost:8001/docs")
            return process
        else:
            print("[ERROR] Backend server failed to start")
            return None
            
    except Exception as e:
        print(f"[ERROR] Error starting backend: {e}")
        return None

def main():
    """Main startup sequence."""
    print("🚀 Starting Job Queue System...")
    print("=" * 50)
    
    # 1. Setup environment
    print("\n1. Setting up environment...")
    setup_environment()
    print("[OK] Environment variables configured")
    
    # 2. Create directories
    print("\n2. Creating necessary directories...")
    create_data_dir()
    
    # 3. Test imports
    print("\n3. Testing backend imports...")
    if not test_backend_import():
        print("[ERROR] Backend import test failed. Please check your setup.")
        sys.exit(1)
    
    # 4. Start backend
    print("\n4. Starting backend server...")
    backend_process = start_backend()
    
    if backend_process:
        print("\n[SUCCESS] System startup completed!")
        print("\nTo test the system:")
        print("  1. Visit http://localhost:8001/docs for API documentation")
        print("  2. Visit http://localhost:3000 for the frontend (if running)")
        print("\nPress Ctrl+C to stop the servers")
        
        try:
            # Wait for the process
            backend_process.wait()
        except KeyboardInterrupt:
            print("\n\n[STOP] Shutting down...")
            backend_process.terminate()
            backend_process.wait()
            print("[OK] System stopped")
    else:
        print("[ERROR] Failed to start system")
        sys.exit(1)

if __name__ == "__main__":
    main()