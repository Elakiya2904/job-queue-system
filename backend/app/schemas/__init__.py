"""
Schemas package for request and response models.
"""

from .auth import (
    UserLogin,
    UserSignup,
    TokenResponse,
    UserInfo,
    RefreshTokenRequest,
    ErrorResponse,
)

from .task import (
    TaskCreate,
    TaskResponse,
    TaskListQuery,
    TaskListResponse,
    TaskUpdate,
    TaskActionRequest,
)

from .worker import (
    WorkerRegister,
    WorkerHeartbeat,
    WorkerResponse,
    WorkerListQuery,
    WorkerListResponse,
    WorkerStats,
    WorkerRegistrationResponse,
)

from .admin import (
    SystemMetrics,
    TaskTypeMetrics,
    WorkerMetrics,
    QueueMetrics,
    ErrorMetrics,
    PerformanceMetrics,
    HealthStatus,
    MetricsResponse,
    MetricsQuery,
)

__all__ = [
    # Auth schemas
    "UserLogin",
    "UserSignup", 
    "TokenResponse",
    "UserInfo",
    "RefreshTokenRequest",
    "ErrorResponse",
    
    # Task schemas
    "TaskCreate",
    "TaskResponse",
    "TaskListQuery",
    "TaskListResponse",
    "TaskUpdate",
    "TaskActionRequest",
    
    # Worker schemas
    "WorkerRegister",
    "WorkerHeartbeat",
    "WorkerResponse",
    "WorkerListQuery",
    "WorkerListResponse",
    "WorkerStats",
    "WorkerRegistrationResponse",
    
    # Admin schemas
    "SystemMetrics",
    "TaskTypeMetrics",
    "WorkerMetrics",
    "QueueMetrics",
    "ErrorMetrics",
    "PerformanceMetrics",
    "HealthStatus",
    "MetricsResponse",
    "MetricsQuery",
]