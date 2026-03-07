"""
AWS Lambda handler for FastAPI application using Mangum.
"""

import os
import json
import boto3
from mangum import Mangum

# Initialize Secrets Manager client
secrets_client = boto3.client('secretsmanager')

def get_database_url():
    """
    Retrieve database URL from environment variables and Secrets Manager.
    Builds PostgreSQL connection string from environment variables and secret credentials.
    """
    db_host = os.environ.get('DB_HOST', '')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'jobqueue')
    db_user = os.environ.get('DB_USER', 'jobqueue_admin')
    db_secret_arn = os.environ.get('DB_SECRET_ARN', '')
    
    db_password = db_user  # Default fallback
    
    # Fetch password from Secrets Manager if ARN is provided
    if db_secret_arn:
        try:
            secret_response = secrets_client.get_secret_value(SecretId=db_secret_arn)
            if 'SecretString' in secret_response:
                secret_dict = json.loads(secret_response['SecretString'])
                db_password = secret_dict.get('password', db_password)
        except Exception as e:
            print(f"Warning: Could not fetch secret from Secrets Manager: {e}")
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return database_url

# Set up environment for Lambda
os.environ.setdefault("ENVIRONMENT", os.environ.get("ENVIRONMENT", "staging"))
os.environ["DATABASE_URL"] = get_database_url()

# Import FastAPI application
from app.main import app

# Create Lambda handler using Mangum
handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    """
    return handler(event, context)
