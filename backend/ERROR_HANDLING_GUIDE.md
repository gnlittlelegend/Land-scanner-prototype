# Error Handling Guide

## Overview

This document describes the comprehensive error handling system implemented in the Land Scanner backend (Tasks 9.1 & 9.2).

## Error Handling Middleware

### Location
- **File**: `backend/main.py`
- **Function**: `error_handling_middleware`

### How It Works

The middleware intercepts all HTTP requests and handles errors at the middleware level:

```
Request → Middleware → Endpoint → Response
           (Error handling)
```

### Error Categories

#### 1. Validation Errors (HTTP 400/422)

**When**: Polygon input is invalid
**Response Status**: HTTP 400 or 422
**Example**:
```json
{
    "status": "error",
    "error_code": "POLYGON_VALIDATION_ERROR",
    "error_message": "Polygon area is too small. Please draw a larger area.",
    "timestamp": "2026-08-05T12:00:00",
    "request_id": "uuid-here",
    "processing_time_ms": 45
}
```

#### 2. Provider Errors (HTTP 500)

**When**: Data provider API fails
**Response Status**: HTTP 500
**Example**:
```json
{
    "status": "error",
    "error_code": "SYSTEM_ERROR",
    "error_message": "The OSM data service is temporarily slow. Please try again in a moment.",
    "timestamp": "2026-08-05T12:00:00",
    "request_id": "uuid-here",
    "processing_time_ms": 32000
}
```

#### 3. System Errors (HTTP 500)

**When**: Unexpected exception in code
**Response Status**: HTTP 500
**Example**:
```json
{
    "status": "error",
    "error_code": "SYSTEM_ERROR",
    "error_message": "An unexpected error occurred. Please try again.",
    "timestamp": "2026-08-05T12:00:00",
    "request_id": "uuid-here",
    "processing_time_ms": 150
}
```

## Error Message Sanitization

### Location
- **File**: `backend/exceptions/error_handler.py`
- **Class**: `ErrorMessageSanitizer`

### Sanitization Features

#### 1. Path Removal
```python
# Input
"Error in /backend/validators/polygon_validator.py:42"

# Output (after sanitization)
"Polygon validation failed"
```

#### 2. Exception Type Masking
```python
# Input
"TypeError: expected int, got str"

# Output
"Expected different data type"
```

#### 3. Credential Masking
```python
# Input
"Database connection failed: postgresql://user:password123@localhost/db"

# Output
"Database connection failed: postgresql://user:[hidden]@localhost/db"
```

#### 4. Memory Address Removal
```python
# Input
"<PolygonValidator object at 0x7f8b8c0d5f10> failed"

# Output
"Validation failed"
```

### Usage Examples

#### Sanitize Validation Error
```python
from backend.exceptions.error_handler import ErrorMessageSanitizer

message = "ValidationError: Missing 'type' field in /backend/validators/polygon_validator.py:42"
clean = ErrorMessageSanitizer.sanitize_validation_error(message)
# Result: "Polygon format is invalid. Please provide valid GeoJSON."
```

#### Sanitize Provider Error
```python
message = "HTTP 429: Too many requests - Rate limited by Overpass API"
clean = ErrorMessageSanitizer.sanitize_provider_error("Overpass", message)
# Result: "The Overpass data service is temporarily busy. Please try again later."
```

#### Sanitize System Error
```python
message = "KeyError: 'coordinates' in backend/standardizers/land_cover_standardizer.py:89"
clean = ErrorMessageSanitizer.sanitize_system_error(message)
# Result: "An unexpected error occurred. Please try again."
```

#### Check for Sensitive Data
```python
dangerous = "Failed to connect: api_key='abc123xyz'"
if ErrorMessageSanitizer.contains_sensitive_data(dangerous):
    print("ALERT: Sensitive data detected!")
```

## Internal Logging

All errors are logged internally with full details:

```python
logger.error(
    "[request-id] ✗ Validation error",
    exc_info=True,
    extra={
        "exception_type": "ValidationError",
        "stack_trace": "full traceback here",
        "module": "polygon_validator"
    }
)
```

