# Complete Frontend-Backend Connection Analysis

## Executive Summary

The Land Scanner Prototype is a geospatial analysis platform with a React frontend and FastAPI backend. The system has been improved with centralized API service layer, comprehensive validation, timeout enforcement, and request tracking.

**Status:** ✅ Well-architected with recent improvements for production readiness

**Key Metrics:**
- 6-stage backend processing pipeline
- 60-second request timeout
- Centralized API service (frontend/src/services/api.js)
- Pydantic validation (backend request/response)
- Zero manual connection code duplication

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React 18)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Components (MapContainer, ControlPanel)         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │    API Service Layer (frontend/src/services/api.js)      │   │
│  │  - analyzePolygon()          [Client validation]         │   │
│  │  - checkHealth()             [Timeout: 60s]              │   │
│  │  - getStatus()               [Request tracking]          │   │
│  │  - executeRequest()          [Error handling]            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         ↓ HTTPS/CORS ↓         [AbortController + Timeout]
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Error Handler Middleware                    │   │
│  │  Global error catching + request ID generation           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          POST /analyze (AnalysisRequest body)            │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ 6-Stage Processing Pipeline:                       │  │   │
│  │  │ 1. Polygon Validation (PolygonValidator)           │  │   │
│  │  │ 2. Data Collection (DataSourceManager)             │  │   │
│  │  │ 3. Data Validation (DataValidator)                 │  │   │
│  │  │ 4. Standardization (Standardizer)                  │  │   │
│  │  │ 5. Rule Engine (RuleEngine)                        │  │   │
│  │  │ 6. Output Generation (AnalysisResponse)            │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │  Returns: AnalysisResponse (Pydantic model)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │    GET /health, GET /status (Service endpoints)          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Complete Data Flow Diagrams

### Analysis Request Flow

```
User Action
    ↓
App.handleAnalyze()
    ├─ Check polygon exists
    ├─ Check analysis not in progress
    ├─ logApiEvent('polygon_analysis_started')
    └─→ analyzePolygon(currentPolygon)
              │
              ├─ validatePolygon()
              │     ├─ Check type = 'Polygon'
              │     ├─ Check coordinates exist
              │     ├─ Check bounds (-180 to 180, -90 to 90)
              │     └─ Throw if invalid
              │
              └─→ executeRequest('/analyze', { polygon })
                    │
                    ├─ Create AbortController
                    ├─ Set 60s timeout
                    ├─ fetch() with signal
                    │
                    └─→ Backend POST /analyze
                          │
                          ├─ Middleware error_handler_middleware
                          │     ├─ Generate request_id
                          │     ├─ Wrap call_next() in try/catch
                          │     └─ Catch all exceptions
                          │
                          ├─ analyze_polygon(body: AnalysisRequest)
                          │     ├─ Pydantic validates request body
                          │     ├─ Extract: polygon = body.polygon
                          │     │
                          │     ├─ STAGE 1: PolygonValidator.validate()
                          │     │     ├─ Check GeoJSON structure
                          │     │     ├─ Validate coordinates
                          │     │     ├─ Calculate area (shapely)
                          │     │     ├─ Calculate bounding box
                          │     │     ├─ Calculate centroid
                          │     │     └─ Return Polygon model
                          │     │
                          │     ├─ STAGE 2: DataSourceManager.collect()
                          │     │     ├─ Loop through collectors
                          │     │     ├─ Execute async collector.get_data()
                          │     │     ├─ Catch individual failures
                          │     │     ├─ Record provider_status
                          │     │     └─ Aggregate RawDataset list
                          │     │
                          │     ├─ STAGE 3: DataValidator.validate()
                          │     │     ├─ Check dataset structure
                          │     │     ├─ Validate feature geometries
                          │     │     ├─ Verify metadata
                          │     │     └─ Return validation status
                          │     │
                          │     ├─ STAGE 4: Standardizer.standardize()
                          │     │     ├─ Convert to common format
                          │     │     ├─ Map properties
                          │     │     ├─ Verify CRS (EPSG:4326)
                          │     │     └─ Return StandardizedDataset
                          │     │
                          │     ├─ STAGE 5: RuleEngine.execute()
                          │     │     ├─ Load rule definitions
                          │     │     ├─ Execute each rule
                          │     │     ├─ Calculate metrics
                          │     │     └─ Return Dict[rule_id, RuleResult]
                          │     │
                          │     └─ STAGE 6: Compile AnalysisResponse
                          │           ├─ Set status (success/partial/failed)
                          │           ├─ Compile land_information
                          │           ├─ Compile processing_status
                          │           ├─ Calculate processing_time_ms
                          │           └─ Return AnalysisResponse
                          │
                          └─→ Return JSON response

Response travels back through HTTP/CORS

Frontend executeRequest() catches response
    ├─ Check response.ok
    ├─ Parse JSON
    └─ Return ApiResponse object

analyzePolygon() returns results

App.jsx handleAnalyze()
    ├─ setCurrentRequestId(results.request_id)
    ├─ logApiEvent(request_id, 'analysis_completed')
    ├─ setAnalysisResults(results)
    └─ Clear loading/analysisInProgress

UI Updates
    ↓
ResultsPanel displays results
```

