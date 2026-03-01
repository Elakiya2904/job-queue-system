# 🚀 Start Worker & Watch Tasks Process

## Quick Start

Open a **new PowerShell terminal** and run:

```powershell
cd c:\Users\vlela\OneDrive\Desktop\job-queue-system

$env:DATABASE_URL = "sqlite:///./backend/data/job_queue.db"
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe .\backend\start_worker.py
```

---

## What You'll See

```
🟢 Worker starting...
✅ Connected to database
📋 Worker ID: worker_abc12345
⚡ Capabilities: email_processing, data_processing, notification
🔄 Polling for tasks every 1 second...

[2026-02-28 10:15:01] 🔍 Checking for tasks...
[2026-02-28 10:15:02] 🎯 Found task: task_2c3fa9ad86ea
[2026-02-28 10:15:02] 🔒 Claimed task (type: email_processing)
[2026-02-28 10:15:02] ⚙️ Processing...
[2026-02-28 10:15:05] ✅ Task completed successfully!
[2026-02-28 10:15:05] 🔄 Looking for next task...
[2026-02-28 10:15:06] 🔍 Checking for tasks...
[2026-02-28 10:15:07] 💤 No tasks found, waiting...
```

---

## 🎯 Complete Demo Flow

### Terminal 1: Backend Server (Already Running)
```powershell
# Should already be running on port 8001
# If not, start it:
cd backend
$env:DATABASE_URL = "sqlite:///./data/job_queue.db"
$env:PYTHONPATH = "$PWD"
C:/Users/vlela/OneDrive/Desktop/job-queue-system/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 2: Frontend UI (Already Running)
```powershell
# Should already be running on port 3000
# Open http://localhost:3000
```

### Terminal 3: Worker (NEW - Start this!)
```powershell
cd c:\Users\vlela\OneDrive\Desktop\job-queue-system
$env:DATABASE_URL = "sqlite:///./backend/data/job_queue.db"
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe .\backend\start_worker.py
```

### Terminal 4: Watch Live Updates (Optional)
```powershell
# Watch tasks in database
cd c:\Users\vlela\OneDrive\Desktop\job-queue-system
$env:DATABASE_URL = "sqlite:///./backend/data/job_queue.db"
$env:PYTHONPATH = "$PWD\backend"

# Run this repeatedly to see status changes:
.\.venv\Scripts\python.exe -c "
from app.db.base import SessionLocal
from app.models.task import Task

session = SessionLocal()
tasks = session.query(Task).order_by(Task.updated_at.desc()).limit(5).all()
print('Recent tasks:')
for t in tasks:
    icon = {'completed': '✅', 'processing': '⚙️', 'queued': '⏳', 'failed': '❌'}.get(t.status, '❓')
    print(f'{icon} {t.type} - {t.status}')
session.close()
"
```

---

## 📊 Timeline Example

```
Time: 00:00 → You create task in UI
Time: 00:01 → Task appears with status "queued" ⏳
Time: 00:02 → Worker polls database
Time: 00:03 → Worker finds & claims task
Time: 00:03 → Status changes to "processing" ⚙️
Time: 00:04 → Worker executing...
Time: 00:05 → Worker executing...
Time: 00:06 → Worker executing...
Time: 00:08 → Execution completes
Time: 00:08 → Status changes to "completed" ✅
Time: 00:09 → UI auto-refreshes, shows completion
Time: 00:10 → Worker looks for next task
```

---

## 🎭 Watch In Real-Time

### In the UI (http://localhost:3000/tasks)
1. **Before worker starts:**
   - Your task shows status: **⏳ Queued**
   - "Locked By" column: empty
   - "Started At": empty

2. **Worker claims task:**
   - Status changes to: **⚙️ Processing**
   - "Locked By": `worker_xyz789`
   - "Started At": timestamp appears

3. **Task completes:**
   - Status changes to: **✅ Completed**
   - "Completed At": timestamp appears
   - Execution time displayed (e.g., "4.2s")

### In Worker Terminal
```
[10:15:01] 🔍 Polling for tasks...
[10:15:02] 🎯 Found task: task_abc123 (email_processing)
[10:15:02] 🔒 Claiming task...
[10:15:02] ⚙️ Executing EmailExecutor...
[10:15:03]    → Validating payload
[10:15:03]    → To: user@example.com
[10:15:03]    → Subject: Welcome Email
[10:15:04]    → Simulating email send...
[10:15:06]    → Email sent successfully!
[10:15:06] ✅ Task completed in 4.2s
[10:15:06] 🔄 Ready for next task
```

---

## 🔥 Multiple Workers (Advanced)

You can run **multiple workers** for parallel processing!

### Terminal 3: Worker 1
```powershell
.\.venv\Scripts\python.exe .\backend\start_worker.py
```

### Terminal 4: Worker 2
```powershell
.\.venv\Scripts\python.exe .\backend\start_worker.py
```

### Terminal 5: Worker 3
```powershell
.\.venv\Scripts\python.exe .\backend\start_worker.py
```

**Result:** Tasks get processed 3x faster! 🚀

---

## ⚠️ Worker Won't Process If:

1. **Task type not supported:**
   - Worker supports: `email_processing`, `data_processing`, `notification`
   - Worker DOESN'T support: `file_conversion`
   - Unsupported tasks stay in "queued" status

2. **Worker not running:**
   - Tasks just sit in "queued" status
   - Start a worker to process them!

3. **Database connection issues:**
   - Check DATABASE_URL environment variable
   - Make sure SQLite database file exists

---

## 🎯 Test It Now!

1. **Start the worker** (Terminal 3 above)
2. **Create a task** in UI at http://localhost:3000/tasks
3. **Watch both:**
   - Worker terminal (see logs)
   - UI tasks table (see status changes)
4. **See the magic!** ✨

---

## 🐛 Troubleshooting

### Worker says "No tasks found"
- ✅ This is normal! Worker is waiting for tasks
- Create a task in the UI to see it process

### Worker crashes on startup
- Check DATABASE_URL is correct
- Check PYTHONPATH is correct
- Make sure backend/data/job_queue.db exists

### Task stays "queued"
- Check worker is running
- Check task type is supported
- Check worker logs for errors

### Multiple workers claim same task
- ✅ This shouldn't happen! Database locking prevents it
- If it does, there's a bug in the locking mechanism

---

## 📈 Monitor Workers

### In UI (http://localhost:3000/workers)
- See all active workers
- Check their status (active/idle)
- View last heartbeat
- See what tasks they're working on

### Dashboard (http://localhost:3000/dashboard)
- Total tasks processed
- Average execution time
- Success rate
- Tasks by status

---

## 🎉 You're Ready!

Now you understand the complete flow:
1. ✅ Create task → queued
2. ✅ Worker starts → polling
3. ✅ Worker finds task → claims it
4. ✅ Worker processes → executing
5. ✅ Task completes → done!

**Start that worker and watch the magic happen!** 🚀
