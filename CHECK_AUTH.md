# 🔐 Authentication Troubleshooting

## The Issue
You're seeing **"Not authenticated"** error when trying to create tasks. This means your JWT token has expired or isn't being sent to the backend.

---

## ✅ Quick Solutions (Try in Order)

### Solution 1: Check Your Login Status
Open browser console (F12) and run:
```javascript
localStorage.getItem('auth_token')
localStorage.getItem('user')
```

**If both are NULL or undefined:**
- You're not logged in!
- Go to http://localhost:3000/login
- Login with: `admin@example.com` / `admin123`

**If both exist:**
- Your token might be expired
- Clear localStorage and login again:
  ```javascript
  localStorage.clear()
  ```
- Then refresh and login

---

### Solution 2: Re-Login via URL
1. Go to http://localhost:3000/login
2. Login with: `admin@example.com` / `admin123`
3. Go back to http://localhost:3000/tasks
4. Try creating the task again

---

### Solution 3: Clear Browser Data
1. Open DevTools (F12)
2. Go to Application tab → Local Storage
3. Clear `auth_token` and `user`
4. Refresh the page
5. Login again

---

## 🎯 Test Authentication

Open browser console (F12) and run this to test your token:

```javascript
fetch('http://localhost:8001/api/v1/tasks/', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
    'Content-Type': 'application/json'
  }
})
.then(r => r.json())
.then(data => console.log('✅ Authenticated!', data))
.catch(err => console.error('❌ Not authenticated:', err))
```

**Expected Result:**
- ✅ If working: You'll see your tasks list
- ❌ If broken: You'll see 401 Unauthorized error

---

## 🔧 Why This Happens

JWT tokens expire after a certain time (usually 1-24 hours). When they expire:
- Backend rejects requests with 401 Unauthorized
- You need to login again to get a fresh token

---

## 📝 Complete Login Flow

1. **Login Page** → Enter credentials → Click Login
2. **Backend** → Validates credentials → Returns JWT token
3. **Frontend** → Saves token to localStorage as `auth_token`
4. **All API Calls** → Include token in `Authorization: Bearer <token>` header
5. **Token Expires** → Login again

---

## 🚀 Create Your Task After Login

Once logged in, use this **Email Processing** payload:
```json
{
  "to": "user@example.com",
  "subject": "Welcome Email",
  "body": "Hello from Job Queue System!"
}
```

**OR** this **Notification** payload:
```json
{
  "user_id": "user_001",
  "message": "Your task completed",
  "channels": ["email", "sms"]
}
```

**Important:** Make sure Task Type matches the payload!
- Email Processing → needs `to`, `subject`, `body`
- Notification → needs `user_id`, `message`, `channels`

---

## ⚠️ Common Mistakes

1. **Wrong Task Type for Payload**: Using email_processing with notification payload
2. **Expired Token**: Need to login again
3. **Browser Cached Old State**: Clear cache and refresh
4. **Backend Not Running**: Make sure backend is on port 8001

---

## 🎬 Start Fresh (Nuclear Option)

If nothing works:

```powershell
# In browser console
localStorage.clear()

# Then refresh page and go to:
http://localhost:3000/login

# Login with:
Email: admin@example.com
Password: admin123
```

---

## ✨ Your Task Creation Should Work After This!

The improved error handling will now:
- ✅ Detect authentication errors
- ✅ Show clear error messages
- ✅ Auto-redirect to login page
- ✅ Validate JSON before sending
