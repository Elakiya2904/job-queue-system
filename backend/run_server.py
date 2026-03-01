"""
Example of how to run the FastAPI application.

This file demonstrates different ways to start the Job Queue System API.
"""

import uvicorn
from app.main import app


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )

# Alternative ways to run:

# 1. Using uvicorn from command line:
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Using gunicorn for production:
# gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 3. Using Docker (create a Dockerfile):
# docker run -p 8000:8000 your-job-queue-api