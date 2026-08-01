# Render Environment Variables - Final Complete Setup

## Architecture Overview

```
Frontend (Static Site)
    ↓
Backend (FastAPI)
    - Serves frontend at root (/)
    - Provides API at /analyze, /health, /status
    - CORS enabled for all origins
```

**Key Point**: Backend serves frontend statically, so backend does NOT need frontend URL.

---

## Backend Service: land-scanner-prototype-backend

### All Required Environment Variables

| Key | Value | Type | Required |
|-----|-------|------|----------|
| `ENVIRONMENT` | `production` | Config | ✅ Yes |
| `DEBUG` | `false` | Config | ✅ Yes |
| `LOG_LEVEL` | `INFO` | Config | ✅ Yes |
| `PYTHONUNBUFFERED` | `true` | Python | ✅ Yes |
| `API_HOST` | `0.0.0.0` | Config | ✅ Yes |
| `API_PORT` | `8000` | Config | ✅ Yes |
| `APP_NAME` | `Land Scanner Prototype` | Display | ❌ Optional |
| `APP_VERSION` | `1.0.0` | Display | ❌ Optional |
| `CORS_ORIGINS` | `*` | Security | ❌ Optional (default: allow all) |
| `REQUEST_TIMEOUT` | `30` | Performance | ❌ Optional |
| `COLLECTION_TIMEOUT` | `60` | Performance | ❌ Optional |
| `ENABLE_OSM` | `true` | Feature | ❌ Optional |
| `ENABLE_ELEVATION` | `true` | Feature | ❌ Optional |
| `ENABLE_LANDCOVER` | `true` | Feature | ❌ Optional |
| `ENABLE_ADMIN_BOUNDARIES` | `true` | Feature | ❌ Optional |
| `ENABLE_ROADS` | `true` | Feature | ❌ Optional |
| `ENABLE_WATER` | `true` | Feature | ❌ Optional |

### Minimum Required (Just these 4):
```
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
PYTHONUNBUFFERED=true
```

### Recommended (All essentials):
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

---

## Frontend Service: land-scanner-prototype

### All Required Environment Variables

| Key | Value | Type | Required |
|-----|-------|------|----------|
| `REACT_APP_API_URL` | `https://land-scanner-prototype-backend.onrender.com` | Connection | ✅ Yes |
| `REACT_APP_APP_NAME` | `Land Scanner Prototype` | Display | ❌ Optional |
| `REACT_APP_VERSION` | `1.0.0` | Display | ❌ Optional |
| `REACT_APP_ENVIRONMENT` | `production` | Display | ❌ Optional |
| `NODE_ENV` | `production` | Build | ⚠️ Usually auto |

### Minimum Required (Just this 1):
```
REACT_APP_API_URL=https://land-scanner-prototype-backend.onrender.com
```

### Recommended (All essentials):
```
REACT_APP_API_URL=https://land-scanner-prototype-backend.onrender.com
REACT_APP_APP_NAME=Land Scanner Prototype
REACT_APP_VERSION=1.0.0
REACT_APP_ENVIRONMENT=production
NODE_ENV=production
```

---

## ❌ Backend Does NOT Need Frontend URL

**Why?**
1. Backend serves frontend statically (see `app.mount("/", StaticFiles(...)` in main.py)
2. Frontend is built assets served as static files
3. Backend already has `allow_origins=["*"]` for CORS
4. Communication flows: Frontend → Backend (not reverse)

**So DO NOT add**:
- ❌ `FRONTEND_URL`
- ❌ `REACT_APP_URL`
- ❌ `CLIENT_URL`
- ❌ Any frontend-related variables to backend

---

## Step-by-Step Setup

### Backend Setup

1. Go to https://dashboard.render.com
2. Click **land-scanner-prototype-backend**
3. Click **Settings**
4. Scroll to **Environment**
5. Add these variables (copy-paste format):

