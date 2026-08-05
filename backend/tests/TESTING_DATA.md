# Test Data Management Guide for Land Scanner

## Overview

The Land Scanner prototype uses a centralized test data management system to ensure tests are efficient, consistent, and don't generate duplicate API calls. All tests share common polygon fixtures and cached provider responses.

## Key Principles

1. **No Duplicate API Calls**: Real API responses are cached and reused across tests
2. **Deterministic**: Same test inputs always produce same results
3. **Reproducible**: Tests use fixed seed values for property-based testing
4. **Efficient**: Test data is shared across the entire test session
5. **Auditable**: All data access is tracked and logged

## Test Fixtures

### Polygon Fixtures

All polygon fixtures are stored in `backend/tests/fixtures/test_polygons.json`. Each fixture includes:

- **id**: Unique identifier for the polygon
- **area_sqkm**: Polygon area in square kilometers
- **location**: Human-readable location description
- **source**: How the polygon was obtained
- **coordinates**: [longitude, latitude] for center or reference point
- **intended_use**: What the polygon is meant to test
- **geojson**: Complete GeoJSON geometry

### Fixture Categories

#### Size Boundary Testing
- `valid_small`: 0.025 km² (small valid area)
- `valid_medium`: 10 km² (typical medium area)
- `valid_large`: 50 km² (large valid area)
- `boundary_minimum`: 0.00001 km² (exactly minimum: 10 m²)
- `boundary_maximum`: 100 km² (exactly maximum)
- `invalid_small`: 0.000005 km² (below minimum)
- `invalid_large`: 105 km² (above maximum)

#### Geographic Features
- `urban_dense`: Manhattan, NYC (high building/road density)
- `urban_medium`: Chicago area (medium urban area)
- `rural_sparse`: Rural Montana (low building/road density)
- `ocean_area`: Atlantic Ocean (no buildings/roads)
- `admin_boundary`: Texas subset (administrative region)
- `mixed_terrain`: Chicago area (mixed urban/rural)
- `mountain_region`: Rocky Mountains (elevation testing)
- `water_region`: Great Lakes (water features testing)

#### Geographic Boundaries
- `equator_crossing`: Crosses the equator (0° latitude)
- `pole_region`: Near North Pole (85°N)
- `south_pole_region`: Near South Pole (85°S)
- `antimeridian_crossing`: Crosses 180°/-180° boundary

#### Quadrants (Full coordinate space coverage)
- `quadrant_northeast`: Positive latitude, positive longitude
- `quadrant_northwest`: Positive latitude, negative longitude
- `quadrant_southeast`: Negative latitude, positive longitude
- `quadrant_southwest`: Negative latitude, negative longitude

#### Coordinate Precision
- `precision_integer`: Integer coordinates (0 decimals)
- `precision_2decimal`: 2 decimal precision (0.01 degree resolution)
- `precision_6decimal`: 6 decimal precision (0.000001 degree resolution)

#### Vertex Limits
- `high_vertex_count`: 9,999 vertices (at limit)
- `over_vertex_limit`: 10,001 vertices (exceeds limit, should fail)

## Using Test Fixtures in Tests

### In pytest Tests

```python
def test_collection_with_small_polygon(polygon_small):
    """Test data collection with small polygon."""
    assert polygon_small is not None
    geojson = polygon_small["geojson"]
    area = polygon_small["area_sqkm"]
    # ... test code
```

### Available Fixtures

Session-level fixtures (shared across all tests):
- `test_data_manager`: Central data manager
- `polygon_generator`: Deterministic polygon generator
- `response_cache`: Provider response cache
- `test_data_validator`: Data consistency validator

Polygon fixtures (for specific polygon types):
- `polygon_small`: Small valid polygon
- `polygon_medium`: Medium valid polygon
- `polygon_boundary_min`: Boundary minimum
- `polygon_boundary_max`: Boundary maximum
- `polygon_urban`: Urban area
- `polygon_rural`: Rural area
- `polygon_ocean`: Ocean area
- `polygon_admin`: Administrative boundary
- `polygon_equator`: Equator crossing
- `polygon_pole`: Pole region
- `polygon_antimeridian`: Antimeridian crossing

Collection fixtures:
- `all_polygons`: Dictionary of all polygons
- `valid_polygons`: Dictionary of valid polygons only
- `invalid_polygons`: Dictionary of invalid polygons only

## Provider Response Cache

### How Caching Works

When a test needs real provider data:

