# Design Document: Land Scanner Prototype

## Overview

The Land Scanner Prototype is a geospatial data analysis platform that demonstrates the technical feasibility of combining multiple open data sources to generate meaningful land intelligence. The system follows a modular architecture where data flows through a series of discrete processing stages: polygon validation, multi-source data collection, format standardization, rule-based analysis, and structured output generation.

The design prioritizes simplicity, reliability, and modularity over production complexity. The architecture remains provider-independent, allowing easy replacement or addition of data sources without affecting core processing logic.

## Architecture

### High-Level System Architecture

```
User Input (Polygon/GeoJSON)
    ↓
Frontend (HTML/CSS/JS with Leaflet map)
    ↓
HTTP POST /analyze request
    ↓
FastAPI Backend
    ├─→ Polygon Validator
    ├─→ Data Source Manager
    │    ├─→ Collector A (Provider 1)
    │    ├─→ Collector B (Provider 2)
    │    ├─→ Collector C (Provider 3)
    │    └─→ [Additional Collectors]
    ├─→ Data Standardizer
    ├─→ Rule Engine
    │    ├─→ Administrative Rules
    │    ├─→ Land Cover Rules
    │    ├─→ Building Rules
    │    ├─→ Road Rules
    │    ├─→ Water Rules
    │    └─→ Elevation Rules
    └─→ Output Generator
    ↓
JSON Response
    ↓
Frontend Display
```

### Processing Flow

The system implements a synchronous, request-response workflow:

1. **User Input**: Frontend receives polygon (drawn or uploaded as GeoJSON)
2. **Validation**: Backend validates polygon structure and geometry
3. **Collection**: Multiple independent collectors query their respective data providers
4. **Standardization**: All collected data is converted to a common internal format
5. **Analysis**: Rule Engine processes standardized data to generate land information
6. **Output**: Results are formatted as JSON and returned to frontend
7. **Display**: Frontend renders results in an interactive map and information panel

### Deployment Model

- **Backend**: Python FastAPI application deployed on Render
- **Frontend**: Static HTML/CSS/JavaScript served from the same Render instance
- **Communication**: RESTful API over HTTP/HTTPS
- **Data Sources**: External open geospatial providers (OpenStreetMap, OSM Buildings, administrative boundaries, elevation data, land cover data)

## Components and Interfaces

### 1. Frontend Module

**Responsibilities**:
- Display interactive map using Leaflet
- Accept polygon input (drawing or GeoJSON upload)
- Send analysis requests to backend
- Display results, errors, and processing status
- Provide user-friendly interface for demonstration

**Key Components**:
- Map display with Leaflet
- Polygon drawing tools
- File upload interface
- Analysis trigger button
- Results panel
- Error display

**Interfaces**:
- Communicates only with Backend API via HTTP
- Receives JSON responses from `/analyze`, `/health`, `/status` endpoints
- Never directly accesses external data providers

### 2. Backend API (FastAPI)

**Responsibilities**:
- Receive HTTP requests
- Coordinate all backend processing
- Return JSON responses
- Handle request validation
- Manage error responses

**Endpoints**:
- `POST /analyze` - Accept polygon and return analysis results
- `GET /health` - Return service health status
- `GET /status` - Return prototype information and configuration

**Request/Response**:
```
POST /analyze
Request: { "polygon": GeoJSON }
Response: { 
  "status": "success",
  "analysis": { land_information },
  "processing_status": { module_statuses },
  "provider_status": { provider_availability }
}
```

### 3. Polygon Validator

**Responsibilities**:
- Validate GeoJSON structure
- Validate polygon geometry
- Verify coordinate format and ranges
- Calculate polygon metadata (area, bounding box, CRS)
- Reject invalid polygons with descriptive errors

**Interface**:
```
Input: Raw GeoJSON object
Output: 
  - Valid: Polygon object with validated geometry and metadata
  - Invalid: ValidationError with descriptive message
```

**Validation Rules**:
- Must be valid GeoJSON
- Must be a Polygon or MultiPolygon geometry
- Coordinates must be valid [longitude, latitude] pairs
- Coordinates must be within valid ranges (-180 to 180 for lon, -90 to 90 for lat)
- Polygon must have at least 3 coordinate pairs (forming valid ring)

### 4. Data Source Manager

**Responsibilities**:
- Identify enabled data collectors from configuration
- Execute collectors in parallel or sequence
- Aggregate collector responses
- Handle collector failures gracefully
- Continue processing if optional providers fail
- Record execution status for each collector