```
Key: ENVIRONMENT
Value: production

Key: DEBUG
Value: false

Key: LOG_LEVEL
Value: INFO

Key: PYTHONUNBUFFERED
Value: true

Key: API_HOST
Value: 0.0.0.0

Key: API_PORT
Value: 8000

Key: APP_NAME
Value: Land Scanner Prototype

Key: APP_VERSION
Value: 1.0.0

Key: CORS_ORIGINS
Value: *

Key: REQUEST_TIMEOUT
Value: 30

Key: COLLECTION_TIMEOUT
Value: 60

Key: ENABLE_OSM
Value: true

Key: ENABLE_ELEVATION
Value: true

Key: ENABLE_LANDCOVER
Value: true

Key: ENABLE_ADMIN_BOUNDARIES
Value: true

Key: ENABLE_ROADS
Value: true

Key: ENABLE_WATER
Value: true
```

6. Click **Save**
7. Service will auto-redeploy

### Frontend Setup

1. Go to https://dashboard.render.com
2. Click **land-scanner-prototype**
3. Click **Settings**
4. Scroll to **Environment**
5. Add these variables:

```
Key: REACT_APP_API_URL
Value: https://land-scanner-prototype-backend.onrender.com

Key: REACT_APP_APP_NAME
Value: Land Scanner Prototype

Key: REACT_APP_VERSION
Value: 1.0.0

Key: REACT_APP_ENVIRONMENT
Value: production

Key: NODE_ENV
Value: production
```

6. Click **Save**
7. Service will auto-redeploy

---

## Verification After Setup

### Test Backend Health
```bash
curl https://land-scanner-prototype-backend.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Land Scanner Prototype",
  "version": "1.0.0",
  "timestamp": "2026-08-01T..."
}
```

### Test Backend Status
```bash
curl https://land-scanner-prototype-backend.onrender.com/status
```

Expected response:
```json
{
  "prototype_name": "Land Scanner Prototype",
  "version": "1.0.0",
  "timestamp": "2026-08-01T...",
  "enabled_providers": [
    "OpenStreetMap",
    "SRTM Elevation",
    "Copernicus Land Cover",
    "Admin Boundaries",
    "Road Network",
    "Water Bodies"
  ],
  "provider_count": 6,
  "debug_mode": false
}
```

### Access Frontend
```
https://land-scanner-prototype.onrender.com
```

Should load the map interface. Check browser console (F12) for any errors.

### Test Full Analysis
```bash
curl -X POST https://land-scanner-prototype-backend.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": {
      "type": "Polygon",
      "coordinates": [[
        [-73.935, 40.731],
        [-73.912, 40.731],
        [-73.912, 40.749],
        [-73.935, 40.749],
        [-73.935, 40.731]
      ]]
    }
  }'
```

Should return analysis results with all providers.

---

## Troubleshooting

### Frontend shows blank or error

**Check**:
1. Frontend URL loads (no 404)
2. Browser console for errors (F12)
3. Check `REACT_APP_API_URL` is correct

**Typical error**: API URL mismatch
- Frontend built with wrong API URL
- Trigger rebuild in Render after setting variables

### Backend /health returns error

**Check**:
1. Service is running (green status in Render)
2. Build completed successfully
3. Check Render logs for startup errors

### Analysis request fails with CORS error

**Check**:
1. Backend has `CORS_ORIGINS=*`
2. Frontend has correct `REACT_APP_API_URL`
3. Check browser console for exact error

---

## Summary Table

| Service | Minimum Variables | Recommended Variables | Key Setting |
|---------|------------------|----------------------|------------|
| Backend | 4 | 16 | `ENVIRONMENT=production` |
| Frontend | 1 | 5 | `REACT_APP_API_URL=...` |

| Service | Deploys When | Build Time | Restart Time |
|---------|---------|-----------|-----------|
| Backend | Variables saved | 1-2 min | ~1 min |
| Frontend | Variables saved | <1 min | <1 min |

---

## Quick Reference

### For Impatient Users (Minimum Setup)

**Backend** (4 variables):
```
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
PYTHONUNBUFFERED=true
```

**Frontend** (1 variable):
```
REACT_APP_API_URL=https://land-scanner-prototype-backend.onrender.com
```

Then:
1. Save both
2. Wait 2 minutes
3. Test: https://land-scanner-prototype.onrender.com

---

**Updated**: August 1, 2026  
**Status**: Production Ready  
**Backend Needs Frontend URL**: ❌ NO
