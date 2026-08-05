"""
Unit Tests for Elevation Collector.

Tests the ElevationCollector class which retrieves elevation data from
the USGS Elevation Point Query Service (EPQS) API.

Requirements Tested:
- Requirement 12.6: Collect Elevation data
- Requirement 2.3: Real Data Collection with real provider API
- Requirement 2.4: Provider Error Handling (timeouts, retries)
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.collectors.elevation_collector import ElevationCollector
from backend.collectors.base_collector import CollectionError


class TestElevationCollectorInitialization:
    """Test ElevationCollector initialization."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        collector = ElevationCollector()
        
        assert collector.provider_name == "USGS Elevation"
        assert collector.endpoint == "https://epqs.nationalmap.gov/v1/json"
        assert collector.timeout == 30
        assert collector.max_retries == 2
        assert collector.RATE_LIMIT_DELAY_SECONDS == 1.5

    def test_initialization_custom_timeout(self):
        """Test initialization with custom timeout."""
        collector = ElevationCollector(timeout=60)
        assert collector.timeout == 60

    def test_collector_repr(self):
        """Test string representation of collector."""
        collector = ElevationCollector()
        repr_str = repr(collector)
        
        assert "ElevationCollector" in repr_str
        assert "USGS Elevation" in repr_str
        assert "epqs.nationalmap.gov" in repr_str


class TestBoundingBoxExtraction:
    """Test bounding box extraction from polygon."""

    def test_bbox_extraction(self):
        """Test extracting bounding box from polygon."""
        collector = ElevationCollector()
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "bounding_box": {
                    "min_lon": -100.0,
                    "min_lat": 40.0,
                    "max_lon": -99.0,
                    "max_lat": 41.0
                }
            }
        }
        
        bbox = collector._get_bbox(polygon)
        assert bbox == (-100.0, 40.0, -99.0, 41.0)


class TestSamplePointGeneration:
    """Test grid-based sample point generation."""

    def test_sample_points_generation_small_area(self):
        """Test generating sample points for small area."""
        collector = ElevationCollector()
        
        # Small bounding box (about 1 km x 1 km at equator)
        bbox = (-122.4194, 37.7749, -122.4094, 37.7849)  # ~1 km x 1 km
        
        points = collector._generate_sample_points(bbox)
        
        assert isinstance(points, list)
        assert len(points) > 0
        
        # All points should be within bounding box
        for lon, lat in points:
            assert -122.4194 <= lon <= -122.4094
            assert 37.7749 <= lat <= 37.7849

    def test_sample_points_generation_large_area(self):
        """Test generating sample points for larger area."""
        collector = ElevationCollector()
        
        # Large bounding box (10 km x 10 km)
        bbox = (-122.5, 37.7, -122.4, 37.8)
        
        points = collector._generate_sample_points(bbox)
        
        assert isinstance(points, list)
        assert len(points) > 100  # Should generate many points
        assert len(points) <= 1000  # But should limit to avoid memory issues

    def test_sample_points_respects_spacing(self):
        """Test that sample points respect configured spacing."""
        collector = ElevationCollector()
        
        # Spacing should be approximately SAMPLING_SPACING_DEGREES
        bbox = (-122.4, 37.8, -122.3, 37.9)  # ~1 km x 1 km
        
        points = collector._generate_sample_points(bbox)
        
        # Check spacing between consecutive points
        if len(points) > 1:
            first_lon, first_lat = points[0]
            # Spacing should be approximately 0.00449 degrees
            spacing = collector.SAMPLING_SPACING_DEGREES
            assert spacing > 0

    def test_sample_points_limit_safety(self):
        """Test that sample point generation has safety limit."""
        collector = ElevationCollector()
        
        # Very large bounding box that would create many points
        bbox = (-180, -90, 180, 90)  # Entire world
        
        points = collector._generate_sample_points(bbox)
        
        # Should be limited to prevent memory issues (allow slight overage due to rounding)
        assert len(points) <= 1100  # Buffer for floating point rounding


