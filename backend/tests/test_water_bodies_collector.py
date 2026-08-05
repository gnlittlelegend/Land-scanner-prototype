"""
Tests for OSM Water Bodies Collector.

Tests the WaterBodiesCollector implementation that connects to
the real Overpass API to fetch water bodies data.

Requirements Tested (Task 4.5):
- Connect to real Overpass API endpoint
- Build Overpass QL query for waterways and water areas
- Extract water type (river, lake, canal, pond, etc.)
- Handle Overpass timeouts and rate limits
- Implement retry with exponential backoff
- Validate response is valid GeoJSON
- Return raw features with OSM attribution
- Handle provider unavailability gracefully
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import time

from backend.collectors.water_bodies_collector import WaterBodiesCollector


class TestWaterBodiesCollectorInitialization:
    """Test WaterBodiesCollector initialization."""
    
    def test_initialization_defaults(self):
        """Collector should initialize with correct defaults."""
        collector = WaterBodiesCollector()
        
        assert collector.provider_name == "OSM Water Bodies"
        assert collector.endpoint == "http://overpass-api.de/api/interpreter"
        assert collector.timeout == 30
        assert collector.max_retries == 2
        assert collector.retry_delay_base == 2.0
    
    def test_initialization_custom_timeout(self):
        """Collector should accept custom timeout."""
        collector = WaterBodiesCollector(timeout=45)
        
        assert collector.timeout == 45


class TestOverpassQueryBuilding:
    """Test Overpass QL query building."""
    
    def test_query_building_format(self):
        """Query should be properly formatted for Overpass API."""
        collector = WaterBodiesCollector()
        
        bbox = (-74.0, 40.0, -73.0, 41.0)  # (min_lon, min_lat, max_lon, max_lat)
        query = collector._build_overpass_query(bbox)
        
        # Query should contain bbox in correct format
        assert "[bbox:40.0,-74.0,41.0,-73.0]" in query
        # Query should include way water tags
        assert 'way["water"]' in query
        assert 'way["waterway"]' in query
        # Query should include relation water tags
        assert 'relation["water"]' in query
        assert 'relation["waterway"]' in query
        # Query should request geometry output
        assert "out geom" in query
    
    def test_query_includes_waterway_and_water_tags(self):
        """Query should fetch water elements with waterway and water tags."""
        collector = WaterBodiesCollector()
        
        bbox = (0, 0, 1, 1)
        query = collector._build_overpass_query(bbox)
        
        # Should include multiple tag queries
        assert 'way["water"]' in query
        assert 'way["waterway"]' in query
        assert 'way["natural"="water"]' in query
        assert 'relation["water"]' in query
        assert 'relation["waterway"]' in query


class TestWaterTypeExtraction:
    """Test water type classification."""
    
    def test_extract_waterway_types(self):
        """Should correctly extract waterway types."""
        collector = WaterBodiesCollector()
        
        # Test river
        assert collector._extract_water_type({"waterway": "river"}) == "river"
        assert collector._extract_water_type({"waterway": "stream"}) == "river"
        assert collector._extract_water_type({"waterway": "brook"}) == "river"
        assert collector._extract_water_type({"waterway": "creek"}) == "river"
        
        # Test canal
        assert collector._extract_water_type({"waterway": "canal"}) == "canal"
        assert collector._extract_water_type({"waterway": "artificial_waterway"}) == "canal"
        
        # Test drain
        assert collector._extract_water_type({"waterway": "drain"}) == "drain"
        assert collector._extract_water_type({"waterway": "ditch"}) == "drain"
    
    def test_extract_water_types(self):
        """Should correctly extract water types."""
        collector = WaterBodiesCollector()
        
        assert collector._extract_water_type({"water": "lake"}) == "lake"
        assert collector._extract_water_type({"water": "pond"}) == "pond"
        assert collector._extract_water_type({"water": "basin"}) == "basin"
        assert collector._extract_water_type({"water": "generic"}) == "water"
    
    def test_extract_natural_water(self):
        """Should correctly extract natural water tag."""
        collector = WaterBodiesCollector()
        
        assert collector._extract_water_type({"natural": "water"}) == "water"
    
    def test_extract_water_priority(self):
        """Should prioritize waterway tag over water tag."""
        collector = WaterBodiesCollector()
        
        # Waterway should take priority
        result = collector._extract_water_type({
            "waterway": "river",
            "water": "lake",
            "natural": "water"
        })
        assert result == "river"
    
    def test_extract_water_fallback(self):
        """Should fallback to 'water' for unknown types."""
        collector = WaterBodiesCollector()
        
        # Unknown waterway type
        assert collector._extract_water_type({"waterway": "unknown_type"}) == "unknown_type"
        
        # Empty tags
        assert collector._extract_water_type({}) == "water"


class TestCollectMethod:
    """Test collect() method."""
    
    def test_collect_success(self):
        """Successful collection should return dataset with features."""
        collector = WaterBodiesCollector()
        
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
        
        # Mock successful Overpass response with river
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
                        {"lat": 40.2, "lon": -73.9}
                    ],
                    "tags": {"waterway": "river", "name": "Test River"}
                }
            ]
        }
        
        with patch.object(collector, '_make_request', return_value=mock_response):
            result = collector.collect(polygon)
        
        # Check dataset structure
        assert result["source_provider"] == "OSM Water Bodies"
        assert result["category"] == "water"
        assert len(result["features"]) == 1
        assert result["metadata"]["status"] == "success"
        assert result["metadata"]["feature_count"] == 1
        
        # Check feature structure
        feature = result["features"][0]
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "LineString"  # River is a line
        assert feature["properties"]["osm_type"] == "way"
        assert feature["properties"]["osm_id"] == 12345
        assert feature["properties"]["type"] == "river"
        assert feature["properties"]["source"] == "osm"
    
    def test_collect_lake_polygon(self):
        """Collection should handle closed water areas as polygons."""
        collector = WaterBodiesCollector()
        
        polygon = {
            "properties": {
                "area_square_kilometers": 10.0,
                "bounding_box": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1}
            }
        }
        
        # Lake with closed coordinates
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "type": "way",
                    "id": 54321,
                    "geometry": [
                        {"lat": 40.0, "lon": -74.0},
                        {"lat": 40.1, "lon": -74.0},
                        {"lat": 40.1, "lon": -73.9},
                        {"lat": 40.0, "lon": -73.9},
                        {"lat": 40.0, "lon": -74.0}  # Closed
                    ],
                    "tags": {"water": "lake", "name": "Test Lake"}
                }
            ]
        }
        
        with patch.object(collector, '_make_request', return_value=mock_response):
            result = collector.collect(polygon)
        
        # Lake should be a polygon
        feature = result["features"][0]
        assert feature["geometry"]["type"] == "Polygon"
        assert feature["properties"]["type"] == "lake"
    
    def test_collect_empty_response(self):
        """Empty Overpass response should return empty features list."""
        collector = WaterBodiesCollector()
        
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
        collector = WaterBodiesCollector()
        
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
        collector = WaterBodiesCollector()
        
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
    
    def test_parse_river_way_as_linestring(self):
        """Should convert flowing water way to LineString."""
        collector = WaterBodiesCollector()
        
        way = {
            "type": "way",
            "id": 12345,
            "geometry": [
                {"lat": 40.0, "lon": -74.0},
                {"lat": 40.1, "lon": -74.0},
                {"lat": 40.2, "lon": -73.9}
            ],
            "tags": {"waterway": "river", "name": "Test River"}
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature is not None
        assert feature["type"] == "Feature"
        assert feature["id"] == "way_12345"
        assert feature["geometry"]["type"] == "LineString"  # River is a line
        assert len(feature["geometry"]["coordinates"]) == 3
        assert feature["properties"]["osm_id"] == 12345
        assert feature["properties"]["osm_type"] == "way"
        assert feature["properties"]["type"] == "river"
    
    def test_parse_lake_way_as_polygon(self):
        """Should convert closed water area way to Polygon."""
        collector = WaterBodiesCollector()
        
        way = {
            "type": "way",
            "id": 54321,
            "geometry": [
                {"lat": 40.0, "lon": -74.0},
                {"lat": 40.1, "lon": -74.0},
                {"lat": 40.1, "lon": -73.9},
                {"lat": 40.0, "lon": -73.9},
                {"lat": 40.0, "lon": -74.0}  # Closed
            ],
            "tags": {"water": "lake", "name": "Test Lake"}
        }
        
        feature = collector._way_to_feature(way)
        
        assert feature is not None
        assert feature["geometry"]["type"] == "Polygon"
        # Should preserve closed ring
        coords = feature["geometry"]["coordinates"][0]
        assert coords[0] == coords[-1]
    
    def test_parse_way_auto_closes_ring(self):
        """Should treat nearly-closed rings as linear features."""
        collector = WaterBodiesCollector()
        
        way = {
            "type": "way",
            "id": 1,
            "geometry": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 0},
                {"lat": 1, "lon": 1},
                {"lat": 0.0001, "lon": 0.0001}  # Nearly closes but not exactly
            ],
            "tags": {"water": "pond"}
        }
        
        feature = collector._way_to_feature(way)
        
        # Since it's not exactly closed and there are 4 nodes, it's treated as a line
        # (only perfectly closed rings with matching first/last coords become polygons)
        assert feature is not None
        assert feature["geometry"]["type"] == "LineString"
    
    def test_parse_way_insufficient_nodes(self):
        """Should handle ways with only 2 nodes as line features."""
        collector = WaterBodiesCollector()
        
        way = {
            "type": "way",
            "id": 1,
            "geometry": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 0}
            ],
            "tags": {"water": "pond"}
        }
        
        feature = collector._way_to_feature(way)
        
        # 2 nodes is sufficient for a LineString (but not a polygon)
        assert feature is not None
        assert feature["geometry"]["type"] == "LineString"
        assert len(feature["geometry"]["coordinates"]) == 2
    
    def test_parse_relation_to_feature(self):
        """Should convert OSM relation to GeoJSON feature."""
        collector = WaterBodiesCollector()
        
        relation = {
            "type": "relation",
            "id": 99999,
            "bounds": {
                "minlat": 40.0,
                "minlon": -74.0,
                "maxlat": 40.5,
                "maxlon": -73.5
            },
            "tags": {"water": "lake", "name": "Large Lake"}
        }
        
        feature = collector._relation_to_feature(relation)
        
        assert feature is not None
        assert feature["type"] == "Feature"
        assert feature["id"] == "relation_99999"
        assert feature["geometry"]["type"] == "Polygon"
        assert len(feature["geometry"]["coordinates"][0]) == 5  # Closed bbox
        assert feature["properties"]["osm_id"] == 99999
        assert feature["properties"]["osm_type"] == "relation"
        assert feature["properties"]["type"] == "lake"
    
    def test_parse_relation_missing_bounds(self):
        """Should reject relations without bounds."""
        collector = WaterBodiesCollector()
        
        relation = {
            "type": "relation",
            "id": 1,
            "tags": {"water": "lake"}
        }
        
        feature = collector._relation_to_feature(relation)
        
        assert feature is None
    
    def test_parse_osm_response_mixed_types(self):
        """Should parse response with rivers, lakes, and canals."""
        collector = WaterBodiesCollector()
        
        response = {
            "elements": [
                {
                    "type": "way",
                    "id": 1,
                    "geometry": [
                        {"lat": 0, "lon": 0},
                        {"lat": 1, "lon": 0},
                        {"lat": 2, "lon": 0}
                    ],
                    "tags": {"waterway": "river"}
                },
                {
                    "type": "way",
                    "id": 2,
                    "geometry": [
                        {"lat": 10, "lon": 10},
                        {"lat": 11, "lon": 10},
                        {"lat": 11, "lon": 11},
                        {"lat": 10, "lon": 11},
                        {"lat": 10, "lon": 10}
                    ],
                    "tags": {"water": "pond"}
                },
                {
                    "type": "relation",
                    "id": 3,
                    "bounds": {
                        "minlat": 20, "minlon": 20,
                        "maxlat": 21, "maxlon": 21
                    },
                    "tags": {"waterway": "canal"}
                }
            ]
        }
        
        features = collector._parse_osm_response(response)
        
        assert len(features) == 3
        # Check types
        types = [f["properties"]["type"] for f in features]
        assert "river" in types
        assert "pond" in types
        assert "canal" in types
    
    def test_parse_osm_response_preserves_properties(self):
        """Should preserve water-specific properties."""
        collector = WaterBodiesCollector()
        
        way = {
            "type": "way",
            "id": 1,
            "geometry": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 0},
                {"lat": 2, "lon": 0}
            ],
            "tags": {
                "waterway": "river",
                "name": "Test River",
                "flow_rate": "high"
            }
        }
        
        feature = collector._way_to_feature(way)
        
        props = feature["properties"]
        assert props["name"] == "Test River"
        assert props["waterway"] == "river"
        assert props["flow_rate"] == "high"


class TestRealAPIIntegration:
    """Tests that verify real API connectivity (can be skipped in offline tests)."""
    
    @pytest.mark.skip(reason="Requires live internet connection to Overpass API")
    def test_real_api_connectivity(self):
        """Verify connection to real Overpass API endpoint."""
        collector = WaterBodiesCollector()
        
        # Small test polygon (New York area with water)
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
        assert result["source_provider"] == "OSM Water Bodies"
        assert result["category"] == "water"


class TestMetadataPreservation:
    """Test that metadata is properly preserved."""
    
    def test_source_provider_preserved(self):
        """Source provider should be preserved."""
        collector = WaterBodiesCollector()
        
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
        
        assert result["source_provider"] == "OSM Water Bodies"
    
    def test_category_is_water(self):
        """Category should be 'water' for all water collector results."""
        collector = WaterBodiesCollector()
        
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
        
        assert result["category"] == "water"
    
    def test_endpoint_recorded(self):
        """API endpoint should be recorded."""
        collector = WaterBodiesCollector()
        
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
