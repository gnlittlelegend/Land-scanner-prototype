# Complete Endpoint Reference & Testing Guide

## Endpoint 1: POST /analyze

**Purpose:** Main geospatial analysis endpoint

**Base URL:** 
- Production: `https://land-scanner-prototype-backend.onrender.com`
- Development: `http://localhost:8000`

**Full URL:** `{BASE_URL}/analyze`

---

### Request Specification

**Method:** POST

**Content-Type:** application/json

**Request Body:**
```json
{
  "polygon": {
    "type": "Polygon",
    "coordinates": [
      [
        [longitude, latitude],
        [longitude, latitude],
        [longitude, latitude],
        [longitude, latitude]
      ]
    ]
  }
}
```

**Example Request (Rectangle):**
```json
{
  "polygon": {
    "type": "Polygon",
    "coordinates": [
      [
        [77.5, 12.5],
        [78.5, 12.5],
        [78.5, 13.5],
        [77.5, 13.5],
        [77.5, 12.5]
      ]
    ]
  }
}
```

**Coordinate System:** WGS84 (EPSG:4326)
- Longitude: -180 to 180
- Latitude: -90 to 90
- Format: [longitude, latitude] (NOT latitude, longitude)

**Polygon Rules:**
- Must close (first coordinate = last coordinate)
- At least 4 coordinate pairs (3 unique + closure)
- No self-intersections
- Counter-clockwise winding order (recommended)

---

### Response Specification

**Success Response (HTTP 200):**

