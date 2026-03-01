"""Test user login on port 8002."""
import requests

print('Testing User Login on Port 8002')
print('='*60)

try:
    response = requests.post(
        'http://localhost:8002/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'user12345'
        },
        timeout=5
    )
    
    print(f'Status Code: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        print(f'✅ SUCCESS!')
        print(f'User ID: {data["user"]["id"]}')
        print(f'User Email: {data["user"]["email"]}')
        print(f'User Role: {data["user"]["role"]}')
        print(f'Token: {data["access_token"][:50]}...')
    else:
        print(f'❌ FAILED!')
        print(f'Response: {response.text}')
        
except requests.exceptions.ConnectionError:
    print('❌ ERROR: Cannot connect to backend on port 8002')
    print('Backend might not be running!')
except Exception as e:
    print(f'❌ ERROR: {e}')
