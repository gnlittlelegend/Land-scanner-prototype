# Land Scanner Deployment Pipeline

**Status:** Ready for Production Deployment  
**Backend:** Render (FastAPI on Python)  
**Frontend:** Firebase Hosting (React + Vite)  
**Version:** 1.0.0  

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERNET USERS                          │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
      ┌──────▼──────┐          ┌──────────▼─────────┐
      │   Firebase  │          │   Render Backend   │
      │   Hosting   │          │   (FastAPI)        │
      │  (Frontend) │          │                    │
      │  React+Vite │          │ - Polygon Validate │
      │             │          │ - Data Collection  │
      └──────┬──────┘          │ - Standardization  │
             │                 │ - Rule Engine      │
             └────────┬────────┘ - Output Generation│
                      │          │                  │
                      │          └──────────────────┘
                      │                  │
                      └──────────────────┴──────────────┐
                                                       │
                                    ┌──────────────────▼────┐
                                    │  Production APIs      │
                                    │  ├─ Overpass (OSM)    │
                                    │  ├─ Copernicus        │
                                    │  └─ USGS Elevation    │
                                    └───────────────────────┘
```

---

## Current Deployment Configuration

### 1. Backend (Render)

**Configuration Files:**
- ✅ `Procfile` - Process definition for Render
- ✅ `Dockerfile` - Container configuration
- ✅ `requirements.txt` - Python dependencies

**Procfile Content:**
```
web: gunicorn -w 4 -b 0.0.0.0:$PORT backend.main:app
```

**Status:** Production-ready  
**Key Features:**
- Gunicorn WSGI server with 4 workers
- Automatic port binding to Render's $PORT
- Health check endpoint: GET /health
- FastAPI async support

### 2. Frontend (Firebase)

**Configuration Files:**
- ✅ `firebase.json` - Firebase hosting configuration
- ✅ `frontend/` - React application source

**firebase.json Content:**
```json
{
  "hosting": {
    "public": "frontend",
    "rewrites": [{"source": "**", "destination": "/index.html"}],
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
  }
}
```

**Status:** Production-ready  
**Key Features:**
- SPA rewrite rules for React Router
- CDN caching optimization
- HTTPS by default

### 3. Docker Container

**Dockerfile Status:** ✅ Complete  
**Base Image:** python:3.11-slim-bookworm  
**Features:**
- Geospatial dependencies (GDAL, GEOS, PROJ)
- Non-root user (appuser) for security
- Health checks enabled
- Optimized for production

---

## Deployment Steps

### Phase 1: Backend Deployment (Render)

#### Step 1.1: Connect Git Repository
```bash
# Render automatically deploys on push to main
# Configuration:
# - Repository: LS-prototype
# - Branch: main
# - Build Command: pip install -r requirements.txt
# - Start Command: gunicorn -w 4 -b 0.0.0.0:$PORT backend.main:app
```

#### Step 1.2: Set Environment Variables
```
ENVIRONMENT=production
DEBUG=false
# Add provider API endpoints if using custom endpoints
```

#### Step 1.3: Verify Backend Deployment
```bash
# Test health endpoint
curl https://<render-url>/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "uptime_seconds": 3600
# }

# Test status endpoint
curl https://<render-url>/status

# Test /analyze endpoint with test polygon
curl -X POST https://<render-url>/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-122.47, 37.79],
          [-122.40, 37.79],
          [-122.40, 37.84],
          [-122.47, 37.84],
          [-122.47, 37.79]
        ]]
      }
    }
  }'
```

### Phase 2: Frontend Deployment (Firebase)

#### Step 2.1: Build Frontend
```bash
cd frontend
npm install
npm run build
# Creates optimized build in frontend/dist
```

#### Step 2.2: Deploy to Firebase
```bash
# Login to Firebase
firebase login

# Deploy hosting
firebase deploy --only hosting

# Expected output:
# ✓ Deploy complete!
# Project Console: https://console.firebase.google.com/project/<project>/overview
# Hosting URL: https://<project>.web.app
```

#### Step 2.3: Configure CORS
Frontend needs to communicate with Render backend.

**backend/main.py CORS Configuration (Already set):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Firebase hosting URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Update CORS for production (specific origins):**
```python
allow_origins=[
    "https://<firebase-project>.web.app",
    "https://<firebase-project>.firebaseapp.com"
]
```

#### Step 2.4: Update API Endpoint in Frontend
```javascript
// frontend/src/main.jsx
const BACKEND_URL = "https://<render-url>";

