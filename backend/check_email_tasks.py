"""Check email processing tasks."""
import requests

admin_login = requests.post(
    'http://localhost:8001/api/v1/auth/login',
    json={'email': 'admin@example.com', 'password': 'admin123'}
)
token = admin_login.json()['access_token']

response = requests.get(
    'http://localhost:8001/api/v1/tasks/?type=email_processing',
    headers={'Authorization': f'Bearer {token}'}
)
tasks = response.json()['tasks']
print(f'Found {len(tasks)} email_processing tasks:')
print()
for t in tasks[:10]:
    print(f"  • {t['id']}")
    print(f"    Status: {t['status']}")
    print(f"    Created: {t['created_at']}")
    if t['started_at']:
        print(f"    Started: {t['started_at']}")
    if t['completed_at']:
        print(f"    Completed: {t['completed_at']}")
    print()