```json
{
  "request_id": "req_1722610800000",
  "status": "success",
  "timestamp": "2024-08-02T10:30:00.000Z",
  "processing_time_ms": 1234.56,
  "analysis_summary": {
    "polygon_area_sqkm": 156.78,
    "bounding_box": [77.5, 12.5, 78.5, 13.5],
    "analysis_date": "2024-08-02T10:30:00.000Z",
    "key_findings": [
      "Urban area covers 25% of polygon",
      "Protected forest found in southeast"
    ]
  },
  "land_information": {
    "ADM-001": {
      "rule_id": "ADM-001",
      "rule_name": "Administrative",
      "status": "success",
      "result": {
        "admin_level": "District",
        "admin_name": "Bangalore Urban",
        "population": 8500000
      },
      "metadata": {
        "execution_time_ms": 120,
        "data_source": "OpenStreetMap",
        "features_analyzed": 45
      }
    },
    "LC-001": {
      "rule_id": "LC-001",
      "rule_name": "Land Cover",
      "status": "success",
      "result": {
        "urban_percent": 25.4,
        "forest_percent": 42.1,
        "agricultural_percent": 22.3,
        "water_percent": 3.2,
        "other_percent": 7.0
      },
      "metadata": {
        "execution_time_ms": 450,
        "data_source": "USGS",
        "classification_accuracy": 0.87
      }
    },
    "BLD-001": {
      "rule_id": "BLD-001",
      "rule_name": "Buildings",
      "status": "success",
      "result": {
        "total_buildings": 12500,
        "avg_building_area_sqm": 150,
        "building_density_per_sqkm": 82.5
      },
      "metadata": {
        "execution_time_ms": 280,
        "data_source": "OpenStreetMap"
      }
    }
  },
  "processing_status": {
    "validation": {
      "module_name": "validation",
      "status": "success",
      "execution_time_ms": 15.2,
      "error_message": null
    },
    "data_collection": {
      "module_name": "data_collection",
      "status": "success",
      "execution_time_ms": 520.3,
      "error_message": null
    },
    "data_validation": {
      "module_name": "data_validation",
      "status": "success",
      "execution_time_ms": 65.1,
      "error_message": null
    },
    "standardization": {
      "module_name": "standardization",
      "status": "success",
      "execution_time_ms": 120.4,
      "error_message": null
    },
    "rule_engine": {
      "module_name": "rule_engine",
      "status": "success",
      "execution_time_ms": 450.2,
      "error_message": null
    },
    "output_generation": {
      "module_name": "output_generation",
      "status": "success",
      "execution_time_ms": 25.0,
      "error_message": null
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

**Partial Response (HTTP 200, status: "partial"):**

```json
{
  "request_id": "req_1722610802000",
  "status": "partial",
  "timestamp": "2024-08-02T10:30:02.000Z",
  "processing_time_ms": 2100.45,
  "analysis_summary": { ... },
  "land_information": {
    "ADM-001": { "status": "success", "result": {...} },
    "LC-001": { "status": "success", "result": {...} },
    "BLD-001": { "status": "failed", "result": {}, "error_message": "..." }
  },
  "processing_status": {
    "validation": { "status": "success" },
    "data_collection": { "status": "partial", "error_message": "USGS API rate limit exceeded" },
    "data_validation": { "status": "success" },
    "standardization": { "status": "success" },
    "rule_engine": { "status": "partial", "error_message": "BLD-001 failed due to insufficient data" }
  },
  "provider_status": [
    { "provider_name": "OpenStreetMap", "status": "available", "data_retrieved": true },
    { "provider_name": "USGS", "status": "error", "data_retrieved": false, "error_message": "Rate limit exceeded" },
    { "provider_name": "GEBCO", "status": "available", "data_retrieved": true }
  ],
  "errors": [
    {
      "module": "data_collection",
      "message": "USGS provider failed: Rate limit exceeded, retrying with cached data",
      "severity": "warning"
    },
    {
      "module": "rule_engine",
      "message": "BLD-001: Insufficient building data, returning partial results",
      "severity": "warning"
    }
  ]
}
```

**Error Response (HTTP 422 - Validation Error):**

```json
{
  "status": "error",
  "error_code": "POLYGON_VALIDATION_ERROR",
  "error_message": "Polygon validation failed: coordinates must form a valid ring",
  "request_id": "req_1722610803000",
  "details": {
    "field": "polygon.coordinates",
    "reason": "First and last coordinates must match (ring not closed)",
    "received": [[77.5, 12.5], [78.5, 12.5], [78.5, 13.5], [77.5, 13.5]],
    "expected": "First coordinate [77.5, 12.5] must equal last coordinate [77.5, 13.5]"
  }
}
```

**Error Response (HTTP 400 - Bad Request):**

```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "error_message": "Invalid request: polygon field is required",
  "request_id": "req_1722610804000",
  "details": {
    "missing_field": "polygon"
  }
}
```

**Error Response (HTTP 408 - Timeout):**

```json
{
  "status": "error",
  "error_code": "REQUEST_TIMEOUT",
  "error_message": "Request exceeded 60000ms timeout",
  "request_id": "req_1722610805000"
}
```

**Error Response (HTTP 500 - Internal Server Error):**

```json
{
  "status": "error",
  "error_code": "INTERNAL_ERROR",
  "error_message": "An unexpected error occurred. Please try again later.",
  "request_id": "req_1722610806000",
  "timestamp": "2024-08-02T10:30:06.000Z"
}
```

---

### HTTP Status Codes

| Status | Meaning | Recovery |
|--------|---------|----------|
| 200 | Success (status: success or partial) | No action needed |
| 400 | Bad request (missing/malformed field) | Fix request body |
| 408 | Request timeout (>60s) | Retry request |
| 422 | Unprocessable entity (invalid polygon) | Fix polygon geometry |
| 500 | Internal server error | Retry after delay |
| 502 | Bad gateway (provider error) | Retry, may get partial results |

---

### Testing with cURL

**Basic Test:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": {
      "type": "Polygon",
      "coordinates": [[[77.5, 12.5], [78.5, 12.5], [78.5, 13.5], [77.5, 13.5], [77.5, 12.5]]]
    }
  }'
```

**Production Test:**
```bash
curl -X POST https://land-scanner-prototype-backend.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": {
      "type": "Polygon",
      "coordinates": [[[77.5, 12.5], [78.5, 12.5], [78.5, 13.5], [77.5, 13.5], [77.5, 12.5]]]
    }
  }' | jq
```

**Large Polygon (Complex Geometry):**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d @large_polygon.json
```

---

## Endpoint 2: GET /health

**Purpose:** Health check for service availability

**URL:** `{BASE_URL}/health`

**Method:** GET

**No Request Body**

**Response (HTTP 200):**

```json
{
  "status": "operational",
  "service": "Land Scanner Prototype",
  "version": "1.0.0",
  "timestamp": "2024-08-02T10:30:00.000Z"
}
```

**Status Values:**
- `operational` - Service healthy
- `degraded` - Service running but some providers unavailable
- `offline` - Service not available

---

### Testing

```bash
# Development
curl http://localhost:8000/health | jq

