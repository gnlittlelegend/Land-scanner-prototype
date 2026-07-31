# Render Environment Variables Configuration

## For Both Backend and Frontend Services

### Backend Service Environment Variables
**Service**: Land-scanner-prototype-backend

Add these key-value pairs in Render Dashboard > Service Settings > Environment:

```
APP_NAME=Land Scanner Prototype
APP_VERSION=1.0.0
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=production
PYTHONUNBUFFERED=true
```

### Frontend Service Environment Variables
**Service**: Land-scanner-prototype

Add these key-value pairs in Render Dashboard > Service Settings > Environment:

```
REACT_APP_API_URL=https://land-scanner-prototype-backend.onrender.com
REACT_APP_APP_NAME=Land Scanner Prototype
REACT_APP_VERSION=1.0.0
NODE_ENV=production
```

---

## Step-by-Step Instructions for Render

### For Backend Service (land-scanner-prototype-backend):

1. Go to https://dashboard.render.com
2. Click on **land-scanner-prototype-backend** service
3. Click **Settings** tab
4. Scroll to **Environment** section
5. Click **"Add Environment Variable"** for each variable below:

| Key | Value |
|-----|-------|
| `APP_NAME` | `Land Scanner Prototype` |
| `APP_VERSION` | `1.0.0` |
| `DEBUG` | `false` |
| `API_HOST` | `0.0.0.0` |
| `API_PORT` | `8000` |
| `LOG_LEVEL` | `INFO` |
| `ENVIRONMENT` | `production` |
| `PYTHONUNBUFFERED` | `true` |

6. **Save** changes
7. Service will automatically redeploy

### For Frontend Service (land-scanner-prototype):

1. Go to https://dashboard.render.com
2. Click on **land-scanner-prototype** service
3. Click **Settings** tab
4. Scroll to **Environment** section
5. Click **"Add Environment Variable"** for each variable below:

| Key | Value |
|-----|-------|
| `REACT_APP_API_URL` | `https://land-scanner-prototype-backend.onrender.com` |
| `REACT_APP_APP_NAME` | `Land Scanner Prototype` |
| `REACT_APP_VERSION` | `1.0.0` |
| `NODE_ENV` | `production` |

6. **Save** changes
7. Service will automatically redeploy

---

## API Key Management

### Already Assigned API Key
You mentioned you already have an API key assigned: **kf177ua1GfG8iuWDdChYWXLmzBYheKrO7DIVfLATviU**

This key is already configured in your Backend service environment. To verify or manage it:

1. Go to Backend service on Render
2. Settings > Environment
3. Look for your API key variable
4. If you need to update it, edit the value and save

---

## Optional Production Environment Variables

Add these if you need additional features:

```
# Logging & Monitoring
LOG_FILE=/var/logs/application.log
LOG_FORMAT=json

# CORS Configuration
CORS_ORIGINS=*
CORS_CREDENTIALS=true

# Rate Limiting (when implemented)
RATE_LIMIT_ENABLED=false
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Data Collection Timeouts
REQUEST_TIMEOUT=30
COLLECTION_TIMEOUT=60

# Provider Configuration
ENABLE_OSM=true
ENABLE_ELEVATION=true
ENABLE_LANDCOVER=true
ENABLE_ADMIN_BOUNDARIES=true
ENABLE_ROADS=true
ENABLE_WATER=true
```

---

## Environment Variable Categories

### Core Application
- `APP_NAME` - Application display name
- `APP_VERSION` - Current version
- `ENVIRONMENT` - Deployment environment (production/staging/development)

### API Configuration
- `API_HOST` - API server host (0.0.0.0 for all interfaces)
- `API_PORT` - API server port ($PORT is Render's dynamic variable)
- `DEBUG` - Debug mode (false for production)

### Logging
- `LOG_LEVEL` - Logging level (INFO, DEBUG, WARNING, ERROR)
- `PYTHONUNBUFFERED` - Ensure Python logs immediately (true for production)

### Frontend Configuration
- `REACT_APP_API_URL` - Backend API endpoint URL
- `NODE_ENV` - Node environment (production)

### Security & Performance
- `CORS_ORIGINS` - Allowed CORS origins
- `REQUEST_TIMEOUT` - Request timeout in seconds
- `COLLECTION_TIMEOUT` - Data collection timeout in seconds

---

## Quick Copy-Paste for Backend

```
APP_NAME=Land Scanner Prototype
APP_VERSION=1.0.0
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=production
PYTHONUNBUFFERED=true
```

## Quick Copy-Paste for Frontend

```
REACT_APP_API_URL=https://land-scanner-prototype-backend.onrender.com
REACT_APP_APP_NAME=Land Scanner Prototype
REACT_APP_VERSION=1.0.0
NODE_ENV=production
```

---

## After Adding Environment Variables

1. **Verify Deployment**: Check service logs for any configuration errors
2. **Test Health Endpoint**: `curl https://land-scanner-prototype-backend.onrender.com/health`
3. **Test API**: Draw polygon on frontend and click "Analyze"
4. **Monitor Logs**: Watch Render logs for any runtime issues

---

## Troubleshooting

### If variables don't appear in logs:
- Verify environment variables are saved (click Save button)
- Check that service is redeployed after changes
- Refresh browser to see updated frontend

### If API calls fail:
- Verify `REACT_APP_API_URL` matches your backend URL
- Check CORS configuration in backend
- Review backend logs for errors

### If service won't start:
- Verify `PYTHONUNBUFFERED=true` is set (prevents buffering issues)
- Check `LOG_LEVEL` is valid (INFO, DEBUG, WARNING, ERROR)
- Review Render deployment logs for startup errors

---

**Last Updated**: August 1, 2026
**Status**: Ready for Configuration
