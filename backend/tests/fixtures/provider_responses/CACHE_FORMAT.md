# Provider Response Cache Format

This directory stores cached real provider API responses to avoid duplicate API calls during testing.

## Directory Structure

```
provider_responses/
├── osm_buildings/
│   ├── valid_small.json
│   ├── urban_dense.json
│   └── ...
├── osm_admin_boundaries/
│   ├── admin_boundary.json
│   └── ...
├── copernicus_landcover/
│   ├── valid_small.json
│   └── ...
├── osm_roads/
│   ├── urban_dense.json
│   └── ...
├── osm_water/
│   ├── water_region.json
│   └── ...
└── usgs_elevation/
    ├── mountain_region.json
    └── ...
```

## Provider Response Formats

### OSM Overpass API Responses (Buildings, Roads, Water, Admin)

All Overpass responses follow GeoJSON FeatureCollection format:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [...]
      },
      "properties": {
        "id": "osm_id",
        "name": "Feature name",
        "building": "yes",
        "height": "25.5",
        "...": "provider-specific fields"
      }
    }
  ],
  "metadata": {
    "provider": "osm_buildings",
    "timestamp": "2024-08-02T00:00:00Z",
    "polygon_id": "urban_dense",
    "query_time_ms": 1234,
    "feature_count": 150
  }
}
```

**Required Fields**:
- `type`: "FeatureCollection"
- `features`: Array of GeoJSON features
- `metadata.provider`: Provider name
- `metadata.timestamp`: When data was fetched
- `metadata.polygon_id`: Which polygon fixture this is for

### Copernicus Land Cover Response

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [...]
      },
      "properties": {
        "id": "tile_123",
        "land_cover_class": "urban",
        "confidence": 0.95
      }
    }
  ],
  "metadata": {
    "provider": "copernicus_landcover",
    "timestamp": "2024-08-02T00:00:00Z",
    "polygon_id": "valid_small",
    "resolution_m": 100,
    "feature_count": 45
  }
}
```

### USGS Elevation Response

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [longitude, latitude]
      },
      "properties": {
        "id": "sample_123",
        "elevation_m": 1234.56,
        "x": longitude,
        "y": latitude
      }
    }
  ],
  "metadata": {
    "provider": "usgs_elevation",
    "timestamp": "2024-08-02T00:00:00Z",
    "polygon_id": "mountain_region",
    "sample_spacing_m": 500,
    "feature_count": 89
  }
}
```

## Cache Management

### Adding a Cached Response

```python
from tests.test_data_manager import ResponseCache
from pathlib import Path

cache = ResponseCache(Path("backend/tests/fixtures/provider_responses"))

# Cache a real API response
response_data = {...}  # From real API
cache.cache_response("osm_buildings", "urban_dense", response_data)
```

### Retrieving a Cached Response

```python
# Get cached response (automatic TTL checking)
cached = cache.get_cached_response("osm_buildings", "urban_dense")

if cached:
    features = cached["features"]
else:
    # Cache miss or expired - would fetch from real API
    pass
```

### Cache Expiration

- **Default TTL**: 30 days
- **Expired cache**: Automatically skipped, triggers fresh API call
- **Manual refresh**: `cache.refresh_cache("provider", "polygon_id")`

## Naming Convention

Cache files are named: `{polygon_fixture_id}.json`

Examples:
- `urban_dense.json` - Response for `urban_dense` polygon
- `valid_small.json` - Response for `valid_small` polygon
- `mountain_region.json` - Response for `mountain_region` polygon

## Provider Directories

### osm_buildings/
Responses from OpenStreetMap Overpass API for building queries.
Query type: All ways and relations with "building" tag

### osm_admin_boundaries/
Responses from OpenStreetMap Overpass API for administrative boundaries.
Query type: Administrative boundaries with admin_level tags

### osm_roads/
Responses from OpenStreetMap Overpass API for road networks.
Query type: All ways with "highway" tag

### osm_water/
Responses from OpenStreetMap Overpass API for water features.
Query type: Water areas and ways

### copernicus_landcover/
Responses from Copernicus Global Land Cover STAC API.
Data: 100m resolution land cover classification

### usgs_elevation/
Responses from USGS Elevation Point Query Service.
Data: Elevation samples on regular grid

## Usage in Tests

### Accessing Cached Data

```python
def test_collection_with_cached_data(test_data_manager, response_cache):
    """Test using cached provider data."""
    # Get polygon
    polygon = test_data_manager.get_polygon("urban_dense")
    
    # Check for cached OSM buildings response
    cached = response_cache.get_cached_response("osm_buildings", "urban_dense")
    
    if cached:
        # Use cached data in test
        features = cached["features"]
        assert len(features) > 0
    else:
        # No cache available - test would mock or skip
        pass
```

### Caching New Responses

```python
def fetch_and_cache_provider_data(polygon_id: str):
    """Fetch real data from provider and cache it."""
    # This would be called once to populate cache
    response = real_api_call(polygon_id)
    cache.cache_response("osm_buildings", polygon_id, response)
```

## Maintenance

### Checking Cache Age

```bash
# Show cache file ages
ls -lh backend/tests/fixtures/provider_responses/*/
```

### Clearing Expired Cache

Cache entries older than 30 days are automatically skipped. To manually clear:

```bash
# Remove specific provider's cache
rm -rf backend/tests/fixtures/provider_responses/osm_buildings/*

# Remove all cache (will be regenerated on next test run)
rm -rf backend/tests/fixtures/provider_responses/*
```

### Updating Cache

```bash
# Force refresh of specific polygon's OSM data
python -c "
from tests.test_data_manager import ResponseCache
from pathlib import Path
cache = ResponseCache(Path('backend/tests/fixtures/provider_responses'))
cache.refresh_cache('osm_buildings', 'urban_dense')
"
```

## Best Practices

1. **Commit fixtures to version control**: Ensure test reproducibility
2. **Don't commit sensitive data**: Redact API keys, authentication tokens
3. **Update monthly**: Keep provider data current (30-day TTL)
4. **Verify on API changes**: If provider API changes, update cache
5. **Document data source**: Include timestamp and version in metadata
6. **Audit usage**: Monitor cache hit rates in test audit reports
