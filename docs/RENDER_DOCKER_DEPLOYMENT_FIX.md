# Render Docker Deployment Fix - Final Solution

## Root Cause
Render was using **Python 3.14 native runtime** instead of Docker, which caused:
- `shapely` unable to build (Python 3.14 too new)
- Missing `pkg_resources` module
- Incompatible build tools

## Solution: Force Docker Runtime

I've updated the configuration to force Render to use **Docker** instead of native Python runtime.

### Changes Made

#### 1. **Updated requirements.txt**
Removed `geopandas` (large dependency), kept `shapely` and `pyproj` with older versions that have wheels:

```txt
setuptools>=68.0.0
wheel>=0.40.0
FastAPI==0.110.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
requests==2.31.0
httpx==0.25.2
shapely==2.0.2
pyproj==3.5.1
numpy==1.26.0
pandas==2.0.3
```

#### 2. **Updated Dockerfile**
- Ensures Python 3.11 (not 3.14)
- Installs ALL required build tools upfront
- Upgrades pip, setuptools, wheel BEFORE installing packages
- Uses `useradd` instead of `adduser` for better compatibility

```dockerfile
FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gcc g++ libffi-dev libgeos-dev \
    gdal-bin libgdal-dev libproj-dev proj-data proj-bin pkg-config

# Upgrade pip, setuptools, wheel FIRST
RUN pip install --upgrade pip setuptools wheel

# Then install requirements
RUN pip install --no-cache-dir -r requirements.txt
```

#### 3. **Created render.yaml**
Explicitly tells Render to use Docker runtime:

```yaml
services:
  - type: web
    name: land-scanner-prototype-backend
    runtime: docker              # Force Docker!
    dockerfilePath: ./Dockerfile
    startCommand: ""             # Let CMD from Dockerfile handle it
    healthCheckPath: /health
```

## Deployment Instructions

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Docker deployment fix"
git push origin main
```

### Step 2: Update Render Service

#### Option A: Redeploy Current Service
1. Go to https://dashboard.render.com
2. Select **land-scanner-prototype-backend**
3. Go to **Deployments**
4. Click **Manual Deploy**
5. Service will now use Docker (3-5 minutes build time)

#### Option B: Delete and Recreate
1. Delete current service
2. Create new Web Service from GitHub
3. Connect to the repository
4. Render will automatically detect `render.yaml` and use Docker

#### Option C: Manual Docker Configuration
If render.yaml is ignored:
1. Dashboard → Service Settings
2. Set **Build Command**: Leave empty or delete
3. Set **Start Command**: Leave empty or delete
4. Save
5. Manual Deploy

## Why Docker Works

✅ Docker builds in a controlled container environment  
✅ Dockerfile specifies Python 3.11 explicitly  
✅ Build tools installed before pip (prevents missing dependencies)  
✅ Compatible with all Python versions up to 3.13  
✅ Faster deployments after first build (layers cached)

## Expected Result

After deploying:
- Build time: ~3-5 minutes (includes Docker image building)
- Service should start successfully
- Health endpoint: `/health` returns 200 OK
- API endpoints available and working

## Verification Checklist

After deployment, test:

```bash
# 1. Health check
curl https://land-scanner-prototype-backend.onrender.com/health

# 2. Status endpoint
curl https://land-scanner-prototype-backend.onrender.com/status

# 3. Analyze endpoint (test with NYC polygon)
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

## If Build Still Fails

### Check Service Logs
1. Dashboard → Service → Logs
2. Look for error messages
3. Verify Docker is building (will see "Building image..." messages)

### Common Issues

| Issue | Solution |
|-------|----------|
| "Dockerfile not found" | Ensure Dockerfile is in repo root |
| "Invalid runtime docker" | Delete render.yaml, update in dashboard |
| "Build takes >10 minutes" | Check logs for stuck processes |
| "Out of memory" | Upgrade from Free to Starter ($7/month) |

### Fallback: Simpler Dependencies

If Docker still fails, use absolute minimum dependencies:

```txt
FastAPI==0.110.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
requests==2.31.0
```

Remove geospatial features temporarily, then add back later.

## Files Modified

- ✅ `requirements.txt` - Compatible versions, removed heavy deps
- ✅ `Dockerfile` - Force Python 3.11, install tools early
- ✅ `render.yaml` - Force Docker runtime (NEW)
- ✅ `.render/build.sh` - No longer needed with Docker

## Next Steps

1. **Push changes to GitHub** (if not already done)
2. **Trigger manual deploy** in Render
3. **Monitor build logs** for any errors
4. **Test endpoints** once deployed
5. **Check frontend** loads correctly

---

**Status**: Ready for Docker deployment  
**Estimated Build Time**: 3-5 minutes  
**Python Version**: 3.11  
**Runtime**: Docker Container
