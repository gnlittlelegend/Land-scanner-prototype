# Render Docker Deployment - Land Scanner Prototype

## Status
✅ **Ready for Deployment** - Using Docker runtime to avoid Python version conflicts

## Key Changes
1. **Docker Runtime**: Using Docker instead of native Python runtime
2. **Dockerfile**: Specifies Python 3.11 with all required system dependencies
3. **render.yaml**: Configuration file for Render deployment
4. **requirements.txt**: Updated with compatible package versions

## How to Deploy on Render

### Step 1: Update Render Service Configuration

1. Go to https://dashboard.render.com
2. Select **land-scanner-prototype-backend** service
3. Click **Settings**
4. Update **Root Directory** to: (leave blank or `/`)
5. Update **Dockerfile Path** to: `./Dockerfile`
6. Update **Docker Build Context** to: `.`
7. Click **Save**

### Step 2: Trigger Manual Deploy

1. Still in Settings, go to **Manual Deploy** section
2. Click **Deploy latest commit**
3. Watch the build progress in the **Deployments** tab

### Step 3: Monitor Build

The build should now:
- Pull Python 3.11 slim image
- Install system dependencies (build-essential, geos, proj, etc.)
- Install Python packages from pre-built wheels
- Complete in 3-5 minutes

## What's Different

**Before (Failed)**:
- Using Render's native Python runtime
- Render defaulted to Python 3.14
- Tried to build shapely from source
- Missing build dependencies

**Now (Should Work)**:
- Using Docker runtime
- Dockerfile specifies Python 3.11 explicitly
- All system dependencies pre-installed
- Dependencies install cleanly

## Dependencies Included

### Python Packages
```
FastAPI==0.110.0              # Web framework
uvicorn[standard]==0.27.0     # ASGI server
pydantic==2.5.3               # Data validation
requests==2.31.0              # HTTP client
httpx==0.25.2                 # Async HTTP
shapely==2.0.2                # Geometry (pre-built wheel)
pyproj==3.5.1                 # Projections (pre-built wheel)
numpy==1.26.0                 # Numerical arrays
pandas==2.0.3                 # Data frames
```

### System Dependencies
```
build-essential    # Compiler toolchain
libgeos-dev        # GEOS geometry library
libproj-dev        # PROJ coordinate library
gdal-bin           # Geospatial data tools
curl               # HTTP client for health checks
```

## Testing After Deployment

Once the service is running:

```bash
# 1. Health Check
curl https://land-scanner-prototype-backend.onrender.com/health

# 2. Status Check
curl https://land-scanner-prototype-backend.onrender.com/status

# 3. Test Analysis
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

## Expected Build Times

- **Initial Build**: 4-5 minutes (first time pulling all dependencies)
- **Rebuild with Changes**: 1-2 minutes (uses Docker layer cache)
- **Container Startup**: <10 seconds

## If Build Still Fails

### Check Render Logs
1. Go to service > **Logs** tab
2. Look for specific error messages
3. Common issues:
   - Dockerfile path incorrect (should be `./Dockerfile`)
   - Docker context path incorrect (should be `.`)
   - Insufficient disk space (free tier limited)

### Troubleshooting Steps

**If "Dockerfile not found"**:
- Verify path is `./Dockerfile` (relative to repo root)
- Ensure Dockerfile is committed to GitHub

**If "Docker build failed"**:
- Check system package installation errors
- Verify internet connectivity for pip downloads
- Check available disk space

**If "Service won't start"**:
- Check `/health` endpoint responds
- Review service startup logs
- Verify environment variables are set

## Environment Variables to Configure

In Render Dashboard > Service Settings > Environment:

```
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
PYTHONUNBUFFERED=true
```

## Files Updated

- **Dockerfile** - Enhanced with Python 3.11, system dependencies, proper pip upgrade
- **requirements.txt** - Compatible versions with pre-built wheels
- **render.yaml** - Docker runtime configuration (optional, for reference)
- **.render/build.sh** - Custom build script (not used with Docker, kept for reference)

## Docker Image Details

```dockerfile
Base Image: python:3.11-slim-bookworm
Size: ~150MB after build
User: appuser (non-root for security)
Port: 8000
Health Check: /health endpoint
```

## Next Steps

1. ✅ Code pushed to GitHub `main` branch
2. Update Render service to use Docker runtime
3. Trigger manual deploy
4. Monitor build progress
5. Test endpoints
6. Verify frontend connectivity

## Support

- **Build Issues**: Check Render Logs tab
- **Runtime Issues**: Check Render Logs > Runtime
- **API Issues**: Test /status endpoint
- **Frontend Issues**: Check browser DevTools (F12)

---

**Updated**: August 1, 2026  
**Status**: Ready for Docker-based deployment