---

## Request/Response Specifications

### 1. Frontend → Backend: AnalysisRequest

**Endpoint:** POST `/analyze`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "polygon": {
    "type": "Polygon",
    "coordinates": [
      [
        [lon1, lat1],
        [lon2, lat2],
        [lon3, lat3],
        [lon1, lat1]
      ]
    ]
  }
}
```

**Validation Rules (Frontend):**
- ✓ polygon is object
- ✓ polygon.type === "Polygon"
- ✓ polygon.coordinates is array
- ✓ polygon.coordinates.length > 0
- ✓ polygon.coordinates[0].length >= 3
- ✓ Each coordinate is [number, number]
- ✓ longitude: -180 to 180
- ✓ latitude: -90 to 90
- ✓ First and last coordinates match (ring closure)

**Validation Rules (Backend):**
- ✓ AnalysisRequest Pydantic model validation (same as above)
- ✓ Shapely geometry validation (topological correctness)
- ✓ Area calculation (must be positive)
- ✓ Coordinate systems (must be WGS84)

---

### 2. Backend → Frontend: AnalysisResponse

**Response Status:** 200 OK (or 400/422/500 on error)

**Response Headers:**
```
Content-Type: application/json
X-Request-ID: req_1722610800000
X-Process-Time: 1.234
```

**Response Body:**
```json
{
  "request_id": "req_1722610800000",
  "status": "success",
  "timestamp": "2024-08-02T10:30:00.000Z",
  "processing_time_ms": 1234.56,
  
  "analysis_summary": {
    "polygon_area_sqkm": 156.78,
    "bounding_box": [lon_min, lat_min, lon_max, lat_max],
    "analysis_date": "2024-08-02T10:30:00.000Z",
    "key_findings": ["Finding 1", "Finding 2"]
  },
  
  "land_information": {
    "ADM-001": {
      "rule_id": "ADM-001",
      "rule_name": "Administrative",
      "status": "success",
      "result": {
        "admin_level": "District",
        "admin_name": "Example District",
        "population": 150000
      },
      "metadata": {
        "execution_time_ms": 100,
        "data_source": "OSM"
      }
    },
    "LC-001": {
      "rule_id": "LC-001",
      "rule_name": "Land Cover",
      "status": "success",
      "result": {
        "urban_percent": 25.5,
        "forest_percent": 60.3,
        "agricultural_percent": 14.2
      },
      "metadata": {
        "execution_time_ms": 150,
        "data_source": "USGS"
      }
    }
  },
  
  "processing_status": {
    "validation": {
      "module_name": "validation",
      "status": "success",
      "execution_time_ms": 10.2
    },
    "data_collection": {
      "module_name": "data_collection",
      "status": "success",
      "execution_time_ms": 500.5
    },
    "data_validation": {
      "module_name": "data_validation",
      "status": "success",
      "execution_time_ms": 50.1
    },
    "standardization": {
      "module_name": "standardization",
      "status": "success",
      "execution_time_ms": 100.3
    },
    "rule_engine": {
      "module_name": "rule_engine",
      "status": "success",
      "execution_time_ms": 400.2
    },
    "output_generation": {
      "module_name": "output_generation",
      "status": "success",
      "execution_time_ms": 50.0
    }
  },
  
  "provider_status": [
    {
      "provider_name": "OpenStreetMap",
      "status": "available",
      "data_retrieved": true,
      "error_message": null
    },
    {
      "provider_name": "USGS",
      "status": "available",
      "data_retrieved": true,
      "error_message": null
    },
    {
      "provider_name": "GEBCO",
      "status": "available",
      "data_retrieved": true,
      "error_message": null
    }
  ],
  
  "errors": []
}
```

**Response on Partial Success (status: "partial"):**
```json
{
  "status": "partial",
  "processing_status": {
    "rule_engine": {
      "status": "partial",
      "error_message": "Rule RD-001 failed due to insufficient data"
    }
  },
  "provider_status": [
    {
      "provider_name": "OSM",
      "status": "available",
      "data_retrieved": true
    },
    {
      "provider_name": "USGS",
      "status": "error",
      "data_retrieved": false,
      "error_message": "API rate limit exceeded"
    }
  ],
  "errors": [
    {
      "module": "rule_engine",
      "message": "Rule RD-001: Insufficient road data for analysis",
      "severity": "warning"
    }
  ]
}
```

**Response on Error (status: 400/422/500):**
```json
{
  "status": "error",
  "error_code": "POLYGON_VALIDATION_ERROR",
  "error_message": "Polygon validation failed: coordinates must be valid GeoJSON",
  "request_id": "req_1722610800000",
  "details": {
    "field": "polygon.coordinates",
    "reason": "Ring not closed"
  }
}
```

---

## Type Definitions & Schemas

### Python Pydantic Models (Backend)

**Location:** `backend/models/schemas.py`

```python
# Enums
class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    INSUFFICIENT_DATA = "insufficient_data"
    PARTIAL = "partial"