### Server Logs Show
- ✅ Full stack traces
- ✅ File paths
- ✅ Line numbers
- ✅ Variable states
- ✅ Exception details

### API Responses Show
- ❌ No stack traces
- ❌ No file paths
- ❌ No implementation details
- ❌ No exception types
- ❌ No internal module names

## Best Practices

### 1. Always Use HTTPException for Expected Errors

```python
# Good
from fastapi import HTTPException

if not polygon:
    raise HTTPException(
        status_code=422,
        detail={
            "status": "error",
            "error_code": "VALIDATION_ERROR",
            "error_message": "Polygon is required"
        }
    )

# Middleware catches and formats it properly
```

### 2. Let Middleware Handle Unexpected Exceptions

```python
# Don't do this:
try:
    process_data()
except Exception as e:
    return {"error": str(e)}  # EXPOSES INTERNALS!

# Instead, just let it raise:
def analyze():
    process_data()  # Exception bubbles up to middleware
    # Middleware catches it and sanitizes the message
```

### 3. Log Sensitive Context Internally

```python
# Good
logger.error(
    f"[{request_id}] Analysis failed",
    exc_info=True,  # Logs full stack trace internally
    extra={"polygon_id": polygon_id}
)

# Bad
raise HTTPException(
    status_code=500,
    detail=str(e)  # EXPOSES STACK TRACE!
)
```

## Testing Error Handling

Run the comprehensive test suite:

```bash
python -m pytest backend/tests/test_error_handling.py -v
```

### Test Coverage
- ✅ All error types (validation, provider, system)
- ✅ All HTTP status codes (400, 422, 500)
- ✅ Response format consistency
- ✅ No leaked implementation details
- ✅ All sanitization patterns
- ✅ Provider-specific error mapping

## Common Error Scenarios

### Polygon Too Small
**Internal Message**: `"Area 5m² is below minimum 10m²"`
**User Message**: `"Polygon area is too small. Please draw a larger area."`

### Polygon Too Large
**Internal Message**: `"Area 150km² exceeds maximum 100km²"`
**User Message**: `"Polygon area is too large. Please select a smaller area."`

### Provider Timeout
**Internal Message**: `"Timeout: Connection timeout after 30 seconds at http://overpass..."`
**User Message**: `"The OSM data service is temporarily slow. Please try again in a moment."`

### Provider Rate Limit
**Internal Message**: `"HTTP 429: Rate limit exceeded by Overpass API"`
**User Message**: `"The Overpass data service is temporarily busy. Please try again later."`

### Provider Unavailable
**Internal Message**: `"HTTP 503: Service Unavailable (Copernicus STAC API)"`
**User Message**: `"The Copernicus data service is temporarily unavailable."`

### System Error
**Internal Message**: `"KeyError: 'properties' in backend/standardizers/...py:42"`
**User Message**: `"An unexpected error occurred. Please try again."`

## Debugging

### To See Full Error Details

Check server logs:
```bash
# With Docker
docker logs land-scanner-backend

# Locally
# Logs printed to stdout with format:
# TIMESTAMP - MODULE - LEVEL - MESSAGE
```

### Request Tracing

Each request has a unique UUID logged at start:
```
[a1b2c3d4-e5f6-7890-abcd-ef1234567890] POST /analyze
```

Search server logs for this UUID to find all log entries for that request.

## Security Considerations

### What's Protected
- ✅ File paths (code structure)
- ✅ Line numbers (code location)
- ✅ Module names (internal organization)
- ✅ Exception types (vulnerability indicators)
- ✅ Memory addresses (system details)
- ✅ Credentials (passwords, API keys)
- ✅ Database URLs (connection strings)
- ✅ Stack traces (code flow)

### What's Exposed
- ✅ Error type (validation, provider, system)
- ✅ General category (polygon, data, unexpected)
- ✅ User guidance (what to do next)
- ✅ Request ID (for tracking)
- ✅ Timestamp (when it happened)

## Future Enhancements

Potential improvements:
- [ ] Error analytics dashboard
- [ ] Error rate monitoring
- [ ] Automatic retry logic
- [ ] Error recovery suggestions
- [ ] Internationalization (multi-language error messages)
- [ ] Error rate limiting (prevent error spam)