# Production
curl https://land-scanner-prototype-backend.onrender.com/health | jq
```

---

## Endpoint 3: GET /status

**Purpose:** Get service status and configuration

**URL:** `{BASE_URL}/status`

**Method:** GET

**No Request Body**

**Response (HTTP 200):**

```json
{
  "prototype_name": "Land Scanner Prototype",
  "version": "1.0.0",
  "timestamp": "2024-08-02T10:30:00.000Z",
  "enabled_providers": [
    "OpenStreetMap",
    "USGS",
    "GEBCO"
  ],
  "provider_count": 3,
  "debug_mode": false,
  "max_polygon_area_sqkm": 10000,
  "min_polygon_area_sqkm": 0.01,
  "processing_timeout_ms": 60000
}
```

---

### Testing

```bash
curl http://localhost:8000/status | jq
```

---

## Frontend Testing Examples

### Using JavaScript Fetch

```javascript
// Test /analyze
async function testAnalyze() {
  const polygon = {
    type: 'Polygon',
    coordinates: [[[77.5, 12.5], [78.5, 12.5], [78.5, 13.5], [77.5, 13.5], [77.5, 12.5]]]
  }
  
  const response = await fetch('http://localhost:8000/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ polygon })
  })
  
  const data = await response.json()
  console.log('Status:', data.status)
  console.log('Processing Time:', data.processing_time_ms, 'ms')
  console.log('Request ID:', data.request_id)
}

// Test /health
async function testHealth() {
  const response = await fetch('http://localhost:8000/health')
  const data = await response.json()
  console.log('Health:', data.status)
}

// Test /status
async function testStatus() {
  const response = await fetch('http://localhost:8000/status')
  const data = await response.json()
  console.log('Providers:', data.enabled_providers)
}
```

### Using Frontend API Service

```javascript
import { analyzePolygon, checkHealth, getStatus } from './src/services/api.js'

// Test analysis
const results = await analyzePolygon({
  type: 'Polygon',
  coordinates: [[[77.5, 12.5], [78.5, 12.5], [78.5, 13.5], [77.5, 13.5], [77.5, 12.5]]]
})
console.log('Results:', results)

// Test health
const health = await checkHealth()
console.log('Health:', health)

// Test status
const status = await getStatus()
console.log('Status:', status)
```

---

## Response Time Expectations

**By Polygon Size:**

| Polygon Size | Typical Response Time | Max Response Time |
|--------------|----------------------|-------------------|
| Small (< 1 sq km) | 1-2 seconds | 10 seconds |
| Medium (1-100 sq km) | 2-5 seconds | 30 seconds |
| Large (100-1000 sq km) | 5-15 seconds | 45 seconds |
| Very Large (> 1000 sq km) | 15-60 seconds | 60 seconds (timeout) |

**By Provider:**

| Provider | Typical Time | Success Rate |
|----------|--------------|--------------|
| OpenStreetMap | 300-800ms | 99% |
| USGS | 200-600ms | 95% |
| GEBCO | 100-400ms | 98% |

**Timeout:** 60 seconds (hardcoded)

---

## Common Error Scenarios & Solutions

### Scenario 1: Ring Not Closed
**Error:** `"coordinates must form a valid ring"`
**Cause:** First and last coordinates don't match
**Solution:** Add closing coordinate: `[...path..., [first_lon, first_lat]]`

### Scenario 2: Invalid Coordinate Format
**Error:** `"coordinate at index 2 must be [longitude, latitude]"`
**Cause:** Coordinates in wrong order (lat, lon instead of lon, lat)
**Solution:** Swap coordinates: `[latitude, longitude]` → `[longitude, latitude]`

### Scenario 3: Out of Bounds
**Error:** `"out of bounds at coordinate index 1"`
**Cause:** Latitude > 90 or longitude > 180
**Solution:** Verify coordinates are within valid ranges

### Scenario 4: Request Timeout
**Error:** `"Request timeout after 60000ms"`
**Cause:** Polygon too large or providers slow
**Solution:** Reduce polygon size or retry later

### Scenario 5: USGS Rate Limited
**Status:** "partial" with USGS provider error
**Cause:** Rate limit exceeded for USGS API
**Solution:** Retry after 1-2 hours; analysis still completes with other providers

---

## Integration Checklist

- [ ] Understand polygon coordinate format (lon, lat)
- [ ] Test with small polygon first
- [ ] Handle both success (200) and partial (200 + status: "partial")
- [ ] Log request_id from response for debugging
- [ ] Implement retry logic for timeouts (408)
- [ ] Handle provider failures gracefully
- [ ] Monitor processing_time_ms for UX feedback
- [ ] Validate polygon structure before sending
- [ ] Handle network errors appropriately

See: `API_CONNECTION_GUIDE.md` for complete integration guide.
