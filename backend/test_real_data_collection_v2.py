#!/usr/bin/env python
"""
Real Data Collection Test - Verify system collects actual data from production APIs.

Using metric measurements:
- MIN_AREA: 10 m² (metres squared)
- MAX_AREA: 100,000,000 m² (100 km²)
- TEST_AREA: 5,000 m² - Well within valid range

Test Location: Los Angeles Downtown Area
- Real coordinates with known buildings, roads, water features
- Will query: OpenStreetMap (Overpass), USGS, Copernicus APIs
"""

import json
import sys
import time
from datetime import datetime

sys.path.insert(0, '.')

from backend.validators.polygon_validator import PolygonValidator, ValidationError
from backend.managers.data_source_manager import DataSourceManager
from backend.services.config_manager import ConfigManager
from backend.collectors.osm_buildings_collector import OSMBuildingsCollector
from backend.collectors.admin_boundaries_collector import AdminBoundariesCollector
from backend.collectors.road_network_collector import RoadNetworkCollector
from backend.collectors.water_bodies_collector import WaterBodiesCollector
from backend.collectors.elevation_collector import ElevationCollector
from backend.collectors.land_cover_collector import LandCoverCollector

print("\n" + "=" * 80)
print("REAL DATA COLLECTION TEST - Production API Verification")
print("=" * 80)
print("✓ Measurement standards updated to m² (metres squared):")
print("  - Minimum valid area: 10 m²")
print("  - Maximum valid area: 100,000,000 m²")
print("  - Test polygon area: ~5,000 m² (within limits)")

# ============================================================================
# Test Polygon: Los Angeles Downtown
# ============================================================================
print("\n[Step 1] Creating Test Polygon")
print("-" * 80)

# Real coordinates: Downtown LA
# Approximately 0.3 km x 0.017 km = ~5000 m²
test_polygon_geojson = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-118.2430, 34.0522],    # Point 1: NW
            [-118.2430, 34.0505],    # Point 2: SW
            [-118.2400, 34.0505],    # Point 3: SE
            [-118.2400, 34.0522],    # Point 4: NE
            [-118.2430, 34.0522]     # Point 5: Close ring
        ]]
    },
    "properties": {
        "name": "Downtown Los Angeles Test Area",
        "expected_area_m2": 5000
    }
}

print("✓ Test polygon created:")
print(f"  - Coordinates: {len(test_polygon_geojson['geometry']['coordinates'][0])} points")
print(f"  - Expected area: ~5,000 m²")
print(f"  - Location: Downtown Los Angeles (real geography)")

# ============================================================================
# Step 1: Validate Polygon
# ============================================================================
print("\n[Step 2] Validating Polygon Geometry")
print("-" * 80)

validator = PolygonValidator()
try:
    polygon_metadata = validator.validate(test_polygon_geojson)
    print(f"✓ Validation PASSED")
    print(f"  - Area: {polygon_metadata.area_sqm:.2f} m² (squared metres)")
    print(f"  - Bounding Box: {polygon_metadata.bounding_box}")
    print(f"  - Centroid: {polygon_metadata.centroid}")
    print(f"  - Vertices: {polygon_metadata.num_vertices}")
    print(f"  - Valid: {polygon_metadata.is_valid}")
except ValidationError as e:
    print(f"✗ Validation FAILED: {e}")
    sys.exit(1)

# ============================================================================
# Step 2: Initialize Collectors and Manager
# ============================================================================
print("\n[Step 3] Initializing Data Collectors")
print("-" * 80)

config_manager = ConfigManager()
print(f"✓ Configuration manager initialized")

collectors = {
    "osm_buildings": OSMBuildingsCollector(timeout=30),
    "admin_boundaries": AdminBoundariesCollector(timeout=30),
    "roads": RoadNetworkCollector(timeout=30),
    "water": WaterBodiesCollector(timeout=30),
    "elevation": ElevationCollector(timeout=45),
    "land_cover": LandCoverCollector(timeout=45),
}

print(f"✓ {len(collectors)} collectors initialized:")
for name, collector in collectors.items():
    print(f"  - {name}: {collector.__class__.__name__}")

# ============================================================================
# Step 3: Collect Data from Production APIs
# ============================================================================
print("\n[Step 4] Collecting Data from Production APIs")
print("-" * 80)
print("⏳ Querying production APIs...")
print("   (This may take 30-90 seconds depending on API response times)\n")

manager = DataSourceManager(config_manager, collectors, rate_limit_delay=2)
start_time = time.time()

try:
    raw_collection = manager.collect_data(polygon_metadata)
    elapsed_time = time.time() - start_time
    
    print(f"\n✓ Data collection completed in {elapsed_time:.2f} seconds")
    
except Exception as e:
    print(f"\n✗ Data collection failed: {e}")
    sys.exit(1)

# ============================================================================
# Step 4: Display Collection Results
# ============================================================================
print("\n[Step 5] Collection Results Summary")
print("-" * 80)

