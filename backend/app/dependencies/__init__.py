"""
Dependencies package for FastAPI dependency injection.
"""

from .auth import (
    get_db,
    get_current_user,
    get_current_admin_user,
    get_current_user_optional,
    get_task_service,
    get_worker_service,
)

__all__ = [
    "get_db",
    "get_current_user", 
    "get_current_admin_user",
    "get_current_user_optional",
    "get_task_service",
    "get_worker_service",
]