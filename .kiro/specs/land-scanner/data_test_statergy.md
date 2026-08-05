# Test Data Strategy: Centralized Management for Land Scanner

## Problem Solved

Your critical insight identified a major testing anti-pattern:

**Without Centralization**:
- Each property-based test independently generates test data
- Multiple tests with identical inputs create duplicate data
- Hundreds/thousands of redundant real API calls
- No awareness that identical inputs are being tested
- Test inconsistency (same input might behave differently across tests)
- Rate limiting issues from real providers
- Slow, expensive test execution

**With Centralization**:
- All tests share a single source of truth for test data
- One real API call per polygon per provider (cached for reuse)
- Test consistency: same input always same output
- Dramatic reduction in API calls and test execution time
- Ability to audit what data is actually being tested
- Reproducible, deterministic test runs

## Centralized Test Data Architecture

### 1. TestDataManager (Core Component)
- **Purpose**: Manage all test data lifecycle
- **Functionality**:
  - Load fixtures at test session start
  - Cache all real provider responses
  - Share data across all tests
  - Track data usage and hits/misses
  - Handle cache invalidation (TTL, manual)
  - Version all data for reproducibility

### 2. Test Fixtures (fixtures/test_polygons.json)
```json
{
  "polygons": {
    "valid_small": {
      "id": "polygon_small",
      "geojson": {...},
      "properties": {
        "area_sqkm": 0.025,
        "location": "Central Park, NYC",
        "coordinates_source": "...",
        "intended_use": ["validation", "collection", "standardization"]
      }
    },
    "valid_medium": {...},
    "boundary_minimum": {"area_sqkm": 0.00001, ...},
    "boundary_maximum": {"area_sqkm": 100, ...},
    "invalid_small": {"area_sqkm": 0.000005, ...},
    "equator_crossing": {...},
    "pole_region": {...},
    "antimeridian": {...},
    "urban_dense": {"location": "Manhattan", ...},
    "rural_sparse": {"location": "Montana", ...},
    "ocean": {"location": "Atlantic", ...},
    "admin_boundary": {"location": "State of Texas", ...},
    "mixed_terrain": {...}
  }
}
```

### 3. Provider Response Cache (fixtures/provider_responses/)
```
fixtures/provider_responses/
├── osm_buildings/
│   ├── valid_small.json          (real Overpass response for polygon_small)
│   ├── valid_medium.json         (real Overpass response for polygon_medium)
│   └── urban_dense.json          (real response for NYC polygon)
├── osm_admin/
│   ├── admin_boundary.json       (real admin data)
│   └── ...
├── osm_roads/
├── osm_water/
├── copernicus_land_cover/
│   ├── valid_small_glc2021.json  (real GLC2021 response)
│   └── ...
└── usgs_elevation/
    ├── valid_small_dem.json      (real USGS DEM response)
    └── ...
```

Each cached file includes metadata:
```json
{
  "polygon_id": "valid_small",
  "provider": "osm_buildings",
  "cached_timestamp": "2024-01-15T10:30:00Z",
  "data_version": "Overpass API 2024-01",
  "cache_age_days": 7,
  "response": { ... actual API response ... }
}
```

### 4. Test Data Sharing Protocol

#### Pattern 1: Fixture Declaration
```python
@pytest.mark.uses_fixture("valid_small")
def test_polygon_validation(test_data_manager):
    polygon = test_data_manager.get_polygon("valid_small")
    # All tests requesting "valid_small" get SAME data
    # Only ONE real API call to fetch this polygon from providers
```

#### Pattern 2: Provider Data Caching
```python
def test_data_collection(test_data_manager):
    polygon = test_data_manager.get_polygon("valid_small")
    
    # Get cached response instead of calling real API
    osm_response = test_data_manager.get_cached_response(
        provider="osm_buildings",
        polygon_id="valid_small"
    )
    # Cache hit: uses fixtures/provider_responses/osm_buildings/valid_small.json
    # No real API call made
```

#### Pattern 3: Audit Trail
```python
def test_suite_summary(test_data_manager):
    audit = test_data_manager.get_audit_report()
    # Output:
    # Total tests: 500
    # Real API calls: 17 (only 17!)
    # Cached responses used: 483
    # Cache hit rate: 96.6%
    # Provider call breakdown:
    #   - osm_buildings: 3 calls (valid_small, urban_dense, admin_boundary)
    #   - osm_admin: 2 calls
    #   - osm_roads: 2 calls
    #   - osm_water: 2 calls
    #   - copernicus_glc: 4 calls
    #   - usgs_elevation: 2 calls
```

## Implementation Details

### Phase 1: Setup Test Data Infrastructure (Task 2.0-2.0.6)
1. Create TestDataManager class
2. Define test polygon fixtures (17 standard polygons)
3. Implement ResponseCache for provider data
4. Create TestPolygonGenerator for deterministic variations
5. Implement test data sharing protocol
6. Create validation and audit system
7. Document all procedures