class DataCategory(str, Enum):
    BUILDINGS = "buildings"
    LAND_COVER = "land_cover"
    ROADS = "roads"
    WATER = "water"
    ELEVATION = "elevation"
    ADMIN = "admin"

# Request Model
class AnalysisRequest(BaseModel):
    polygon: Dict[str, Any]  # Validated GeoJSON
    
    @validator('polygon')
    def validate_polygon_structure(cls, v):
        # Validates GeoJSON structure

# Response Models
class Polygon(BaseModel)
class RawDataset(BaseModel)
class Feature(BaseModel)
class StandardizedDataset(BaseModel)
class RuleResult(BaseModel)
class ModuleStatus(BaseModel)
class ErrorInfo(BaseModel)
class ProviderStatus(BaseModel)

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

### JavaScript JSDoc Types (Frontend)

**Location:** `frontend/src/services/api.js`

```javascript
/**
 * @typedef {Object} ApiResponse
 * @property {string} request_id
 * @property {string} status
 * @property {number} processing_time_ms
 * @property {Object} analysis_summary
 * @property {Object} land_information
 * @property {Object} processing_status
 * @property {Array} provider_status
 * @property {Array} errors
 */

// Usage:
/** @type {Promise<ApiResponse>} */
const results = await analyzePolygon(polygon)
```

---

## All Connection Functions

### Frontend API Functions (frontend/src/services/api.js)

| Function | Endpoint | Method | Purpose | Returns |
|----------|----------|--------|---------|---------|
| `analyzePolygon(polygon)` | `/analyze` | POST | Main analysis | `Promise<ApiResponse>` |
| `checkHealth()` | `/health` | GET | Health check | `Promise<HealthStatus>` |
| `getStatus()` | `/status` | GET | Service config | `Promise<StatusResponse>` |
| `executeRequest(endpoint, options)` | Any | Any | Low-level | `Promise<Object>` |
| `validatePolygon(polygon)` | - | - | Client validation | `void` |
| `formatError(error, context)` | - | - | Error formatting | `Object` |
| `logApiEvent(requestId, type, details)` | - | - | Event logging | `void` |

### Backend Endpoints (backend/main.py)

| Endpoint | Method | Handler | Purpose | Returns |
|----------|--------|---------|---------|---------|
| `/analyze` | POST | `analyze_polygon()` | Polygon analysis | `AnalysisResponse` |
| `/health` | GET | `health_check()` | Health status | `{ status, service, version, timestamp }` |
| `/status` | GET | `get_status()` | Service status | `{ prototype_name, version, providers, ... }` |

---

## Error Handling Complete Map

### Error Types & Responses

| Error Type | HTTP Status | Error Code | Recovery |
|-----------|------------|-----------|----------|
| Invalid GeoJSON | 422 | POLYGON_VALIDATION_ERROR | User must fix polygon |
| Missing polygon field | 422 | VALIDATION_ERROR | User must provide polygon |
| Invalid coordinates | 400 | POLYGON_VALIDATION_ERROR | User must verify coordinates |
| Timeout (60s) | 408 | REQUEST_TIMEOUT | User can retry |
| Provider error | 502 | PROVIDER_ERROR | Backend retries, returns partial |
| Rule execution error | 200 (status: partial) | Rule-specific | Returns partial results |
| Internal error | 500 | INTERNAL_ERROR | User should retry later |

### Frontend Error Handling

```javascript
try {
  const results = await analyzePolygon(polygon)
} catch (err) {
  if (err.message.includes('timeout')) {
    // Handle timeout: "Request timeout after 60000ms..."
  } else if (err.message.includes('Invalid GeoJSON')) {
    // Handle validation: "Invalid GeoJSON: ..."
  } else if (err.status === 502) {
    // Handle provider error
  } else if (err.status >= 500) {
    // Handle server error
  } else {
    // Generic error handling
  }
}
```

