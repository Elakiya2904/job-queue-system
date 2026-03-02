"""
AWS Lambda handler for FastAPI application using Mangum.
"""

import os
from mangum import Mangum

# Set up environment for Lambda
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("DATABASE_URL", os.environ.get("RDS_DATABASE_URL", ""))

# Import FastAPI application
from app.main import app

# Create Lambda handler using Mangum
handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    """
    AWS Lambda entry point for API Gateway requests.
    
    Args:
        event: API Gateway request event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    return handler(event, context)