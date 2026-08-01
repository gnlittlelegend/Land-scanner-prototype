# Task 12: End-to-End Testing Guide

## Overview
This guide walks through verifying that all Land Scanner modules work together end-to-end, from frontend polygon input to backend analysis and result display.

## Prerequisites
- All backend modules implemented (Tasks 1-10)
- All frontend modules implemented (Task 11)
- Dependencies installed from requirements.txt
- Port 8000 available for backend
- Port 3000 or similar available for frontend

## System Startup

### 1. Start Backend Server

```bash
# Navigate to project root
cd /path/to/land-scanner

# Option 1: Direct Python execution
python backend/main.py

# Option 2: Using uvicorn directly
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
Starting Land Scanner Prototype v1.0.0
Server: 0.0.0.0:8000
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Verification:**
- Backend should be accessible at http://localhost:8000
- OpenAPI docs available at http://localhost:8000/docs
- ReDoc available at http://localhost:8000/redoc

### 2. Start Frontend Server

```bash
# Option 1: Python built-in HTTP server
cd frontend
python -m http.server 3000

# Option 2: Node.js http-server
cd frontend
npx http-server . -p 3000

# Option 3: Python's SimpleHTTPServer (Python 2)
cd frontend
python -m SimpleHTTPServer 3000
```

**Expected Output:**
```
Serving HTTP on 0.0.0.0 port 3000 (http://0.0.0.0:3000/) ...
```

**Verification:**
- Frontend should be accessible at http://localhost:3000
- Index page loads without errors
- Map displays with OpenStreetMap tiles

## API Endpoint Testing

### Test 1: Health Check Endpoint

**Purpose:** Verify backend is running and healthy

**Test Command:**
```bash
curl -X GET http://localhost:8000/health
```

**Expected Response (HTTP 200):**
```json
{
  "status": "healthy",
  "service": "Land Scanner Prototype",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

**Verification Points:**
- ✅ HTTP Status 200
- ✅ Response includes status, service name, version, timestamp
- ✅ Service name matches configuration
- ✅ Version matches expected

### Test 2: Status Endpoint

**Purpose:** Verify backend configuration and enabled providers

**Test Command:**
```bash
curl -X GET http://localhost:8000/status
```

**Expected Response (HTTP 200):**
```json
{
  "prototype_name": "Land Scanner Prototype",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:45.123456",
  "enabled_providers": [
    "osm_buildings",
    "admin_boundaries",
    "land_cover",
    "osm_roads",
    "osm_water",
    "elevation"
  ],
  "provider_count": 6,
  "debug_mode": false
}
```

**Verification Points:**
- ✅ HTTP Status 200
- ✅ All 6 providers listed as enabled
- ✅ Provider count matches enabled_providers length
- ✅ Debug mode set correctly from configuration

## Frontend-Backend Communication Testing

### Test 3: Invalid Polygon Submission

**Purpose:** Verify error handling for invalid input

**Test Steps:**
1. Open frontend at http://localhost:3000
2. Do NOT draw polygon
3. Click "Analyze" button
4. Observe error handling

**Expected Behavior:**
- ✅ Error message displayed: "Please draw or upload a polygon first"
- ✅ Error panel appears with readable message
- ✅ No backend call made

**Verification:**
- Check browser console for any JavaScript errors
- Verify error message is user-friendly

### Test 4: Malformed Polygon Upload

**Purpose:** Verify polygon validation error handling

**Create Test File** (`test_invalid.json`):
```json
{
  "type": "Feature",
  "geometry": {
    "type": "InvalidType",
    "coordinates": []
  }
}
```

**Test Steps:**
1. Click "Upload GeoJSON" file input
2. Upload test_invalid.json
3. Observe error handling

**Expected Behavior:**
- ✅ Frontend shows error: "Failed to parse GeoJSON"
- ✅ Error message explains what's wrong
- ✅ No server crash logs

**Verification in Backend Logs:**
- Look for validation error message
- Verify error is safely handled

### Test 5: Valid Polygon Analysis

**Purpose:** Verify end-to-end successful analysis

**Create Test File** (`test_valid.json`):
```json
{
  "type": "Polygon",
  "coordinates": [[
    [-73.9352, 40.7306],
    [-73.9352, 40.7489],
    [-73.9122, 40.7489],
    [-73.9122, 40.7306],
    [-73.9352, 40.7306]
  ]]
}
```

This is a small area in Manhattan, New York.

**Test Steps:**
1. Click "Upload GeoJSON" file input
2. Upload test_valid.json
3. Observe polygon displayed on map
4. Click "Analyze" button
5. Wait for processing (5-15 seconds)
6. Observe results display

**Expected Behavior:**
- ✅ Polygon displays on map (polygon boundary visible)
- ✅ Loading indicator appears during processing
- ✅ Results panel appears after processing
- ✅ No JavaScript errors in console
- ✅ Backend returns HTTP 200 with analysis results

**Result Panel Should Show:**
- Status badge (success/partial/error)
- Processing time in seconds
- Analysis summary with area, land cover, key findings
- Land information sections for each data type
- Processing status for each module
- Provider status listing all 6 providers

**Verification Points:**
- ✅ Area calculated and displayed (should be ~0.05-0.1 sq km for test polygon)
- ✅ All 6 providers show in status (available or unavailable)
- ✅ Each module shows success/partial/failed/skipped status
- ✅ No sensitive data or stack traces in error messages

## Backend Processing Pipeline Verification

### Test 6: Polygon Validation Stage

**Purpose:** Verify polygon is validated before processing

**Backend Log Check:**
```
[req_TIMESTAMP] STAGE 1: Validating polygon...
[req_TIMESTAMP] ✓ Polygon validated: area=X.XX sq km
```

**Expected Log Output:**
- ✅ Polygon validation stage started
- ✅ Polygon accepted
- ✅ Area calculated and logged
- ✅ Polygon metadata populated

### Test 7: Data Collection Stage

**Purpose:** Verify data is collected from all providers

**Backend Log Check:**
```
[req_TIMESTAMP] STAGE 2: Collecting data from providers...
[req_TIMESTAMP] ✓ Data collection complete: N datasets collected
```

**Expected Log Output:**
- ✅ Collection stage started
- ✅ All 6 collectors executed
- ✅ Total datasets collected logged
- ✅ Provider status tracking logged

**Response Should Include Provider Status:**
```json
"provider_status": [
  {
    "provider_name": "osm_buildings",
    "status": "available|unavailable|error",
    "data_retrieved": true|false,
    "error_message": null|"error details"
  },
  // ... one for each provider
]
```

### Test 8: Data Standardization Stage

**Purpose:** Verify data converted to standard format

**Backend Log Check:**
```
[req_TIMESTAMP] STAGE 4: Standardizing data to common format...
[req_TIMESTAMP] ✓ Standardization complete: N datasets standardized
```

**Verification:**
- ✅ All data converted to WGS84 (EPSG:4326)
- ✅ Field names normalized consistently
- ✅ Data structure consistent across all providers
- ✅ No raw provider formats in output

### Test 9: Rule Engine Processing

**Purpose:** Verify rules process standardized data independently

**Backend Log Check:**
```
[req_TIMESTAMP] STAGE 5: Processing with Rule Engine...
[req_TIMESTAMP] ✓ Rule Engine complete: N rules executed
```

**Expected Rules to Execute:**
- ADM-001: Administrative Boundary Detection
- LC-001: Land Cover Summary
- BLD-001: Building Presence
- RD-001: Road Network
- WT-001: Water Features
- ELV-001: Elevation Analysis

**Verification:**
- ✅ Each rule processes independently
- ✅ Rule failures don't prevent other rules from running
- ✅ Results include rule ID, name, status, data
- ✅ Insufficient data marked appropriately

### Test 10: Output Generation

**Purpose:** Verify final response properly formatted

**Expected Response Structure:**
```json
{
  "request_id": "req_TIMESTAMP",
  "status": "success|partial|error",
  "timestamp": "2024-01-15T10:30:45.123456",
  "processing_time_ms": 8432.5,
  "analysis_summary": {
    "polygon_area_sqkm": 0.0745,
    "bounding_box": [-73.9352, 40.7306, -73.9122, 40.7489],
    "analysis_date": "2024-01-15T10:30:45.123456",
    "key_findings": [...]
  },
  "land_information": {
    "administrative": {...},
    "land_cover": {...},
    "buildings": {...},
    "roads": {...},
    "water": {...},
    "elevation": {...}
  },
  "processing_status": [
    {"module_name": "validation", "status": "success"},
    {"module_name": "data_collection", "status": "success"},
    {"module_name": "data_validation", "status": "success"},
    {"module_name": "standardization", "status": "success"},
    {"module_name": "rule_engine", "status": "success"},
    {"module_name": "output_generation", "status": "success"}
  ],
  "provider_status": [
    {"provider_name": "osm_buildings", "status": "available", ...},
    ...
  ],
  "errors": []
}
```

**Verification Points:**
- ✅ Response is valid JSON
- ✅ All required fields present
- ✅ Status correctly set (success/partial/error)
- ✅ Processing time calculated and included
- ✅ All 6 modules show status
- ✅ All 6 providers show status
- ✅ Analysis data populated correctly
- ✅ No raw provider data in output
- ✅ No stack traces or implementation details

## Error Handling Verification

### Test 11: Provider Failure Handling

**Purpose:** Verify system continues if provider unavailable

**Manual Test:**
1. Stop one provider (simulate by modifying config)
2. Submit valid polygon for analysis
3. Observe results

**Expected Behavior:**
- ✅ Analysis completes despite missing provider
- ✅ Results show partial data from available providers
- ✅ Unavailable provider status shown correctly
- ✅ No cascading failures

### Test 12: Network Error Handling

**Purpose:** Verify graceful handling of network timeouts

**Test Steps:**
1. Start analysis
2. While processing, turn off network
3. Observe error handling

**Expected Behavior:**
- ✅ Request times out after configured timeout (60s)
- ✅ Error message displayed to user
- ✅ Error is readable and helpful
- ✅ Backend logs error but doesn't crash

### Test 13: Invalid JSON Upload

**Purpose:** Verify JSON parse error handling

**Create Test File** (`test_broken.json`):
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[  // missing closing bracket
```

**Test Steps:**
1. Click "Upload GeoJSON" input
2. Upload test_broken.json
3. Observe error

**Expected Behavior:**
- ✅ Frontend catches JSON parse error
- ✅ User-friendly error message displayed
- ✅ Error explains the problem
- ✅ No backend call made

## Performance Verification

### Test 14: Response Time

**Purpose:** Verify analysis completes in reasonable time

**Test Steps:**
1. Submit valid polygon analysis
2. Measure time from submission to results display
3. Compare with expected baseline

**Expected Performance:**
- Total Analysis Time: 5-20 seconds (network dependent)
  - Polygon Validation: < 100ms
  - Data Collection: 3-10s (provider network latency)
  - Data Validation: < 500ms
  - Standardization: 500-1000ms
  - Rule Engine: 1-5s
  - Output Generation: < 100ms

**Verification Points:**
- ✅ Processing time displayed in results
- ✅ Total time reasonable for demonstration
- ✅ No unnecessary delays
- ✅ Concurrent collection maximizes speed

## Regression Testing

### Quick Regression Suite

Run these tests to verify no regressions:

**Test Checklist:**
- [ ] Backend health check returns 200
- [ ] Backend status lists 6 enabled providers
- [ ] Frontend loads without errors
- [ ] Frontend map displays correctly
- [ ] Can draw polygon on map
- [ ] Can upload GeoJSON file
- [ ] Analyze button submits to backend
- [ ] Loading indicator shows during processing
- [ ] Results display after completion
- [ ] Error display works for invalid input
- [ ] Response includes all required fields
- [ ] Status codes correct (200/400/500)
- [ ] No console errors
- [ ] No server crashes
- [ ] No stack traces in responses

## Logging Review

### Backend Logs to Check

Look for these in backend logs:

**Success Path:**
```
STAGE 1: Validating polygon...
✓ Polygon validated: area=X.XX sq km

STAGE 2: Collecting data from providers...
✓ Data collection complete: N datasets collected

STAGE 3: Validating collected data...
✓ Data validation complete: M successful, K failed

STAGE 4: Standardizing data to common format...
✓ Standardization complete: N datasets standardized

STAGE 5: Processing with Rule Engine...
✓ Rule Engine complete: N rules executed

STAGE 6: Generating output...
✓ Analysis complete: status=success, time=XXXXX.XXms
```

**Error Path:**
```
Polygon validation failed: [error reason]
or
Data collection error: [error reason]
or
Unexpected exception: [error type]
```

## Troubleshooting

### Issue: Backend won't start

**Symptoms:** Port already in use or import errors

**Solutions:**
```bash
# Check port 8000 is available
lsof -i :8000

# If occupied, kill process or use different port
python backend/main.py --port 8001

# If import errors, check dependencies
pip install -r requirements.txt

# Verify Python version (3.8+)
python --version
```

### Issue: Frontend can't reach backend

**Symptoms:** "Failed to connect to server" error

**Solutions:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS headers in response
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     http://localhost:8000/analyze

# Try accessing directly in browser
http://localhost:8000/docs
```

### Issue: Polygon validation fails

**Symptoms:** "Invalid GeoJSON" error

**Solutions:**
- Verify GeoJSON format is correct
- Use http://geojson.io to validate polygon
- Check coordinates are [longitude, latitude] not reversed
- Ensure polygon has at least 3 coordinate pairs

### Issue: No data collected

**Symptoms:** Analysis returns but no provider data

**Solutions:**
- Check provider status in response (available/unavailable)
- Verify config/providers.json has providers enabled
- Check backend logs for collection errors
- Try with different polygon (different region may have more data)

## Success Criteria

Task 12 is complete when:

✅ **All Endpoints Functional**
- /health returns 200 with service status
- /status returns 200 with provider list
- /analyze returns 200 with analysis results (for valid input)
- /analyze returns 400/422 for invalid input
- /analyze returns 500 for server errors (safely)

✅ **Frontend Working**
- Frontend loads and displays map
- Can draw and upload polygons
- Can submit analysis requests
- Results display correctly formatted
- Errors display clearly

✅ **Error Handling**
- Invalid input caught and reported
- Provider failures handled gracefully
- Unexpected errors don't crash system
- Error messages are safe and descriptive

✅ **Data Flow**
- All 6 modules execute in sequence
- Each stage processes data correctly
- Results include all expected fields
- No raw provider data exposed
- Status codes correct for all scenarios

✅ **Performance**
- Analysis completes in reasonable time
- Response includes processing time
- UI responsive during processing
- Loading indicator functions

✅ **Logging**
- Backend logs key events
- Error messages logged safely
- Request IDs track flow
- No sensitive data logged

## Next Steps

If Task 12 verification is **successful**:
- ✅ Proceed to Task 13: Backend Tests - Unit Tests
- ✅ Start implementing unit tests for individual modules
- ✅ Implement property-based tests for correctness properties

If Task 12 verification **failed**:
- 🔄 Debug the specific failure using this guide
- 🔄 Check backend logs for detailed error information
- 🔄 Review the relevant module implementation
- 🔄 Fix the issue and re-test

