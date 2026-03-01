"""
Main FastAPI application.

Production-ready job queue system API with authentication, task management,
worker coordination, and admin monitoring capabilities.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging
import time

from .core.config import settings
from .api import auth, tasks, workers, admin


# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware for request/response tracking."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"{request.method} {request.url.path} - Start")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    
    # Startup
    logger.info("Starting Job Queue System API...")
    logger.info(f"Environment: {'Development' if settings.debug else 'Production'}")
    logger.info(f"Database URL: {settings.database_url.split('@')[0]}@...")  # Hide credentials
    
    # TODO: Add any startup tasks here
    # - Database connection verification
    # - Background service initialization
    # - Worker health checks
    
    yield
    
    # Shutdown
    logger.info("Shutting down Job Queue System API...")
    
    # TODO: Add any cleanup tasks here
    # - Close database connections
    # - Stop background services
    # - Graceful worker shutdown


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    **Job Queue System API**
    
    A production-ready distributed job queue and background task processing system.
    
    ## Features
    
    * **Task Management** - Create, monitor, and manage background tasks
    * **Worker Coordination** - Register and coordinate distributed workers
    * **Real-time Monitoring** - Comprehensive metrics and health monitoring
    * **Authentication** - JWT-based authentication with role-based access
    * **Production Ready** - Built for scalability and reliability
    
    ## Authentication
    
    Most endpoints require JWT authentication. Use the `/auth/login` endpoint to obtain tokens.
    
    ## Rate Limiting
    
    API requests are rate-limited to ensure system stability. Check response headers for rate limit information.
    """,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Logging middleware
app.add_middleware(LoggingMiddleware)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "timestamp": time.time()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error" if not settings.debug else str(exc),
            "status_code": 500,
            "timestamp": time.time()
        }
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Basic health check endpoint"
)
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": time.time()
    }


# Root endpoint
@app.get(
    "/",
    tags=["root"],
    summary="API information",
    description="Get basic API information"
)
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "description": "Job Queue System API",
        "docs_url": settings.docs_url,
        "health_url": "/health",
        "api_prefix": settings.api_v1_prefix
    }


# API version prefix
API_V1_PREFIX = settings.api_v1_prefix

# Register routers
app.include_router(
    auth.router,
    prefix=API_V1_PREFIX,
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)

app.include_router(
    tasks.router,
    prefix=API_V1_PREFIX,
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)

app.include_router(
    workers.router,
    prefix=API_V1_PREFIX,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)

app.include_router(
    admin.router,
    prefix=API_V1_PREFIX,
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin access required"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)


# Development mode indicator
if settings.debug:
    logger.warning("Running in DEBUG mode - not suitable for production!")


# Export app for ASGI servers
__all__ = ["app"]