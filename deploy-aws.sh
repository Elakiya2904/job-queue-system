#!/bin/bash

# Job Queue System - AWS Deployment Script
# This script facilitates the deployment of the job queue system to AWS

set -e  # Exit on any error

echo "🚀 Job Queue System - AWS Deployment"
echo "===================================="
echo ""

# Default values
ENVIRONMENT="${ENVIRONMENT:-staging}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DEPLOY_BACKEND="${DEPLOY_BACKEND:-true}"
DEPLOY_FRONTEND="${DEPLOY_FRONTEND:-true}"

# Functions
print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment    Deployment environment (staging|production) [default: staging]"
    echo "  -r, --region         AWS region [default: us-east-1]"
    echo "  --no-backend         Skip backend deployment"
    echo "  --no-frontend        Skip frontend deployment"
    echo "  --check-only         Only run validation checks"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  AWS_ACCESS_KEY_ID     AWS Access Key"
    echo "  AWS_SECRET_ACCESS_KEY AWS Secret Key"
    echo "  AWS_ACCOUNT_ID        AWS Account ID (optional)"
    echo ""
}

check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI is not installed. Please install it first."
        echo "   See: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "❌ AWS credentials not configured or invalid."
        echo "   Run: aws configure"
        echo "   Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
        exit 1
    fi
    
    echo "✅ AWS CLI and credentials verified"
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        echo "🔧 Installing AWS CDK..."
        npm install -g aws-cdk
    fi
    
    echo "✅ AWS CDK available"
    
    # Check Node.js and npm
    if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
        echo "❌ Node.js and npm are required but not installed."
        echo "   See: https://nodejs.org/"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        echo "❌ Python 3 is required but not installed."
        exit 1
    fi
    
    echo "✅ Prerequisites check completed"
    echo ""
}

validate_infrastructure() {
    echo "🔍 Validating infrastructure code..."
    
    cd aws/infrastructure
    
    # Install dependencies
    echo "📦 Installing CDK dependencies..."
    npm install
    
    # Build TypeScript
    echo "🏗️ Building TypeScript..."
    npm run build
    
    # Validate CDK syntax
    echo "🔍 Validating CDK syntax..."
    export ENVIRONMENT="$ENVIRONMENT"
    cdk synth --quiet
    
    echo "✅ Infrastructure validation completed"
    cd ../..
    echo ""
}

bootstrap_cdk() {
    echo "🚀 Bootstrapping CDK..."
    
    cd aws/infrastructure
    
    export ENVIRONMENT="$ENVIRONMENT"
    export CDK_DEFAULT_REGION="$AWS_REGION"
    
    cdk bootstrap || echo "CDK already bootstrapped"
    
    cd ../..
    echo ""
}

deploy_infrastructure() {
    echo "🏗️ Deploying AWS Infrastructure..."
    
    cd aws/infrastructure
    
    export ENVIRONMENT="$ENVIRONMENT"
    export CDK_DEFAULT_REGION="$AWS_REGION"
    
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo ""
    
    # Deploy all stacks
    cdk deploy --all --require-approval never --outputs-file outputs.json
    
    if [ -f outputs.json ]; then
        echo ""
        echo "✅ Infrastructure deployment completed!"
        echo "📋 Stack outputs:"
        cat outputs.json | jq . 2>/dev/null || cat outputs.json
        
        # Save outputs for other scripts
        cp outputs.json ../../deployment-outputs.json
    else
        echo "⚠️ No outputs file generated"
    fi
    
    cd ../..
    echo ""
}