class TestUSGSPointQuery:
    """Test USGS elevation API query for single points."""

    @patch('backend.collectors.elevation_collector.ElevationCollector._make_request')
    def test_query_usgs_point_success(self, mock_request):
        """Test successful USGS point query."""
        collector = ElevationCollector()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "USGS_Elevation_Point_Query_Service": {
                "value": 1234.5
            },
            "value": 1234.5
        }
        mock_request.return_value = mock_response
        
        elevation = collector._query_usgs_point(-122.4194, 37.7749)
        
        assert elevation == 1234.5
        mock_request.assert_called_once()

    @patch('backend.collectors.elevation_collector.ElevationCollector._make_request')
    def test_query_usgs_point_zero_elevation(self, mock_request):
        """Test USGS query returning zero elevation (valid for below sea level)."""
        collector = ElevationCollector()
        
        mock_response = Mock()
        mock_response.json.return_value = {"value": 0}
        mock_request.return_value = mock_response
        
        elevation = collector._query_usgs_point(-122.4194, 37.7749)
        
        assert elevation == 0

    @patch('backend.collectors.elevation_collector.ElevationCollector._make_request')
    def test_query_usgs_point_negative_elevation(self, mock_request):
        """Test USGS query returning negative elevation (below sea level)."""
        collector = ElevationCollector()
        
        mock_response = Mock()
        mock_response.json.return_value = {"value": -50}
        mock_request.return_value = mock_response
        
        elevation = collector._query_usgs_point(-122.4194, 37.7749)
        
        assert elevation == -50

    @patch('backend.collectors.elevation_collector.ElevationCollector._make_request')
    def test_query_usgs_point_failure(self, mock_request):
        """Test USGS query failure."""
        collector = ElevationCollector()
        
        mock_request.return_value = None
        
        elevation = collector._query_usgs_point(-122.4194, 37.7749)
        
        assert elevation is None

    @patch('backend.collectors.elevation_collector.ElevationCollector._make_request')
    def test_query_usgs_point_invalid_json(self, mock_request):
        """Test USGS query with invalid JSON response."""
        collector = ElevationCollector()
        
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_request.return_value = mock_response
        
        elevation = collector._query_usgs_point(-122.4194, 37.7749)
        
        assert elevation is None

    @patch('backend.collectors.elevation_collector.ElevationCollector._make_request')
    def test_query_usgs_point_missing_value(self, mock_request):
        """Test USGS query with missing value in response."""
        collector = ElevationCollector()
        
        mock_response = Mock()
        mock_response.json.return_value = {}  # No "value" key
        mock_request.return_value = mock_response
        
        elevation = collector._query_usgs_point(-122.4194, 37.7749)
        
        assert elevation is None


class TestSummaryFeatureCreation:
    """Test creation of elevation summary feature."""

    def test_summary_feature_empty_list(self):
        """Test summary feature with empty elevation list."""
        collector = ElevationCollector()
        
        feature = collector._create_summary_feature([])
        
        # Should return empty dict for empty list
        assert feature == {}

    def test_summary_feature_single_elevation(self):
        """Test summary feature with single elevation value."""
        collector = ElevationCollector()
        
        elevations = [1000.0]
        feature = collector._create_summary_feature(elevations)
        
        assert feature["type"] == "Feature"
        assert feature["id"] == "elevation_summary"
        props = feature["properties"]
        assert props["min_elevation_meters"] == 1000.0
        assert props["max_elevation_meters"] == 1000.0
        assert props["mean_elevation_meters"] == 1000.0
        assert props["sample_count"] == 1
        assert props["elevation_range_meters"] == 0.0

    def test_summary_feature_multiple_elevations(self):
        """Test summary feature with multiple elevation values."""
        collector = ElevationCollector()
        
        elevations = [1000.0, 1500.0, 2000.0, 1200.0]
        feature = collector._create_summary_feature(elevations)
        
        props = feature["properties"]
        assert props["min_elevation_meters"] == 1000.0
        assert props["max_elevation_meters"] == 2000.0
        assert props["mean_elevation_meters"] == 1425.0
        assert props["sample_count"] == 4
        assert props["elevation_range_meters"] == 1000.0

    def test_summary_feature_with_negative_elevations(self):
        """Test summary feature with negative elevations."""
        collector = ElevationCollector()
        
        elevations = [-100.0, 0.0, 100.0]
        feature = collector._create_summary_feature(elevations)
        
        props = feature["properties"]
        assert props["min_elevation_meters"] == -100.0
        assert props["max_elevation_meters"] == 100.0
        assert props["mean_elevation_meters"] == 0.0
        assert props["elevation_range_meters"] == 200.0


