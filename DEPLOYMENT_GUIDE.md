# AWS Deployment Quick Start Guide

This guide helps you get started with deploying the Job Queue System to AWS.

## 🚀 Prerequisites

### Required Tools
- **AWS CLI v2**: [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Node.js 18+**: [Download Node.js](https://nodejs.org/)
- **Python 3.11+**: [Download Python](https://www.python.org/downloads/)
- **Git**: [Download Git](https://git-scm.com/downloads)

### AWS Account Setup
1. **AWS Account**: Ensure you have an AWS account with appropriate permissions
2. **AWS Credentials**: Configure your AWS credentials:
   ```bash
   aws configure
   ```
3. **GitHub Secrets** (for GitHub Actions deployment):
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY` 
   - `AWS_ACCOUNT_ID` (optional but recommended)

## 🎯 Deployment Options

### Option 1: GitHub Actions Deployment (Recommended)

1. **Set up GitHub Secrets**:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `AWS_ACCESS_KEY_ID`: Your AWS access key
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
     - `AWS_ACCOUNT_ID`: Your AWS account ID (optional)

2. **Trigger Deployment**:
   - Go to Actions tab in GitHub
   - Select "☁️ AWS Deployment" workflow
   - Click "Run workflow"
   - Choose environment (staging/production)
   - Click "Run workflow"

3. **Monitor Progress**:
   - Watch the workflow execution in GitHub Actions
   - Check CloudWatch logs in AWS Console

### Option 2: Local Deployment

#### Windows (PowerShell)
```powershell
# Clone the repository (if not already done)
git clone <your-repo-url>
cd job-queue-system

# Run deployment script
.\deploy-aws.ps1 -Environment staging

# Or with specific options
.\deploy-aws.ps1 -Environment staging -Region us-east-1 -CheckOnly
```

#### Linux/Mac (Bash)
```bash
# Clone the repository (if not already done)
git clone <your-repo-url>
cd job-queue-system

# Make script executable
chmod +x deploy-aws.sh

# Run deployment script
./deploy-aws.sh --environment staging

# Or with specific options
./deploy-aws.sh --environment staging --region us-east-1 --check-only
```

## 🔧 Deployment Steps Explained

### 1. Prerequisites Check
- Verifies AWS CLI installation and credentials
- Checks Node.js, Python, and other dependencies
- Installs AWS CDK if needed

### 2. Infrastructure Deployment
- Deploys AWS resources using CDK:
  - SQS queues (main and dead letter)
  - RDS Aurora Serverless PostgreSQL
  - Lambda functions (API and Worker)
  - API Gateway
  - VPC, Security Groups, IAM roles

### 3. Backend Deployment
- Packages FastAPI application for Lambda
- Creates separate packages for API and Worker functions
- Updates Lambda function code

### 4. Frontend Build
- Builds Next.js application for production
- Prepares for S3/CloudFront deployment (manual step)

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────┐
│              AWS CLOUD                  │
│                                         │
│  ┌────────────┐    ┌─────────────────┐  │
│  │ API Gateway│────│ Lambda (API)    │  │
│  └────────────┘    └─────────────────┘  │
│                                         │
│  ┌────────────┐    ┌─────────────────┐  │
│  │    SQS     │────│ Lambda (Worker) │  │
│  │   Queue    │    └─────────────────┘  │
│  └────────────┘                        │
│                                         │
│  ┌─────────────────────────────────────┐  │
│  │        RDS PostgreSQL               │  │
│  │      (Aurora Serverless)            │  │
│  └─────────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## 🔍 Validation & Testing

### 1. Check Infrastructure
```bash
# Validate without deploying
./deploy-aws.sh --check-only

# Or on Windows
.\deploy-aws.ps1 -CheckOnly
```

### 2. Test API Endpoints
Once deployed, test your API:
```bash
# Get your API Gateway URL from deployment outputs
export API_URL="your-api-gateway-url"

# Test health endpoint
curl $API_URL/health

# Test authentication (use your actual credentials)
curl -X POST $API_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

### 3. Monitor CloudWatch Logs
```bash
# Monitor API Lambda logs
aws logs tail /aws/lambda/job-queue-api-staging --follow

# Monitor Worker Lambda logs  
aws logs tail /aws/lambda/job-queue-worker-staging --follow

# Check SQS queue
aws sqs get-queue-attributes \
  --queue-url "your-queue-url" \
  --attribute-names All
```

## ⚠️ Common Issues & Solutions

### Issue: CDK Bootstrap Error
**Solution**: Your account needs to be bootstrapped for CDK:
```bash
cdk bootstrap aws://YOUR-ACCOUNT-ID/YOUR-REGION
```

### Issue: Lambda Package Too Large
**Solution**: The system automatically packages dependencies. If too large:
- Use Lambda layers for shared dependencies
- Optimize dependencies in `requirements.txt`

### Issue: Database Connection Error
**Solution**: 
- Check VPC security groups
- Verify RDS is in the correct subnets
- Check database credentials in Secrets Manager

### Issue: SQS Permission Denied
**Solution**:
- Verify IAM roles have SQS permissions
- Check SQS queue policy
- Ensure Lambda functions have correct execution roles

## 🎯 Next Steps After Deployment

1. **Test System End-to-End**:
   - Create tasks via API
   - Verify workers process tasks
   - Check task status updates

2. **Set Up Monitoring**:
   - Configure CloudWatch alarms
   - Set up notification channels
   - Review Lambda metrics

3. **Configure Frontend Deployment**:
   - Set up S3 bucket for static hosting
   - Configure CloudFront distribution
   - Update DNS records

4. **Production Hardening**:
   - Review security groups
   - Enable AWS WAF for API Gateway
   - Set up backup policies
   - Configure auto-scaling policies

## 📞 Support

- **Documentation**: Check `README.md` and `AWS_MIGRATION.md`
- **Testing Results**: See `CONCURRENCY_TESTING_RESULTS.md`
- **Infrastructure Code**: Review `aws/infrastructure/` directory

Happy deploying! 🚀