"""
FastAPI dependency injection functions.
"""

from typing import Optional, Dict, Any, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..db.base import get_db
from ..core.security import verify_token
from ..services import TaskService, WorkerService


# Security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        User information from token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token is refresh token
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "user")
    }


def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current admin user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Admin user information
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    """
    Get TaskService instance with database session.
    """
    return TaskService(db_session=db)


def get_worker_service(db: Session = Depends(get_db)) -> WorkerService:
    """
    Get WorkerService instance with database session.
    """
    return WorkerService(db_session=db)


# Optional authentication for some endpoints
def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    Get current user from JWT token (optional).
    
    Args:
        credentials: HTTP Bearer credentials (optional)
        
    Returns:
        User information from token or None if not provided/invalid
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        return None
    
    # Check if token is refresh token
    if payload.get("type") == "refresh":
        return None
    
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    
    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "user")
    }