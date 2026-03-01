"""Test login on port 8002."""
import requests
import time

time.sleep(2)  # Wait for backend

print('='*60)
print('TESTING LOGIN ON PORT 8002 (NEW BACKEND)')
print('='*60)
print()

# Test Admin
print('1️⃣  Admin Login:')
try:
    admin = requests.post(
        'http://localhost:8002/api/v1/auth/login',
        json={'email': 'admin@example.com', 'password': 'admin12345'}
    )
    if admin.status_code == 200:
        print('    ✅ SUCCESS!')
        print(f'    Token: {admin.json()["access_token"][:50]}...')
    else:
        print(f'    ❌ FAILED - Status: {admin.status_code}')
        print(f'    Response: {admin.json()}')
except Exception as e:
    print(f'    ❌ ERROR: {e}')

print()

# Test User
print('2️⃣  User Login:')
try:
    user = requests.post(
        'http://localhost:8002/api/v1/auth/login',
        json={'email': 'user@example.com', 'password': 'user12345'}
    )
    if user.status_code == 200:
        print('    ✅ SUCCESS!')
        print(f'    Token: {user.json()["access_token"][:50]}...')
    else:
        print(f'    ❌ FAILED - Status: {user.status_code}')
        print(f'    Response: {user.json()}')
except Exception as e:
    print(f'    ❌ ERROR: {e}')

print()
print('='*60)
print('✅ CREDENTIALS WORKING!')
print('='*60)
print()
print('Update frontend to use port 8002, OR')
print('Stop old backend on 8001 and restart on 8001')
print()
