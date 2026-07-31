"""
Unit tests for individual data collectors.
Tests verify each collector can be instantiated and collects data successfully.
"""

import pytest
from unittest.mock import Mock, patch

from backend.models.schemas import Polygon, DataCategory
from backend.collectors.osm_buildings_collector import OSMBuildingsCollector
from backend.collectors.admin_boundaries_collector import AdminBoundariesCollector
from backend.collectors.land_cover_collector import LandCoverCollector
from backend.collectors.road_network_collector import RoadNetworkCollector
from backend.collectors.water_bodies_collector import WaterBodiesCollector
from backend.collectors.elevation_collector import ElevationCollector


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_polygon():
    """Create a sample valid polygon for testing."""
    return Polygon(
        geojson={
            "type": "Polygon",
            "coordinates": [[
                [-73.935242, 40.730610],
                [-73.935242, 40.730810],
                [-73.935042, 40.730810],
                [-73.935042, 40.730610],
                [-73.935242, 40.730610]
            ]]
        },
        geometry=None,
        area_sqkm=0.0,
        bounding_box=(-73.935242, 40.730610, -73.935042, 40.730810),
        centroid=(-73.935142, 40.730710),
        crs="EPSG:4326",
        is_valid=True
    )


# ============================================================================
# Collector Instantiation Tests
# ============================================================================

def test_osm_buildings_collector_instantiation():
    """Test OSM Buildings collector can be instantiated."""
    collector = OSMBuildingsCollector(timeout_seconds=30)
    
    assert collector.provider_name == "osm_buildings"
    assert collector.category == DataCategory.BUILDINGS
    assert collector.timeout_seconds == 30


def test_admin_boundaries_collector_instantiation():
    """Test Admin Boundaries collector can be instantiated."""
    collector = AdminBoundariesCollector(timeout_seconds=30)
    
    assert collector.provider_name == "admin_boundaries"
    assert collector.category == DataCategory.ADMIN
    assert collector.timeout_seconds == 30


def test_land_cover_collector_instantiation():
    """Test Land Cover collector can be instantiated."""
    collector = LandCoverCollector(timeout_seconds=30)
    
    assert collector.provider_name == "land_cover"
    assert collector.category == DataCategory.LAND_COVER
    assert collector.timeout_seconds == 30


def test_road_network_collector_instantiation():
    """Test Road Network collector can be instantiated."""
    collector = RoadNetworkCollector(timeout_seconds=30)
    
    assert collector.provider_name == "road_network"
    assert collector.category == DataCategory.ROADS
    assert collector.timeout_seconds == 30


def test_water_bodies_collector_instantiation():
    """Test Water Bodies collector can be instantiated."""
    collector = WaterBodiesCollector(timeout_seconds=30)
    
    assert collector.provider_name == "water_bodies"
    assert collector.category == DataCategory.WATER
    assert collector.timeout_seconds == 30


def test_elevation_collector_instantiation():
    """Test Elevation collector can be instantiated."""
    collector = ElevationCollector(timeout_seconds=30)
    
    assert collector.provider_name == "elevation"
    assert collector.category == DataCategory.ELEVATION
    assert collector.timeout_seconds == 30


# ============================================================================
# Land Cover Collector Tests (Synthetic Data)
# ============================================================================

def test_land_cover_collector_collect(sample_polygon):
    """Test Land Cover collector can collect data."""
    collector = LandCoverCollector()
    dataset = collector.collect(sample_polygon)
    
    assert dataset is not None
    assert dataset.source_provider == "land_cover"
    assert dataset.category == DataCategory.LAND_COVER
    assert len(dataset.features) > 0
    assert all("geometry" in f for f in dataset.features)
    assert all("properties" in f for f in dataset.features)


def test_land_cover_features_have_required_fields(sample_polygon):
    """Test Land Cover features have required fields."""
    collector = LandCoverCollector()
    dataset = collector.collect(sample_polygon)
    
    for feature in dataset.features:
        props = feature["properties"]
        assert "lc_code" in props
        assert "lc_class" in props
        assert "confidence" in props
        assert "source" in props
        assert "year" in props


# ============================================================================
# Elevation Collector Tests (Synthetic Data)
# ============================================================================

def test_elevation_collector_collect(sample_polygon):
    """Test Elevation collector can collect data."""
    collector = ElevationCollector()
    dataset = collector.collect(sample_polygon)
    
    assert dataset is not None
    assert dataset.source_provider == "elevation"
    assert dataset.category == DataCategory.ELEVATION
    assert len(dataset.features) > 0
    assert all("geometry" in f for f in dataset.features)
    assert all("properties" in f for f in dataset.features)


