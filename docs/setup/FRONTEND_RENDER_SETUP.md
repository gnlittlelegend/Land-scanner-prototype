# Frontend Render Setup - Important Information

## Current Frontend Architecture

The frontend is a **static HTML/CSS/JavaScript site**, NOT a React app or Node.js application.

### Key Point: Frontend Does NOT Need Environment Variables

The frontend JavaScript uses:
```javascript
const API_BASE = window.location.origin;
```

This means:
- ✅ Frontend auto-detects API URL from its own domain
- ✅ No environment variables needed for static sites
- ✅ Frontend works with backend automatically if they're on same domain

---

## Render Frontend Service Configuration

### Current Setup (Static Site Service)

Since frontend is a static site:
1. It's deployed as a **Static Site** on Render
2. No build process (just serves HTML/CSS/JS files)
3. No environment variables needed
4. No Node.js/npm required

### Settings on Render Dashboard

Go to: **land-scanner-prototype** service → **Settings**

**No Environment Variables Needed!**

The only settings you need are:

| Setting | Value |
|---------|-------|
| **Build Command** | (leave empty or use default) |
| **Publish Directory** | `frontend` |
| **Root Directory** | (leave empty) |
| **Branch** | `main` |

---

## Why Frontend Doesn't Need Environment Variables

**Backend serves frontend:**
```python
# In backend/main.py
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
```

**Frontend auto-discovers API:**
```javascript
// In frontend/js/app.js
const API_BASE = window.location.origin;  // Uses current domain
```

**Result:**
- Frontend loads from: `https://land-scanner-prototype-backend.onrender.com/`
- API calls go to: `https://land-scanner-prototype-backend.onrender.com/analyze`
- Both on same domain = No CORS issues

---

## Current Issue: Frontend as Separate Static Site

You have TWO frontend services on Render:

1. **land-scanner-prototype** (Static Site)
   - Serves frontend files
   - URL: https://land-scanner-prototype.onrender.com
   - But backend is at different domain!
   - This causes CORS issues

2. **land-scanner-prototype-backend** (Web Service)
   - Serves backend API
   - Also serves frontend as static files
   - URL: https://land-scanner-prototype-backend.onrender.com
   - Frontend here works perfectly

---

## Recommended Solution: Delete Separate Frontend Service

Since backend already serves frontend, you have two options:

### Option A: Keep Only Backend (Recommended)
1. Delete the **land-scanner-prototype** static site service
2. Use only **land-scanner-prototype-backend**
3. Access at: `https://land-scanner-prototype-backend.onrender.com`
4. Everything works together!

### Option B: Keep Separate Services (Needs Configuration)
If you must keep both:

1. Modify frontend/js/app.js to use backend URL:
```javascript
// Change this:
const API_BASE = window.location.origin;

// To this:
const API_BASE = 'https://land-scanner-prototype-backend.onrender.com';
```

2. No environment variables needed (static site doesn't support them)
3. Frontend at: https://land-scanner-prototype.onrender.com
4. Backend at: https://land-scanner-prototype-backend.onrender.com

---

## Step-by-Step: Fix Frontend on Render

### If Keeping Only Backend (Recommended):

1. Delete the **land-scanner-prototype** static site
2. Access frontend at: `https://land-scanner-prototype-backend.onrender.com`
3. No configuration needed - it all works!

### If Keeping Both Services:

1. Edit `frontend/js/app.js`
2. Find line: `const API_BASE = window.location.origin;`
3. Replace with: `const API_BASE = 'https://land-scanner-prototype-backend.onrender.com';`
4. Commit and push to GitHub
5. Trigger rebuild of frontend service on Render

---

## Why Environment Variables Don't Work with Static Sites

Static site hosting (like Render's static service) serves files as-is:
- HTML files are served unchanged
- JavaScript files are served unchanged
- No build process to inject environment variables
- No runtime to substitute variables

**Only works with:**
- React apps (build process injects vars)
- Vue apps (build process injects vars)
- Node.js apps (runtime reads env vars)
- Python apps (runtime reads env vars)

---

## Current Architecture

```
Option 1: Unified (Recommended)
┌─────────────────────────────────────────┐
│ land-scanner-prototype-backend          │
├─────────────────────────────────────────┤
│ Frontend (Static Files via /mount)      │
│ Backend API (/analyze, /health, etc)    │
│ CORS: Enabled ✓                         │
└─────────────────────────────────────────┘
URL: https://land-scanner-prototype-backend.onrender.com


Option 2: Separate (Current - Broken)
┌──────────────────────────┐  ┌──────────────────────────┐
│ land-scanner-prototype   │  │ land-scanner-prototype   │
│ (Static Site)            │  │ -backend (Web Service)   │
├──────────────────────────┤  ├──────────────────────────┤
│ Frontend Files           │  │ Frontend (Mounted)       │
│                          │  │ Backend API              │
│ CORS: ✗ (Different URL)  │  │ CORS: Enabled ✓          │
└──────────────────────────┘  └──────────────────────────┘
URL: https://...prototype    URL: https://...backend
         ↓ Fails (CORS) ↓
Frontend cannot call backend API
```

---

## Frontend Settings Summary

### For Static Site Service (If Keeping Separate):
- **Build Command**: (leave empty)
- **Publish Directory**: `frontend`
- **Environment**: ❌ NOT NEEDED (static sites don't support env vars)
- **Root Directory**: (leave empty)

### For Backend Service (Recommended Approach):
- **Runtime**: Docker
- **Dockerfile Path**: `./Dockerfile`
- **Start Command**: (empty - Dockerfile has CMD)
- **Environment**: Set the 16 backend variables (as per RENDER_ENV_FINAL.md)

---

## What To Do Now

### Quick Fix (Recommended):
1. Go to Render Dashboard
2. Delete service: **land-scanner-prototype** (static site)
3. Keep only: **land-scanner-prototype-backend**
4. Access frontend at: `https://land-scanner-prototype-backend.onrender.com`
5. Done! Everything works

### Alternative Fix (If You Want Separate Frontend):
1. Edit `frontend/js/app.js` line 6
2. Change: `const API_BASE = window.location.origin;`
3. To: `const API_BASE = 'https://land-scanner-prototype-backend.onrender.com';`
4. Commit and push
5. Trigger rebuild on Render frontend service

---

## Verification

After fix, test:

```bash
# Frontend loads
curl https://land-scanner-prototype-backend.onrender.com/

# Returns HTML ✓

# API works
curl https://land-scanner-prototype-backend.onrender.com/health

# Returns JSON ✓

# In browser: Open DevTools (F12) → Console
# Should see NO CORS errors ✓
```

---

**Summary**: Static sites on Render don't support environment variables. Frontend auto-discovers backend from window.location.origin. Best solution: Delete separate frontend service and use backend's mounted frontend instead.

**Next Step**: Choose Option A (delete frontend service) or Option B (hardcode API URL in frontend)

---

**Updated**: August 1, 2026  
**Status**: Frontend Configuration Complete
