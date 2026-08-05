# Frontend-Backend Connection Guide

## Overview

This document outlines the connection patterns, call syntax, and best practices for communication between the frontend and backend services in the Land Scanner Prototype.

---

## Call Syntax

### Frontend API Client (`frontend/src/services/api.js`)

The frontend uses a centralized API service layer that wraps all backend communication.

#### 1. Analyze Polygon

**Function Signature:**
```javascript
async analyzePolygon(polygon: Object): Promise<ApiResponse>
```

**Usage:**
```javascript
import { analyzePolygon, logApiEvent } from './services/api'

try {
  const results = await analyzePolygon(currentPolygon)
  logApiEvent(results.request_id, 'analysis_completed', { 
    processing_time_ms: results.processing_time_ms 
  })
} catch (err) {
  console.error('Analysis failed:', err.message)
}
```

**Request Structure:**
```json
{
  "polygon": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], [lon, lat], ...]]
  }
}
```

**Response Structure:**
```json
{
  "request_id": "req_1722610800000",
  "status": "success|partial|failed",
  "timestamp": "2024-08-02T10:30:00.000Z",
  "processing_time_ms": 1234.56,
  "analysis_summary": {
    "polygon_area_sqkm": 156.78,
    "bounding_box": [lon_min, lat_min, lon_max, lat_max],
    "analysis_date": "2024-08-02T10:30:00.000Z",
    "key_findings": ["...", "..."]
  },
  "land_information": {
    "ADM-001": { "rule_id": "ADM-001", "rule_name": "Administrative", "status": "success", "result": {...} },
    "LC-001": { "rule_id": "LC-001", "rule_name": "Land Cover", "status": "success", "result": {...} }
  },
  "processing_status": {
    "validation": { "module_name": "validation", "status": "success", "execution_time_ms": 10 },
    "data_collection": { "module_name": "data_collection", "status": "success", "execution_time_ms": 500 }
  },
  "provider_status": [
    { "provider_name": "OSM", "status": "available", "data_retrieved": true },
    { "provider_name": "USGS", "status": "available", "data_retrieved": true }
  ],
  "errors": []
}
```

#### 2. Check Health

**Function Signature:**
```javascript
async checkHealth(): Promise<Object>
```

**Usage:**
```javascript
import { checkHealth } from './services/api'

const healthStatus = await checkHealth()
console.log(healthStatus.status) // 'operational'
```

**Response Structure:**
```json
{
  "status": "operational",
  "service": "Land Scanner Prototype",
  "version": "1.0.0",
  "timestamp": "2024-08-02T10:30:00.000Z"
}
```

#### 3. Get Service Status

**Function Signature:**
```javascript
async getStatus(): Promise<Object>
```

**Usage:**
```javascript
import { getStatus } from './services/api'

const status = await getStatus()
console.log(status.enabled_providers) // ['OSM', 'USGS', ...]
```

**Response Structure:**
```json
{
  "prototype_name": "Land Scanner Prototype",
  "version": "1.0.0",
  "timestamp": "2024-08-02T10:30:00.000Z",
  "enabled_providers": ["OSM", "USGS", "GEBCO"],
  "provider_count": 3,
  "debug_mode": false
}
```

---

### Backend Endpoints (`backend/main.py`)

#### 1. POST /analyze

**Endpoint Signature:**
```python
@app.post("/analyze")
async def analyze_polygon(body: AnalysisRequest) -> AnalysisResponse:
```

**Input Model (`backend/models/schemas.py`):**
```python
class AnalysisRequest(BaseModel):
    polygon: Dict[str, Any] = Field(
        ...,
        description="GeoJSON polygon object with type='Polygon' and coordinates array"
    )
    
    @validator('polygon')
    def validate_polygon_structure(cls, v):
        # Validates GeoJSON structure on server side
```

**Processing Pipeline:**
1. **Validation Stage** - PolygonValidator validates GeoJSON structure
2. **Data Collection** - DataSourceManager collects from all enabled providers
3. **Data Validation** - DataValidator verifies collected data structure
4. **Standardization** - Standardizer converts to common format
5. **Rule Engine** - RuleEngine applies analysis rules
6. **Output Generation** - Compiles results into AnalysisResponse