1. **Check In-Memory Cache**: Fast access to recently used data
2. **Check Disk Cache**: Load from `backend/tests/fixtures/provider_responses/`
3. **Check Cache Age**: Verify cache is not expired (30-day TTL default)
4. **Make Real API Call**: If cache miss or expired, fetch from real API
5. **Cache Response**: Save to both memory and disk for future use

### Cache Structure

```
backend/tests/fixtures/provider_responses/
├── osm_buildings/
│   ├── valid_small.json
│   ├── urban_dense.json
│   └── ...
├── copernicus_landcover/
│   ├── valid_small.json
│   └── ...
├── usgs_elevation/
│   └── ...
└── ...
```

Each cached file contains the raw provider response with timestamp and metadata.

### Accessing Cached Data

```python
def test_with_cached_provider_data(response_cache):
    """Test using cached provider data."""
    # Check for cached data
    cached = response_cache.get_cached_response("osm_buildings", "urban_dense")
    
    if cached is None:
        # No cache, would need to fetch from real API
        # (actual tests would use mocks instead)
        pass
    else:
        # Use cached data
        features = cached["features"]
        assert len(features) > 0
```

## Deterministic Test Data Generation

### TestPolygonGenerator

Generates test polygons deterministically using seed-based generation:

```python
def test_generated_polygon(polygon_generator):
    """Test with deterministically generated polygon."""
    # Generate by area
    polygon = polygon_generator.generate_by_size(
        area_sqkm=5.0,
        seed=42  # Same seed always produces same polygon
    )
    assert polygon["area_sqkm"] == 5.0
    
    # Generate at specific location
    polygon = polygon_generator.generate_by_location(
        latitude=40.0,
        longitude=-75.0,
        area_sqkm=10.0,
        seed=42
    )
    
    # Generate with specific vertex count
    polygon = polygon_generator.generate_by_vertex_count(
        num_vertices=100,
        area_sqkm=5.0,
        seed=42
    )
```

### Property of Determinism

For property-based testing:

```python
from hypothesis import given
from hypothesis import strategies as st

@given(seed=st.integers(min_value=0, max_value=1000))
def test_generator_determinism(polygon_generator, seed):
    """Test that generator produces deterministic results."""
    poly1 = polygon_generator.generate_by_size(5.0, seed=seed)
    poly2 = polygon_generator.generate_by_size(5.0, seed=seed)
    
    assert poly1["geojson"] == poly2["geojson"]
```

## Data Validation and Consistency

### TestDataValidator

Validates provider responses and checks data consistency:

```python
def test_provider_response_validity(test_data_validator):
    """Test provider response validity."""
    response = {
        "type": "FeatureCollection",
        "features": [...]
    }
    
    is_valid, errors = test_data_validator.validate_provider_response(
        response,
        provider="osm_buildings"
    )
    
    if not is_valid:
        for error in errors:
            print(f"Validation error: {error}")
```

### Comparing Datasets

```python
def test_data_consistency(test_data_validator):
    """Test data consistency between multiple runs."""
    data1 = fetch_data_for_polygon(polygon_id="urban_dense")
    data2 = fetch_data_for_polygon(polygon_id="urban_dense")
    
    consistency, description = test_data_validator.compare_datasets(data1, data2)
    
    assert consistency == DataConsistency.IDENTICAL
```

### Detecting Duplicate Data

```python
def test_no_duplicate_test_data(test_data_validator):
    """Test that no test data is duplicated."""
    test_data_sets = [
        fetch_data(polygon_id1),
        fetch_data(polygon_id2),
        fetch_data(polygon_id3),
    ]
    
    all_unique = test_data_validator.assert_no_duplicate_data(test_data_sets)
    assert all_unique
```

## Audit Reporting

### Getting Audit Report

```python
def test_session_audit(test_data_manager):
    """Get audit report of test data usage."""
    audit_report = test_data_manager.get_audit_report()
    
    print(f"Cache hit rate: {audit_report['cache_hit_rate_percent']:.1f}%")
    print(f"Real API calls: {audit_report['real_api_calls']}")
    print(f"Provider calls: {audit_report['provider_calls']}")
```

Audit report includes:
- **timestamp**: When audit was generated
- **total_cache_requests**: Total cache requests made
- **cache_hits**: Number of cache hits
- **cache_misses**: Number of cache misses
- **cache_hit_rate_percent**: Percentage of requests served from cache
- **real_api_calls**: Total real API calls made
- **provider_calls**: Per-provider breakdown of API calls