**Interface**:
```
Input: Validated Polygon
Output: 
  - RawDataCollection: {
      "provider_name": raw_dataset,
      "provider_status": {
        "success": bool,
        "error": str (if failed)
      }
    }
```

**Configuration-Driven Behavior**:
- Reads enabled providers from configuration
- Applies timeout values from configuration
- Supports retry logic from configuration
- Can enable/disable providers via configuration

### 5. Data Collectors

**Design Principle**: One collector per data provider. Collectors remain independent and never communicate with each other.

**Responsibilities** (per collector):
- Build provider-specific API requests
- Handle provider authentication (if required)
- Download or query geospatial datasets
- Validate basic response structure
- Return raw dataset with source attribution
- Handle provider-specific errors

**Generic Collector Interface**:
```
class DataCollector:
    def collect(self, polygon: Polygon) -> RawDataset:
        # 1. Build request for specific provider
        # 2. Query provider
        # 3. Validate response structure
        # 4. Return dataset with metadata
```

**Example Collectors** (to be implemented):
- OpenStreetMap Buildings Collector
- Administrative Boundaries Collector
- Land Cover Collector
- Road Network Collector
- Water Bodies Collector
- Elevation Data Collector

**Collector Return Format**:
```
RawDataset: {
  "source_provider": "provider_name",
  "category": "buildings|land_cover|roads|water|elevation|admin",
  "geometry_type": "Point|LineString|Polygon",
  "features": [ raw provider features ],
  "metadata": {
    "timestamp": datetime,
    "version": str,
    "crs": str
  }
}
```

### 6. Data Standardizer

**Responsibilities**:
- Convert each provider's raw data format to common internal model
- Normalize field names across providers
- Normalize coordinate reference systems (CRS) to standard (typically WGS84)
- Normalize data structure to common schema
- Preserve data integrity during transformation
- Validate standardized output

**Interface**:
```
Input: RawDataset (from any provider)
Output: StandardizedDataset with:
  - Common field names (provider-agnostic)
  - Standard geometry (in WGS84)
  - Standard feature structure
  - Preserved metadata with source attribution
```

**Standardization Rules**:
- All coordinates converted to WGS84 (EPSG:4326)
- Field names normalized to lowercase with underscores
- All geometry types preserved (Point, LineString, Polygon)
- Null/missing values represented consistently
- Data integrity validated before output

**Standardized Dataset Schema**:
```
StandardizedDataset: {
  "category": "buildings|land_cover|roads|water|elevation|admin",
  "source_provider": "original_provider_name",
  "features": [
    {
      "id": "feature_id",
      "geometry": { "type": "...", "coordinates": [...] },
      "properties": {
        "name": str (if available),
        "type": str,
        "confidence": float (if available),
        ... (category-specific properties)
      }
    }
  ],
  "metadata": {
    "timestamp": datetime,
    "crs": "EPSG:4326",
    "record_count": int
  }
}
```

### 7. Rule Engine

**Responsibilities**:
- Orchestrate execution of all enabled rules
- Process only standardized data
- Generate structured analysis results
- Handle rule failures gracefully
- Continue processing if individual rules fail
- Compile final analysis output

**Architecture**:
- Rule Engine acts as orchestrator
- Individual rule modules implement specific analysis categories
- Rules execute independently (no inter-rule dependencies)
- Each rule receives standardized datasets and returns structured results

**Rule Categories**:

#### Administrative Rules (ADM)
- **Purpose**: Identify administrative regions intersecting polygon
- **Input**: Administrative boundary dataset (standardized)
- **Output**: Country, State, District, Administrative status

#### Land Cover Rules (LC)
- **Purpose**: Summarize dominant land cover types
- **Input**: Land cover dataset (standardized)
- **Output**: Primary land cover type, coverage percentages

#### Building Rules (BLD)
- **Purpose**: Detect infrastructure (buildings) presence
- **Input**: Building footprint dataset (standardized)
- **Output**: Buildings detected (yes/no), building count, coverage estimate

#### Road Rules (RD)
- **Purpose**: Identify transportation network access
- **Input**: Road network dataset (standardized)
- **Output**: Road access available (yes/no), road types, accessibility estimate

#### Water Rules (WT)
- **Purpose**: Identify hydrological features
- **Input**: Water bodies dataset (standardized)
- **Output**: Water features detected (rivers/lakes/canals), coverage estimate

#### Elevation Rules (ELV)
- **Purpose**: Characterize terrain elevation
- **Input**: Elevation/DEM dataset (standardized)
- **Output**: Min elevation, Max elevation, Mean elevation, Slope category

