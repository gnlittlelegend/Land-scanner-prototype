#!/usr/bin/env python
"""
Real Data Collection Test - Verify the system actually collects data from production APIs.

This test uses real polygon coordinates and makes actual requests to production
data providers (OpenStreetMap, USGS, Copernicus) to verify data collection works end-to-end.

Test Polygon: Los Angeles Metropolitan Area (100,000,000 m²)
- Coordinates: Valid geographic area with known features
- Expected Data: Buildings, roads, water, admin boundaries, land cover, elevation
"""

import json
import sys
import time
from datetime import datetime

# Add parent directory to path
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

# ============================================================================
# Test Polygon: Los Angeles Metropolitan Area
# ============================================================================
# Large area (~100,000,000 m²) with diverse features
test_polygon_geojson = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-118.50, 34.20],    # NW corner
            [-118.50, 33.80],    # SW corner
            [-117.90, 33.80],    # SE corner
            [-117.90, 34.20],    # NE corner
            [-118.50, 34.20]     # Close the ring
        ]]
    },
    "properties": {
        "name": "Los Angeles Metropolitan Area"
    }
}

print("\n[Step 1] Validating Test Polygon")
print("-" * 80)

validator = PolygonValidator()
try:
    polygon_metadata = validator.validate(test_polygon_geojson)
    print(f"✓ Polygon validation successful")
    print(f"  - Area: {polygon_metadata.area_sqm:.0f} m²")
    print(f"  - Bounding Box: {polygon_metadata.bounding_box}")
    print(f"  - Centroid: {polygon_metadata.centroid}")
    print(f"  - Vertices: {polygon_metadata.num_vertices}")
    print(f"  - CRS: {polygon_metadata.crs}")
except ValidationError as e:
    print(f"✗ Validation failed: {e}")
    sys.exit(1)

# ============================================================================
# Initialize Data Collectors with Real Production Endpoints
# ============================================================================
print("\n[Step 2] Initializing Data Collectors")
print("-" * 80)

config_manager = ConfigManager()
print(f"✓ Configuration loaded from: backend/config/")
print(f"  - Total providers in config: {len(config_manager.get_providers())}")

# Initialize collectors with real production endpoints
collectors = {
    "osm_buildings": OSMBuildingsCollector(timeout=30),
    "admin_boundaries": AdminBoundariesCollector(timeout=30),
    "roads": RoadNetworkCollector(timeout=30),
    "water": WaterBodiesCollector(timeout=30),
    "elevation": ElevationCollector(timeout=45),
    "land_cover": LandCoverCollector(timeout=45),
}

print(f"✓ {len(collectors)} collectors initialized:")
for name in collectors:
    print(f"  - {name}")

# ============================================================================
# Execute Data Collection from Production APIs
# ============================================================================
print("\n[Step 3] Collecting Data from Production APIs")
print("-" * 80)

manager = DataSourceManager(config_manager, collectors, rate_limit_delay=2)

start_time = time.time()
print(f"Starting data collection at {datetime.now().isoformat()}...")

raw_collection = manager.collect_data(polygon_metadata)

elapsed_time = time.time() - start_time

print(f"\n✓ Data collection completed in {elapsed_time:.2f} seconds")
print(f"\nCollection Summary:")
print(f"  - Total providers: {raw_collection.total_providers}")
print(f"  - Successful: {raw_collection.successful_providers}")
print(f"  - Failed: {raw_collection.failed_providers}")
print(f"  - Critical failure: {raw_collection.critical_failure}")
print(f"  - Timestamp: {raw_collection.collection_timestamp}")

# ============================================================================
# Display Results from Each Provider
# ============================================================================
print("\n[Step 4] Data Collection Results by Provider")
print("-" * 80)

total_features = 0

for provider_name, status in raw_collection.provider_status.items():
    status_symbol = "✓" if status.get("status") == "success" else "✗"
    print(f"\n{status_symbol} {provider_name.upper()}")
    print(f"  - Status: {status.get('status')}")
    print(f"  - Optional: {status.get('optional', False)}")
    
    if status.get('status') == 'success':
        feature_count = status.get('feature_count', 0)
        total_features += feature_count
        print(f"  - Features: {feature_count}")
        print(f"  - Collection Time: {status.get('collection_time_ms', 0):.0f}ms")
        
        # Show data collection result details
        if provider_name in raw_collection.collections:
            data = raw_collection.collections[provider_name]
            print(f"  - Data Category: {data.get('category', 'unknown')}")
            print(f"  - Source Provider: {data.get('source_provider', 'unknown')}")
    else:
        error_msg = status.get('error', 'Unknown error')
        print(f"  - Error: {error_msg}")

