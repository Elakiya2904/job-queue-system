"""
Authentication API routes.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from ..dependencies import get_current_user 
from ..schemas.auth import UserLogin, UserSignup, TokenResponse, UserInfo, ErrorResponse
from ..core.security import create_access_token, create_refresh_token
from ..core.config import settings


router = APIRouter(prefix="/auth", tags=["authentication"])


# Simplified mock user database for demonstration (no password hashing)
# In production, this would be replaced with actual user service/repository
MOCK_USERS_DB = {
    "admin@example.com": {
        "id": "user_admin_001",
        "email": "admin@example.com",
        "password": "admin12345",  # Plain text for demo (8+ chars)
        "role": "admin",
        "created_at": "2024-01-01T00:00:00Z"
    },
    "user@example.com": {
        "id": "user_demo_001", 
        "email": "user@example.com",
        "password": "user12345",  # Plain text for demo (8+ chars)
        "role": "user",
        "created_at": "2024-01-01T00:00:00Z"
    }
}

# Worker credentials database for authentication
MOCK_WORKERS_DB = {
    "worker_01": {
        "worker_id": "worker_01",
        "api_key": "worker_key_123456_secure_token_abcdefghijklmnop",  # Plain text for demo (32+ chars)
        "capabilities": ["email_processing", "data_processing", "notification"],
        "created_at": "2024-01-01T00:00:00Z"
    },
    "worker_02": {
        "worker_id": "worker_02",
        "api_key": "worker_key_789012_secure_token_qrstuvwxyz123456",  # Plain text for demo (32+ chars)
        "capabilities": ["email_processing"],
        "created_at": "2024-01-01T00:00:00Z"
    }
}


def authenticate_user(email: str, password: str) -> dict | None:
    """
    Authenticate user with email and password (simplified for demo).
    
    Args:
        email: User email
        password: Plain password
        
    Returns:
        User dict if authenticated, None otherwise
    """
    print(f"[DEBUG] Authenticating user: {email}")
    print(f"[DEBUG] Available users: {list(MOCK_USERS_DB.keys())}")
    user = MOCK_USERS_DB.get(email)
    if not user:
        print(f"[DEBUG] User not found: {email}")
        return None
    
    print(f"[DEBUG] User found. Expected password: {user['password']}, Got: {password}")
    # Simple password check (no hashing for demo)
    if password != user["password"]:
        print(f"[DEBUG] Password mismatch!")
        return None
    
    print(f"[DEBUG] Authentication successful!")
    return user


def create_user(email: str, password: str, role: str = "user") -> dict:
    """
    Create a new user (simplified for demo).
    
    Args:
        email: User email
        password: Plain password
        role: User role
        
    Returns:
        Created user dict
    """
    if email in MOCK_USERS_DB:
        raise ValueError("User already exists")
    
    user_id = f"user_{len(MOCK_USERS_DB) + 1:06d}"
    
    user = {
        "id": user_id,
        "email": email,
        "password": password,  # Plain password for demo
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    MOCK_USERS_DB[email] = user
    return user


def authenticate_worker(worker_id: str, api_key: str) -> dict | None:
    """
    Authenticate worker with worker_id and API key.
    
    Args:
        worker_id: Worker identifier
        api_key: Worker API key
        
    Returns:
        Worker dict if authenticated, None otherwise
    """
    worker = MOCK_WORKERS_DB.get(worker_id)
    if not worker:
        return None
    
    # Simple API key check (no hashing for demo)
    if api_key != worker["api_key"]:
        return None
    
    return worker


def create_worker(worker_id: str, api_key: str, capabilities: list) -> dict:
    """
    Register a new worker.
    
    Args:
        worker_id: Worker identifier
        api_key: Worker API key
        capabilities: List of task types worker can handle
        
    Returns:
        Created worker dict
    """
    if worker_id in MOCK_WORKERS_DB:
        raise ValueError("Worker ID already exists")
    
    worker = {
        "worker_id": worker_id,
        "api_key": api_key,
        "capabilities": capabilities,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    MOCK_WORKERS_DB[worker_id] = worker
    return worker


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and receive JWT access and refresh tokens"
)
async def login(
    user_data: UserLogin
):
    """
    Authenticate user and return JWT tokens.
    
    Args:
        user_data: User login credentials
        
    Returns:
        JWT tokens and user information
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Authenticate user
    user = authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"], "role": user["role"]},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user["id"], "email": user["email"], "role": user["role"]}
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserInfo(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"]
        )
    )


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User signup",
    description="Register new user account and receive JWT tokens"
)
async def signup(
    user_data: UserSignup
):
    """
    Register new user and return JWT tokens.
    
    Args:
        user_data: User registration data
        
    Returns:
        JWT tokens and user information
        
    Raises:
        HTTPException: If user already exists or registration fails
    """
    try:
        # Create new user
        user = create_user(user_data.email, user_data.password, user_data.role)
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user["id"], "email": user["email"], "role": user["role"]},
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": user["id"], "email": user["email"], "role": user["role"]}
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserInfo(
                id=user["id"],
                email=user["email"],
                role=user["role"],
                created_at=user["created_at"]
            )
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user",
    description="Get current user information from token"
)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user information.
    
    Args:
        current_user: Current user from JWT token
        
    Returns:
        User information
    """
    user_data = MOCK_USERS_DB.get(current_user["email"])
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserInfo(
        id=user_data["id"],
        email=user_data["email"],
        role=user_data["role"],
        created_at=user_data["created_at"]
    )


# ======================================
# Worker Authentication Endpoints
# ======================================

@router.post(
    "/worker/login",
    status_code=status.HTTP_200_OK,
    summary="Worker login",
    description="Authenticate worker and receive JWT access token"
)
async def worker_login(worker_credentials: Dict[str, str]):
    """
    Authenticate worker and return JWT token.
    
    Request body: {"worker_id": "worker_01", "api_key": "..."}
    """
    worker_id = worker_credentials.get("worker_id")
    api_key = worker_credentials.get("api_key")
    
    if not worker_id or not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="worker_id and api_key are required"
        )
    
    worker = authenticate_worker(worker_id, api_key)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid worker credentials"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes * 10)
    access_token = create_access_token(
        data={"sub": worker["worker_id"], "type": "worker", "role": "worker", "capabilities": worker["capabilities"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.access_token_expire_minutes * 10 * 60,
        "worker": {
            "worker_id": worker["worker_id"],
            "capabilities": worker["capabilities"],
            "created_at": worker["created_at"]
        }
    }


@router.post(
    "/worker/register",
    status_code=status.HTTP_201_CREATED,
    summary="Worker registration"
)
async def worker_register(worker_data: Dict[str, Any]):
    """Register new worker."""
    worker_id = worker_data.get("worker_id")
    api_key = worker_data.get("api_key")
    capabilities = worker_data.get("capabilities", [])
    
    if not worker_id or not api_key:
        raise HTTPException(status_code=400, detail="worker_id and api_key required")
    
    try:
        worker = create_worker(worker_id, api_key, capabilities)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes * 10)
        access_token = create_access_token(
            data={"sub": worker["worker_id"], "type": "worker", "role": "worker", "capabilities": worker["capabilities"]},
            expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.access_token_expire_minutes * 10 * 60,
            "worker": {"worker_id": worker["worker_id"], "capabilities": worker["capabilities"]}
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

