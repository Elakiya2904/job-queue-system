"""Check backend status."""
import requests

try:
    r = requests.get('http://localhost:8001/health', timeout=2)
    print(f'✅ Backend is ALIVE! Status: {r.status_code}')
    print(f'   Response: {r.text}')
except Exception as e:
    print(f'❌ Backend is NOT responding: {e}')