**Error Handling:**
```python
# HTTP 400 - Bad Request (validation error)
# HTTP 422 - Unprocessable Entity (invalid polygon)
# HTTP 500 - Internal Server Error
```

**Error Response Format:**
```json
{
  "status": "error",
  "error_code": "POLYGON_VALIDATION_ERROR",
  "error_message": "Polygon validation failed: coordinates not valid",
  "request_id": "req_1722610800000",
  "details": {...}
}
```

#### 2. GET /health

**Endpoint Signature:**
```python
@app.get("/health")
async def health_check() -> Dict[str, str]:
```

**Returns:** Service health status

#### 3. GET /status

**Endpoint Signature:**
```python
@app.get("/status")
async def get_status() -> Dict[str, Any]:
```

**Returns:** Service configuration and provider status

---

## Request/Response Flow

### Complete Analysis Request Flow

```
Frontend (App.jsx)
    ↓
    └─→ analyzePolygon(polygon)
         ├─ validatePolygon(polygon)  [Client-side validation]
         └─ executeRequest('/analyze', { polygon })
            └─→ fetch() with AbortController & timeout
                ↓
Backend (main.py)
    ↓
    @app.post("/analyze")
    └─→ analyze_polygon(body: AnalysisRequest)
         ├─ Validate polygon (server-side)
         ├─ DataSourceManager.collect()
         ├─ DataValidator.validate_collection()
         ├─ Standardizer.standardize()
         ├─ RuleEngine.execute()
         └─ Return AnalysisResponse
                ↓
Frontend (ResultsPanel.jsx)
    ↓
    └─→ Display results with safe string conversion
```

---

## Error Handling Patterns

### Frontend Error Handling

```javascript
try {
  const results = await analyzePolygon(polygon)
  // Success handling
} catch (err) {
  // err.message - User-friendly error message
  // err.status - HTTP status code (if available)
  // err.response - Full error response object
}
```

**Error Types:**
- Validation errors (client-side): "Invalid GeoJSON: ..."
- Timeout errors: "Request timeout after 60000ms..."
- Server errors: "HTTP 500: Internal Server Error"

### Backend Error Handling

```python
# Middleware catches all exceptions
# SafeError class provides consistent error formatting
# Error responses never expose implementation details
```

**Error Response Schema:**
```python
{
  "status": "error",
  "error_code": str,  # Enum: VALIDATION_ERROR, POLYGON_VALIDATION_ERROR, etc.
  "error_message": str,  # User-friendly message
  "request_id": str,  # For debugging/tracking
  "details": {}  # Additional context
}
```

---

## Timeout & Retry Strategy

### Frontend Timeout

**Default Timeout:** 60 seconds (60000ms)

**Implementation:**
```javascript
const controller = new AbortController()
const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT)
// Request aborted if exceeds timeout
```

**User-Facing Message:** "Request timeout after 60000ms. Please try again."

### No Automatic Retry

Currently, no automatic retry is implemented. Users must manually retry via the UI.

**Future Enhancement:** Consider exponential backoff retry for network failures.

---

## Type Definitions

### Frontend API Response Type (JSDoc)

```javascript
/**
 * @typedef {Object} ApiResponse
 * @property {string} request_id - Unique request identifier
 * @property {string} status - Processing status (success, partial, failed)
 * @property {number} processing_time_ms - Total processing time
 * @property {Object} analysis_summary - High-level summary
 * @property {Object} land_information - Rule results organized by category
 * @property {Object} processing_status - Status of each processing module
 * @property {Array} provider_status - Status of each data provider
 * @property {Array} errors - List of errors if any occurred
 */
```

### Backend Models (Pydantic)

**AnalysisRequest:**
```python
class AnalysisRequest(BaseModel):
    polygon: Dict[str, Any]
```

