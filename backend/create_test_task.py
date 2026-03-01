"""Create a test task for the authenticated worker to process."""
import requests
import time

# Admin login
print('🔐 Admin login...')
admin_login = requests.post(
    'http://localhost:8001/api/v1/auth/login',
    json={'email': 'admin@example.com', 'password': 'admin123'}
)
admin_token = admin_login.json()['access_token']
print('✅ Admin authenticated')
print()

# Create task
print('📝 Creating new task...')
task_response = requests.post(
    'http://localhost:8001/api/v1/tasks/',
    headers={'Authorization': f'Bearer {admin_token}'},
    json={
        'task_type': 'email_processing',
        'priority': 3,
        'payload': {
            'to': 'test@example.com',
            'subject': '🎉 Worker Auth Test',
            'body': 'Testing authenticated worker claiming and processing this task!'
        }
    }
)
task = task_response.json()
print(f'✅ Task created: {task["id"]}')
print(f'   Status: {task["status"]}')
print(f'   Type: {task["task_type"]}')
print()
print('⏳ Waiting for worker to process task...')
print('   (Check worker terminal for processing logs)')
print()
print(f'Task ID: {task["id"]}')