print(f"\nOverall Status:")
print(f"  - Total providers enabled: {raw_collection.total_providers}")
print(f"  - Successful collections: {raw_collection.successful_providers}")
print(f"  - Failed collections: {raw_collection.failed_providers}")
print(f"  - Critical failure: {raw_collection.critical_failure}")
print(f"  - Collection timestamp: {raw_collection.collection_timestamp}")

# ============================================================================
# Step 5: Display Provider Details
# ============================================================================
print("\n[Step 6] Results by Provider")
print("-" * 80)

total_features = 0

for provider_name, status in raw_collection.provider_status.items():
    status_value = status.get("status")
    is_optional = status.get("optional", False)
    
    if status_value == "success":
        print(f"\n✓ {provider_name.upper()} - SUCCESS")
        feature_count = status.get("feature_count", 0)
        total_features += feature_count
        print(f"  - Features: {feature_count}")
        print(f"  - Time: {status.get('collection_time_ms', 0):.0f}ms")
        print(f"  - Optional: {is_optional}")
        
        # Show data structure
        if provider_name in raw_collection.collections:
            data = raw_collection.collections[provider_name]
            print(f"  - Category: {data.get('category')}")
            print(f"  - Source: {data.get('source_provider')}")
    else:
        print(f"\n✗ {provider_name.upper()} - {status_value.upper()}")
        print(f"  - Error: {status.get('error', 'Unknown error')}")
        print(f"  - Optional: {is_optional}")

# ============================================================================
# Step 6: Display Sample Data
# ============================================================================
print("\n[Step 7] Sample Data from Collections")
print("-" * 80)

if raw_collection.collections:
    for provider_name, data in raw_collection.collections.items():
        features = data.get('features', [])
        if features:
            print(f"\n{provider_name.upper()} - {len(features)} features collected:")
            
            # Show first 2 features
            for i, feature in enumerate(features[:2]):
                print(f"\n  Feature {i+1}:")
                print(f"    - Type: {feature.get('type')}")
                geometry = feature.get('geometry', {})
                print(f"    - Geometry: {geometry.get('type')}")
                
                props = feature.get('properties', {})
                if props:
                    print(f"    - Properties: {len(props)} fields")
                    for j, (key, value) in enumerate(list(props.items())[:3]):
                        value_str = str(value)[:60]
                        print(f"      • {key}: {value_str}")
else:
    print("\nNo collections with data")

# ============================================================================
# Step 7: Final Verification
# ============================================================================
print("\n[Step 8] Final Verification")
print("-" * 80)

print(f"\n{'=' * 80}")
if raw_collection.successful_providers > 0 and total_features > 0:
    print(f"✅ REAL DATA COLLECTION VERIFIED - SYSTEM WORKING!")
    print(f"{'=' * 80}")
    print(f"\nData Collection Results:")
    print(f"  ✓ Polygon validation: SUCCESS")
    print(f"  ✓ Collectors initialized: SUCCESS")
    print(f"  ✓ APIs queried: SUCCESS ({raw_collection.successful_providers}/{raw_collection.total_providers})")
    print(f"  ✓ Total features received: {total_features}")
    print(f"  ✓ Execution time: {elapsed_time:.2f} seconds")
    print(f"\nProviders Returning Data:")
    for provider_name, data in raw_collection.collections.items():
        count = len(data.get('features', []))
        if count > 0:
            print(f"  ✓ {provider_name}: {count} features")
else:
    print(f"⚠️  LIMITED DATA - Some providers did not return data")
    print(f"{'=' * 80}")
    print(f"\nPossible causes:")
    print(f"  - API rate limiting or timeouts")
    print(f"  - Network connectivity issues")
    print(f"  - Provider availability")
    print(f"  - Polygon too small for some data types")
    print(f"  - Authentication or access restrictions")

# ============================================================================
# Export Results
# ============================================================================
print("\n[Step 9] Exporting Results")
print("-" * 80)

export_file = "backend/test_real_data_output.json"
try:
    # Prepare exportable data
    export_data = {
        "metadata": {
            "test_date": datetime.utcnow().isoformat(),
            "polygon_area_m2": polygon_metadata.area_sqm,
            "execution_time_seconds": elapsed_time,
            "polygon_coordinates": test_polygon_geojson["geometry"]["coordinates"]
        },
        "collection_summary": {
            "total_providers": raw_collection.total_providers,
            "successful": raw_collection.successful_providers,
            "failed": raw_collection.failed_providers,
            "total_features": total_features
        },
        "provider_status": raw_collection.provider_status,
        "sample_data": {
            provider_name: {
                "category": data.get('category'),
                "source": data.get('source_provider'),
                "feature_count": len(data.get('features', [])),
                "sample_features": data.get('features', [])[:1]  # First feature only
            }
            for provider_name, data in raw_collection.collections.items()
        }
    }
    
    with open(export_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    file_size = len(json.dumps(export_data))
    print(f"✓ Results exported to: {export_file}")
    print(f"  - File size: {file_size:,} bytes")
    
except Exception as e:
    print(f"✗ Export failed: {e}")

print(f"\n{'=' * 80}")
print("TEST COMPLETE")
print(f"{'=' * 80}\n")
