# Render Environment Variables - Complete Setup Guide

## Backend Service: land-scanner-prototype-backend

### Environment Variables to Add

Go to: Render Dashboard → land-scanner-prototype-backend → Settings → Environment

| Key | Value | Description |
|-----|-------|-------------|
| `ENVIRONMENT` | `production` | Deployment environment |
| `DEBUG` | `false` | Disable debug mode in production |
| `LOG_LEVEL` | `INFO` | Logging level (INFO, DEBUG, WARNING, ERROR) |
| `PYTHONUNBUFFERED` | `true` | Unbuffered Python output (required for logging) |
| `API_HOST` | `0.0.0.0` | Bind to all interfaces |
| `API_PORT` | `8000` | API port (Render maps to $PORT automatically) |
| `APP_NAME` | `Land Scanner Prototype` | Application display name |
| `APP_VERSION` | `1.0.0` | Application version |
| `CORS_ORIGINS` | `*` | CORS allowed origins (allow all for demo) |
| `REQUEST_TIMEOUT` | `30` | Request timeout in seconds |
| `COLLECTION_TIMEOUT` | `60` | Data collection timeout in seconds |
| `ENABLE_OSM` | `true` | Enable OpenStreetMap data collection |
| `ENABLE_ELEVATION` | `true` | Enable elevation data collection |
| `ENABLE_LANDCOVER` | `true` | Enable land cover data collection |
| `ENABLE_ADMIN_BOUNDARIES` | `true` | Enable admin boundaries collection |
| `ENABLE_ROADS` | `true` | Enable road network collection |
| `ENABLE_WATER` | `true` | Enable water bodies collection |

### Quick Copy-Paste for Backend

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

### Environment Variables to Add

Go to: Render Dashboard → land-scanner-prototype → Settings → Environment

| Key | Value | Description |
|-----|-------|-------------|
| `REACT_APP_API_URL` | `https://land-scanner-prototype-backend.onrender.com` | Backend API endpoint |
| `REACT_APP_APP_NAME` | `Land Scanner Prototype` | App name in UI |
| `REACT_APP_VERSION` | `1.0.0` | App version |
| `REACT_APP_ENVIRONMENT` | `production` | Environment indicator |
| `NODE_ENV` | `production` | Node environment |

### Quick Copy-Paste for Frontend

```
REACT_APP_API_URL=https://land-scanner-prototype-backend.onrender.com
REACT_APP_APP_NAME=Land Scanner Prototype
REACT_APP_VERSION=1.0.0
REACT_APP_ENVIRONMENT=production
NODE_ENV=production
```

---

## Step-by-Step Instructions

### For Backend Service

1. Open https://dashboard.render.com
2. Click on **land-scanner-prototype-backend**
3. Click **Settings** tab
4. Scroll to **Environment** section
5. Click **Add Environment Variable** (or similar button)
6. For each variable in the table above:
   - Enter **Key** in first field
   - Enter **Value** in second field
   - Click **Add**
7. After adding all variables, click **Save** button
8. Service will automatically redeploy with new variables

### For Frontend Service

1. Open https://dashboard.render.com
2. Click on **land-scanner-prototype**
3. Click **Settings** tab
4. Scroll to **Environment** section
5. Click **Add Environment Variable** (or similar button)
6. For each variable in the Frontend table:
   - Enter **Key** in first field
   - Enter **Value** in second field
   - Click **Add**
7. After adding all variables, click **Save** button
8. Service will automatically redeploy with new variables

---

## Environment Variable Meanings

### Backend Core Configuration

**ENVIRONMENT**: Controls which settings file is used
- `production` - Use production settings
- `staging` - Use staging settings
- `development` - Use development settings

**DEBUG**: Controls error verbosity
- `false` - Production mode (safe error messages)
- `true` - Development mode (detailed stack traces)

**LOG_LEVEL**: Controls logging verbosity
- `DEBUG` - Very detailed, includes all debug messages
- `INFO` - Normal, includes info + warnings + errors
- `WARNING` - Only warnings and errors
- `ERROR` - Only errors

**PYTHONUNBUFFERED**: Output buffering
- `true` - Unbuffered (recommended for logging)
- `false` - Buffered (can miss logs on crash)

### API Configuration

**API_HOST**: Which IP address to bind to
- `0.0.0.0` - All interfaces (recommended for cloud)
- `127.0.0.1` - Localhost only