**Rule Execution Interface**:
```
class Rule:
    def execute(self, standardized_data: StandardizedDataset) -> RuleResult:
        # 1. Validate required inputs are available
        # 2. Execute analysis logic
        # 3. Return structured result
        # Return RuleResult with status (success/failed/insufficient_data/skipped)
```

**Rule Result Format**:
```
RuleResult: {
  "rule_id": "ADM-001",
  "rule_name": "Administrative Boundary Detection",
  "status": "success|failed|insufficient_data|skipped",
  "result": {
    "administrative_region": {...},
    "country": str,
    "state": str,
    "district": str
  },
  "metadata": {
    "execution_time": float,
    "data_points_used": int
  }
}
```

**Rule Execution Guarantees**:
- Rules execute only on standardized data
- Rule failures do not cascade to other rules
- Missing data results in "insufficient_data" status, not failure
- All rule results are collected regardless of individual failures
- Rules remain independent of each other and data providers

### 8. Output Generator

**Responsibilities**:
- Compile rule results into structured analysis
- Build JSON response for API
- Include processing status information
- Include error summaries if applicable
- Format data suitable for frontend consumption
- Never expose raw provider-specific data

**Interface**:
```
Input: 
  - Rule results (from Rule Engine)
  - Processing status (from each module)
  - Original polygon
  
Output: AnalysisResponse (JSON)
```

**Response Structure**:
```
AnalysisResponse: {
  "request_id": "unique_id",
  "status": "success|partial|error",
  "timestamp": datetime,
  "processing_time_ms": int,
  
  "analysis_summary": {
    "polygon_area_sqkm": float,
    "analysis_date": datetime,
    "primary_land_cover": str,
    "key_findings": [str]
  },
  
  "land_information": {
    "administrative": {rule_result},
    "land_cover": {rule_result},
    "buildings": {rule_result},
    "roads": {rule_result},
    "water": {rule_result},
    "elevation": {rule_result}
  },
  
  "processing_status": {
    "validation": "success|failed",
    "data_collection": "success|partial|failed",
    "standardization": "success|failed",
    "rule_engine": "success|partial",
    "output_generation": "success|failed"
  },
  
  "provider_status": {
    "provider_name": {
      "status": "available|unavailable|error",
      "error_message": str (if applicable),
      "data_retrieved": bool
    }
  },
  
  "errors": [
    {
      "module": str,
      "message": str,
      "severity": "warning|error"
    }
  ]
}
```

### 9. Configuration Manager

**Responsibilities**:
- Load application configuration from external files
- Provide configuration to all modules
- Support enabling/disabling providers
- Manage timeout values, retry counts
- Support environment-specific configurations

**Configuration Structure**:
```yaml
# config/settings.json
{
  "app": {
    "name": "Land Scanner",
    "version": "1.0.0",
    "debug": false
  },
  "providers": [
    {
      "name": "osm_buildings",
      "enabled": true,
      "category": "buildings",
      "timeout_seconds": 30,
      "retry_count": 2,
      "collector_class": "OSMBuildingsCollector"
    },
    {
      "name": "admin_boundaries",
      "enabled": true,
      "category": "admin",
      "timeout_seconds": 30,
      "retry_count": 2,
      "collector_class": "AdminBoundariesCollector"
    }
    // ... additional providers
  ]
}
```

## Data Models

### Core Data Model: Polygon

```python
class Polygon:
    geojson: dict              # Valid GeoJSON structure
    geometry: shapely.Polygon  # Validated geometry
    area_sqkm: float          # Calculated area
    bounding_box: tuple       # (minx, miny, maxx, maxy)
    centroid: tuple           # (lon, lat)
    crs: str                  # Coordinate Reference System
    is_valid: bool
```

### Standardized Dataset Model

```python
class StandardizedDataset:
    category: str             # buildings|land_cover|roads|water|elevation|admin
    source_provider: str      # Original provider name
    features: List[Feature]
    metadata: DatasetMetadata
    
class Feature:
    id: str
    geometry: dict           # GeoJSON geometry
    properties: dict         # Standardized properties
    
class DatasetMetadata:
    timestamp: datetime
    crs: str                 # Always "EPSG:4326" after standardization
    record_count: int
    source_version: str (optional)
```

### Rule Result Model

```python
class RuleResult:
    rule_id: str
    rule_name: str
    status: str              # success|failed|insufficient_data|skipped
    result: dict             # Rule-specific output structure
    metadata: ResultMetadata
    
class ResultMetadata:
    execution_time_ms: float
    data_points_used: int
    errors: List[str] (optional)
```

