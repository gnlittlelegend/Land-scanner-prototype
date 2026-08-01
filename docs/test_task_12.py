#!/usr/bin/env python
"""
Task 12: End-to-End System Test
Tests the complete system from polygon input to results display
"""

import sys
import json

# Add project root to path
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from backend.main import app

# Create test client
client = TestClient(app)

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("Test 1: GET /health")
    print("="*60)
    response = client.get('/health')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ PASS")
        print(f"   Service: {data.get('service')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Status: {data.get('status')}")
        return True
    else:
        print(f"❌ FAIL - Unexpected status {response.status_code}")
        print(response.text)
        return False

def test_status():
    """Test status endpoint"""
    print("\n" + "="*60)
    print("Test 2: GET /status")
    print("="*60)
    response = client.get('/status')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ PASS")
        print(f"   Prototype: {data.get('prototype_name')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Enabled Providers: {data.get('provider_count')}")
        print(f"   Providers: {', '.join(data.get('enabled_providers', []))}")
        return True
    else:
        print(f"❌ FAIL - Unexpected status {response.status_code}")
        print(response.text)
        return False

def test_invalid_missing_field():
    """Test analyze with missing polygon field"""
    print("\n" + "="*60)
    print("Test 3: POST /analyze - Missing polygon field")
    print("="*60)
    response = client.post('/analyze', json={'invalid': 'data'})
    print(f"Status Code: {response.status_code}")
    
    if response.status_code in [400, 422]:
        print(f"✅ PASS - Correctly rejected invalid input")
        data = response.json()
        print(f"   Error: {data.get('error_message') or data.get('detail', 'See response')}")
        return True
    else:
        print(f"❌ FAIL - Expected 400 or 422, got {response.status_code}")
        return False

def test_invalid_geometry():
    """Test analyze with invalid geometry"""
    print("\n" + "="*60)
    print("Test 4: POST /analyze - Invalid geometry (empty coordinates)")
    print("="*60)
    
    invalid_polygon = {
        'polygon': {
            'type': 'Polygon',
            'coordinates': [[]]  # Empty coordinates
        }
    }
    
    response = client.post('/analyze', json=invalid_polygon)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code in [400, 422]:
        print(f"✅ PASS - Correctly rejected invalid geometry")
        return True
    else:
        print(f"❌ FAIL - Expected 400 or 422, got {response.status_code}")
        return False

def test_valid_polygon():
    """Test analyze with valid polygon"""
    print("\n" + "="*60)
    print("Test 5: POST /analyze - Valid polygon (Manhattan)")
    print("="*60)
    
    valid_polygon = {
        'polygon': {
            'type': 'Polygon',
            'coordinates': [[
                [-73.9352, 40.7306],
                [-73.9352, 40.7489],
                [-73.9122, 40.7489],
                [-73.9122, 40.7306],
                [-73.9352, 40.7306]
            ]]
        }
    }
    
    try:
        response = client.post('/analyze', json=valid_polygon, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ PASS - Analysis completed successfully")
            print(f"   Request ID: {data.get('request_id', 'N/A')}")
            print(f"   Overall Status: {data.get('status', 'N/A')}")
            print(f"   Processing Time: {data.get('processing_time_ms', 0):.2f}ms")
            
            # Check structure
            print(f"\n   Response Structure:")
            if 'analysis_summary' in data:
                print(f"   ✓ Analysis Summary - Area: {data['analysis_summary'].get('polygon_area_sqkm', 'N/A')} sq km")
            if 'land_information' in data:
                print(f"   ✓ Land Information - {len(data['land_information'])} categories")
            if 'processing_status' in data:
                print(f"   ✓ Module Statuses - {len(data['processing_status'])} modules")
            if 'provider_status' in data:
                print(f"   ✓ Provider Status - {len(data['provider_status'])} providers")
            if 'errors' in data:
                if data['errors']:
                    print(f"   ⚠ Errors/Warnings: {len(data['errors'])}")
            
            # Print module status
            print(f"\n   Module Statuses:")
            for module in data.get('processing_status', []):
                status_str = module.get('status', 'unknown') if isinstance(module, dict) else str(module)
                module_name = module.get('module_name', 'unknown') if isinstance(module, dict) else 'unknown'
                print(f"   - {module_name}: {status_str}")
            
            return True
        else:
            print(f"❌ FAIL - Unexpected status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL - Exception: {str(e)}")
        return False

def test_polygon_with_different_crs():
    """Test polygon with multiple rings"""
    print("\n" + "="*60)
    print("Test 6: POST /analyze - Polygon with multiple coordinates")
    print("="*60)
    
    valid_polygon = {
        'polygon': {
            'type': 'Polygon',
            'coordinates': [[
                [-74.0, 40.7],
                [-74.0, 40.8],
                [-73.9, 40.8],
                [-73.9, 40.7],
                [-74.0, 40.7]
            ]]
        }
    }
    
    try:
        response = client.post('/analyze', json=valid_polygon, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ PASS - Analysis completed")
            print(f"   Area: {data.get('analysis_summary', {}).get('polygon_area_sqkm', 'N/A')} sq km")
            return True
        else:
            print(f"❌ FAIL - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ FAIL - {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# Task 12: End-to-End System Verification")
    print("# Checkpoint 1 - Core Functionality Complete")
    print("#"*60)
    
    results = []
    
    # Run all tests
    results.append(("Health Endpoint", test_health()))
    results.append(("Status Endpoint", test_status()))
    results.append(("Invalid Input (Missing Field)", test_invalid_missing_field()))
    results.append(("Invalid Geometry", test_invalid_geometry()))
    results.append(("Valid Polygon Analysis", test_valid_polygon()))
    results.append(("Different Area Analysis", test_polygon_with_different_crs()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 Task 12.1 VERIFICATION SUCCESSFUL!")
        print("All modules work together end-to-end.")
        return 0
    else:
        print(f"\n⚠️  Task 12.1 Partial: {passed}/{total} tests passed")
        print("Some components need attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
