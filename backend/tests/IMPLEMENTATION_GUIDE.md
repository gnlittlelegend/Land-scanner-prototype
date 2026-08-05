# Land Scanner Test Infrastructure Implementation Guide

## Architecture Overview

The Land Scanner test infrastructure provides three key capabilities:

1. **Centralized Test Data Management** - Shared polygon fixtures and cached provider responses
2. **Test Data Protocol** - Declarative dependencies for efficient data loading
3. **Audit Logging** - Comprehensive tracking of test data usage and cache performance

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ conftest.py (Pytest Configuration)                          │
│ - Session-level fixtures                                    │
│ - Polygon fixtures                                          │
│ - Test hooks and markers                                    │
└─────────────────────────────────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│TestDataMgr   │  │ResponseCache │  │TestValidator │
│- Polygons    │  │- Get/cache   │  │- Validate    │
│- Fixtures    │  │- TTL mgmt    │  │- Compare     │
│- Audit       │  │- Age check   │  │- Assert      │
└──────────────┘  └──────────────┘  └──────────────┘
         │              │              │
         └──────────────┼──────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│TestDataProto │  │TestAuditLog  │  │PolygonGen    │
│- Decorators  │  │- Track usage │  │- Generate    │
│- Registry    │  │- Export rpt  │  │- Determinism │
│- Dependencies│  │- Efficiency  │  │- Variations  │
└──────────────┘  └──────────────┘  └──────────────┘
         │              │              │
         └──────────────┼──────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │ Pytest Test Execution   │
            │ With audit logging      │
            └─────────────────────────┘
```

## Core Components

### 1. TestDataManager (`test_data_manager.py`)

**Responsibilities**:
- Load and manage polygon fixtures
- Cache provider responses
- Track test data usage
- Generate audit reports

**Key Methods**:
- `get_polygon(polygon_id)` - Get a specific polygon fixture
- `get_all_polygons()` - Get all polygons
- `get_cached_response(provider, polygon_id)` - Get cached response
- `cache_response(provider, polygon_id, response)` - Cache a response
- `get_cache_age(provider, polygon_id)` - Check cache age
- `get_audit_report()` - Get comprehensive audit data
- `export_audit_report(filepath)` - Export audit to file

**Usage Example**:
```python
@pytest.fixture
def test_data_manager():
    manager = TestDataManager("backend/tests/fixtures")
    yield manager
    report = manager.get_audit_report()
    print(f"Cache hit rate: {report['cache_hit_rate_percent']:.1f}%")
```

### 2. TestPolygonGenerator (`test_data_manager.py`)

**Responsibilities**:
- Generate test polygons deterministically
- Support reproducible property-based testing
- Generate variations by size, location, vertex count

**Key Methods**:
- `generate_by_size(area_sqkm, seed)` - Generate by area
- `generate_by_location(lat, lon, area, seed)` - Generate at location
- `generate_by_vertex_count(num_vertices, area, seed)` - Generate by vertices

**Determinism Property**:
```python
# Same seed always produces same polygon
poly1 = gen.generate_by_size(5.0, seed=42)
poly2 = gen.generate_by_size(5.0, seed=42)
assert poly1["geojson"] == poly2["geojson"]
```

### 3. ResponseCache (`test_data_manager.py`)

**Responsibilities**:
- Cache provider API responses
- Manage cache expiration (30-day TTL)
- Avoid duplicate API calls

**Key Methods**:
- `get_cached_response(provider, polygon_id)` - Get or None
- `cache_response(provider, polygon_id, response)` - Save to cache
- `get_cache_age(provider, polygon_id)` - Get age in days
- `refresh_cache(provider, polygon_id)` - Clear cache entry

**Cache Structure**:
```
backend/tests/fixtures/provider_responses/
├── osm_buildings/
│   ├── urban_dense.json
│   └── valid_small.json
├── usgs_elevation/
│   └── mountain_region.json
└── ...
```

### 4. TestDataValidator (`test_data_manager.py`)

**Responsibilities**:
- Validate provider response structure
- Compare datasets for consistency
- Detect duplicate test data

**Key Methods**:
- `validate_provider_response(response, provider)` - Returns (is_valid, errors)
- `compare_datasets(data1, data2)` - Returns (consistency, description)
- `assert_no_duplicate_data(test_data_sets)` - Returns bool

**Usage Example**:
```python
is_valid, errors = validator.validate_provider_response(response, "osm_buildings")
if not is_valid:
    for error in errors:
        logger.error(error)

