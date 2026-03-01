# Task Creation Examples

## How to Create Tasks in the UI

1. **Open the UI**: Navigate to http://localhost:3000
2. **Login**: Use credentials `admin@example.com` / `admin123`
3. **Go to Tasks Page**: Click on "Tasks" in the sidebar
4. **Click "Create Task" Button**: Blue button in the top right corner
5. **Fill in the Form** using examples below
6. **Click "Create"** to submit

---

## Example Task Payloads

### 1. Email Processing Task
**Task Type:** `email_processing`  
**Priority:** `2` (Normal)  
**Payload:**
```json
{
  "to": "user@example.com",
  "subject": "Welcome to Job Queue System",
  "body": "Your account has been created successfully!"
}
```

---

### 2. Data Processing Task
**Task Type:** `data_processing`  
**Priority:** `1` (High)  
**Payload:**
```json
{
  "dataset_id": "ds_12345",
  "operation": "transform",
  "columns": ["name", "email", "created_at"],
  "filters": {
    "status": "active"
  }
}
```

---

### 3. Notification Task
**Task Type:** `notification`  
**Priority:** `3` (Low)  
**Payload:**
```json
{
  "user_id": "user_001",
  "message": "Your task has been completed",
  "channels": ["email", "sms"],
  "metadata": {
    "task_id": "task_12345"
  }
}
```

---

### 4. File Conversion Task (Will Queue - No Worker Support)
**Task Type:** `file_conversion`  
**Priority:** `2` (Normal)  
**Payload:**
```json
{
  "source_file": "document.pdf",
  "target_format": "docx",
  "quality": "high"
}
```
*Note: This task will remain in 'queued' status because the current worker doesn't support file conversion.*

---

### 5. Complex Email with Attachments
**Task Type:** `email_processing`  
**Priority:** `1` (High)  
**Payload:**
```json
{
  "to": "manager@example.com",
  "cc": ["admin@example.com"],
  "subject": "Monthly Report - January 2026",
  "body": "Please find attached the monthly report.",
  "attachments": [
    {
      "filename": "report_jan_2026.pdf",
      "url": "https://storage.example.com/reports/jan2026.pdf"
    }
  ],
  "send_at": "2026-02-28T10:00:00Z"
}
```

---

### 6. Batch Data Processing
**Task Type:** `data_processing`  
**Priority:** `2` (Normal)  
**Payload:**
```json
{
  "batch_id": "batch_2026_02_28",
  "operation": "aggregate",
  "source_tables": ["orders", "customers", "products"],
  "aggregations": {
    "total_sales": "sum",
    "customer_count": "count",
    "avg_order_value": "avg"
  },
  "output_table": "daily_summary"
}
```

---

### 7. Multi-Channel Notification
**Task Type:** `notification`  
**Priority:** `1` (High)  
**Payload:**
```json
{
  "user_ids": ["user_001", "user_002", "user_003"],
  "message": "System maintenance scheduled for tonight at 10 PM",
  "channels": ["email", "sms", "push"],
  "priority": "urgent",
  "expires_at": "2026-02-28T22:00:00Z"
}
```

---

## Priority Levels

- **1 = High Priority**: Processed first
- **2 = Normal Priority**: Standard processing
- **3 = Low Priority**: Processed when no higher priority tasks

---

## Task Lifecycle

1. **Created** → Task is submitted via UI
2. **Queued** → Task is waiting for a worker
3. **Processing** → Worker has claimed and is executing the task
4. **Completed** ✅ → Task finished successfully
5. **Failed** ❌ → Task encountered an error (with retry logic)

---

## Watch Your Tasks Get Processed

After creating a task:
1. The task appears in the table immediately with status "queued"
2. Within seconds, a worker will claim it (status changes to "processing")
3. Worker executes the task (simulates 3-5 seconds of work)
4. Status changes to "completed" ✅
5. Page auto-refreshes to show updated status

---

## Worker Capabilities

Current worker supports:
- ✅ `email_processing`
- ✅ `data_processing`
- ✅ `notification`
- ❌ `file_conversion` (not supported - will stay queued)

---

## Testing the System

### Quick Test Workflow:
1. Create an email_processing task
2. Watch it transition from queued → processing → completed
3. Check the execution time in the table
4. Create multiple tasks at once to see parallel processing
5. Try different priority levels to see execution order

### Advanced Testing:
- Create 5 tasks with different priorities
- Observe high priority tasks being processed first
- Check task execution statistics on the Dashboard
- Monitor worker status on the Workers page

---

## API Alternative

You can also create tasks via API:

```bash
# Get auth token first
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# Create task
curl -X POST http://localhost:8001/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "task_type": "email_processing",
    "priority": 2,
    "payload": {
      "to": "test@example.com",
      "subject": "Test",
      "body": "Hello World"
    }
  }'
```

---

## Troubleshooting

**Task stays in "queued" status:**
- Check if worker is running
- Verify task_type is supported by worker
- Check worker logs for errors

**"Invalid JSON" error:**
- Ensure payload is valid JSON format
- Use a JSON validator before submitting
- Check for missing quotes or commas

**Authentication error:**
- Verify you're logged in
- Check token hasn't expired
- Re-login if needed

---

## Next Steps

- **Start a Worker**: Run `$env:DATABASE_URL = "sqlite:///./backend/data/job_queue.db"; $env:PYTHONPATH = "$PWD\backend"; .\.venv\Scripts\python.exe .\backend\start_worker.py` from project root
- **Monitor Dashboard**: View real-time statistics at http://localhost:3000/dashboard
- **Check API Docs**: Visit http://localhost:8001/docs for full API documentation
