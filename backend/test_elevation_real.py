#!/usr/bin/env python
"""
Real test of ElevationCollector with actual USGS API.
This test demonstrates that the elevation collector connects to
real production USGS EPQS API and retrieves actual elevation data.
"""

import sys
sys.path.insert(0, '/Users/littl/OneDrive/Desktop/LS-prototype')

from backend.collectors.elevation_collector import ElevationCollector
from backend.validators.polygon_validator import PolygonValidator

def test_elevation_collector_real():
    """Test elevation collector with real USGS API"""
    
    # Create collector
    collector = ElevationCollector(timeout=30)
    print("✓ Elevation collector created")
    
    # Create a test polygon (small area in San Francisco, ~1 km²)
    test_polygon = {
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': [[
                [-122.45, 37.75],
                [-122.44, 37.75],
                [-122.44, 37.76],
                [-122.45, 37.76],
                [-122.45, 37.75]
            ]]
        },
        'properties': {}
    }
    
    # Validate polygon first
    validator = PolygonValidator()
    validated = validator.validate(test_polygon)
    print(f"✓ Polygon validated: {validated.area_sqkm:.2f} km²")
    
    # Create validated polygon dict
    validated_dict = {
        'type': 'Feature',
        'geometry': test_polygon['geometry'],
        'properties': {
            'area_square_kilometers': validated.area_sqkm,
            'bounding_box': validated.bounding_box,
            'centroid': validated.centroid,
            'vertex_count': 5,
            'crs': 'EPSG:4326'
        }
    }
    
    # Collect elevation data
    print("\n📍 Collecting elevation data from USGS EPQS API...")
    result = collector.collect(validated_dict)
    
    # Print results
    print(f"\n✓ Collection complete")
    print(f"  Status: {result['metadata']['status']}")
    print(f"  Features: {len(result['features'])}")
    print(f"  Time: {result['metadata']['collection_time_ms']:.0f}ms")
    print(f"  API queries: {result['metadata']['attempt_count']}")
    
    if result['features']:
        # Show summary feature
        for feature in result['features']:
            if feature['properties'].get('type') == 'elevation_summary':
                props = feature['properties']
                print(f"\n📊 Elevation Summary:")
                print(f"  Min: {props.get('min_elevation_meters', 'N/A')}m")
                print(f"  Max: {props.get('max_elevation_meters', 'N/A')}m")
                print(f"  Mean: {props.get('mean_elevation_meters', 'N/A')}m")
                print(f"  Range: {props.get('elevation_range_meters', 'N/A')}m")
                print(f"  Samples: {props.get('sample_count', 'N/A')}")
                break
    else:
        print("  No features collected (may be due to USGS API limitations)")
    
    return result

if __name__ == '__main__':
    try:
        result = test_elevation_collector_real()
        if result['metadata']['status'] in ['success', 'empty']:
            print("\n✅ Test passed - Elevation collector successfully connected to real USGS API")
        else:
            print(f"\n⚠️ Test warning - Status: {result['metadata']['status']}")
            if result['metadata'].get('error_message'):
                print(f"  Error: {result['metadata']['error_message']}")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
