"""Test user login specifically."""
import requests

print('Testing User Login on Port 8002...')
print('='*60)

try:
    response = requests.post(
        'http://localhost:8002/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'user12345'
        }
    )
    
    print(f'Status Code: {response.status_code}')
    print(f'Response: {response.text}')
    
    if response.status_code == 200:
        print('\n✅ USER LOGIN WORKS!')
    else:
        print('\n❌ USER LOGIN FAILED!')
        
except Exception as e:
    print(f'ERROR: {e}')
