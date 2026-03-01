# 🔐 Worker Authentication Guide

## Overview
Workers now require authentication before they can claim and process tasks. This adds security to your job queue system.

---

## 📋 Pre-configured Worker Credentials

### Worker 1 (Default)
```
Worker ID: worker_01
API Key:   worker_key_123456
Capabilities: email_processing, data_processing, notification
```

### Worker 2
```
Worker ID: worker_02
API Key:   worker_key_789012
Capabilities: email_processing
```

---

## 🚀 How to Start an Authenticated Worker

### Step 1: Update start_worker.py

The worker needs to login before claiming tasks. Let me update the worker code...

---

## 🔑 Worker Authentication Endpoints

### Login Endpoint
```http
POST /api/v1/auth/worker/login
Content-Type: application/json

{
  "worker_id": "worker_01",
  "api_key": "worker_key_123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 28800,
  "worker": {
    "worker_id": "worker_01",
    "capabilities": ["email_processing", "data_processing", "notification"],
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### Register New Worker
```http
POST /api/v1/auth/worker/register
Content-Type: application/json

{
  "worker_id": "worker_03",
  "api_key": "my_secure_key_123",
  "capabilities": ["email_processing", "notification"]
}
```

---

## 🔄 Updated Worker Flow

1. **Worker Starts** → Reads credentials from config/environment
2. **Worker Authenticates** → POST to /api/v1/auth/worker/login
3. **Receives JWT Token** → Stores token for API calls 
4. **Polls for Tasks** → Includes Bearer token in requests
5. **Claims Tasks** → Backend verifies token before allowing claim
6. **Processes Tasks** → Normal execution
7. **Token Expires** → Re-authenticates automatically

---

## 💻 Test Worker Authentication

```powershell
# Test login via PowerShell
$body = @{
    worker_id = "worker_01"
    api_key = "worker_key_123456"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/worker/login" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

Write-Host "Worker logged in!"
Write-Host "Token: $($response.access_token)"
```

---

## 🛡️ Security Benefits

### Before (No Authentication):
- ❌ Any process could claim tasks
- ❌ No tracking of which worker did what
- ❌ No capability verification
- ❌ Anyone with database access could interfere

### After (With Authentication):
- ✅ Only authenticated workers can claim tasks
- ✅ JWT tokens track worker identity
- ✅ Capabilities verified via token
- ✅ API-level security enforced
- ✅ Token expiration prevents stale access

---

## 🔐 Production Recommendations

1. **Use Environment Variables** for API keys:
   ```powershell
   $env:WORKER_ID = "worker_prod_01"
   $env:WORKER_API_KEY = "secure_random_key_here"
   ```

2. **Store API Keys Securely**:
   - Use secrets management (Azure Key Vault, AWS Secrets Manager)
   - Never commit keys to version control
   - Rotate keys regularly

3. **Use HTTPS** in production for API calls

4. **Implement Key Rotation**:
   - Periodically change API keys
   - Support multiple valid keys during transition

5. **Monitor Failed Auth Attempts**:
   - Log failed login attempts
   - Alert on suspicious activity
   - Rate limit authentication endpoints

---

## 📊 Worker Management

### List All Registered Workers
```powershell
# (To be implemented in admin endpoint)
GET /api/v1/admin/workers
Authorization: Bearer <admin_token>
```

### Revoke Worker Access
```powershell
# (To be implemented in admin endpoint)
DELETE /api/v1/admin/workers/{worker_id}
Authorization: Bearer <admin_token>
```

---

## 🐛 Troubleshooting

### Error: "Invalid worker credentials"
- Check worker_id is correct
- Verify API key matches exactly
- Ensure worker is registered in system

### Error: "Token expired"
- Worker token lasts 8 hours (480 minutes)
- Worker should re-authenticate automatically
- Check system time is synchronized

### Error: "Unauthorized" when claiming tasks
- Verify token is included in request headers
- Check token hasn't expired
- Ensure Authorization header format: `Bearer <token>`

---

## 🎯 Next Steps

I'm now updating the worker code to:
1. Read credentials from environment/config
2. Authenticate on startup
3. Include JWT token in all API requests
4. Handle token expiration and re-authentication

Stay tuned...