consistency, description = validator.compare_datasets(data1, data2)
assert consistency == DataConsistency.IDENTICAL
```

### 5. Test Data Protocol (`test_data_protocol.py`)

**Responsibilities**:
- Track data dependencies declaratively
- Optimize data loading
- Generate data load plans

**Key Classes**:
- `TestDataDependency` - Single test's dependencies
- `TestDataDependencyRegistry` - Central registry
- `DataDependencyTracker` - Track actual usage

**Decorators**:
```python
@needs_polygon("urban_dense")
@needs_provider_data("osm_buildings", "urban_dense")
def test_collection(test_data_manager, response_cache):
    pass
```

### 6. Test Audit Logger (`test_audit_logger.py`)

**Responsibilities**:
- Log all test data access
- Track cache performance
- Generate audit reports
- Export detailed metrics

**Key Methods**:
- `start_test(test_name, test_file)` - Record test start
- `end_test(test_name)` - Record test end
- `record_cache_hit/miss/api_call()` - Track access
- `get_session_report()` - Get summary
- `export_session_report()` - Save to file
- `print_summary()` - Print human-readable output

**Output Example**:
```
TEST DATA AUDIT SUMMARY
Tests run: 42
Cache hit rate: 94.3%
Real API calls made: 12
Cache efficiency: 15.8x
```

## Usage Patterns

### Pattern 1: Using Fixtures in Tests

```python
def test_polygon_validation(polygon_small, polygon_large):
    """Test with specific polygon fixtures."""
    validator = PolygonValidator()
    
    result_small = validator.validate(polygon_small["geojson"])
    result_large = validator.validate(polygon_large["geojson"])
    
    assert result_small.is_valid
    assert result_large.is_valid
```

### Pattern 2: Using Cached Provider Data

```python
def test_collection_with_cache(response_cache):
    """Test using cached provider data."""
    cached = response_cache.get_cached_response("osm_buildings", "urban_dense")
    
    if cached:
        # Use cached response
        features = cached["features"]
        assert len(features) > 0
    else:
        # Handle cache miss (real test would mock or skip)
        pass
```

### Pattern 3: Deterministic Test Data Generation

```python
@given(polygon_id=st.sampled_from(["urban_dense", "rural_sparse", "ocean_area"]))
def test_collection_all_locations(polygon_id, polygon_generator):
    """Property-based test with deterministic generation."""
    polygon = test_data_manager.get_polygon(polygon_id)
    
    # Test implementation
    assert polygon is not None
```

### Pattern 4: Data Consistency Checking

```python
def test_data_consistency(test_data_validator):
    """Test that repeated data access returns consistent results."""
    data1 = fetch_polygon_data("urban_dense")
    data2 = fetch_polygon_data("urban_dense")
    
    consistency, description = test_data_validator.compare_datasets(data1, data2)
    assert consistency == DataConsistency.IDENTICAL
```

### Pattern 5: Audit Reporting

```python
@pytest.fixture(autouse=True)
def audit_logging(request, audit_logger):
    """Automatically log all tests."""
    test_name = request.node.name
    audit_logger.start_test(test_name, request.node.fspath)
    
    yield
    
    audit_logger.end_test(test_name)

def test_something(audit_logger):
    """Test automatically logged."""
    audit_logger.record_polygon_usage("test_something", "urban_dense")
    # Test code
```

## File Organization

### Fixtures Directory

```
backend/tests/fixtures/
├── test_polygons.json          # 28 polygon fixtures
├── provider_responses/          # Cached API responses
│   ├── osm_buildings/
│   ├── osm_roads/
│   ├── usgs_elevation/
│   └── ...
├── CACHE_FORMAT.md             # Cache format documentation
└── .gitkeep
```

### Test Infrastructure Files

```
backend/tests/
├── conftest.py                 # Pytest configuration & fixtures
├── test_data_manager.py        # Core data management
├── test_data_protocol.py       # Data dependency protocol
├── test_audit_logger.py        # Audit logging
├── fixtures/                   # Test data
└── audit/                      # Generated audit reports
    ├── session_20240802_120000.json
    ├── audit_20240802_120000.json
    └── ...
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install pytest hypothesis shapely geopandas pyproj
```

### 2. Create Fixtures Directory

```bash
mkdir -p backend/tests/fixtures/provider_responses
```

### 3. Initialize Test Data

```python
from backend.tests.test_data_manager import TestDataManager