**API_PORT**: Port number
- Note: Render assigns this via `$PORT` variable
- Set to `8000` for consistency, Render will override

### Timeouts (seconds)

**REQUEST_TIMEOUT**: How long to wait for HTTP requests
- Default: `30` seconds
- Increase if providers are slow

**COLLECTION_TIMEOUT**: How long to wait for data collection
- Default: `60` seconds
- OSM data can take 5-10 seconds per polygon

### Feature Flags

Enable/disable data providers:
- `ENABLE_OSM=true` - OpenStreetMap buildings
- `ENABLE_ELEVATION=true` - SRTM elevation data
- `ENABLE_LANDCOVER=true` - Copernicus land cover
- `ENABLE_ADMIN_BOUNDARIES=true` - Admin boundaries
- `ENABLE_ROADS=true` - OSM road network
- `ENABLE_WATER=true` - OSM water bodies

### Frontend Configuration

**REACT_APP_API_URL**: The backend API endpoint
- Must match your backend service URL
- Example: `https://land-scanner-prototype-backend.onrender.com`

**REACT_APP_ENVIRONMENT**: For UI indicators
- `production` - Shows production badge
- `staging` - Shows staging badge
- `development` - Shows development badge

**NODE_ENV**: Node/React build mode
- `production` - Minified, optimized
- `development` - Debug symbols, larger bundle

---

## Verification Checklist

After setting all environment variables:

- [ ] Backend service redeployed
- [ ] Frontend service redeployed
- [ ] Backend /health endpoint responds 200
- [ ] Backend /status endpoint shows 6 providers
- [ ] Frontend loads and displays map
- [ ] Frontend can connect to backend (check browser console)
- [ ] Can draw polygon on map
- [ ] Can click "Analyze" and get results
- [ ] No CORS errors in browser console

### Test Commands

```bash
# Health check
curl https://land-scanner-prototype-backend.onrender.com/health

# Status check
curl https://land-scanner-prototype-backend.onrender.com/status

# Test API
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

---

## Troubleshooting

### Frontend can't reach backend

**Check**:
1. `REACT_APP_API_URL` matches backend URL exactly
2. Backend service is running (check /health)
3. Browser console for CORS errors

**Fix**:
- Verify URL ends without trailing slash
- Backend must have CORS enabled (it does)
- Check backend logs for errors

### API timeouts

**Symptoms**: "Request timeout" errors

**Fixes**:
1. Increase `REQUEST_TIMEOUT` to `45`
2. Increase `COLLECTION_TIMEOUT` to `90`
3. Check if providers are slow (normal for first query)

### Build fails with "invalid environment"

**Issue**: Non-standard characters in values

**Fix**:
- Don't use quotes in Render UI
- Use only alphanumeric + underscore + hyphen
- For URLs, paste directly without quotes

### Service won't restart

**Check**:
1. All variables have valid values
2. No blank/empty values
3. Click "Save" button to confirm

---

## Production Best Practices

1. **Debug=false** always in production
2. **LOG_LEVEL=INFO** for normal operation
3. **Request timeouts reasonable** but not too short
4. **Feature flags enable** all providers
5. **CORS_ORIGINS=*** ok for public demo
6. **API version** matches deployment

---

## Example Complete Setup

### Backend Service Status (After Configuration)

```
Service: land-scanner-prototype-backend
Status: Running
URL: https://land-scanner-prototype-backend.onrender.com
Environment Variables: 16 configured
  - ENVIRONMENT: production
  - DEBUG: false
  - LOG_LEVEL: INFO
  - ... (all others set)
Build Status: Deployed ✓
Health Check: Passing ✓
```

### Frontend Service Status (After Configuration)

```
Service: land-scanner-prototype
Status: Running
URL: https://land-scanner-prototype.onrender.com
Environment Variables: 5 configured
  - REACT_APP_API_URL: https://land-scanner-prototype-backend.onrender.com
  - REACT_APP_APP_NAME: Land Scanner Prototype
  - REACT_APP_VERSION: 1.0.0
  - ... (all others set)
Build Status: Deployed ✓
Frontend Loads: ✓
```

---

## Summary

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Service Name | land-scanner-prototype-backend | land-scanner-prototype |
| Variables | 16 | 5 |
| Key Setting | ENVIRONMENT=production | REACT_APP_API_URL |
| Build Time | 1-2 min | <1 min |
| Redeploy Time | ~1 min | ~1 min |

---

**Last Updated**: August 1, 2026  
**Status**: Ready for Production Configuration