### Phase 2: Update Property Tests (Tasks 3.2 onwards)
For each property test, change from:
```python
# OLD: Generate random data for each test
@given(valid_geojson_polygon())  # Generates new data each time
def test_polygon_validation(polygon):
    ...
```

To:
```python
# NEW: Reuse centralized fixtures
@pytest.mark.parametrize("polygon_id", [
    "valid_small",
    "valid_medium",
    "boundary_minimum",
    "boundary_maximum",
    "urban_dense",
    ...  # All shared fixtures
])
@pytest.mark.uses_fixture
def test_polygon_validation(test_data_manager, polygon_id):
    polygon = test_data_manager.get_polygon(polygon_id)
    # Same polygon used across ALL tests requesting "valid_small"
    # No duplication, shared data
```

### Phase 3: Provider Data Caching
All tests requesting provider data use cached responses:
```python
def test_data_standardization(test_data_manager):
    polygon = test_data_manager.get_polygon("valid_small")
    
    # Get cached provider responses (NO real API calls)
    osm_buildings = test_data_manager.get_cached_response(
        provider="osm_buildings",
        polygon_id="valid_small"
    )
    copernicus_lc = test_data_manager.get_cached_response(
        provider="copernicus_land_cover",
        polygon_id="valid_small"
    )
    # ... use cached data for standardization testing
```

## Test Data Dimensions

### Polygon Fixtures (17 standard polygons)
- **Validity**: valid (10), invalid (2)
- **Sizes**: small, medium, large, boundary-min, boundary-max
- **Locations**: equator, poles, antimeridian, urban, rural, ocean, admin
- **Geometry**: various shapes, vertex counts

### Provider Response Variations
For each provider × polygon combination:
- Real API response (cached)
- Error scenarios (timeout, 500, malformed - stored separately)
- Multiple date versions (for regression testing)

### Deterministic Data Generation
```python
polygon_gen = TestPolygonGenerator(seed=42)
# Same seed = IDENTICAL polygon every time
# For property tests needing 500+ iterations:
for i in range(500):
    polygon = polygon_gen.get_size_variation(size_index=i)
    # Reproducible, deterministic, but varied
```

## Benefits

### 1. Test Efficiency
- **Before**: 500 property tests × 100 iterations = 50,000 API calls
- **After**: 17 real API calls + 49,983 cache hits
- **Improvement**: ~3000x reduction in API calls

### 2. Test Reliability
- Same inputs always produce same outputs (no randomness)
- Can reproduce exact test conditions
- Easier debugging (you know exactly what data was tested)

### 3. Cost Savings
- No rate limiting issues from providers
- Faster test execution (seconds instead of minutes/hours)
- Lower bandwidth usage

### 4. Testability
- All tests share common truth (fixtures)
- Can verify "data consistency" properties
- Can audit exactly what was tested

### 5. Maintainability
- Add new test cases by adding new fixture
- Update provider data by refreshing cache
- Version control all test data in git

## Cache Refresh Strategy

### Automatic Refresh
- **Monthly**: Refresh all provider caches monthly (scheduled)
- **On-demand**: `pytest --refresh-test-data` flag

### Manual Refresh Process
```bash
# Refresh specific provider
pytest --refresh-provider osm_buildings

# Refresh specific polygon
pytest --refresh-polygon valid_small

# Refresh all
pytest --refresh-all
```

### Versioning
- Each cache snapshot includes timestamp
- Keep history of provider responses (for regression testing)
- Can compare current behavior vs historical

## Audit and Transparency

### Test Data Audit Report
```
Test Data Usage Report
======================
Total Tests Run: 500
Real API Calls Made: 17
Cached Responses Used: 10,000+
Cache Hit Rate: 99.8%

Provider Call Breakdown:
- osm_buildings: 3 calls (4 cached responses × 100 tests = 400 reuses)
- osm_admin: 2 calls (2 cached responses × 100 tests = 200 reuses)
- osm_roads: 2 calls
- osm_water: 2 calls
- copernicus_land_cover: 4 calls
- usgs_elevation: 2 calls

Fixture Usage:
- valid_small: used by 150 tests (cache hit rate 100%)
- valid_medium: used by 100 tests (cache hit rate 100%)
- urban_dense: used by 75 tests (cache hit rate 100%)
- ...
```

## Next Steps

1. **Implement Tasks 2.0-2.0.6**: Set up all centralized infrastructure
2. **Create fixtures/test_polygons.json**: Define 17 standard test polygons
3. **Populate fixtures/provider_responses/**: Cache real provider data
4. **Update property tests**: Modify to use centralized fixtures
5. **Run audit**: Verify cache hit rates and efficiency

## Key Principle

**All tests at the same level should use the same test data.**

If 100 tests are testing "polygon validation," they should all test the same set of 17 polygons (possibly in different orders), not generate 100 different random polygons.

This ensures:
- Consistency (same input = same output)
- Efficiency (no duplicate work)
- Reliability (reproducible results)
- Transparency (you know what was tested)