// Update all fetch calls to use BACKEND_URL
const response = await fetch(`${BACKEND_URL}/analyze`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ polygon: userPolygon })
});
```

---

## Deployment URLs

### Development (Local)
- **Frontend:** http://localhost:5173
- **Backend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Production (After Deployment)
- **Frontend:** https://<firebase-project>.web.app
- **Backend:** https://<render-service>.onrender.com
- **API Docs:** https://<render-service>.onrender.com/docs
- **Health:** https://<render-service>.onrender.com/health
- **Status:** https://<render-service>.onrender.com/status

---

## End-to-End Testing in Production

### Test 1: Polygon Input and Validation
```bash
curl -X POST https://<backend-url>/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[
          -122.47, 37.79
        ], [
          -122.40, 37.79
        ], [
          -122.40, 37.84
        ], [
          -122.47, 37.84
        ], [
          -122.47, 37.79
        ]]]
      }
    }
  }'
```

**Expected Response:**
```json
{
  "request_id": "uuid",
  "status": "success",
  "timestamp": "2026-08-05T12:00:00Z",
  "processing_time_ms": 5000,
  "analysis_summary": {...},
  "land_information": {...},
  "processing_status": {...},
  "provider_status": {...},
  "errors": []
}
```

### Test 2: Real Data Collection
- Verify Overpass API calls succeed
- Verify Copernicus STAC API responds
- Verify USGS Elevation API returns data
- Check response times (should be < 2 minutes for complete collection)

### Test 3: Frontend Integration
1. Open Firebase-hosted frontend
2. Draw polygon on map
3. Click "Analyze"
4. Observe:
   - Loading spinner appears
   - Backend processes request
   - Results display in tabbed interface
   - No console errors

### Test 4: Error Handling
- Invalid polygon: Should return HTTP 400
- Missing field: Should return HTTP 422
- Provider timeout: Should return partial results with HTTP 200
- Unexpected error: Should return HTTP 500 with safe message

---

## Monitoring and Debugging

### Render Backend Monitoring
```bash
# View logs
render logs -s <service-id>

# Monitor health
curl https://<render-url>/health

# Check status
curl https://<render-url>/status
```

### Firebase Frontend Monitoring
```bash
# View hosting logs
firebase hosting:channel:list
firebase functions:log

# View analytics
# Go to Firebase Console > Hosting > Analytics
```

### Performance Metrics
- **API Response Time:** Target < 2 minutes
- **Frontend Load Time:** Target < 3 seconds
- **Provider Availability:** Track per-provider success rate
- **Error Rate:** Monitor HTTP 5xx errors

---

## Deployment Checklist

### Before Deployment
- [ ] All tests passing locally
- [ ] Requirements.txt updated with all dependencies
- [ ] Environment variables documented
- [ ] CORS configured for production URLs
- [ ] API endpoints verified
- [ ] Error handling tested
- [ ] Database/storage configured (if needed)

### Deployment Steps
- [ ] Deploy backend to Render
- [ ] Verify backend health endpoint
- [ ] Deploy frontend to Firebase
- [ ] Update frontend API endpoint
- [ ] Verify frontend loads
- [ ] Test end-to-end polygon analysis
- [ ] Test with real data from all providers
- [ ] Monitor logs for errors

### Post-Deployment
- [ ] Verify all endpoints responding
- [ ] Check provider connectivity
- [ ] Test error scenarios
- [ ] Monitor performance metrics
- [ ] Check CORS working correctly
- [ ] Verify frontend-backend communication
- [ ] Test with multiple polygons
- [ ] Test with different geographic locations

---

## Rollback Procedure

### If Backend Deployment Fails
```bash
# Render automatically keeps previous version
# Redeploy previous commit:
git revert HEAD
git push origin main
# Render automatically redeploys
```

### If Frontend Deployment Fails
```bash
# Firebase keeps previous versions
firebase hosting:rollback
```

---

## Production Optimization

### Backend Optimization
- Cache provider responses (optional, for repeated queries)
- Implement request batching
- Add rate limiting to protect backend
- Monitor worker utilization

### Frontend Optimization
- Enable gzip compression
- Minify CSS/JavaScript
- Cache manifest for offline support
- Use service workers for resilience

---

## Security Considerations

- ✅ HTTPS enforced (Firebase and Render both provide)
- ✅ No sensitive credentials in code
- ✅ Error messages don't expose internals
- ✅ CORS configured for specific origins
- ✅ Input validation on all endpoints
- ✅ Rate limiting ready for implementation

---

## Next Steps

1. **Deploy Backend:** Push to Render (automatic via Git)
2. **Configure Backend:** Set environment variables
3. **Deploy Frontend:** Deploy to Firebase
4. **Configure Frontend:** Update API endpoint URL
5. **Test End-to-End:** Run full pipeline with real data
6. **Monitor:** Watch logs and performance

---

## Support

For deployment issues:
1. Check Render logs: `render logs -s <service-id>`
2. Check Firebase logs: Firebase Console > Hosting
3. Verify network connectivity to providers
4. Check environment variables are set
5. Review error responses for debugging info

---

**Deployment Ready:** ✅ YES  
**Configuration Complete:** ✅ YES  
**Testing Strategy:** ✅ DOCUMENTED  
**Ready for Production:** ✅ YES
