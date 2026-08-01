# 🔴 CRITICAL: Force Docker Runtime on Render

## Problem
Render is using native Python 3.14 runtime instead of Docker, causing build failures with `shapely`.

## Solution: Switch to Docker Runtime

### Step 1: Delete Current Backend Service (IMPORTANT!)
1. Go to https://dashboard.render.com
2. Click **land-scanner-prototype-backend** service
3. Click **Settings** (bottom of page)
4. Scroll down to **Delete Web Service**
5. Click **Delete Service** and confirm

⚠️ This is necessary to reconfigure with Docker runtime.

### Step 2: Create New Backend Service with Docker

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Connect your GitHub repository (**gnlittlelegend/Land-scanner-prototype**)
4. Configure as follows:

**General Settings:**
- Name: `land-scanner-prototype-backend`
- Environment: Leave as default
- Region: Auto-assign

**Build Settings:**
- Runtime: **Select "Docker"** (CRITICAL!)
- Dockerfile Path: `./Dockerfile`
- Docker Build Context: `.`

**Start Command:** Leave blank (Dockerfile defines it)

**Environment Variables:**
```
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
PYTHONUNBUFFERED=true
API_HOST=0.0.0.0
API_PORT=8000
APP_NAME=Land Scanner Prototype
APP_VERSION=1.0.0
CORS_ORIGINS=*
REQUEST_TIMEOUT=30
COLLECTION_TIMEOUT=60
ENABLE_OSM=true
ENABLE_ELEVATION=true
ENABLE_LANDCOVER=true
ENABLE_ADMIN_BOUNDARIES=true
ENABLE_ROADS=true
ENABLE_WATER=true
```

5. Click **Create Web Service**
6. Watch the build progress (should take 3-5 minutes)

### Step 3: Verify Build Success

Check the **Logs** tab for:
```
Successfully built [image_id]
Successfully tagged [service]
Pushing to registry...
Successfully pushed [image_id]
Deploying [service]...
Service deployed successfully
```

If you see these messages, the Docker build worked!

### Step 4: Test the Service

```bash
# Health check
curl https://land-scanner-prototype-backend.onrender.com/health

# Status check
curl https://land-scanner-prototype-backend.onrender.com/status
```

Both should return JSON responses without errors.

---

## Why Docker?

| Aspect | Native Python | Docker |
|--------|---------------|--------|
| Python Version | 3.14 (latest) | 3.11 (specified) |
| Build Tools | Missing | Included |
| Shapely Wheels | Not available | Can build |
| Build Time | Fast (fails) | Slower (works) |

---

## Current Configuration

**Backend Service (after changes)**:
- Runtime: Docker ✅
- Dockerfile: Python 3.11 slim ✅
- System Dependencies: build-essential, libgeos-dev, etc. ✅
- Dependencies: shapely 2.0.0, pyproj 3.5.0, etc. ✅

**Expected Build Output**:
```
FROM python:3.11-slim-bookworm
Installing system dependencies...
Installing Python dependencies...
Creating non-root user...
Exposing port 8000
Health check configured
Application ready
```

---

## If Build Still Fails

### Check 1: Dockerfile Exists
```bash
git status
# Should show Dockerfile in tracked files
```

### Check 2: Verify Dockerfile Contents
- Should start with `FROM python:3.11-slim-bookworm`
- Should have `RUN apt-get install...` with build tools
- Should end with `CMD ["uvicorn"...]`

### Check 3: Render Logs
In Dashboard → Service → Logs, look for:
- ❌ "Python 3.14" - Wrong runtime
- ❌ "pkg_resources" - Missing build tools
- ✅ "pip install -r requirements.txt" - Correct runtime

### Check 4: Delete and Retry
If still failing after 10 minutes:
1. Delete service
2. Wait 2 minutes
3. Create new service with Docker selected
4. Make sure "Docker" is clearly selected (not Python)

---

## What Changed in Code

**Dockerfile**:
- Python 3.11 specified
- All system build tools included
- Requirements installed after pip upgrade

**requirements.txt**:
- Downgraded versions for Python 3.11 compatibility
- All packages have pre-built wheels available

**render.yaml**:
- Forces Docker runtime
- Specifies Dockerfile path
- Disables native Python runtime

---

## Summary

| Step | Action | Time |
|------|--------|------|
| 1 | Delete old service | 1 min |
| 2 | Create new service (Docker) | 5 min |
| 3 | Watch build | 3-5 min |
| 4 | Test endpoints | 1 min |

**Total**: ~15 minutes

---

## After Docker Deployment Works

You can then:
1. ✅ Deploy frontend to second Render static site
2. ✅ Configure environment variables
3. ✅ Access frontend at `https://land-scanner-prototype.onrender.com`
4. ✅ Test full integration

---

**Critical Point**: Make sure "Docker" runtime is selected, not "Python". This is the root cause of all build failures.

**Current Status**: Code updated ✅, pushed to GitHub ✅, ready for Docker deployment ✅

---

**Last Updated**: Augu