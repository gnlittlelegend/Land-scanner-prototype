#!/usr/bin/env python
"""
End-to-end test of the /analyze endpoint with real collectors.
This test demonstrates that the full pipeline works with real production APIs.
"""

import sys
sys.path.insert(0, '/Users/littl/OneDrive/Desktop/LS-prototype')

from backend.validators.polygon_validator import PolygonValidator
from backend.managers.data_source_manager import DataSourceManager
from backend.collectors.osm_buildings_collector import OSMBuildingsCollector
from backend.collectors.admin_boundaries_collector import AdminBoundariesCollector
from backend.collectors.road_network_collector import RoadNetworkCollector
from backend.collectors.water_bodies_collector import WaterBodiesCollector
from backend.collectors.elevation_collector import ElevationCollector
from backend.collectors.land_cover_collector import LandCoverCollector
from backend.services.config_manager import ConfigManager

def test_end_to_end():
    """Test complete data collection pipeline with real APIs"""
    
    print("=" * 70)
    print("END-TO-END TEST: Land Scanner Data Collection Pipeline")
    print("=" * 70)
    
    # Step 1: Create and validate polygon
    print("\n[1/5] Creating test polygon...")
    test_polygon_geojson = {
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': [[
                [-122.47, 37.79],  # San Francisco
                [-122.40, 37.79],
                [-122.40, 37.84],
                [-122.47, 37.84],
                [-122.47, 37.79]
            ]]
        },
        'properties': {}
    }
    
    validator = PolygonValidator()
    polygon_metadata = validator.validate(test_polygon_geojson)
    print(f"[OK] Polygon validated: {polygon_metadata.area_sqm:.0f} m²")
    
    # Convert to proper format for collectors
    polygon = {
        'type': 'Feature',
        'geometry': test_polygon_geojson['geometry'],
        'properties': {
            'area_sqm': polygon_metadata.area_sqm,
            'bounding_box': polygon_metadata.bounding_box,
            'centroid': polygon_metadata.centroid,
            'num_vertices': polygon_metadata.num_vertices,
            'crs': polygon_metadata.crs
        }
    }
    
    # Step 2: Initialize collectors
    print("\n[2/5] Initializing real data collectors...")
    collectors = {
        'osm_buildings': OSMBuildingsCollector(timeout=30),
        'osm_admin_boundaries': AdminBoundariesCollector(timeout=30),  # Must match config ID!
        'osm_roads': RoadNetworkCollector(timeout=30),
        'osm_water': WaterBodiesCollector(timeout=30),
        'usgs_elevation': ElevationCollector(timeout=45),
        'copernicus_land_cover': LandCoverCollector(timeout=45),
    }
    print(f"[OK] Initialized {len(collectors)} collectors")
    print(f"     Collectors: {list(collectors.keys())}")
    
    # Step 3: Create config manager mock
    print("\n[3/5] Creating configuration...")
    config = ConfigManager()
    enabled = config.get_enabled_providers()
    print(f"[OK] Configuration loaded: {len(enabled)} providers enabled")
    print(f"     Provider IDs: {list(enabled.keys())}")
    
    # Step 4: Run data collection
    print("\n[4/5] Collecting data from all providers (connecting to real production APIs)...")
    manager = DataSourceManager(config, collectors)
    collection_result = manager.collect_data(polygon)
    
    # Print collection summary
    print(f"\n[OK] Collection complete:")
    print(f"  Total providers: {collection_result.total_providers}")
    print(f"  Successful: {collection_result.successful_providers}")
    print(f"  Failed: {collection_result.failed_providers}")
    print(f"  Critical failure: {collection_result.critical_failure}")
    
    # Print provider-by-provider status
    print(f"\n  Provider status:")
    for provider_name, status in collection_result.provider_status.items():
        status_icon = "[OK]" if status['status'] == 'success' else "[ERR]"
        status_str = status['status']
        details = ""
        if 'feature_count' in status:
            details = f" ({status['feature_count']} features)"
        elif 'error' in status:
            details = f" ({status['error'][:40]}...)"
        print(f"    {status_icon} {provider_name:20} {status_str:15} {details}")
    
    # Step 5: Verify results
    print("\n[5/5] Verifying results...")
    
    collected_count = len(collection_result.collections)
    print(f"  [OK] Datasets collected: {collected_count}/{collection_result.total_providers}")
    
    if collected_count > 0:
        print(f"\n  [OK] Sample data from collected providers:")
        for provider_name, dataset in list(collection_result.collections.items())[:3]:
            features = dataset.get('features', [])
            print(f"    - {provider_name}: {len(features)} features")
    
    # Final summary
    print("\n" + "=" * 70)
    if collection_result.successful_providers > 0:
        print(f"SUCCESS: Collected data from {collection_result.successful_providers} providers")
        print(f"DATA: Ready for standardization and analysis (Task 6+)")
    else:
        print(f"WARNING: No providers succeeded")
        print(f"   This may be due to API issues or network connectivity")
    print("=" * 70)
    
    return collection_result

if __name__ == '__main__':
    try:
        result = test_end_to_end()
        sys.exit(0 if result.successful_providers > 0 else 1)
    except Exception as e:
        print(f"\nERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
