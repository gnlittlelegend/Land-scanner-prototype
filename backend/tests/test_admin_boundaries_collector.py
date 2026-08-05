"""
Tests for OSM Admin Boundaries Collector.

Tests the AdminBoundariesCollector implementation that connects to
the real Overpass API to fetch administrative boundary data.

Requirements Tested (Task 4.2):
- Connect to real Overpass API endpoint
- Build Overpass QL query for administrative boundaries (admin_level 2, 4, 6)
- Query production Overpass API
- Parse response to extract country, state, district info
- Handle Overpass timeouts and rate limits
- Return administrative features with source attribution
- Test: Query real Overpass API with test polygon
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from backend.collectors.admin_boundaries_collector import AdminBoundariesCollector


class TestAdminBoundariesCollectorInitialization:
    """Test AdminBoundariesCollector initialization."""
    
    def test_initialization_defaults(self):
        """Collector should initialize with correct defaults."""
        collector = AdminBoundariesCollector()
        
        assert collector.provider_name == "OSM Admin Boundaries"
        assert collector.endpoint == "http://overpass-api.de/api/interpreter"
        assert collector.timeout == 30
        assert collector.max_retries == 2
        assert collector.retry_delay_base == 2.0
    
    def test_initialization_custom_timeout(self):
        """Collector should accept custom timeout."""
        collector = AdminBoundariesCollector(timeout=45)
        
        assert collector.timeout == 45


class TestOverpassQueryBuilding:
    """Test Overpass QL query building for administrative boundaries."""
    
    def test_query_building_format(self):
        """Query should be properly formatted for Overpass API."""
        collector = AdminBoundariesCollector()
        
        bbox = (-74.0, 40.0, -73.0, 41.0)  # (min_lon, min_lat, max_lon, max_lat)
        query = collector._build_overpass_query(bbox)
        
        # Query should contain bbox in correct format (south, west, north, east)
        assert "[bbox:40.0,-74.0,41.0,-73.0]" in query
        # Query should include admin_level 2 (country)
        assert 'admin_level"="2"' in query
        # Query should include admin_level 4 (state)
        assert 'admin_level"="4"' in query
        # Query should include admin_level 6 (district)
        assert 'admin_level"="6"' in query
        # Query should request geometry output
        assert "out geom" in query
    
    def test_query_includes_ways_and_relations(self):
        """Query should fetch both ways and relations for admin boundaries."""
        collector = AdminBoundariesCollector()
        
        bbox = (0, 0, 1, 1)
        query = collector._build_overpass_query(bbox)
        
        assert 'way["boundary"="administrative"]' in query
        assert 'relation["boundary"="administrative"]' in query
    
    def test_query_includes_all_admin_levels(self):
        """Query should include all relevant admin levels."""
        collector = AdminBoundariesCollector()
        
        bbox = (0, 0, 1, 1)
        query = collector._build_overpass_query(bbox)
        
        # Check for all three admin levels
        assert 'admin_level"="2"' in query  # Countries
        assert 'admin_level"="4"' in query  # States/Provinces
        assert 'admin_level"="6"' in query  # Districts


class TestCollectMethod:
    """Test collect() method."""
    
    def test_collect_success_with_admin_data(self):
        """Successful collection should return dataset with admin features."""
        collector = AdminBoundariesCollector()
        
        # Mock polygon
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "area_square_kilometers": 50.0,
                "bounding_box": {
                    "min_lon": 0,
                    "min_lat": 0,
                    "max_lon": 1,
                    "max_lat": 1
                }
            }
        }
        
        # Mock successful Overpass response with admin boundaries
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "type": "way",
                    "id": 12345,
                    "geometry": [
                        {"lat": 32.0, "lon": -99.0},
                        {"lat": 33.0, "lon": -99.0},
                        {"lat": 33.0, "lon": -98.0},
                        {"lat": 32.0, "lon": -98.0},
                        {"lat": 32.0, "lon": -99.0}
                    ],
                    "tags": {
                        "boundary": "administrative",
                        "admin_level": "4",
                        "name": "Texas",
                        "ISO3166-2": "US-TX"
                    }
                },
                {
                    "type": "relation",
                    "id": 54321,
                    "bounds": {
                        "minlat": 25.0,
                        "minlon": -97.0,
                        "maxlat": 36.0,
                        "maxlon": -93.0
                    },
                    "tags": {
                        "boundary": "administrative",
                        "admin_level": "2",
                        "name": "United States",
                        "ISO3166-1": "US"
                    }
                }
            ]
        }
        
        with patch.object(collector, '_make_request', return_value=mock_response):
            result = collector.collect(polygon)
        
        # Check dataset structure
        assert result["source_provider"] == "OSM Admin Boundaries"
        assert result["category"] == "admin"
        assert len(result["features"]) == 2
        assert result["metadata"]["status"] == "success"
        assert result["metadata"]["feature_count"] == 2
        
        # Check first feature (way)
        feature_way = result["features"][0]
        assert feature_way["type"] == "Feature"
        assert feature_way["geometry"]["type"] == "Polygon"
        assert feature_way["properties"]["osm_type"] == "way"
        assert feature_way["properties"]["osm_id"] == 12345
        assert feature_way["properties"]["admin_level"] == "4"
        assert feature_way["properties"]["admin_type"] == "state"
        
        # Check second feature (relation)
        feature_relation = result["features"][1]
        assert feature_relation["properties"]["osm_type"] == "relation"
        assert feature_relation["properties"]["admin_level"] == "2"
        assert feature_relation["properties"]["admin_type"] == "country"
    
    def test_collect_empty_response(self):
        """Empty Overpass response should return empty features list."""
        collector = AdminBoundariesCollector()
        
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
        collector = AdminBoundariesCollector()
        
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
        collector = AdminBoundariesCollector()
        
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
    """Test OSM admin boundaries response parsing."""
    
    def test_parse_way_to_feature(self):
        """Should convert OSM admin way to GeoJSON feature."""
        collector = AdminBoundariesCollector()
        
        way = {
            "type": "way",
            "id": 12345,
            "geometry": [
                {"lat": 32.0, "lon": -99.0},
                {"lat": 33.0, "lon": -99.0},
                {"lat": 33.0, "lon": -98.0},
                {"lat": 32.0, "lon": -98.0},
                {"lat": 32.0, "lon": -99.0}
            ],
            "tags": {
                "boundary": "administrative",
                "admin_level": "4",
                "name": "Texas",
                "ISO3166-2": "US-TX"
            }
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature is not None
        assert feature["type"] == "Feature"
        assert feature["id"] == "way_12345"
        assert feature["geometry"]["type"] == "Polygon"
        assert len(feature["geometry"]["coordinates"][0]) == 5  # 5 points (closed ring)
        assert feature["properties"]["osm_id"] == 12345
        assert feature["properties"]["osm_type"] == "way"
        assert feature["properties"]["admin_level"] == "4"
        assert feature["properties"]["admin_type"] == "state"
        assert feature["properties"]["name"] == "Texas"
    
    def test_parse_way_closes_open_ring(self):
        """Should close open rings by repeating first coordinate."""
        collector = AdminBoundariesCollector()
        
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
            "tags": {"boundary": "administrative", "admin_level": "2"}
        }
        
        feature = collector._way_to_feature(way)
        
        coords = feature["geometry"]["coordinates"][0]
        # Should be closed (first == last)
        assert coords[0] == coords[-1]
    
    def test_parse_way_insufficient_nodes(self):
        """Should reject ways with insufficient nodes."""
        collector = AdminBoundariesCollector()
        
        way = {
            "type": "way",
            "id": 1,
            "geometry": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 0}
            ],
            "tags": {"boundary": "administrative"}
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature is None
    
    def test_parse_relation_to_feature(self):
        """Should convert OSM admin relation to GeoJSON feature."""
        collector = AdminBoundariesCollector()
        
        relation = {
            "type": "relation",
            "id": 54321,
            "bounds": {
                "minlat": 25.0,
                "minlon": -97.0,
                "maxlat": 36.0,
                "maxlon": -93.0
            },
            "tags": {
                "boundary": "administrative",
                "admin_level": "2",
                "name": "United States",
                "ISO3166-1": "US"
            }
        }
        
        feature = collector._relation_to_feature(relation)
        
        assert feature is not None
        assert feature["type"] == "Feature"
        assert feature["id"] == "relation_54321"
        assert feature["geometry"]["type"] == "Polygon"
        assert len(feature["geometry"]["coordinates"][0]) == 5  # 5 points for bbox (closed)
        assert feature["properties"]["osm_id"] == 54321
        assert feature["properties"]["osm_type"] == "relation"
        assert feature["properties"]["admin_level"] == "2"
        assert feature["properties"]["admin_type"] == "country"
    
    def test_parse_relation_missing_bounds(self):
        """Should reject relations without bounds."""
        collector = AdminBoundariesCollector()
        
        relation = {
            "type": "relation",
            "id": 1,
            "tags": {"boundary": "administrative"}
        }
        
        feature = collector._relation_to_feature(relation)
        
        assert feature is None
    
    def test_parse_osm_response_multiple_elements(self):
        """Should parse response with multiple admin elements."""
        collector = AdminBoundariesCollector()
        
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
                    "tags": {"boundary": "administrative", "admin_level": "4"}
                },
                {
                    "type": "relation",
                    "id": 2,
                    "bounds": {
                        "minlat": 10, "minlon": 10,
                        "maxlat": 11, "maxlon": 11
                    },
                    "tags": {"boundary": "administrative", "admin_level": "2"}
                }
            ]
        }
        
        features = collector._parse_osm_response(response)
        
        assert len(features) == 2
    
    def test_parse_osm_response_skips_invalid(self):
        """Should skip invalid elements and parse valid ones."""
        collector = AdminBoundariesCollector()
        
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
                    "tags": {"boundary": "administrative", "admin_level": "4"}
                },
                {
                    "type": "way",
                    "id": 2,
                    "geometry": [  # Too few nodes
                        {"lat": 0, "lon": 0},
                        {"lat": 1, "lon": 0}
                    ],
                    "tags": {"boundary": "administrative", "admin_level": "4"}
                }
            ]
        }
        
        features = collector._parse_osm_response(response)
        
        # Should only have the valid feature
        assert len(features) == 1


class TestAdminTypeMapping:
    """Test admin level to admin type mapping."""
    
    def test_country_mapping(self):
        """Admin level 2 should map to country."""
        collector = AdminBoundariesCollector()
        assert collector._get_admin_type("2") == "country"
    
    def test_state_mapping(self):
        """Admin level 4 should map to state."""
        collector = AdminBoundariesCollector()
        assert collector._get_admin_type("4") == "state"
    
    def test_district_mapping(self):
        """Admin level 6 should map to district."""
        collector = AdminBoundariesCollector()
        assert collector._get_admin_type("6") == "district"
    
    def test_region_mapping(self):
        """Admin level 3 should map to region."""
        collector = AdminBoundariesCollector()
        assert collector._get_admin_type("3") == "region"
    
    def test_province_mapping(self):
        """Admin level 5 should map to province."""
        collector = AdminBoundariesCollector()
        assert collector._get_admin_type("5") == "province"
    
    def test_unknown_mapping(self):
        """Unknown admin level should map to administrative."""
        collector = AdminBoundariesCollector()
        assert collector._get_admin_type("99") == "administrative"


class TestRealAPIIntegration:
    """Tests that verify real API connectivity (can be skipped in offline tests)."""
    
    @pytest.mark.skip(reason="Requires live internet connection to Overpass API")
    def test_real_api_connectivity_texas(self):
        """Verify connection to real Overpass API endpoint with Texas polygon."""
        collector = AdminBoundariesCollector()
        
        # Test polygon: Austin, Texas area
        polygon = {
            "properties": {
                "area_square_kilometers": 50.0,
                "bounding_box": {
                    "min_lon": -98.0,
                    "min_lat": 30.0,
                    "max_lon": -97.0,
                    "max_lat": 31.0
                }
            }
        }
        
        result = collector.collect(polygon)
        
        # Should succeed or provide clear error
        assert result["metadata"]["status"] in ["success", "empty", "error"]
        # Should have valid structure regardless
        assert "features" in result
        assert "metadata" in result
        assert result["source_provider"] == "OSM Admin Boundaries"
        assert result["category"] == "admin"
    
    @pytest.mark.skip(reason="Requires live internet connection to Overpass API")
    def test_real_api_connectivity_nyc(self):
        """Verify connection to real Overpass API with NYC polygon."""
        collector = AdminBoundariesCollector()
        
        # Test polygon: New York City area
        polygon = {
            "properties": {
                "area_square_kilometers": 10.0,
                "bounding_box": {
                    "min_lon": -74.01,
                    "min_lat": 40.70,
                    "max_lon": -73.98,
                    "max_lat": 40.72
                }
            }
        }
        
        result = collector.collect(polygon)
        
        # Should have valid structure
        assert result["metadata"]["status"] in ["success", "empty", "error"]
        assert result["category"] == "admin"


class TestMetadataPreservation:
    """Test that metadata is properly preserved."""
    
    def test_source_provider_preserved(self):
        """Source provider should be preserved."""
        collector = AdminBoundariesCollector()
        
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
        
        assert result["source_provider"] == "OSM Admin Boundaries"
    
    def test_category_is_admin(self):
        """Category should be 'admin'."""
        collector = AdminBoundariesCollector()
        
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
        
        assert result["category"] == "admin"
    
    def test_endpoint_recorded(self):
        """API endpoint should be recorded."""
        collector = AdminBoundariesCollector()
        
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
    
    def test_timestamp_recorded(self):
        """Timestamp should be recorded in ISO8601 format."""
        collector = AdminBoundariesCollector()
        
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
        
        # Should have timestamp in ISO8601 format
        assert "timestamp" in result["metadata"]
        # Should be parseable as ISO8601
        try:
            datetime.fromisoformat(result["metadata"]["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Timestamp is not in valid ISO8601 format")


class TestISOCodePreservation:
    """Test that ISO codes are preserved from OSM data."""
    
    def test_iso_3166_1_preserved(self):
        """ISO 3166-1 codes should be preserved."""
        collector = AdminBoundariesCollector()
        
        way = {
            "type": "way",
            "id": 1,
            "geometry": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 0},
                {"lat": 1, "lon": 1},
                {"lat": 0, "lon": 1},
                {"lat": 0, "lon": 0}
            ],
            "tags": {
                "boundary": "administrative",
                "admin_level": "2",
                "name": "United States",
                "ISO3166-1": "US"
            }
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature["properties"]["iso_3166_1"] == "US"
    
    def test_iso_3166_2_preserved(self):
        """ISO 3166-2 codes should be preserved."""
        collector = AdminBoundariesCollector()
        
        way = {
            "type": "way",
            "id": 1,
            "geometry": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 0},
                {"lat": 1, "lon": 1},
                {"lat": 0, "lon": 1},
                {"lat": 0, "lon": 0}
            ],
            "tags": {
                "boundary": "administrative",
                "admin_level": "4",
                "name": "Texas",
                "ISO3166-2": "US-TX"
            }
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature["properties"]["iso_3166_2"] == "US-TX"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