deploy_backend() {
    if [ "$DEPLOY_BACKEND" != "true" ]; then
        echo "⏭️ Skipping backend deployment"
        return 0
    fi
    
    echo "⚡ Deploying Backend Lambda Functions..."
    
    cd backend
    
    # Create deployment package for API Lambda
    echo "📦 Creating API Lambda package..."
    rm -rf package api-package.zip
    mkdir package
    
    # Install dependencies
    pip install -r requirements.txt -t package/
    
    # Copy application code
    cp -r app/ package/
    cp ../aws/lambda/api/lambda_handler.py package/
    
    # Create zip
    cd package && zip -r ../api-package.zip . && cd ..
    
    echo "✅ API package created: $(du -h api-package.zip | cut -f1)"
    
    # Create deployment package for Worker Lambda
    echo "📦 Creating Worker Lambda package..."
    rm -rf worker-package worker-package.zip
    mkdir worker-package
    
    # Install dependencies
    pip install -r requirements.txt -t worker-package/
    
    # Copy application code
    cp -r app/ worker-package/
    cp ../aws/lambda/worker/lambda_handler.py worker-package/
    
    # Create zip
    cd worker-package && zip -r ../worker-package.zip . && cd ..
    
    echo "✅ Worker package created: $(du -h worker-package.zip | cut -f1)"
    
    # Update Lambda functions (if they exist)
    API_FUNCTION_NAME="job-queue-api-$ENVIRONMENT"
    WORKER_FUNCTION_NAME="job-queue-worker-$ENVIRONMENT"
    
    if aws lambda get-function --function-name "$API_FUNCTION_NAME" &>/dev/null; then
        echo "📤 Updating API Lambda function..."
        aws lambda update-function-code \
            --function-name "$API_FUNCTION_NAME" \
            --zip-file fileb://api-package.zip
        echo "✅ API Lambda updated"
    else
        echo "ℹ️ API Lambda function will be created by CDK"
    fi
    
    if aws lambda get-function --function-name "$WORKER_FUNCTION_NAME" &>/dev/null; then
        echo "📤 Updating Worker Lambda function..."
        aws lambda update-function-code \
            --function-name "$WORKER_FUNCTION_NAME" \
            --zip-file fileb://worker-package.zip
        echo "✅ Worker Lambda updated"
    else
        echo "ℹ️ Worker Lambda function will be created by CDK"
    fi
    
    cd ..
    echo ""
}

deploy_frontend() {
    if [ "$DEPLOY_FRONTEND" != "true" ]; then
        echo "⏭️ Skipping frontend deployment"
        return 0
    fi
    
    echo "🌐 Building Frontend..."
    
    cd frontend
    
    # Install dependencies
    echo "📦 Installing frontend dependencies..."
    npm ci || npm install
    
    # Build
    echo "🏗️ Building frontend..."
    export NODE_ENV=production
    export NEXT_PUBLIC_API_URL="${API_GATEWAY_URL:-https://api-$ENVIRONMENT.job-queue.aws}"
    npm run build
    
    echo "✅ Frontend build completed"
    echo "ℹ️ Frontend deployment to S3/CloudFront is not yet implemented"
    echo "   Next step: Configure S3 bucket and CloudFront distribution"
    
    cd ..
    echo ""
}

show_summary() {
    echo "🎉 Deployment Summary"
    echo "===================="
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo ""
    
    if [ -f deployment-outputs.json ]; then
        echo "📋 Infrastructure Outputs:"
        cat deployment-outputs.json | jq . 2>/dev/null || cat deployment-outputs.json
        echo ""
    fi
    
    echo "🔧 Next Steps:"
    echo "1. Test the API endpoints"
    echo "2. Monitor CloudWatch logs"
    echo "3. Set up frontend deployment (S3/CloudFront)"
    echo "4. Configure monitoring and alerts"
    echo ""
    echo "📚 Useful Commands:"
    echo "aws logs tail /aws/lambda/job-queue-api-$ENVIRONMENT --follow"
    echo "aws logs tail /aws/lambda/job-queue-worker-$ENVIRONMENT --follow"
    echo "aws sqs get-queue-attributes --queue-url [QUEUE_URL] --attribute-names All"
    echo ""
}

# Parse command line arguments
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        --no-backend)
            DEPLOY_BACKEND=false
            shift
            ;;
        --no-frontend)
            DEPLOY_FRONTEND=false
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo "❌ Invalid environment: $ENVIRONMENT"
    echo "   Valid options: staging, production"
    exit 1
fi

# Main execution
main() {
    echo "Configuration:"
    echo "- Environment: $ENVIRONMENT"
    echo "- Region: $AWS_REGION"
    echo "- Deploy Backend: $DEPLOY_BACKEND"
    echo "- Deploy Frontend: $DEPLOY_FRONTEND"
    echo "- Check Only: $CHECK_ONLY"
    echo ""
    
    check_prerequisites
    validate_infrastructure
    
    if [ "$CHECK_ONLY" = "true" ]; then
        echo "✅ Check completed successfully!"
        exit 0
    fi
    
    bootstrap_cdk
    deploy_infrastructure
    deploy_backend
    deploy_frontend
    show_summary
}

# Run main function
main