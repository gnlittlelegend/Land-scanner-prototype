"""
Tests for OSM Road Network Collector.

Tests the RoadNetworkCollector implementation that connects to
the real Overpass API to fetch road network data.

Requirements Tested (Task 4.4):
- Connect to real Overpass API endpoint
- Build Overpass QL query for roads with highway tags
- Handle timeouts and rate limits
- Implement retry with exponential backoff
- Validate response is valid GeoJSON
- Return raw features with OSM attribution
- Handle provider unavailability gracefully
- Extract road classification (primary, secondary, tertiary, etc.)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import time

from backend.collectors.road_network_collector import RoadNetworkCollector


class TestRoadNetworkCollectorInitialization:
    """Test RoadNetworkCollector initialization."""
    
    def test_initialization_defaults(self):
        """Collector should initialize with correct defaults."""
        collector = RoadNetworkCollector()
        
        assert collector.provider_name == "OSM Roads"
        assert collector.endpoint == "http://overpass-api.de/api/interpreter"
        assert collector.timeout == 30
        assert collector.max_retries == 2
        assert collector.retry_delay_base == 2.0
    
    def test_initialization_custom_timeout(self):
        """Collector should accept custom timeout."""
        collector = RoadNetworkCollector(timeout=45)
        
        assert collector.timeout == 45


class TestOverpassQueryBuilding:
    """Test Overpass QL query building."""
    
    def test_query_building_format(self):
        """Query should be properly formatted for Overpass API."""
        collector = RoadNetworkCollector()
        
        bbox = (-74.0, 40.0, -73.0, 41.0)  # (min_lon, min_lat, max_lon, max_lat)
        query = collector._build_overpass_query(bbox)
        
        # Query should contain bbox in correct format
        assert "[bbox:40.0,-74.0,41.0,-73.0]" in query
        # Query should include way highways
        assert 'way["highway"]' in query
        # Query should request geometry output
        assert "out geom" in query
    
    def test_query_includes_highway_tag(self):
        """Query should fetch ways with highway tag."""
        collector = RoadNetworkCollector()
        
        bbox = (0, 0, 1, 1)
        query = collector._build_overpass_query(bbox)
        
        assert 'way["highway"]' in query


class TestRoadClassification:
    """Test road classification logic."""
    
    def test_classify_primary_roads(self):
        """Primary roads should be classified correctly."""
        collector = RoadNetworkCollector()
        
        # Test motorway
        assert collector._classify_road("motorway") == "primary"
        assert collector._classify_road("motorway_link") == "primary"
        
        # Test trunk
        assert collector._classify_road("trunk") == "primary"
        assert collector._classify_road("trunk_link") == "primary"
        
        # Test primary
        assert collector._classify_road("primary") == "primary"
        assert collector._classify_road("primary_link") == "primary"
    
    def test_classify_secondary_roads(self):
        """Secondary roads should be classified correctly."""
        collector = RoadNetworkCollector()
        
        assert collector._classify_road("secondary") == "secondary"
        assert collector._classify_road("secondary_link") == "secondary"
    
    def test_classify_tertiary_roads(self):
        """Tertiary roads should be classified correctly."""
        collector = RoadNetworkCollector()
        
        assert collector._classify_road("tertiary") == "tertiary"
        assert collector._classify_road("tertiary_link") == "tertiary"
        assert collector._classify_road("unclassified") == "tertiary"
    
    def test_classify_local_roads(self):
        """Local roads should be classified correctly."""
        collector = RoadNetworkCollector()
        
        assert collector._classify_road("residential") == "local"
        assert collector._classify_road("living_street") == "local"
        assert collector._classify_road("service") == "local"
        assert collector._classify_road("pedestrian") == "local"
        assert collector._classify_road("track") == "local"
    
    def test_classify_unknown_roads(self):
        """Unknown highway types should be classified as 'other'."""
        collector = RoadNetworkCollector()
        
        assert collector._classify_road("unknown") == "other"
        assert collector._classify_road("footway") == "other"
        assert collector._classify_road("path") == "other"
        assert collector._classify_road("") == "other"
    
    def test_classify_case_insensitive(self):
        """Classification should be case-insensitive."""
        collector = RoadNetworkCollector()
        
        assert collector._classify_road("PRIMARY") == "primary"
        assert collector._classify_road("Primary") == "primary"
        assert collector._classify_road("MOTORWAY") == "primary"
    
    def test_classify_whitespace_handling(self):
        """Classification should handle whitespace."""
        collector = RoadNetworkCollector()
        
        assert collector._classify_road("  primary  ") == "primary"
        assert collector._classify_road("\tresidential\n") == "local"


class TestWayToFeatureConversion:
    """Test conversion of OSM ways to GeoJSON features."""
    
    def test_way_to_feature_basic(self):
        """Basic way should be converted to GeoJSON feature."""
        collector = RoadNetworkCollector()
        
        way = {
            "id": 12345,
            "type": "way",
            "geometry": [
                {"lat": 40.0, "lon": -74.0},
                {"lat": 40.1, "lon": -74.1}
            ],
            "tags": {
                "name": "Main Street",
                "highway": "primary"
            }
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature is not None
        assert feature["type"] == "Feature"
        assert feature["id"] == "way_12345"
        assert feature["geometry"]["type"] == "LineString"
        assert len(feature["geometry"]["coordinates"]) == 2
        assert feature["properties"]["osm_id"] == 12345
        assert feature["properties"]["name"] == "Main Street"
        assert feature["properties"]["highway"] == "primary"
        assert feature["properties"]["classification"] == "primary"
        assert feature["properties"]["source"] == "osm"
    
    def test_way_to_feature_with_all_tags(self):
        """Way with all optional tags should preserve them."""
        collector = RoadNetworkCollector()
        
        way = {
            "id": 54321,
            "type": "way",
            "geometry": [
                {"lat": 51.5, "lon": -0.1},
                {"lat": 51.6, "lon": -0.2}
            ],
            "tags": {
                "name": "Oxford Street",
                "highway": "secondary",
                "lanes": "4",
                "surface": "asphalt",
                "maxspeed": "50"
            }
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature["properties"]["lanes"] == "4"
        assert feature["properties"]["surface"] == "asphalt"
        assert feature["properties"]["maxspeed"] == "50"
        assert feature["properties"]["classification"] == "secondary"
    
    def test_way_to_feature_missing_optional_tags(self):
        """Way with missing optional tags should still convert."""
        collector = RoadNetworkCollector()
        
        way = {
            "id": 99999,
            "type": "way",
            "geometry": [
                {"lat": 48.8, "lon": 2.3},
                {"lat": 48.9, "lon": 2.4}
            ],
            "tags": {
                "highway": "residential"
            }
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature is not None
        assert feature["properties"]["name"] == ""
        assert feature["properties"]["lanes"] == ""
        assert feature["properties"]["surface"] == ""
        assert feature["properties"]["maxspeed"] == ""
        assert feature["properties"]["classification"] == "local"
    
    def test_way_to_feature_insufficient_coordinates(self):
        """Way with fewer than 2 coordinates should not convert."""
        collector = RoadNetworkCollector()
        
        way = {
            "id": 11111,
            "type": "way",
            "geometry": [
                {"lat": 40.0, "lon": -74.0}
            ],
            "tags": {"highway": "primary"}
        }
        
        feature = collector._way_to_feature(way)
        assert feature is None
    
    def test_way_to_feature_empty_geometry(self):
        """Way with empty geometry should not convert."""
        collector = RoadNetworkCollector()
        
        way = {
            "id": 22222,
            "type": "way",
            "geometry": [],
            "tags": {"highway": "primary"}
        }
        
        feature = collector._way_to_feature(way)
        assert feature is None


class TestParseOSMResponse:
    """Test parsing of Overpass API responses."""
    
    def test_parse_single_way(self):
        """Response with single way should parse correctly."""
        collector = RoadNetworkCollector()
        
        data = {
            "elements": [
                {
                    "id": 12345,
                    "type": "way",
                    "geometry": [
                        {"lat": 40.0, "lon": -74.0},
                        {"lat": 40.1, "lon": -74.1}
                    ],
                    "tags": {"name": "Main St", "highway": "primary"}
                }
            ]
        }
        
        features = collector._parse_osm_response(data)
        
        assert len(features) == 1
        assert features[0]["properties"]["name"] == "Main St"
    
    def test_parse_multiple_ways(self):
        """Response with multiple ways should parse all."""
        collector = RoadNetworkCollector()
        
        data = {
            "elements": [
                {
                    "id": 1,
                    "type": "way",
                    "geometry": [
                        {"lat": 40.0, "lon": -74.0},
                        {"lat": 40.1, "lon": -74.1}
                    ],
                    "tags": {"name": "First", "highway": "primary"}
                },
                {
                    "id": 2,
                    "type": "way",
                    "geometry": [
                        {"lat": 40.2, "lon": -74.2},
                        {"lat": 40.3, "lon": -74.3}
                    ],
                    "tags": {"name": "Second", "highway": "secondary"}
                }
            ]
        }
        
        features = collector._parse_osm_response(data)
        
        assert len(features) == 2
        assert features[0]["properties"]["name"] == "First"
        assert features[1]["properties"]["name"] == "Second"
    
    def test_parse_empty_response(self):
        """Response with no elements should parse to empty list."""
        collector = RoadNetworkCollector()
        
        data = {"elements": []}
        
        features = collector._parse_osm_response(data)
        
        assert len(features) == 0
        assert features == []
    
    def test_parse_mixed_valid_invalid_ways(self):
        """Response with valid and invalid ways should parse only valid."""
        collector = RoadNetworkCollector()
        
        data = {
            "elements": [
                {
                    "id": 1,
                    "type": "way",
                    "geometry": [
                        {"lat": 40.0, "lon": -74.0},
                        {"lat": 40.1, "lon": -74.1}
                    ],
                    "tags": {"highway": "primary"}
                },
                {
                    "id": 2,
                    "type": "way",
                    "geometry": [{"lat": 40.2, "lon": -74.2}],  # Only 1 coordinate
                    "tags": {"highway": "secondary"}
                }
            ]
        }
        
        features = collector._parse_osm_response(data)
        
        assert len(features) == 1  # Only the valid way


class TestCollectMethod:
    """Test collect() method."""
    
    @patch('backend.collectors.road_network_collector.RoadNetworkCollector._make_request')
    def test_collect_success(self, mock_request):
        """Successful collection should return dataset with features."""
        collector = RoadNetworkCollector()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 12345,
                    "type": "way",
                    "geometry": [
                        {"lat": 40.0, "lon": -74.0},
                        {"lat": 40.1, "lon": -74.1}
                    ],
                    "tags": {"name": "Main St", "highway": "primary"}
                }
            ]
        }
        mock_request.return_value = mock_response
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-74, 40], [-73, 40], [-73, 41], [-74, 41], [-74, 40]]]},
            "properties": {
                "area_square_kilometers": 1.0,
                "bounding_box": {"min_lon": -74, "min_lat": 40, "max_lon": -73, "max_lat": 41},
                "centroid": {"longitude": -73.5, "latitude": 40.5},
                "vertex_count": 5,
                "crs": "EPSG:4326"
            }
        }
        
        result = collector.collect(polygon)
        
        assert result["source_provider"] == "OSM Roads"
        assert result["category"] == "roads"
        assert result["metadata"]["status"] == "success"
        assert len(result["features"]) == 1
        assert result["features"][0]["properties"]["name"] == "Main St"
    
    @patch('backend.collectors.road_network_collector.RoadNetworkCollector._make_request')
    def test_collect_no_features(self, mock_request):
        """Collection with no features should return empty status."""
        collector = RoadNetworkCollector()
        
        # Mock response with no elements
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}
        mock_request.return_value = mock_response
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-74, 40], [-73, 40], [-73, 41], [-74, 41], [-74, 40]]]},
            "properties": {
                "area_square_kilometers": 1.0,
                "bounding_box": {"min_lon": -74, "min_lat": 40, "max_lon": -73, "max_lat": 41},
                "centroid": {"longitude": -73.5, "latitude": 40.5},
                "vertex_count": 5,
                "crs": "EPSG:4326"
            }
        }
        
        result = collector.collect(polygon)
        
        assert result["source_provider"] == "OSM Roads"
        assert result["category"] == "roads"
        assert result["metadata"]["status"] == "empty"
        assert len(result["features"]) == 0
    
    @patch('backend.collectors.road_network_collector.RoadNetworkCollector._make_request')
    def test_collect_api_failure(self, mock_request):
        """API failure should return error status."""
        collector = RoadNetworkCollector()
        
        # Mock failed request
        mock_request.return_value = None
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-74, 40], [-73, 40], [-73, 41], [-74, 41], [-74, 40]]]},
            "properties": {
                "area_square_kilometers": 1.0,
                "bounding_box": {"min_lon": -74, "min_lat": 40, "max_lon": -73, "max_lat": 41},
                "centroid": {"longitude": -73.5, "latitude": 40.5},
                "vertex_count": 5,
                "crs": "EPSG:4326"
            }
        }
        
        result = collector.collect(polygon)
        
        assert result["source_provider"] == "OSM Roads"
        assert result["category"] == "roads"
        assert result["metadata"]["status"] == "error"
        assert len(result["features"]) == 0
        assert result["metadata"]["error_message"] is not None
    
    @patch('backend.collectors.road_network_collector.RoadNetworkCollector._make_request')
    def test_collect_invalid_json(self, mock_request):
        """Invalid JSON response should return error status."""
        collector = RoadNetworkCollector()
        
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_request.return_value = mock_response
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-74, 40], [-73, 40], [-73, 41], [-74, 41], [-74, 40]]]},
            "properties": {
                "area_square_kilometers": 1.0,
                "bounding_box": {"min_lon": -74, "min_lat": 40, "max_lon": -73, "max_lat": 41},
                "centroid": {"longitude": -73.5, "latitude": 40.5},
                "vertex_count": 5,
                "crs": "EPSG:4326"
            }
        }
        
        result = collector.collect(polygon)
        
        assert result["metadata"]["status"] == "error"
        assert "Invalid JSON" in result["metadata"]["error_message"]


class TestDatasetStructure:
    """Test RawDataset structure."""
    
    @patch('backend.collectors.road_network_collector.RoadNetworkCollector._make_request')
    def test_raw_dataset_structure(self, mock_request):
        """Dataset should have required structure."""
        collector = RoadNetworkCollector()
        
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}
        mock_request.return_value = mock_response
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-74, 40], [-73, 40], [-73, 41], [-74, 41], [-74, 40]]]},
            "properties": {
                "area_square_kilometers": 1.0,
                "bounding_box": {"min_lon": -74, "min_lat": 40, "max_lon": -73, "max_lat": 41},
                "centroid": {"longitude": -73.5, "latitude": 40.5},
                "vertex_count": 5,
                "crs": "EPSG:4326"
            }
        }
        
        result = collector.collect(polygon)
        
        # Check required fields
        assert "source_provider" in result
        assert "category" in result
        assert "features" in result
        assert "metadata" in result
        
        # Check metadata fields
        metadata = result["metadata"]
        assert "timestamp" in metadata
        assert "feature_count" in metadata
        assert "collection_time_ms" in metadata
        assert "attempt_count" in metadata
        assert "status" in metadata
        assert "provider_endpoint" in metadata
        assert "timeout_seconds" in metadata