## Cache Management

### Manual Cache Refresh

To refresh provider data cache before running tests:

```bash
# Via Python
from backend.tests.test_data_manager import ResponseCache
from pathlib import Path

cache = ResponseCache(Path("backend/tests/fixtures/provider_responses"))
cache.refresh_cache("osm_buildings", "urban_dense")
```

### Cache Age Checking

```python
def test_cache_age(response_cache):
    """Check age of cached data."""
    age = response_cache.get_cache_age("osm_buildings", "urban_dense")
    
    if age is None:
        print("No cache for this data")
    elif age > 30:
        print(f"Cache is {age:.1f} days old, refresh recommended")
```

### Automatic Cache Refresh Policy

Cache entries automatically expire after 30 days (configurable). When a cache entry expires:

1. Test detects expiration
2. Log warning about stale cache
3. System falls back to real API call (or test mock)
4. New response cached

Manual refresh schedule:
- **Monthly**: Refresh all provider caches
- **Before demonstrations**: Refresh critical polygon data
- **On demand**: When providers update their APIs

## Running Tests with Different Cache Modes

### With Cache (Default - Faster)

```bash
pytest backend/tests/
# Uses cached provider data, runs quickly
```

### Refresh Cache Before Running

```bash
# Clear cache first, then run tests
rm -rf backend/tests/fixtures/provider_responses/*
pytest backend/tests/
# Makes real API calls, caches results
```

### Run Specific Polygon Fixture

```bash
# Run tests with only urban_dense polygon
pytest backend/tests/ -m "needs_polygon[urban_dense]"
```

## Troubleshooting

### Cache Misses Occurring Frequently

**Symptom**: Audit report shows low cache hit rate

**Solution**:
1. Check if cache directory exists: `backend/tests/fixtures/provider_responses/`
2. Verify cache files aren't corrupted: `python -m json.tool <cache_file>`
3. Check if cache TTL (30 days) has been exceeded
4. Manually refresh cache if outdated

### Polygon Fixtures Not Loading

**Symptom**: `"Polygon fixture not found: xyz"`

**Solution**:
1. Check fixture file exists: `backend/tests/fixtures/test_polygons.json`
2. Verify JSON is valid: `python -m json.tool backend/tests/fixtures/test_polygons.json`
3. Verify polygon ID matches exactly
4. Check fixture is listed in the documentation above

### Test Data Manager Not Initializing

**Symptom**: `TestDataManager initialization fails`

**Solution**:
1. Verify `backend/tests/fixtures/` directory is writable
2. Check disk space (cache can grow large)
3. Verify Python has permission to create subdirectories
4. Check conftest.py is in `backend/tests/` directory

## Adding New Test Polygons

To add a new test polygon:

1. Open `backend/tests/fixtures/test_polygons.json`
2. Add new entry in `polygons` object:

```json
{
  "id": "my_new_polygon",
  "area_sqkm": 5.0,
  "location": "My location description",
  "source": "How I obtained this",
  "coordinates": [longitude, latitude],
  "intended_use": "What this polygon tests",
  "geojson": {
    "type": "Polygon",
    "coordinates": [[...]]
  }
}
```

3. Create a new fixture in `conftest.py` if commonly used:

```python
@pytest.fixture
def my_polygon(test_data_manager):
    """Description of polygon."""
    return test_data_manager.get_polygon("my_new_polygon")
```

4. Use in tests:

```python
def test_with_my_polygon(my_polygon):
    # ... test code
```

## Best Practices

1. **Use Fixtures**: Always use pytest fixtures instead of loading data directly
2. **Share Data**: Reuse fixtures across tests instead of creating duplicate data
3. **Document Intent**: Include `intended_use` in polygon fixtures
4. **Check Cache Age**: Before running important tests, verify cache age
5. **Monitor Hit Rate**: Review audit reports to ensure cache is being used effectively
6. **Version Control**: Keep fixture files in version control, not cache files
7. **Deterministic Seeds**: Use consistent seeds in property-based tests for reproducibility
8. **Validate Results**: Use TestDataValidator to ensure data quality

## Related Files

- Test data manager: `backend/tests/test_data_manager.py`
- Test fixtures: `backend/tests/fixtures/test_polygons.json`
- Provider responses: `backend/tests/fixtures/provider_responses/`
- Pytest configuration: `backend/tests/conftest.py`
- Test base classes: `backend/tests/test_*.py`
