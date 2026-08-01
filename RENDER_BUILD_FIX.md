# Render Build Fix - Python 3.11 Compatibility

## Problem Identified
Render deployment was failing because:
1. `shapely==2.0.4` requires build dependencies (`pkg_resources`, `setuptools`)
2. Render was attempting to use Python 3.14 which doesn't have wheel support for some packages
3. Missing `build-essential` and `pkg-config` in the build environment

## Solution Implemented

### 1. Updated `requirements.txt`
Changed from pinned versions to flexible versions that support pre-built wheels:

```
setuptools>=68.0.0
wheel>=0.40.0
FastAPI==0.110.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
requests==2.31.0
httpx==0.25.2
shapely>=2.0.0
geopandas>=0.14.0
pyproj>=3.6.0
numpy>=1.24.0
pandas>=2.0.0
```

**Key changes:**
- Added `setuptools` and `wheel` at the top (required for building C extensions)
- Changed pinned versions to minimum version constraints (>=) to allow pip to find compatible pre-built wheels
- This allows pip to use binary wheels instead of building from source

### 2. Updated `Dockerfile`
Enhanced the build environment:

```dockerfile
# Added system dependencies
pkg-config          # Required for building C extensions
build-essential     # Provides gcc, make, and other build tools

# Upgraded pip, setuptools, and wheel before installing dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
```

### 3. Created `render.yaml`
Explicit Render configuration:

```yaml
services:
  - type: web
    name: land-scanner-prototype-backend
    runtime: python
    runtimeVersion: 3.11.0          # Explicitly set Python 3.11
    buildCommand: bash .render/build.sh
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Benefits:**
- Explicitly specifies Python 3.11 (prevents Render from using 3.14)
- Uses custom build script for better control
- Defines environment variables and health checks

### 4. Created `.render/build.sh`
Build script that:
- Sets Python version
- Upgrades pip, setuptools, and wheel
- Installs dependencies with proper error handling

## How to Deploy

### Option A: Update Render Service via Dashboard (Recommended)

1. Go to https://dashboard.render.com
2. Select **land-scanner-prototype-backend** service
3. Click **Settings**
4. Find **Build Command** and change to:
   ```bash
   bash .render/build.sh
   ```
5. Find **Start Command** and verify it's:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```
6. Click **Save**
7. Go to **Manual Deploy** and click **Deploy latest commit**

### Option B: Use render.yaml (For New Services)

If creating a new service:
1. Go to Render Dashboard
2. Click **New +** → **Web Service**
3. Connect to GitHub
4. Click **Upload render.yaml**
5. Select the `render.yaml` file from this repo
6. Deploy

## Testing After Fix

Once deployed, test the endpoints:

```bash
# Health check
curl https://land-scanner-prototype-backend.onrender.com/health

# Status check
curl https://land-scanner-prototype-backend.onrender.com/status

# Test analysis
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

## Files Changed

1. **requirements.txt** - Added setuptools/wheel, flexible version constraints
2. **Dockerfile** - Added pkg-config, build-essential, pip upgrade
3. **render.yaml** - New Render configuration file (optional but recommended)
4. **.render/build.sh** - New custom build script

## Expected Build Time

- First build: ~3-4 minutes (downloading dependencies)
- Subsequent builds: ~1-2 minutes (using cache)

## If Build Still Fails

**Common issues:**

1. **"ModuleNotFoundError: No module named 'pkg_resources'"**
   - Ensure `setuptools` is installed before other packages
   - Delete Render service and redeploy from scratch

2. **"Python 3.14 not supported"**
   - Add `render.yaml` to specify Python 3.11
   - Or manually set in Render dashboard

3. **"Out of disk space"**
   - Free tier has limited space
   - Reduce dependencies or upgrade instance

## Alternative: Pre-built Wheels

If issues persist, use a simpler requirements.txt with only proven compatible versions:

```
FastAPI==0.110.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
requests==2.31.0
httpx==0.25.2
Shapely[vectorized]==2.0.1
```

## Support

- Check Render logs: Dashboard → Service → Logs
- Monitor build process: Dashboard → Service → Deployments
- Review error messages for specific failures

---

**Updated**: August 1, 2026  
**Status**: Ready for deployment with Python 3.11 fix