### Backend Error Handling

```python
# Middleware catches ALL exceptions
@app.middleware("http")
async def error_handler_middleware(request, call_next):
    try:
        response = await call_next(request)
        return response
    except HTTPException as e:
        # HTTP exceptions (422, 400, etc.)
    except PolygonValidationError as e:
        # Validation errors
    except ValueError as e:
        # Value errors
    except Exception as e:
        # Unexpected errors
```

---

## Validation Layers

### Client-Side Validation (Frontend)

**Function:** `validatePolygon()` in `api.js`

Checks:
1. Polygon is truthy
2. Type is "Polygon"
3. Coordinates is array
4. Coordinates non-empty
5. At least 3 coordinate pairs
6. Each coordinate is [number, number]
7. Bounds: -180 ≤ lon ≤ 180, -90 ≤ lat ≤ 90
8. Ring closure (first = last)

**Throws on Fail:** Immediately stops request

### Server-Side Validation (Backend)

**Layer 1: Pydantic Model** (`AnalysisRequest`)
- Validates request body structure

**Layer 2: GeoJSON Validator** (`PolygonValidator`)
- ✓ Structure validation
- ✓ Shapely geometry validation (topological)
- ✓ Area calculation
- ✓ Bounding box calculation
- ✓ Centroid calculation
- ✓ CRS verification (EPSG:4326)

**Layer 3: Data Collection** (`DataSourceManager`)
- ✓ Provider availability checks
- ✓ Feature validation per provider
- ✓ Graceful failure handling

**Layer 4: Standardization** (`Standardizer`)
- ✓ Property mapping validation
- ✓ CRS consistency
- ✓ Feature structure validation

---

## Performance Characteristics

### Request Timeline

```
Frontend:
  validatePolygon()           ~1ms (client-side)
  executeRequest()            <1ms (setup)
  fetch() send                ~50-100ms (network)
  
Backend:
  Middleware                  ~5ms (request setup)
  Pydantic validation         ~2ms (request body)
  PolygonValidator            ~10-50ms (geometry)
  DataSourceManager           ~500-2000ms (collectors)
  DataValidator               ~50-200ms (validation)
  Standardizer                ~100-500ms (mapping)
  RuleEngine                  ~200-1000ms (rules)
  Output generation           ~10-50ms (compilation)
  
Total Backend: ~900-3800ms (typical)

Frontend:
  Response parse              ~10-50ms
  State updates               ~5ms
  UI render                   ~100-500ms (depends on data size)

Total Round Trip: ~1000-4500ms (typical)
Timeout: 60000ms (60 seconds)
Timeout utilization: 1.67-7.5%
```

### Data Size Estimates

**Typical Request:**
```
polygon coordinates: ~50-200 pairs = 1-4 KB
Total request: ~1-5 KB
```

**Typical Response (1000+ features across providers):**
```
Analysis response: 500 KB - 2 MB
Processing status: 1-5 KB
Provider status: 1-3 KB
Errors (if any): 1-10 KB
Total: 500 KB - 2 MB
```

---

## Files & Code Locations

### Frontend Files
- `frontend/src/services/api.js` - Centralized API service
- `frontend/src/App.jsx` - Main app component (uses api.js)
- `frontend/src/components/MapContainer.jsx` - Map UI
- `frontend/src/components/ControlPanel.jsx` - Control UI
- `frontend/src/components/ResultsPanel.jsx` - Results display

### Backend Files
- `backend/main.py` - FastAPI app + endpoints + middleware
- `backend/models/schemas.py` - Pydantic models + AnalysisRequest
- `backend/validators/polygon_validator.py` - Polygon validation
- `backend/managers/data_source_manager.py` - Data collection
- `backend/standardizers/standardizer.py` - Data standardization
- `backend/rules/rule_engine.py` - Rule processing
- `backend/exceptions/error_handler.py` - Error handling

---

## Summary

✅ **Strong Architecture:**
- Centralized API layer (frontend)
- Comprehensive validation (client + server)
- Timeout enforcement (60s)
- Request tracking (request_id)
- Structured error handling
- Type safety (Pydantic + JSDoc)
- Graceful degradation (provider failures)

⚠️ **Considerations:**
- No automatic retry (manual UI retry available)
- CORS origins hardcoded (should use env vars)
- No request caching
- Single timeout for all providers
- No rate limiting

✨ **Recent Improvements:**
- API service layer (NEW)
- Client-side validation (NEW)
- Request tracking (NEW)
- Timeout implementation (ENHANCED)
- Server request model (ENHANCED)

See: `API_CONNECTION_GUIDE.md` and `CONNECTION_BEFORE_AFTER.md` for detailed documentation.