manager = TestDataManager("backend/tests/fixtures")
polygons = manager.get_all_polygons()
print(f"Loaded {len(polygons)} polygon fixtures")
```

### 4. Populate Provider Cache (One-Time)

```bash
# Run script to fetch real provider data and cache it
python backend/scripts/populate_test_cache.py
```

### 5. Run Tests

```bash
# With cache (fast)
pytest backend/tests/

# With audit reporting
pytest backend/tests/ --audit

# Specific test file
pytest backend/tests/test_polygon_validator.py -v

# With audit export
pytest backend/tests/ --export-audit
```

## Best Practices

### 1. Always Use Fixtures

✅ **Good**:
```python
def test_polygon_validation(polygon_small):
    assert polygon_small is not None
```

❌ **Bad**:
```python
def test_polygon_validation():
    polygon = json.load(open("fixtures/polygon.json"))
    # Creates duplicate loading
```

### 2. Share Data Across Tests

✅ **Good**:
```python
# conftest.py defines session fixture
@pytest.fixture(scope="session")
def test_data_manager():
    return TestDataManager()

# All tests use same instance
```

❌ **Bad**:
```python
# Each test creates new instance
def test_1():
    manager = TestDataManager()

def test_2():
    manager = TestDataManager()  # Duplicate initialization
```

### 3. Document Data Dependencies

✅ **Good**:
```python
@needs_polygon("urban_dense")
@needs_provider_data("osm_buildings", "urban_dense")
def test_collection():
    pass
```

❌ **Bad**:
```python
def test_collection():
    # Hard to see what data is needed
    polygon = test_data_manager.get_polygon("urban_dense")
```

### 4. Cache Provider Data

✅ **Good**:
```python
cached = response_cache.get_cached_response("osm_buildings", "urban_dense")
# Uses cache, avoids API call
```

❌ **Bad**:
```python
response = requests.get("http://overpass-api.de/api/interpreter?...")
# Makes real API call every test run
```

### 5. Validate Data Quality

✅ **Good**:
```python
is_valid, errors = validator.validate_provider_response(response, "osm_buildings")
assert is_valid, f"Response validation failed: {errors}"
```

❌ **Bad**:
```python
response = fetch_data()
# Assume data is valid, may have hidden issues
```

## Troubleshooting

### Issue: Low Cache Hit Rate

**Symptom**: Cache hit rate below 50%

**Solutions**:
1. Check cache directory exists: `backend/tests/fixtures/provider_responses/`
2. Verify cache TTL hasn't expired (default 30 days)
3. Run with `--refresh-test-data` flag to refresh cache
4. Check audit report for missing cache entries

### Issue: Test Isolation Problems

**Symptom**: Tests pass individually but fail when run together

**Solutions**:
1. Verify fixtures are session-scoped (not function-scoped)
2. Check for shared state pollution
3. Ensure deterministic seed values for generators
4. Review audit log for data conflicts

### Issue: Slow Test Execution

**Symptom**: Tests take > 5 minutes

**Solutions**:
1. Check cache hit rate (should be > 90%)
2. Verify no real API calls are being made (check audit report)
3. Clear cache and rebuild: `rm -rf backend/tests/fixtures/provider_responses/*`
4. Profile test execution with `pytest --durations=10`

### Issue: Fixture Loading Errors

**Symptom**: `Polygon fixture not found: xyz`

**Solutions**:
1. Verify fixture ID is correct in test_polygons.json
2. Check fixture name matches exactly (case-sensitive)
3. Validate JSON file: `python -m json.tool backend/tests/fixtures/test_polygons.json`
4. Check fixture hasn't been deleted or moved

## Monitoring and Maintenance

### Weekly Tasks
- Review cache hit rates in audit reports
- Check for expired cache entries
- Monitor for test failures

### Monthly Tasks
- Refresh provider data cache (`--refresh-test-data`)
- Review audit reports for efficiency trends
- Update documentation if needed

### Quarterly Tasks
- Archive old audit reports
- Update polygon fixtures with new locations
- Review and optimize test data access patterns

## Performance Targets

- **Cache hit rate**: > 95%
- **Test execution time**: < 2 minutes for full suite
- **Cache efficiency**: > 10x (fewer API calls than tests)
- **Audit report generation**: < 1 second

## References

- Test Data Manager: `backend/tests/test_data_manager.py`
- Pytest Configuration: `backend/tests/conftest.py`
- Data Protocol: `backend/tests/test_data_protocol.py`
- Audit Logger: `backend/tests/test_audit_logger.py`
- Cache Format: `backend/tests/fixtures/provider_responses/CACHE_FORMAT.md`
- Testing Guide: `backend/tests/TESTING_DATA.md`