### Analysis Response Model

```python
class AnalysisResponse:
    request_id: str
    status: str              # success|partial|error
    timestamp: datetime
    processing_time_ms: int
    analysis_summary: dict
    land_information: dict   # All rule results
    processing_status: dict  # Module statuses
    provider_status: dict    # Provider availability
    errors: List[ErrorInfo]  # If any
```

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Polygon Validation Consistency
**For any** valid GeoJSON polygon input, the system should accept it and proceed to data collection. Invalid polygons should be rejected with descriptive error messages.
**Validates: Requirements 1.3, 1.4, 1.5, 1.6**

### Property 2: Data Collection Completeness
**For any** validated polygon with N enabled data collectors, the system should query all N collectors, regardless of individual collector success or failure status.
**Validates: Requirements 2.1, 2.2, 2.7**

### Property 3: Provider Independence in Collection
**For any** two different polygons analyzed with different provider availability states, the system should produce results for available providers and skip unavailable ones without crashing or degrading other providers.
**Validates: Requirements 2.5, 2.6**

### Property 4: Data Standardization Normalization
**For any** raw dataset from any provider, after standardization, all coordinate systems should be normalized to WGS84 (EPSG:4326), and all field names should use consistent lowercase underscore convention regardless of the original provider format.
**Validates: Requirements 4.2, 4.3, 4.4**

### Property 5: Standardized Data Model Consistency
**For any** standardized dataset regardless of source provider, the output should conform to the StandardizedDataset schema with category, source_provider, features array, and metadata fields always present and correctly formatted.
**Validates: Requirements 4.1, 4.5, 4.6**

### Property 6: Rule Engine Input Isolation
**For any** Rule Engine execution, the input should contain only standardized data—never raw provider-specific formats. Raw data should be encapsulated within the Data Standardizer.
**Validates: Requirements 5.1, 5.2**

### Property 7: Rule Independence and Continuation
**For any** set of rules where one rule fails or encounters insufficient data, the remaining rules should continue executing independently and produce their results without cascading failure.
**Validates: Requirements 5.9, 5.10**

### Property 8: Rule Result Compilation
**For any** Rule Engine execution, regardless of individual rule outcomes, the system should compile all rule results (success, failure, insufficient_data, skipped) into a single structured analysis output.
**Validates: Requirements 5.11**

### Property 9: Output Format Consistency
**For any** analysis request that completes (successfully or with errors), the system should return valid JSON with required fields: request_id, status, analysis_summary, land_information, processing_status, provider_status.
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8**

### Property 10: Data Encapsulation in Output
**For any** analysis response returned to the frontend, the response should contain only standardized, processed data—never raw provider-specific formats or internal implementation details.
**Validates: Requirements 6.7**

### Property 11: HTTP Status Code Consistency
**For any** valid analysis request with valid polygon input, the system should return HTTP 200 with JSON results. Invalid polygon inputs should return HTTP 400 or 422 with error details. Unexpected errors should return HTTP 500 with safe error messages.
**Validates: Requirements 9.4, 9.5, 9.6, 9.7**

### Property 12: Error Message Safety
**For any** error condition (validation error, provider failure, unexpected exception), error messages returned to the user should be readable and descriptive, but should never expose stack traces, internal implementation details, or sensitive information.
**Validates: Requirements 8.2, 8.5, 8.6**

### Property 13: Configuration-Driven Collector Execution
**For any** configuration change that enables or disables data collectors, the system should respect the configuration state and only execute enabled collectors without requiring code changes.
**Validates: Requirements 10.3, 10.7**

### Property 14: Graceful Degradation with Optional Providers
**For any** analysis where optional data providers are unavailable, the system should continue processing and return partial results with available data rather than failing entirely.
**Validates: Requirements 11.2, 12.8**

### Property 15: Module Failure Isolation
**For any** module failure (validation, collection, standardization, rules), the system should log the failure and continue processing with remaining modules when possible, eventually returning a response with failure status information.
**Validates: Requirements 8.3, 8.4, 8.7, 8.8**

## Error Handling

### Error Categories and Handling Strategies

#### 1. Validation Errors
**Trigger**: Invalid polygon input (malformed GeoJSON, invalid geometry)
**Response**: HTTP 400/422 with descriptive validation error message
**Continuation**: Halt processing and return error immediately

#### 2. Collection Errors
**Trigger**: Provider unavailable, network timeout, API error
**Response**: Log error, mark provider as unavailable, continue with other providers
**Continuation**: Continue if optional provider; skip if critical
**Output**: Partial analysis with provider status

