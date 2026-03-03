# Job Queue System - AWS Deployment Script (PowerShell)
# This script facilitates the deployment of the job queue system to AWS

param(
    [string]$Environment = "staging",
    [string]$Region = "us-east-1",
    [switch]$NoBackend,
    [switch]$NoFrontend,
    [switch]$CheckOnly,
    [switch]$Help
)

if ($Help) {
    Write-Host "🚀 Job Queue System - AWS Deployment" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\deploy-aws.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Environment        Deployment environment (staging|production) [default: staging]"
    Write-Host "  -Region             AWS region [default: us-east-1]"
    Write-Host "  -NoBackend          Skip backend deployment"
    Write-Host "  -NoFrontend         Skip frontend deployment"
    Write-Host "  -CheckOnly          Only run validation checks"
    Write-Host "  -Help               Show this help message"
    Write-Host ""
    Write-Host "Environment Variables:"
    Write-Host "  AWS_ACCESS_KEY_ID     AWS Access Key"
    Write-Host "  AWS_SECRET_ACCESS_KEY AWS Secret Key"
    Write-Host "  AWS_ACCOUNT_ID        AWS Account ID (optional)"
    Write-Host ""
    exit 0
}

# Validate environment
if ($Environment -notin @("staging", "production")) {
    Write-Host "❌ Invalid environment: $Environment" -ForegroundColor Red
    Write-Host "   Valid options: staging, production" -ForegroundColor Red
    exit 1
}

$DeployBackend = -not $NoBackend
$DeployFrontend = -not $NoFrontend

Write-Host "🚀 Job Queue System - AWS Deployment" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "- Environment: $Environment"
Write-Host "- Region: $Region"
Write-Host "- Deploy Backend: $DeployBackend"
Write-Host "- Deploy Frontend: $DeployFrontend"
Write-Host "- Check Only: $CheckOnly"
Write-Host ""

# Main execution
try {
    # Check Prerequisites
    Write-Host "🔍 Checking prerequisites..." -ForegroundColor Blue
    
    # Check AWS CLI
    if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Host "❌ AWS CLI is not installed. Please install it first." -ForegroundColor Red
        Write-Host "   Download from: https://aws.amazon.com/cli/" -ForegroundColor Red
        exit 1
    }
    
    # Check AWS credentials
    $awsTest = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ AWS credentials not configured or invalid." -ForegroundColor Red
        Write-Host "   Run: aws configure" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ AWS CLI and credentials verified" -ForegroundColor Green
    
    if ($CheckOnly) {
        Write-Host "✅ Prerequisites check completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🚀 Next steps to deploy:" -ForegroundColor Cyan
        Write-Host "1. Run: .\deploy-aws.ps1 -Environment staging" -ForegroundColor Yellow
        Write-Host "2. Monitor the deployment progress" -ForegroundColor Yellow
        Write-Host "3. Test the deployed endpoints" -ForegroundColor Yellow
        exit 0
    }
    
    # Validate Infrastructure
    Write-Host "🔍 Validating infrastructure..." -ForegroundColor Blue
    Push-Location "aws\infrastructure"
    npm install
    npm run build
    $env:ENVIRONMENT = $Environment
    cdk synth --quiet
    Pop-Location
    Write-Host "✅ Infrastructure validation completed" -ForegroundColor Green
    
    # Bootstrap CDK
    Write-Host "🚀 Bootstrapping CDK..." -ForegroundColor Blue
    Push-Location "aws\infrastructure"
    $env:ENVIRONMENT = $Environment
    $env:CDK_DEFAULT_REGION = $Region
    cdk bootstrap
    Pop-Location
    Write-Host "✅ CDK bootstrap completed" -ForegroundColor Green
    
    # Deploy Infrastructure
    Write-Host "🏗️ Deploying infrastructure..." -ForegroundColor Blue
    Push-Location "aws\infrastructure"
    cdk deploy --all --require-approval never --outputs-file outputs.json
    if (Test-Path "outputs.json") {
        Copy-Item "outputs.json" "..\..\deployment-outputs.json"
        Write-Host "✅ Infrastructure deployed successfully" -ForegroundColor Green
    }
    Pop-Location
    
    Write-Host ""
    Write-Host "🎉 Deployment completed!" -ForegroundColor Green
    Write-Host "Check the AWS Console for deployed resources." -ForegroundColor Yellow
    Write-Host "Next: Configure your frontend with the API Gateway URL from outputs." -ForegroundColor Yellow
    
} catch {
    Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
    exit 1
}