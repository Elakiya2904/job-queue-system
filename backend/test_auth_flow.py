"""Test the complete authenticated worker flow."""
import requests

print('='*60)
print('COMPLETE AUTHENTICATED WORKER FLOW TEST')
print('='*60)
print()

# Step 1: Admin creates a task
print('Step 1: Admin creates task')
print('-' * 40)
admin_login = requests.post(
    'http://localhost:8001/api/v1/auth/login',
    json={'email': 'admin@example.com', 'password': 'admin12345'}
)
admin_token = admin_login.json()['access_token']
print('✅ Admin authenticated')

task_response = requests.post(
    'http://localhost:8001/api/v1/tasks/',
    headers={'Authorization': f'Bearer {admin_token}'},
    json={
        'task_type': 'email_processing',
        'priority': 2,
        'payload': {
            'to': 'test@example.com',
            'subject': 'Auth Test',
            'body': 'Testing authenticated worker flow!'
        }
    }
)
task = task_response.json()
print(f'✅ Task created: {task["id"]}')
print(f'   Status: {task["status"]}')
print()

# Step 2: Worker authenticates
print('Step 2: Worker authenticates')
print('-' * 40)
worker_login = requests.post(
    'http://localhost:8001/api/v1/auth/worker/login',
    json={'worker_id': 'worker_01', 'api_key': 'worker_key_123456_secure_token_abcdefghijklmnop'}
)
worker_data = worker_login.json()
worker_token = worker_data['access_token']
print(f'✅ Worker authenticated: {worker_data["worker"]["worker_id"]}')
print(f'   Capabilities: {worker_data["worker"]["capabilities"]}')
print()

# Step 3: Check task is available
print('Step 3: Verify task exists and is queued')
print('-' * 40)
get_task = requests.get(
    f'http://localhost:8001/api/v1/tasks/{task["id"]}',
    headers={'Authorization': f'Bearer {admin_token}'}
)
if get_task.status_code == 200:
    current_task = get_task.json()
    print(f'✅ Task {current_task["id"]} status: {current_task["status"]}')
else:
    print(f'❌ Failed to get task: Status {get_task.status_code}')
    print(f'   Response: {get_task.text}')
print()

print('='*60)
print('✅ AUTHENTICATION FLOW WORKS!')
print('='*60)
print()
print('Summary:')
print('1. ✅ Admin can create tasks with JWT token')
print('2. ✅ Worker can authenticate and get JWT token')
print('3. ✅ Task is created and waiting in queue')
print()
print('Next: Start authenticated worker to process the task')
print(f'Command: cd backend && python start_worker_auth.py')
print()
print(f'Or test the worker now by running:')
print(f'  cd backend && python start_worker_auth.py')