#### 3. Standardization Errors
**Trigger**: Unexpected data format from provider, missing required fields
**Response**: Log error, attempt to standardize available fields
**Continuation**: Continue processing with best-effort standardization

#### 4. Rule Execution Errors
**Trigger**: Missing required data, calculation error, invalid data state
**Response**: Mark rule as "insufficient_data" or "failed", log error
**Continuation**: Execute remaining rules independently

#### 5. Unexpected System Errors
**Trigger**: Any unhandled exception
**Response**: HTTP 500 with generic safe error message (no stack trace)
**Continuation**: Log full error details, return failure status

### Error Response Format

```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR | PROVIDER_ERROR | PROCESSING_ERROR | SYSTEM_ERROR",
  "error_message": "Readable user-facing message",
  "details": {
    "failed_module": "module_name",
    "stage": "validation | collection | standardization | processing",
    "timestamp": "ISO8601 timestamp"
  }
}
```

## Testing Strategy

### Dual Testing Approach

The system requires both unit tests and property-based tests working together:

**Unit Tests** verify:
- Specific examples and edge cases
- Integration points between modules
- Error conditions and error messages
- Specific GeoJSON validation rules
- API endpoint responses

**Property-Based Tests** verify:
- Universal properties hold across many inputs
- Behavioral guarantees across data variations
- Graceful degradation with missing/invalid data
- Format consistency across processing pipeline
- Module independence and data flow

### Unit Test Strategy

**Test Organization**:
- Co-locate tests with source files using `.test.py` suffix
- Organize by module (validator_test.py, collector_test.py, etc.)
- Use pytest framework

**Test Coverage Areas**:
- **Polygon Validator**: Valid/invalid GeoJSON, geometry validation, coordinate ranges
- **Data Collectors**: Provider communication, timeout handling, error responses
- **Data Standardizer**: Format normalization, field name mapping, CRS conversion
- **Rule Engine**: Rule execution, result compilation, error handling
- **API Endpoints**: Request validation, response format, HTTP status codes

### Property-Based Test Strategy

**Testing Framework**: Use `hypothesis` library for Python

**Property Test Configuration**:
- Minimum 100 iterations per property test
- Generate random but valid inputs matching domain constraints
- Each property test references its design document property

**Test Annotation Format**:
```python
# Feature: land-scanner, Property 1: Polygon Validation Consistency
@given(valid_geojson_polygon())
def test_polygon_validation_consistency(polygon):
    """
    For any valid GeoJSON polygon input, the system should accept it 
    and proceed to data collection.
    """
    # Test implementation
```

**Property Test Categories**:

1. **Validation Properties**: Verify validation logic holds for all inputs
2. **Data Flow Properties**: Verify data moves correctly through pipeline
3. **Standardization Properties**: Verify output consistency regardless of input
4. **Error Handling Properties**: Verify graceful handling of various failures
5. **API Properties**: Verify endpoint behavior across request types

### Minimal Testing Approach

- Test core functionality and important edge cases only
- Avoid over-testing obvious behavior
- Focus on properties that ensure system reliability
- Use parametrized tests to cover multiple scenarios efficiently

## Future Extensibility

The architecture supports future expansion without redesign:

### Adding New Data Providers
1. Create new Collector class implementing DataCollector interface
2. Add provider configuration to config/providers.json
3. Update Data Standardizer with provider-specific mapping if needed
4. No changes required to Rule Engine, frontend, or core architecture

### Adding New Rules
1. Create new Rule class implementing Rule interface
2. Register rule in Rule Engine
3. Rule processes existing standardized data
4. Output automatically included in analysis results

### Adding Authentication/Authorization
1. Add authentication layer between frontend and API
2. All modules remain unaffected
3. Configuration-driven authentication

### Adding Database Persistence
1. Add database layer for storing analysis results
2. Modify output generator to persist results
3. Add API endpoints for result retrieval
4. Core processing logic remains unchanged

### Adding AI/ML Capabilities
1. Create AI Rule subclass
2. AI rules process standardized data like other rules
3. Results integrate with existing rule output
4. Frontend displays AI results alongside traditional rules

## Summary

The Land Scanner Prototype follows a modular, provider-independent architecture that transforms open geospatial data into meaningful land information through deterministic rule-based processing. The design emphasizes simplicity, reliability, and future extensibility while maintaining strict data encapsulation and module independence. Error handling prioritizes graceful degradation, allowing partial results when optional components fail. The dual testing approach—combining unit tests for specific behavior and property-based tests for universal guarantees—ensures both correctness and resilience across diverse inputs and scenarios.