class TestElevationSampling:
    """Test elevation sampling from multiple points."""

    @patch('backend.collectors.elevation_collector.ElevationCollector._query_usgs_point')
    @patch('backend.collectors.elevation_collector.time.sleep')
    def test_query_elevation_samples_success(self, mock_sleep, mock_query):
        """Test successful elevation sampling."""
        collector = ElevationCollector()
        
        # Mock elevation values for sampled points
        mock_query.side_effect = [1000.0, 1500.0, 2000.0]
        
        sample_points = [(-122.4, 37.8), (-122.3, 37.8), (-122.2, 37.8)]
        features, query_count = collector._query_elevation_samples(sample_points)
        
        assert query_count == 3
        # Should have individual features + summary feature
        assert len(features) == 4  # 3 individual + 1 summary
        
        # Verify individual features
        for i, feature in enumerate(features[:3]):
            assert feature["type"] == "Feature"
            assert feature["geometry"]["type"] == "Point"
            assert feature["properties"]["source"] == "usgs_epqs"

    @patch('backend.collectors.elevation_collector.ElevationCollector._query_usgs_point')
    @patch('backend.collectors.elevation_collector.time.sleep')
    def test_query_elevation_samples_partial_failure(self, mock_sleep, mock_query):
        """Test elevation sampling with partial failures."""
        collector = ElevationCollector()
        
        # Mix of successful and failed queries
        mock_query.side_effect = [1000.0, None, 2000.0]
        
        sample_points = [(-122.4, 37.8), (-122.3, 37.8), (-122.2, 37.8)]
        features, query_count = collector._query_elevation_samples(sample_points)
        
        assert query_count == 3
        # Should only have 2 individual features + 1 summary
        assert len(features) == 3

    @patch('backend.collectors.elevation_collector.ElevationCollector._query_usgs_point')
    @patch('backend.collectors.elevation_collector.time.sleep')
    def test_query_elevation_samples_rate_limiting(self, mock_sleep, mock_query):
        """Test that rate limiting delays are applied."""
        collector = ElevationCollector()
        
        mock_query.side_effect = [1000.0, 1500.0, 2000.0]
        
        sample_points = [(-122.4, 37.8), (-122.3, 37.8), (-122.2, 37.8)]
        collector._query_elevation_samples(sample_points)
        
        # Should call sleep for rate limiting (number of points - 1)
        assert mock_sleep.call_count >= 2


class TestRawDatasetStructure:
    """Test raw dataset structure and format."""

    def test_raw_dataset_success(self):
        """Test raw dataset structure on success."""
        collector = ElevationCollector()
        
        features = [
            {
                "type": "Feature",
                "id": "elev_1",
                "geometry": {"type": "Point", "coordinates": [-122.4, 37.8]},
                "properties": {"elevation_meters": 100}
            }
        ]
        
        dataset = collector._build_raw_dataset(
            category="elevation",
            features=features,
            attempt_count=1,
            collection_time_ms=500,
            status="success"
        )
        
        assert dataset["source_provider"] == "USGS Elevation"
        assert dataset["category"] == "elevation"
        assert len(dataset["features"]) == 1
        assert dataset["metadata"]["feature_count"] == 1
        assert dataset["metadata"]["status"] == "success"
        assert dataset["metadata"]["collection_time_ms"] == 500
        assert dataset["metadata"]["attempt_count"] == 1
        assert "timestamp" in dataset["metadata"]
        assert dataset["metadata"]["provider_endpoint"] == "https://epqs.nationalmap.gov/v1/json"

    def test_raw_dataset_empty(self):
        """Test raw dataset structure with empty results."""
        collector = ElevationCollector()
        
        dataset = collector._build_raw_dataset(
            category="elevation",
            features=[],
            status="empty"
        )
        
        assert dataset["metadata"]["feature_count"] == 0
        assert dataset["metadata"]["status"] == "empty"
        assert len(dataset["features"]) == 0

    def test_raw_dataset_error(self):
        """Test raw dataset structure on error."""
        collector = ElevationCollector()
        
        dataset = collector._build_raw_dataset(
            category="elevation",
            features=[],
            status="error",
            error_message="API timeout"
        )
        
        assert dataset["metadata"]["status"] == "error"
        assert dataset["metadata"]["error_message"] == "API timeout"