**AnalysisResponse:**
```python
class AnalysisResponse(BaseModel):
    request_id: str
    status: ProcessingStatus
    timestamp: datetime
    processing_time_ms: float
    analysis_summary: Dict[str, Any]
    land_information: Dict[str, RuleResult]
    processing_status: Dict[str, ModuleStatus]
    provider_status: List[ProviderStatus]
    errors: List[ErrorInfo]
```

---

## Improvements Made

### ✅ Implemented

1. **Centralized API Service Layer** (`frontend/src/services/api.js`)
   - Single source of truth for all API calls
   - Consistent error handling
   - Request/response formatting

2. **Client-Side Validation** 
   - GeoJSON structure validation before sending
   - Prevents invalid requests reaching backend

3. **Timeout Implementation**
   - AbortController with configurable timeout
   - Handles timeout gracefully with user-friendly message

4. **Request Tracking**
   - Request ID logging for debugging
   - `logApiEvent()` function for monitoring

5. **Server-Side Request Model**
   - `AnalysisRequest` Pydantic model with built-in validation
   - Type safety and auto-generated OpenAPI documentation

6. **Error Formatting Standardization**
   - Consistent error response structure
   - Safe error messages (no implementation details exposed)

---

## Usage Examples

### Example 1: Basic Analysis

```javascript
// In App.jsx
import { analyzePolygon } from './services/api'

const handleAnalyze = async () => {
  try {
    const results = await analyzePolygon({
      type: 'Polygon',
      coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
    })
    console.log('Analysis complete:', results.status)
  } catch (err) {
    console.error('Analysis failed:', err.message)
  }
}
```

### Example 2: Error Handling with Request ID

```javascript
// In App.jsx
import { analyzePolygon, logApiEvent } from './services/api'

const handleAnalyze = async () => {
  try {
    const results = await analyzePolygon(currentPolygon)
    
    // Log successful analysis
    logApiEvent(results.request_id, 'analysis_success', {
      processing_time_ms: results.processing_time_ms,
      rule_count: Object.keys(results.land_information).length
    })
    
    setAnalysisResults(results)
  } catch (err) {
    logApiEvent(null, 'analysis_failed', {
      error: err.message,
      polygon: currentPolygon
    })
    setError(err.message)
  }
}
```

### Example 3: Health Check on App Load

```javascript
// In App.jsx
import { useEffect } from 'react'
import { checkHealth } from './services/api'

useEffect(() => {
  checkHealth()
    .then(status => console.log('Backend healthy:', status))
    .catch(err => console.error('Backend unavailable:', err.message))
}, [])
```

---

## Environment Variables

**Frontend:**
- `VITE_API_BASE` - Backend API URL (default: `https://land-scanner-prototype-backend.onrender.com`)

**Backend:**
- `ALLOWED_ORIGINS` - CORS allowed origins (default: hardcoded, should move to env)
- `API_TIMEOUT` - Request timeout in ms (default: hardcoded per provider)

---

## Testing API Connections

### Using cURL (Backend Testing)

```bash
# Test /analyze endpoint
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"polygon":{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]]}'

# Test /health endpoint
curl http://localhost:8000/health

# Test /status endpoint
curl http://localhost:8000/status
```

### Using Frontend Console

```javascript
// In browser console
import('http://localhost:5173/src/services/api.js')
  .then(api => api.checkHealth())
  .then(console.log)
  .catch(console.error)
```

---

## Future Enhancements

1. **API Versioning** - Add `/v1/`, `/v2/` patterns
2. **Automatic Retry** - Exponential backoff for transient failures
3. **Request Caching** - Cache analysis results for duplicate polygons
4. **WebSocket Support** - Real-time progress updates during analysis
5. **Rate Limiting** - Implement frontend rate limiting
6. **TypeScript Migration** - Add full type safety to frontend
7. **Mock API** - Mock backend for frontend development/testing

---

## Summary

The improved frontend-backend connection provides:
- **Type Safety:** Pydantic models on backend, JSDoc types on frontend
- **Error Handling:** Consistent error responses across all endpoints
- **Timeout Management:** Proper request timeout with AbortController
- **Request Tracking:** Unique request IDs for debugging
- **Client Validation:** Pre-flight validation prevents invalid requests
- **Centralized API:** Single service layer for all communication
