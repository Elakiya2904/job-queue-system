"""Test updated login credentials."""
import requests
import time

time.sleep(2)  # Wait for backend to be ready

print('='*60)
print('TESTING UPDATED LOGIN CREDENTIALS')
print('='*60)
print()

# Test Admin Login
print('1️⃣  Testing Admin Login:')
print('    Email: admin@example.com')
print('    Password: admin12345')
try:
    admin = requests.post(
        'http://localhost:8001/api/v1/auth/login',
        json={'email': 'admin@example.com', 'password': 'admin12345'}
    )
    if admin.status_code == 200:
        print('    ✅ SUCCESS - Admin can login!')
    else:
        print(f'    ❌ FAILED - Status: {admin.status_code}')
        print(f'    Response: {admin.text}')
except Exception as e:
    print(f'    ❌ ERROR: {e}')

print()

# Test User Login
print('2️⃣  Testing User Login:')
print('    Email: user@example.com')
print('    Password: user12345')
try:
    user = requests.post(
        'http://localhost:8001/api/v1/auth/login',
        json={'email': 'user@example.com', 'password': 'user12345'}
    )
    if user.status_code == 200:
        print('    ✅ SUCCESS - User can login!')
    else:
        print(f'    ❌ FAILED - Status: {user.status_code}')
        print(f'    Response: {user.text}')
except Exception as e:
    print(f'    ❌ ERROR: {e}')

print()
print('='*60)
print('UPDATED CREDENTIALS:')
print('='*60)
print()
print('👤 Admin Account:')
print('   Email: admin@example.com')
print('   Password: admin12345')
print()
print('👤 User Account:')
print('   Email: user@example.com')
print('   Password: user12345')
print()
