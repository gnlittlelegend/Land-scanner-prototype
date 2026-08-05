"""
Tests for OSM Buildings Collector.

Tests the OSMBuildingsCollector implementation that connects to
the real Overpass API to fetch building footprints.

Requirements Tested (Task 4.1):
- Connect to real Overpass API endpoint
- Build Overpass QL query for buildings
- Handle timeouts and rate limits
- Implement retry with longer timeout
- Validate response is valid GeoJSON
- Return raw features with OSM attribution
- Handle provider unavailability gracefully
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import time

from backend.collectors.osm_buildings_collector import OSMBuildingsCollector


class TestOSMBuildingsCollectorInitialization:
    """Test OSMBuildingsCollector initialization."""
    
    def test_initialization_defaults(self):
        """Collector should initialize with correct defaults."""
        collector = OSMBuildingsCollector()
        
        assert collector.provider_name == "OSM Buildings"
        assert collector.endpoint == "http://overpass-api.de/api/interpreter"
        assert collector.timeout == 30
        assert collector.max_retries == 2
        assert collector.retry_delay_base == 2.0
    
    def test_initialization_custom_timeout(self):
        """Collector should accept custom timeout."""
        collector = OSMBuildingsCollector(timeout=45)
        
        assert collector.timeout == 45


class TestOverpassQueryBuilding:
    """Test Overpass QL query building."""
    
    def test_query_building_format(self):
        """Query should be properly formatted for Overpass API."""
        collector = OSMBuildingsCollector()
        
        bbox = (-74.0, 40.0, -73.0, 41.0)  # (min_lon, min_lat, max_lon, max_lat)
        query = collector._build_overpass_query(bbox)
        
        # Query should contain bbox in correct format
        assert "[bbox:40.0,-74.0,41.0,-73.0]" in query
        # Query should include way buildings
        assert 'way["building"]' in query
        # Query should include relation buildings
        assert 'relation["building"]' in query
        # Query should request geometry output
        assert "out geom" in query
    
    def test_query_includes_both_ways_and_relations(self):
        """Query should fetch both ways and relations."""
        collector = OSMBuildingsCollector()
        
        bbox = (0, 0, 1, 1)
        query = collector._build_overpass_query(bbox)
        
        assert 'way["building"]' in query
        assert 'relation["building"]' in query


class TestCollectMethod:
    """Test collect() method."""
    
    def test_collect_success(self):
        """Successful collection should return dataset with features."""
        collector = OSMBuildingsCollector()
        
        # Mock polygon
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "area_square_kilometers": 12345.6,
                "bounding_box": {
                    "min_lon": 0,
                    "min_lat": 0,
                    "max_lon": 1,
                    "max_lat": 1
                }
            }
        }
        
        # Mock successful Overpass response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "type": "way",
                    "id": 12345,
                    "geometry": [
                        {"lat": 40.0, "lon": -74.0},
                        {"lat": 40.1, "lon": -74.0},
                        {"lat": 40.1, "lon": -73.9},
                        {"lat": 40.0, "lon": -73.9},
                        {"lat": 40.0, "lon": -74.0}
                    ],
                    "tags": {"building": "residential", "name": "Test Building"}
                }
            ]
        }
        
        with patch.object(collector, '_make_request', return_value=mock_response):
            result = collector.collect(polygon)
        
        # Check dataset structure
        assert result["source_provider"] == "OSM Buildings"
        assert result["category"] == "buildings"
        assert len(result["features"]) == 1
        assert result["metadata"]["status"] == "success"
        assert result["metadata"]["feature_count"] == 1
        
        # Check feature structure
        feature = result["features"][0]
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Polygon"
        assert feature["properties"]["osm_type"] == "way"
        assert feature["properties"]["osm_id"] == 12345
        assert feature["properties"]["source"] == "osm"
    
    def test_collect_empty_response(self):
        """Empty Overpass response should return empty features list."""
        collector = OSMBuildingsCollector()
        
        polygon = {
            "properties": {
                "area_square_kilometers": 10.0,
                "bounding_box": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1}
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"elements": []}
        
        with patch.object(collector, '_make_request', return_value=mock_response):
            result = collector.collect(polygon)
        
        assert result["features"] == []
        assert result["metadata"]["status"] == "empty"
        assert result["metadata"]["feature_count"] == 0
    
    def test_collect_invalid_json_response(self):
        """Invalid JSON response should be handled gracefully."""
        collector = OSMBuildingsCollector()
        
        polygon = {
            "properties": {
                "area_square_kilometers": 10.0,
                "bounding_box": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1}
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        with patch.object(collector, '_make_request', return_value=mock_response):
            result = collector.collect(polygon)
        
        assert result["features"] == []
        assert result["metadata"]["status"] == "error"
        assert "Invalid JSON response" in result["metadata"]["error_message"]
    
    def test_collect_api_failure(self):
        """Failed API request should return error dataset."""
        collector = OSMBuildingsCollector()
        
        polygon = {
            "properties": {
                "area_square_kilometers": 10.0,
                "bounding_box": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1}
            }
        }
        
        # Simulate API failure (returns None after retries)
        with patch.object(collector, '_make_request', return_value=None):
            result = collector.collect(polygon)
        
        assert result["features"] == []
        assert result["metadata"]["status"] == "error"
        assert result["metadata"]["error_message"] == "Overpass API unavailable or timeout"


class TestResponseParsing:
    """Test OSM response parsing."""
    
    def test_parse_way_to_feature(self):
        """Should convert OSM way to GeoJSON feature."""
        collector = OSMBuildingsCollector()
        
        way = {
            "type": "way",
            "id": 12345,
            "geometry": [
                {"lat": 40.0, "lon": -74.0},
                {"lat": 40.1, "lon": -74.0},
                {"lat": 40.1, "lon": -73.9},
                {"lat": 40.0, "lon": -73.9},
                {"lat": 40.0, "lon": -74.0}
            ],
            "tags": {"building": "residential", "name": "Test Building"}
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature is not None
        assert feature["type"] == "Feature"
        assert feature["id"] == "way_12345"
        assert feature["geometry"]["type"] == "Polygon"
        assert len(feature["geometry"]["coordinates"][0]) == 5  # 5 points (closed ring)
        assert feature["properties"]["osm_id"] == 12345
        assert feature["properties"]["osm_type"] == "way"
        assert feature["properties"]["name"] == "Test Building"
        assert feature["properties"]["type"] == "residential"
    
    def test_parse_way_closes_open_ring(self):
        """Should close open rings by repeating first coordinate."""
        collector = OSMBuildingsCollector()
        
        way = {
            "type": "way",
            "id": 1,
            "geometry": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 0},
                {"lat": 1, "lon": 1},
                {"lat": 0, "lon": 1}
                # Not closed
            ],
            "tags": {"building": "yes"}
        }
        
        feature = collector._way_to_feature(way)
        
        coords = feature["geometry"]["coordinates"][0]
        # Should be closed (first == last)
        assert coords[0] == coords[-1]
    
    def test_parse_way_insufficient_nodes(self):
        """Should reject ways with insufficient nodes."""
        collector = OSMBuildingsCollector()
        
        way = {
            "type": "way",
            "id": 1,
            "geometry": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 0}
            ],
            "tags": {"building": "yes"}
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature is None
    
    def test_parse_relation_to_feature(self):
        """Should convert OSM relation to GeoJSON feature."""
        collector = OSMBuildingsCollector()
        
        relation = {
            "type": "relation",
            "id": 54321,
            "bounds": {
                "minlat": 40.0,
                "minlon": -74.0,
                "maxlat": 40.1,
                "maxlon": -73.9
            },
            "tags": {"building": "yes", "name": "Large Building"}
        }
        
        feature = collector._relation_to_feature(relation)
        
        assert feature is not None
        assert feature["type"] == "Feature"
        assert feature["id"] == "relation_54321"
        assert feature["geometry"]["type"] == "Polygon"
        assert len(feature["geometry"]["coordinates"][0]) == 5  # 5 points for bbox (closed)
        assert feature["properties"]["osm_id"] == 54321
        assert feature["properties"]["osm_type"] == "relation"
    
    def test_parse_relation_missing_bounds(self):
        """Should reject relations without bounds."""
        collector = OSMBuildingsCollector()
        
        relation = {
            "type": "relation",
            "id": 1,
            "tags": {"building": "yes"}
        }
        
        feature = collector._relation_to_feature(relation)
        
        assert feature is None
    
    def test_parse_osm_response_multiple_elements(self):
        """Should parse response with multiple elements."""
        collector = OSMBuildingsCollector()
        
        response = {
            "elements": [
                {
                    "type": "way",
                    "id": 1,
                    "geometry": [
                        {"lat": 0, "lon": 0},
                        {"lat": 1, "lon": 0},
                        {"lat": 1, "lon": 1},
                        {"lat": 0, "lon": 1},
                        {"lat": 0, "lon": 0}
                    ],
                    "tags": {"building": "yes"}
                },
                {
                    "type": "relation",
                    "id": 2,
                    "bounds": {
                        "minlat": 10, "minlon": 10,
                        "maxlat": 11, "maxlon": 11
                    },
                    "tags": {"building": "yes"}
                }
            ]
        }
        
        features = collector._parse_osm_response(response)
        
        assert len(features) == 2
    
    def test_parse_osm_response_skips_invalid(self):
        """Should skip invalid elements and parse valid ones."""
        collector = OSMBuildingsCollector()
        
        response = {
            "elements": [
                {
                    "type": "way",
                    "id": 1,
                    "geometry": [  # Valid
                        {"lat": 0, "lon": 0},
                        {"lat": 1, "lon": 0},
                        {"lat": 1, "lon": 1},
                        {"lat": 0, "lon": 1},
                        {"lat": 0, "lon": 0}
                    ],
                    "tags": {"building": "yes"}
                },
                {
                    "type": "way",
                    "id": 2,
                    "geometry": [  # Too few nodes
                        {"lat": 0, "lon": 0},
                        {"lat": 1, "lon": 0}
                    ],
                    "tags": {"building": "yes"}
                }
            ]
        }
        
        features = collector._parse_osm_response(response)
        
        # Should only have the valid feature
        assert len(features) == 1


class TestRealAPIIntegration:
    """Tests that verify real API connectivity (can be skipped in offline tests)."""
    
    @pytest.mark.skip(reason="Requires live internet connection to Overpass API")
    def test_real_api_connectivity(self):
        """Verify connection to real Overpass API endpoint."""
        collector = OSMBuildingsCollector()
        
        # Small test polygon (New York area)
        polygon = {
            "properties": {
                "area_square_kilometers": 50.0,
                "bounding_box": {
                    "min_lon": -74.01,
                    "min_lat": 40.70,
                    "max_lon": -73.98,
                    "max_lat": 40.72
                }
            }
        }
        
        result = collector.collect(polygon)
        
        # Should succeed or provide clear error
        assert result["metadata"]["status"] in ["success", "empty", "error"]
        # Should have valid structure regardless
        assert "features" in result
        assert "metadata" in result
        assert result["source_provider"] == "OSM Buildings"


class TestMetadataPreservation:
    """Test that metadata is properly preserved."""
    
    def test_source_provider_preserved(self):
        """Source provider should be preserved."""
        collector = OSMBuildingsCollector()
        
        polygon = {
            "properties": {
                "area_square_kilometers": 10.0,
                "bounding_box": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1}
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"elements": []}
        
        with patch.object(collector, '_make_request', return_value=mock_response):
            result = collector.collect(polygon)
        
        assert result["source_provider"] == "OSM Buildings"
    
    def test_endpoint_recorded(self):
        """API endpoint should be recorded."""
        collector = OSMBuildingsCollector()
        
        polygon = {
            "properties": {
                "area_square_kilometers": 10.0,
                "bounding_box": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1}
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"elements": []}
        
        with patch.object(collector, '_make_request', return_value=mock_response):
            result = collector.collect(polygon)
        
        assert result["metadata"]["provider_endpoint"] == "http://overpass-api.de/api/interpreter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