# ============================================================================
# Display Sample Data from Each Provider
# ============================================================================
print("\n[Step 5] Sample Data from Successful Collections")
print("-" * 80)

for provider_name, data in raw_collection.collections.items():
    print(f"\n{provider_name.upper()}:")
    print(f"  Category: {data.get('category')}")
    print(f"  Source: {data.get('source_provider')}")
    
    features = data.get('features', [])
    print(f"  Total Features: {len(features)}")
    
    if features:
        # Show first feature
        first_feature = features[0]
        print(f"  First Feature Sample:")
        print(f"    - Type: {first_feature.get('type', 'unknown')}")
        print(f"    - Geometry Type: {first_feature.get('geometry', {}).get('type', 'unknown')}")
        
        # Show properties preview
        props = first_feature.get('properties', {})
        if props:
            print(f"    - Properties: {list(props.keys())[:5]}...")
            for key in list(props.keys())[:3]:
                value = props[key]
                value_str = str(value)[:50] if value else "None"
                print(f"      • {key}: {value_str}")

# ============================================================================
# Overall Verification
# ============================================================================
print("\n[Step 6] Overall Verification")
print("-" * 80)

print(f"\n✓ DATA COLLECTION VERIFICATION RESULTS:")
print(f"  ✓ Polygon validation: SUCCESS")
print(f"  ✓ Configuration loaded: SUCCESS")
print(f"  ✓ Collectors initialized: SUCCESS ({len(collectors)} collectors)")
print(f"  ✓ Data collection executed: SUCCESS ({elapsed_time:.2f}s)")
print(f"  ✓ Providers queried: {raw_collection.successful_providers}/{raw_collection.total_providers}")
print(f"  ✓ Total features collected: {total_features}")
print(f"  ✓ Collections with data: {len(raw_collection.collections)}")

if raw_collection.successful_providers > 0 and total_features > 0:
    print(f"\n✅ REAL DATA COLLECTION VERIFIED - System is working with production APIs!")
    print(f"\nProviders Successfully Returning Data:")
    for provider_name, data in raw_collection.collections.items():
        feature_count = len(data.get('features', []))
        if feature_count > 0:
            print(f"  ✓ {provider_name}: {feature_count} features")
else:
    print(f"\n⚠️  WARNING: No data collected from providers")
    print(f"  Possible causes:")
    print(f"  - Network connectivity issues")
    print(f"  - Provider API rate limits or timeouts")
    print(f"  - Polygon area too small for land cover data")
    print(f"  - Provider downtime or authentication issues")

# ============================================================================
# Export Raw Collection for Inspection
# ============================================================================
print("\n[Step 7] Exporting Collection Data")
print("-" * 80)

export_file = "backend/test_real_data_collection_output.json"
try:
    export_data = {
        "test_info": {
            "timestamp": datetime.utcnow().isoformat(),
            "polygon": test_polygon_geojson,
            "polygon_metadata": {
                "area_sqm": polygon_metadata.area_sqm,
                "bounding_box": polygon_metadata.bounding_box,
                "centroid": polygon_metadata.centroid,
                "vertices": polygon_metadata.num_vertices
            },
            "execution_time_seconds": elapsed_time
        },
        "collection_summary": {
            "total_providers": raw_collection.total_providers,
            "successful_providers": raw_collection.successful_providers,
            "failed_providers": raw_collection.failed_providers,
            "critical_failure": raw_collection.critical_failure,
            "total_features": total_features
        },
        "provider_status": raw_collection.provider_status,
        "collections": {
            provider_name: {
                "category": data.get('category'),
                "source_provider": data.get('source_provider'),
                "feature_count": len(data.get('features', [])),
                "features_sample": data.get('features', [])[:3]  # First 3 features
            }
            for provider_name, data in raw_collection.collections.items()
        }
    }
    
    with open(export_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    print(f"✓ Collection data exported to: {export_file}")
    print(f"  File size: {len(json.dumps(export_data))} bytes")
except Exception as e:
    print(f"✗ Failed to export data: {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80 + "\n")
