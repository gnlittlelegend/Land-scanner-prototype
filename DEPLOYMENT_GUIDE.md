# Land Scanner Prototype - Deployment Guide

## Overview

The Land Scanner Prototype is ready for deployment on Render or similar cloud platforms. This guide provides step-by-step instructions for deploying the application.

## Prerequisites

- GitHub account (for version control)
- Render account (for hosting)
- Git installed locally
- Python 3.11+ (local testing)

## Local Testing Before Deployment

### 1. Setup Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suite
python -m pytest tests/test_polygon_validator.py -v
python -m pytest tests/test_data_standardizer.py -v
python -m pytest tests/test_rule_engine.py -v
```

### 4. Start Backend Server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start Frontend Server

```bash
cd frontend
python -m http.server 3000
```

### 6. Test the System

Open browser: `http://localhost:3000`

Test the analysis pipeline:
1. Draw a polygon on the map
2. Click "Analyze"
3. Verify results display

## Deployment Steps

### Step 1: Push Code to GitHub

```bash
git add .
git commit -m "Ready for deployment - Task 14"
git push origin main
```

### Step 2: Create Render Web Service

1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure deployment:

**Basic Settings:**
- Name: `land-scanner-prototype`
- Environment: `Python 3`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

**Environment Variables:**
```
APP_NAME=Land Scanner Prototype
APP_VERSION=1.0.0
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

**Instance Type:**
- Free tier initially, or Starter plan for better performance

### Step 3: Configure Frontend

The frontend serves from the same domain as the backend due to CORS configuration. Render will serve static files through the FastAPI app or a separate static file configuration.

For Render:
1. Create a second Web Service for frontend (optional)
2. Or serve frontend as static content from backend

### Step 4: Verify Deployment

Once deployed:

1. Test health endpoint:
```bash
curl https://your-render-url.onrender.com/health
```

2. Test status endpoint:
```bash
curl https://your-render-url.onrender.com/status
```

3. Test with valid polygon:
```bash
curl -X POST https://your-render-url.onrender.com/analyze \
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

## Production Deployment Checklist

- [ ] All tests passing (144/144)
- [ ] Code pushed to GitHub
- [ ] Environment variables configured on Render
- [ ] Health endpoint responds (200 OK)
- [ ] Status endpoint shows all 6 providers enabled
- [ ] /analyze endpoint processes valid polygons
- [ ] Error handling works (invalid input returns 400/422)
- [ ] API response times acceptable (<500ms for simple polygons)
- [ ] Frontend loads and displays map
- [ ] Frontend can draw polygons
- [ ] Frontend can upload GeoJSON files
- [ ] Frontend displays analysis results
- [ ] CORS headers configured correctly
- [ ] Logging configured for production
- [ ] Database connections stable (if applicable)
- [ ] Memory usage acceptable
- [ ] CPU usage acceptable

## Troubleshooting

### Health Check Fails
- Verify environment variables are set
- Check Render logs for startup errors
- Ensure Python 3.11 is selected

### Slow Response Times
- Data collection from OSM takes 5-10 seconds
- This is normal for the first query
- Subsequent queries may be faster due to caching

### CORS Errors in Frontend
- Verify CORS middleware is enabled in backend/main.py
- Check browser console for specific CORS error
- Verify frontend and backend URLs match

### Memory Issues
- Check Render logs for OOM messages
- Increase instance size if needed
- Profile memory usage with production data

## Scaling Considerations

For production scaling:

1. **Horizontal Scaling**: Deploy multiple backend instances behind a load balancer
2. **Caching**: Add Redis for provider response caching
3. **Database**: Add PostgreSQL for result persistence
4. **CDN**: Serve frontend assets from CDN
5. **Rate Limiting**: Implement rate limiting for API endpoints

## Monitoring

Setup monitoring for:
- API response times
- Error rates
- Provider availability
- Memory and CPU usage
- Request volume and patterns

## Support

For issues or questions:
1. Check backend logs: `tail -f logs/application.log`
2. Check frontend console: Press F12 in browser
3. Review error messages in /analyze response

## Security Considerations

Current implementation:
- ✅ No authentication (demo/prototype)
- ✅ CORS enabled for public access
- ✅ Error messages sanitized (no stack traces)
- ⚠️ Rate limiting not implemented (add for production)
- ⚠️ API key authentication not implemented (add for production)

## Next Steps

1. Deploy to Render
2. Test all endpoints in production
3. Monitor performance metrics
4. Gather user feedback
5. Plan for production hardening (auth, rate limiting, etc.)

---

**Deployment Date**: August 1, 2026  
**Version**: 1.0.0  
**Status**: Ready for Deployment
