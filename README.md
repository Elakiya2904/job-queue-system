# 🚀 Job Queue System

A scalable, production-ready distributed job queue system built with FastAPI, Next.js, Docker, and AWS.

[![CI/CD](https://github.com/Elakiya2904/job-queue-system/actions/workflows/ci.yml/badge.svg)](https://github.com/Elakiya2904/job-queue-system/actions/workflows/ci.yml)
[![AWS Deploy](https://github.com/Elakiya2904/job-queue-system/actions/workflows/aws-deploy.yml/badge.svg)](https://github.com/Elakiya2904/job-queue-system/actions/workflows/aws-deploy.yml)

## ✅ Current Status

| Component | Status |
|-----------|--------|
| FastAPI Backend | ✅ Production Ready |
| Next.js Frontend | ✅ Production Ready |
| Docker Containers | ✅ Built & Running |
| AWS SQS + DLQ | ✅ Deployed (ap-south-1) |
| AWS SNS | ✅ Deployed |
| AWS Lambda | ✅ Deployed with SQS trigger |
| CloudWatch Logging | ✅ Active (7-day retention) |
| GitHub Actions CI/CD | ✅ Passing |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    AWS (ap-south-1)                       │
│                                                          │
│  Next.js Frontend ──▶ FastAPI Backend ──▶ PostgreSQL     │
│                             │                            │
│                             ▼                            │
│                       Amazon SQS ──▶ Lambda Worker       │
│                             │                            │
│                             ▼                            │
│                     Dead Letter Queue                     │
│                             │                            │
│                             ▼                            │
│               CloudWatch Logs + SNS Alerts               │
└──────────────────────────────────────────────────────────┘
```

### Tech Stack

- **Backend**: FastAPI, Python 3.11, SQLAlchemy, Alembic, JWT Auth
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Radix UI
- **Database**: PostgreSQL (Docker) / Aurora (AWS)
- **Queue**: Amazon SQS with Dead Letter Queue (max 3 retries)
- **Workers**: AWS Lambda (SQS trigger, batch size 10)
- **Notifications**: Amazon SNS
- **Monitoring**: CloudWatch (`/job-queue-system/app`)
- **Containers**: Docker + Docker Compose
- **CI/CD**: GitHub Actions (4 workflows)
- **IaC**: AWS CDK (TypeScript)

---

## 🐳 Docker Quick Start

```bash
# Clone the repo
git clone https://github.com/Elakiya2904/job-queue-system.git
cd job-queue-system

# Set AWS credentials
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret

# Start all services
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

---

## ☁️ AWS Resources

| Resource | Name | Region |
|----------|------|--------|
| SQS Queue | `JobQueue` | ap-south-1 |
| SQS DLQ | `JobQueue-DLQ` | ap-south-1 |
| SNS Topic | `NotificationsTopic` | ap-south-1 |
| Lambda | `BasicFunction` | ap-south-1 |
| IAM Role | `lambda-execution-role` | global |
| CloudWatch | `/job-queue-system/app` | ap-south-1 |

---

## ⚙️ GitHub Actions Workflows

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `ci.yml` | Push / PR | Tests, lint, CDK validate |
| `aws-deploy.yml` | Push to main | Deploy infra + Lambda |
| `security.yml` | Push / Weekly | Bandit, Safety, npm audit |
| `health.yml` | Weekly / Manual | Dependency health check |

### Required Secrets

Add in **Settings → Secrets → Actions**:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_ACCOUNT_ID
```

---

## 🚀 Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python setup_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Worker (new terminal)
cd backend
python start_background_services.py
```

---

## 🔐 API Authentication

Default admin credentials:
- **Email**: `admin@example.com`
- **Password**: `admin12345`

```bash
# Get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin12345"}'

# Use token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/tasks
```

### Key Endpoints

```
POST /api/v1/auth/login           Login
GET  /api/v1/tasks                List tasks
POST /api/v1/tasks                Create task
POST /api/v1/tasks/{id}/claim     Claim task
PUT  /api/v1/tasks/{id}/complete  Complete task
PUT  /api/v1/tasks/{id}/fail      Fail task
POST /api/v1/workers/register     Register worker
GET  /api/v1/workers              List workers
GET  /health                      Health check
GET  /api/v1/admin/metrics        System metrics
```

---

## 🧪 Testing

```bash
cd backend
flake8 app/ --select=E9,F63,F7,F82   # Lint
pytest --cov=app --cov-report=term    # Unit tests

cd ../frontend
npx tsc --noEmit                      # Type check
npm run lint                          # ESLint
```

---

## 📁 Project Structure

```
job-queue-system/
├── backend/                 FastAPI app
│   ├── app/                 API code, models, services
│   ├── alembic/             DB migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                Next.js dashboard
│   ├── app/                 Pages
│   ├── components/          UI components
│   ├── Dockerfile
│   └── package.json
├── worker/                  Background worker service
│   └── Dockerfile
├── aws/
│   ├── infrastructure/      CDK stack (TypeScript)
│   ├── lambda/              Lambda handlers
│   └── structure/           AWS config templates
├── .github/workflows/       CI/CD pipelines
└── docker-compose.yml       Local orchestration
```
