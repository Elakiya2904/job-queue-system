# Job Queue System

> A scalable, production-ready distributed task queue and job processing system built with modern cloud-native technologies. Designed for high-throughput async task processing with comprehensive monitoring, error handling, and horizontal scaling capabilities.


## 📋 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker Deployment](#docker-deployment)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [AWS Deployment](#aws-deployment)
- [Monitoring & Observability](#monitoring--observability)



---

## Overview

The Job Queue System is an enterprise-grade distributed task queue that enables reliable, scalable asynchronous job processing. It provides:

- **Distributed Task Processing**: Scale horizontally with multiple workers
- **High Availability**: Automatic failover, dead-letter queues, and retry mechanisms
- **Production Monitoring**: Real-time dashboards, health checks, and comprehensive logging
- **Cloud-Native Architecture**: AWS Lambda, SQS, RDS, CloudWatch integration
- **Type Safety**: Full TypeScript/Python type hints for better development experience
- **RestAPI & GraphQL Ready**: RESTful API with automatic documentation

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| **FastAPI** | 0.100+ | High-performance async web framework |
| **Python** | 3.11+ | Core language |
| **SQLAlchemy** | 2.0+ | ORM for database operations |
| **PostgreSQL** | 15.4+ | Primary relational database |
| **Pydantic** | 2.0+ | Data validation & serialization |
| **Alembic** | 1.12+ | Database schema migrations |
| **Uvicorn** | 0.23+ | ASGI application server |

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 14+ | React framework with SSR/SSG |
| **TypeScript** | 5.0+ | Type-safe JavaScript |
| **React** | 18+ | UI component library |
| **Tailwind CSS** | 3.3+ | Utility-first CSS framework |
| **Radix UI** | 1.7+ | Unstyled, accessible components |
| **React Query** | 5.0+ | Server state management |

### Infrastructure & DevOps
| Technology | Version | Purpose |
|-----------|---------|---------|
| **AWS CDK** | 2.0+ | Infrastructure as Code (TypeScript) |
| **AWS Lambda** | Latest | Serverless compute |
| **AWS SQS** | - | Message queue service |
| **AWS RDS Aurora** | PostgreSQL 15.4 | Managed database |
| **AWS API Gateway** | v2 | HTTP API endpoints |
| **Docker** | 24+ | Containerization |
| **Docker Compose** | 2.20+ | Local orchestration |
| **CloudWatch** | - | Logging & monitoring |

### CI/CD & Code Quality
| Technology | Version | Purpose |
|-----------|---------|---------|
| **GitHub Actions** | Latest | Continuous Integration/Deployment |
| **Pytest** | 7.0+ | Python testing framework |
| **Flake8** | 6.0+ | Python linting |
| **Bandit** | 1.7+ | Security vulnerability scanning |
| **ESLint** | 8.0+ | JavaScript/TypeScript linting |

---

## Key Features

### Core Functionality
✅ **Distributed Task Queue** - Reliable asynchronous job processing across multiple workers  
✅ **Task Prioritization** - Support for high/normal/low priority tasks  
✅ **Automatic Retries** - Configurable retry logic with exponential backoff  
✅ **Dead Letter Queue** - Failed tasks automatically routed to DLQ after max retries  
✅ **Worker Management** - Register, monitor, and manage worker instances  
✅ **Task Claiming** - Lock-based task claiming mechanism to prevent duplicate processing  

### Monitoring & Observability
✅ **Real-time Dashboard** - Monitor tasks, workers, and system health  
✅ **Worker Dashboard** - View claimed tasks, completion rates, and performance metrics  
✅ **CloudWatch Integration** - Centralized logging with 7-day retention  
✅ **Health Check Endpoints** - System status and dependency availability  
✅ **Task Metrics** - Track completion rates, failure rates, and processing times  

### Production Ready
✅ **JWT Authentication** - Secure API access with token-based auth  
✅ **Role-Based Access Control** - Admin, worker, and user roles  
✅ **Database Migrations** - Alembic-based schema versioning  
✅ **Error Handling** - Comprehensive error responses with detailed messaging  
✅ **CORS Support** - Pre-configured for modern SPA architectures  

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Cloud (us-east-1)                       │
│                                                                   │
│  ┌──────────────┐         ┌─────────────────────────────────┐   │
│  │  Next.js     │         │     FastAPI Backend (Lambda)    │   │
│  │  Frontend    │◄───────►│   ├── Task Management           │   │
│  │  (S3+CDN)    │         │   ├── Worker Management         │   │
│  └──────────────┘         │   ├── Auth & Security           │   │
│                           │   └── Admin Dashboard           │   │
│                           └─────────────┬───────────────────┘   │
│                                         │                        │
│                                         ▼                        │
│                           ┌─────────────────────────┐           │
│                           │   API Gateway (v2)      │           │
│                           └─────────────┬───────────┘           │
│                                         │                        │
│                    ┌────────────────────┼────────────────────┐  │
│                    ▼                    ▼                    ▼  │
│           ┌──────────────┐      ┌──────────────┐    ┌────────┐ │
│           │  SQS Queue   │      │  Aurora RDS  │    │ Secrets│ │
│           │  (Main)      │      │ (PostgreSQL) │    │Manager │ │
│           └──────┬───────┘      └──────────────┘    └────────┘ │
│                  │                                              │
│                  ▼                                              │
│           ┌──────────────┐      ┌──────────────┐              │
│           │   Lambda     │      │  CloudWatch  │              │
│           │  (Workers)   │      │  (Logging)   │              │
│           └──────┬───────┘      └──────────────┘              │
│                  │                                              │
│                  ▼                                              │
│           ┌──────────────┐                                     │
│           │  SQS DLQ     │                                     │
│           │ (Dead Letter) │                                    │
│           └──────────────┘                                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Task Creation**: Admin/User creates task via API → stored in RDS
2. **Task Queuing**: Task published to SQS queue
3. **Worker Claiming**: Lambda workers poll SQS, claim queued tasks
4. **Processing**: Task executed by worker → results stored in RDS
5. **Retry Logic**: Failed tasks auto-requeued up to max retries
6. **Dead Letter**: Permanently failed tasks moved to DLQ for investigation

---

## Getting Started

### Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Docker 24+** - [Download](https://www.docker.com/products/docker-desktop)
- **Git** - Version control
- **AWS Account** (for cloud deployment) - [Sign up](https://aws.amazon.com/)
- **AWS CLI v2** - [Installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

### Local Development

#### 1. Clone Repository
```bash
git clone https://github.com/yourusername/job-queue-system.git
cd job-queue-system
```

#### 2. Set Up Python Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 4. Initialize Database
```bash
python setup_db.py
```

#### 5. Start Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend available at: **http://localhost:8000**  
API Documentation: **http://localhost:8000/docs**

#### 6. Start Frontend (New Terminal)
```bash
cd frontend
npm install
npm run dev
```

Frontend available at: **http://localhost:3000**

#### 7. Start Background Services (New Terminal)
```bash
cd backend
python start_background_services.py
```

### Docker Deployment

#### 1. Build and Start All Services
```bash
docker-compose up --build
```

#### 2. Access Services
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

#### 3. Tear Down
```bash
docker-compose down
```

---

## Configuration

### Environment Variables

#### Backend (.env)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/jobqueue

# JWT
SECRET_KEY=your-secret-key-min-32-chars-recommended
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS (Optional - for cloud deployment)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Environment
ENVIRONMENT=development
DEBUG=true
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Job Queue System
```

### Database Configuration

Default admin credentials:
```
Email: admin@example.com
Password: admin12345
```

⚠️ **Security**: Change default credentials in production!

---

## API Documentation

### Authentication

All API requests (except `/health`) require JWT bearer token:

```bash
# Get Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin12345"
  }'

# Use Token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/tasks
```

### Core Endpoints

#### Tasks
```
POST   /api/v1/tasks                    Create task
GET    /api/v1/tasks                    List tasks (with filtering)
GET    /api/v1/tasks/{task_id}          Get task details
DELETE /api/v1/tasks/{task_id}          Delete task
POST   /api/v1/tasks/{task_id}/claim    Claim task for processing
PUT    /api/v1/tasks/{task_id}/complete Complete task
PUT    /api/v1/tasks/{task_id}/fail     Mark task as failed
```

#### Workers
```
GET    /api/v1/workers                  List all workers
POST   /api/v1/workers/register         Register new worker
GET    /api/v1/workers/{worker_id}      Get worker details
DELETE /api/v1/workers/{worker_id}      Remove worker
GET    /api/v1/workers/{worker_id}/tasks Get worker's completed tasks
```

#### Admin
```
GET    /api/v1/admin/metrics            System metrics and stats
GET    /health                          Health check
```

### Auto-Generated Documentation

✨ **Interactive Swagger UI**: http://localhost:8000/docs  
📚 **OpenAPI Schema**: http://localhost:8000/openapi.json

---

## Project Structure

```
job-queue-system/
│
├── backend/                          # FastAPI Backend
│   ├── app/
│   │   ├── main.py                   # Application entry point
│   │   ├── api/
│   │   │   ├── auth.py               # Authentication endpoints
│   │   │   ├── tasks.py              # Task management endpoints
│   │   │   ├── workers.py            # Worker management endpoints
│   │   │   └── admin.py              # Admin endpoints
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── schemas/                  # Pydantic request/response models
│   │   ├── services/                 # Business logic
│   │   ├── core/
│   │   │   ├── config.py             # Configuration management
│   │   │   ├── security.py           # JWT & auth utilities
│   │   │   └── dependencies.py       # FastAPI dependencies
│   │   ├── db/                       # Database utilities
│   │   └── middleware/               # Custom middleware
│   ├── alembic/                      # Database migrations
│   ├── requirements.txt              # Python dependencies
│   ├── Dockerfile                    # Container image
│   ├── setup_db.py                   # Database initialization
│   └── lambda_handler.py             # AWS Lambda entry point
│
├── frontend/                         # Next.js Frontend
│   ├── app/
│   │   ├── layout.tsx                # Root layout
│   │   ├── page.tsx                  # Home page
│   │   ├── dashboard/                # Dashboard pages
│   │   ├── tasks/                    # Task management pages
│   │   ├── workers/                  # Worker management pages
│   │   └── login/                    # Authentication pages
│   ├── components/                   # Reusable UI components
│   ├── hooks/                        # Custom React hooks
│   ├── lib/                          # Utilities and helpers
│   │   └── api.ts                    # API client library
│   ├── types/                        # TypeScript type definitions
│   ├── public/                       # Static assets
│   ├── package.json                  # Node.js dependencies
│   ├── tsconfig.json                 # TypeScript configuration
│   ├── tailwind.config.js            # Tailwind CSS configuration
│   ├── Dockerfile                    # Container image
│   └── .env.example                  # Environment variable template
│
├── worker/                           # Background Worker
│   ├── app/
│   │   ├── executors/                # Task execution logic
│   │   ├── services/                 # Worker services
│   │   ├── utils/                    # Utility functions
│   │   └── lambda_handler.py         # Lambda worker handler
│   ├── Dockerfile                    # Container image
│   └── requirements.txt              # Python dependencies
│
├── aws/                              # AWS Infrastructure
│   ├── infrastructure/               # AWS CDK Stack (TypeScript)
│   │   ├── lib/
│   │   │   └── job-queue-stack.ts    # CDK stack definition
│   │   ├── bin/
│   │   │   └── app.ts                # CDK app entry point
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── cdk.json
│   ├── lambda/
│   │   ├── api/                      # API Lambda handler
│   │   └── worker/                   # Worker Lambda handler
│   └── sns/                          # SNS notification setup
│
├── .github/
│   └── workflows/                    # GitHub Actions CI/CD
│       ├── ci.yml                    # Testing & validation
│       ├── aws-deploy.yml            # AWS deployment
│       └── security.yml              # Security scanning
│
├── docker-compose.yml                # Local development orchestration
├── .dockerignore                     # Docker build exclusions
├── .gitignore                        # Git exclusions
├── README.md                         # This file
└── LICENSE                           # MIT License
```

---

## AWS Deployment

### Prerequisites
- AWS Account with appropriate IAM permissions
- AWS CLI v2 configured with credentials
- Node.js 18+ (for CDK)
- Docker (for Lambda packaging)

### Deployment Steps

#### 1. Configure AWS Credentials
```bash
aws configure
# Enter: Access Key, Secret Key, Region (us-east-1), Output format (json)
```

#### 2. Install CDK (if not already installed)
```bash
npm install -g aws-cdk
```

#### 3. Deploy Infrastructure
```bash
cd aws/infrastructure
npm install
cdk synth
cdk deploy --require-approval=never
```

#### 4. Deploy Backend Lambda
```bash
cd ../..
# Build backend package
cd backend
pip install -r requirements.txt -t package/
cp -r app/ lambda_handler.py package/
cd package
zip -r ../backend-lambda.zip .
aws lambda update-function-code \
  --function-name job-queue-api-staging \
  --zip-file fileb://../backend-lambda.zip
```

#### 5. Deploy Worker Lambda
```bash
cd ../../worker
pip install -r requirements.txt -t package/
cp -r app/ lambda_handler.py package/
cd package
zip -r ../worker-lambda.zip .
aws lambda update-function-code \
  --function-name job-queue-worker-staging \
  --zip-file fileb://../worker-lambda.zip
```

### CDK Stack Resources

| Resource | Type | Purpose |
|----------|------|---------|
| RDS Aurora | Database | PostgreSQL cluster (Serverless v2) |
| SQS Queue | Message Queue | Main task queue |
| SQS DLQ | Message Queue | Dead letter queue |
| Lambda API | Compute | REST API handler |
| Lambda Worker | Compute | Task processing |
| API Gateway | HTTP | Public API endpoint |
| CloudWatch | Monitoring | Logging & metrics |
| VPC | Network | Isolated network environment |
| Secrets Manager | Security | Database credentials |

---

## Monitoring & Observability

### CloudWatch Logs
- **Log Group**: `/job-queue-system/app`
- **Retention**: 7 days (configurable)
- **Metrics**: Task processing times, success/failure rates

### Health Checks
```bash
# System health
curl http://localhost:8000/health

# API docs
curl http://localhost:8000/docs
```

### Metrics Dashboard
Access the frontend dashboard at http://localhost:3000
- **System Overview**: Queue depth, worker status, error rates
- **Task Analytics**: Success/failure rates, processing time trends
- **Worker Statistics**: Capacity, current tasks, performance

### Alerts & Notifications
- Failed tasks routed to SQS Dead Letter Queue
- SNS notifications for critical errors (AWS only)
- CloudWatch alarms for queue depth anomalies

---