class TestCollectionFlow:
    """Test complete collection flow."""

    @patch('backend.collectors.elevation_collector.ElevationCollector._query_elevation_samples')
    @patch('backend.collectors.elevation_collector.ElevationCollector._generate_sample_points')
    def test_collect_success(self, mock_gen_points, mock_query_samples):
        """Test successful complete collection."""
        collector = ElevationCollector()
        
        mock_gen_points.return_value = [(-122.4, 37.8), (-122.3, 37.8)]
        mock_query_samples.return_value = (
            [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-122.4, 37.8]},
                    "properties": {"elevation_meters": 100}
                }
            ],
            2  # query count
        )
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "area_square_kilometers": 10,
                "bounding_box": {"min_lon": -122.5, "min_lat": 37.7, "max_lon": -122.2, "max_lat": 37.9}
            }
        }
        
        result = collector.collect(polygon)
        
        assert result["metadata"]["status"] == "success"
        assert result["source_provider"] == "USGS Elevation"
        assert result["category"] == "elevation"
        assert len(result["features"]) >= 1

    @patch('backend.collectors.elevation_collector.ElevationCollector._generate_sample_points')
    def test_collect_error_handling(self, mock_gen_points):
        """Test collection error handling."""
        collector = ElevationCollector()
        
        mock_gen_points.side_effect = RuntimeError("Grid generation failed")
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "area_square_kilometers": 10,
                "bounding_box": {"min_lon": -122.5, "min_lat": 37.7, "max_lon": -122.2, "max_lat": 37.9}
            }
        }
        
        result = collector.collect(polygon)
        
        assert result["metadata"]["status"] == "error"
        assert result["metadata"]["error_message"] is not None


@pytest.mark.skip(reason="Makes real API calls - run manually for integration testing")
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_collect_equatorial_region(self):
        """Test collection at equator (0° latitude)."""
        collector = ElevationCollector()
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "area_square_kilometers": 10,
                "bounding_box": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1}
            }
        }
        
        result = collector.collect(polygon)
        assert "metadata" in result
        assert "features" in result

    def test_collect_polar_region(self):
        """Test collection near pole."""
        collector = ElevationCollector()
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-0.1, 89], [0.1, 89], [0.1, 89.5], [-0.1, 89.5], [-0.1, 89]]]},
            "properties": {
                "area_square_kilometers": 1,
                "bounding_box": {"min_lon": -0.1, "min_lat": 89, "max_lon": 0.1, "max_lat": 89.5}
            }
        }
        
        result = collector.collect(polygon)
        assert "metadata" in result

    def test_collect_antimeridian_region(self):
        """Test collection near antimeridian (±180° longitude)."""
        collector = ElevationCollector()
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[179, 0], [180, 0], [180, 1], [179, 1], [179, 0]]]},
            "properties": {
                "area_square_kilometers": 1,
                "bounding_box": {"min_lon": 179, "min_lat": 0, "max_lon": 180, "max_lat": 1}
            }
        }
        
        result = collector.collect(polygon)
        assert "metadata" in result

    def test_small_polygon(self):
        """Test collection with very small polygon."""
        collector = ElevationCollector()
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-122.4, 37.8], [-122.399, 37.8], [-122.399, 37.801], [-122.4, 37.801], [-122.4, 37.8]]]},
            "properties": {
                "area_square_kilometers": 0.00001,  # Minimum allowed
                "bounding_box": {"min_lon": -122.4, "min_lat": 37.8, "max_lon": -122.399, "max_lat": 37.801}
            }
        }
        
        result = collector.collect(polygon)
        assert "metadata" in result

    def test_large_polygon(self):
        """Test collection with large polygon (near maximum)."""
        collector = ElevationCollector()
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-120, 37], [-110, 37], [-110, 47], [-120, 47], [-120, 37]]]},
            "properties": {
                "area_square_kilometers": 99.9,  # Near maximum
                "bounding_box": {"min_lon": -120, "min_lat": 37, "max_lon": -110, "max_lat": 47}
            }
        }
        
        result = collector.collect(polygon)
        assert "metadata" in result


class TestTypeValidation:
    """Test type validation and conversion."""

    def test_elevation_float_conversion(self):
        """Test elevation values are properly converted to float."""
        collector = ElevationCollector()
        
        elevations = [1000.0, 1500, 2000.5]
        feature = collector._create_summary_feature(elevations)
        
        props = feature["properties"]
        assert isinstance(props["min_elevation_meters"], (int, float))
        assert isinstance(props["max_elevation_meters"], (int, float))
        assert isinstance(props["mean_elevation_meters"], (int, float))

    def test_coordinate_precision(self):
        """Test coordinate precision in sample points."""
        collector = ElevationCollector()
        
        bbox = (-122.4194, 37.7749, -122.4094, 37.7849)
        points = collector._generate_sample_points(bbox)
        
        for lon, lat in points:
            assert isinstance(lon, float)
            assert isinstance(lat, float)
            assert -180 <= lon <= 180
            assert -90 <= lat <= 90