def test_elevation_features_have_required_fields(sample_polygon):
    """Test Elevation features have required fields."""
    collector = ElevationCollector()
    dataset = collector.collect(sample_polygon)
    
    for feature in dataset.features:
        assert feature["geometry"]["type"] == "Point"
        props = feature["properties"]
        assert "elevation_m" in props
        assert "source" in props
        assert "confidence" in props


# ============================================================================
# OSM Buildings Collector Tests (with mocking)
# ============================================================================

@patch('backend.collectors.osm_buildings_collector.requests.post')
def test_osm_buildings_collector_bbox_format(mock_post, sample_polygon):
    """Test OSM Buildings collector creates correct bbox format."""
    # Mock successful API response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"elements": []}
    
    collector = OSMBuildingsCollector()
    dataset = collector.collect(sample_polygon)
    
    # Verify the request was made
    assert mock_post.called
    call_data = mock_post.call_args[1]["data"]
    
    # Bbox should be in the query (south,west,north,east format)
    assert "[bbox:" in call_data
    assert "]" in call_data


@patch('backend.collectors.osm_buildings_collector.requests.post')
def test_osm_buildings_collector_error_handling(mock_post, sample_polygon):
    """Test OSM Buildings collector handles API errors."""
    from backend.collectors.base_collector import DataCollectorError
    
    # Mock failed API response
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = "Internal Server Error"
    
    collector = OSMBuildingsCollector()
    
    with pytest.raises(DataCollectorError):
        collector.collect(sample_polygon)


# ============================================================================
# Admin Boundaries Collector Tests (with mocking)
# ============================================================================

@patch('backend.collectors.admin_boundaries_collector.requests.post')
def test_admin_boundaries_collector_success(mock_post, sample_polygon):
    """Test Admin Boundaries collector with successful response."""
    # Mock successful API response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"elements": []}
    
    collector = AdminBoundariesCollector()
    dataset = collector.collect(sample_polygon)
    
    assert dataset is not None
    assert dataset.source_provider == "admin_boundaries"
    assert dataset.category == DataCategory.ADMIN


# ============================================================================
# Road Network Collector Tests (with mocking)
# ============================================================================

@patch('backend.collectors.road_network_collector.requests.post')
def test_road_network_collector_success(mock_post, sample_polygon):
    """Test Road Network collector with successful response."""
    # Mock successful API response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"elements": []}
    
    collector = RoadNetworkCollector()
    dataset = collector.collect(sample_polygon)
    
    assert dataset is not None
    assert dataset.source_provider == "road_network"
    assert dataset.category == DataCategory.ROADS


# ============================================================================
# Water Bodies Collector Tests (with mocking)
# ============================================================================

@patch('backend.collectors.water_bodies_collector.requests.post')
def test_water_bodies_collector_success(mock_post, sample_polygon):
    """Test Water Bodies collector with successful response."""
    # Mock successful API response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"elements": []}
    
    collector = WaterBodiesCollector()
    dataset = collector.collect(sample_polygon)
    
    assert dataset is not None
    assert dataset.source_provider == "water_bodies"
    assert dataset.category == DataCategory.WATER


# ============================================================================
# Timeout Tests
# ============================================================================

@patch('backend.collectors.osm_buildings_collector.requests.post')
def test_osm_buildings_collector_timeout(mock_post, sample_polygon):
    """Test OSM Buildings collector handles timeout."""
    from backend.collectors.base_collector import DataCollectorError
    import requests
    
    # Mock timeout
    mock_post.side_effect = requests.Timeout("Connection timeout")
    
    collector = OSMBuildingsCollector(timeout_seconds=5)
    
    with pytest.raises(DataCollectorError) as exc_info:
        collector.collect(sample_polygon)
    
    assert "timeout" in str(exc_info.value).lower()


# ============================================================================
# Metadata Tests
# ============================================================================

def test_collectors_include_metadata(sample_polygon):
    """Test all collectors include metadata in results."""
    collectors = [
        LandCoverCollector(),
        ElevationCollector()
    ]
    
    for collector in collectors:
        dataset = collector.collect(sample_polygon)
        
        assert "timestamp" in dataset.metadata
        assert "version" in dataset.metadata
        assert "crs" in dataset.metadata
        assert dataset.metadata["crs"] == "EPSG:4326"
