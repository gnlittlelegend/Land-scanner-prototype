"""
Property-based tests for data collection infrastructure.
Tests verify that data collection is complete, independent, and handles failures gracefully.
"""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from backend.managers.data_source_manager import DataSourceManager
from backend.collectors.base_collector import DataCollector, DataCollectorError
from backend.models.schemas import (
    Polygon, RawDataset, DataCategory, Feature
)
from backend.services.config_manager import ConfigManager


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


@pytest.fixture
def mock_config_manager():
    """Create a mock ConfigManager."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.get_enabled_providers.return_value = [
        {"name": "provider_1", "enabled": True},
        {"name": "provider_2", "enabled": True},
        {"name": "provider_3", "enabled": True}
    ]
    return config_manager


@pytest.fixture
def data_source_manager(mock_config_manager):
    """Create a DataSourceManager with mock config."""
    return DataSourceManager(mock_config_manager)


# ============================================================================
# Mock Collectors
# ============================================================================

class MockSuccessCollector(DataCollector):
    """Mock collector that always succeeds."""
    
    def collect(self, polygon: Polygon) -> RawDataset:
        return RawDataset(
            source_provider=self.provider_name,
            category=self.category,
            geometry_type="Point",
            features=[
                {
                    "id": "feature_1",
                    "geometry": {"type": "Point", "coordinates": [-73.935142, 40.730710]},
                    "properties": {"name": "test_feature"}
                }
            ],
            metadata={"timestamp": "2024-01-01T00:00:00", "crs": "EPSG:4326"}
        )


class MockFailingCollector(DataCollector):
    """Mock collector that always fails."""
    
    def collect(self, polygon: Polygon) -> RawDataset:
        raise DataCollectorError(f"Provider {self.provider_name} is unavailable")


class MockEmptyCollector(DataCollector):
    """Mock collector that returns empty dataset."""
    
    def collect(self, polygon: Polygon) -> RawDataset:
        return RawDataset(
            source_provider=self.provider_name,
            category=self.category,
            geometry_type="Point",
            features=[],
            metadata={"timestamp": "2024-01-01T00:00:00", "crs": "EPSG:4326"}
        )


# ============================================================================
# Unit Tests
# ============================================================================

def test_register_single_collector(data_source_manager):
    """Test registering a single collector."""
    collector = MockSuccessCollector("test_provider", DataCategory.BUILDINGS)
    data_source_manager.register_collector(collector)
    
    assert "test_provider" in data_source_manager.collectors
    assert data_source_manager.collectors["test_provider"] == collector


def test_register_multiple_collectors(data_source_manager):
    """Test registering multiple collectors."""
    collectors = [
        MockSuccessCollector("provider_1", DataCategory.BUILDINGS),
        MockSuccessCollector("provider_2", DataCategory.LAND_COVER),
        MockSuccessCollector("provider_3", DataCategory.ROADS)
    ]
    
    for collector in collectors:
        data_source_manager.register_collector(collector)
    
    assert len(data_source_manager.collectors) == 3
    for collector in collectors:
        assert collector.provider_name in data_source_manager.collectors


def test_get_enabled_collectors(data_source_manager):
    """Test retrieving only enabled collectors."""
    # Mock config to have 2 enabled, 1 disabled
    data_source_manager.config_manager.get_enabled_providers.return_value = [
        {"name": "provider_1", "enabled": True},
        {"name": "provider_2", "enabled": True}
    ]
    
    collectors = [
        MockSuccessCollector("provider_1", DataCategory.BUILDINGS),
        MockSuccessCollector("provider_2", DataCategory.LAND_COVER),
        MockSuccessCollector("provider_3", DataCategory.ROADS)
    ]
    
    for collector in collectors:
        data_source_manager.register_collector(collector)
    
    enabled = data_source_manager.get_enabled_collectors()
    
    # Should only return enabled providers
    assert len(enabled) == 2
    provider_names = [c.provider_name for c in enabled]
    assert "provider_1" in provider_names
    assert "provider_2" in provider_names


def test_collect_all_successful(data_source_manager, sample_polygon):
    """Test collecting data when all providers succeed."""
    collectors = [
        MockSuccessCollector("provider_1", DataCategory.BUILDINGS),
        MockSuccessCollector("provider_2", DataCategory.LAND_COVER),
        MockSuccessCollector("provider_3", DataCategory.ROADS)
    ]
    
    for collector in collectors:
        data_source_manager.register_collector(collector)
    
    collected, statuses = data_source_manager.collect(sample_polygon)
    
    # All providers should succeed
    assert len(collected) == 3
    assert len(statuses) == 3
    
    for provider_name, status in statuses.items():
        assert status["success"] is True
        assert status["status"] == "available"
        assert status["data_retrieved"] is True


def test_collect_partial_failure(data_source_manager, sample_polygon):
    """Test collecting data when some providers fail (Property 2)."""
    collectors = [
        MockSuccessCollector("provider_1", DataCategory.BUILDINGS),
        MockFailingCollector("provider_2", DataCategory.LAND_COVER),
        MockSuccessCollector("provider_3", DataCategory.ROADS)
    ]
    
    for collector in collectors:
        data_source_manager.register_collector(collector)
    
    collected, statuses = data_source_manager.collect(sample_polygon)
    
    # Should have 2 successful, 1 failed
    assert len(collected) == 2
    assert "provider_1" in collected
    assert "provider_3" in collected
    assert "provider_2" not in collected
    
    # Status should record both successes and failures
    assert len(statuses) == 3
    assert statuses["provider_2"]["success"] is False
    assert statuses["provider_1"]["success"] is True
    assert statuses["provider_3"]["success"] is True


def test_collect_all_fail(data_source_manager, sample_polygon):
    """Test collecting data when all providers fail."""
    collectors = [
        MockFailingCollector("provider_1", DataCategory.BUILDINGS),
        MockFailingCollector("provider_2", DataCategory.LAND_COVER),
        MockFailingCollector("provider_3", DataCategory.ROADS)
    ]
    
    for collector in collectors:
        data_source_manager.register_collector(collector)
    
    collected, statuses = data_source_manager.collect(sample_polygon)
    
    # No data collected
    assert len(collected) == 0
    
    # All statuses should record failure
    assert len(statuses) == 3
    for status in statuses.values():
        assert status["success"] is False


def test_collect_empty_datasets(data_source_manager, sample_polygon):
    """Test collecting empty datasets still succeeds."""
    collectors = [
        MockSuccessCollector("provider_1", DataCategory.BUILDINGS),
        MockEmptyCollector("provider_2", DataCategory.LAND_COVER),
        MockSuccessCollector("provider_3", DataCategory.ROADS)
    ]
    
    for collector in collectors:
        data_source_manager.register_collector(collector)
    
    collected, statuses = data_source_manager.collect(sample_polygon)
    
    # All providers should succeed (empty data is still success)
    assert len(collected) == 3
    assert statuses["provider_2"]["success"] is True
    assert statuses["provider_2"]["feature_count"] == 0


def test_collection_summary(data_source_manager, sample_polygon):
    """Test getting collection summary."""
    collectors = [
        MockSuccessCollector("provider_1", DataCategory.BUILDINGS),
        MockFailingCollector("provider_2", DataCategory.LAND_COVER),
        MockSuccessCollector("provider_3", DataCategory.ROADS)
    ]
    
    for collector in collectors:
        data_source_manager.register_collector(collector)
    
    collected, statuses = data_source_manager.collect(sample_polygon)
    summary = data_source_manager.get_collection_summary()
    
    assert summary["total_providers"] == 3
    assert summary["successful"] == 2
    assert summary["failed"] == 1
    assert "timestamp" in summary
    assert "details" in summary


def test_no_enabled_collectors(data_source_manager, sample_polygon):
    """Test behavior with no enabled collectors."""
    data_source_manager.config_manager.get_enabled_providers.return_value = []
    
    collected, statuses = data_source_manager.collect(sample_polygon)
    
    # Should handle gracefully
    assert len(collected) == 0
    assert len(statuses) == 0


# ============================================================================
# Property-Based Tests
# ============================================================================

from hypothesis import settings

@given(
    num_providers=st.integers(min_value=1, max_value=6),
    failure_rate=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100, deadline=2000)
def test_property_2_data_collection_completeness(num_providers, failure_rate):
    """
    Property 2: Data Collection Completeness
    
    For any validated polygon with N enabled data collectors, the system 
    should query all N collectors, regardless of individual collector 
    success or failure status.
    
    **Validates: Requirements 2.1, 2.2, 2.7**
    """
    config_manager = Mock(spec=ConfigManager)
    
    # Create provider configs
    provider_configs = [
        {"name": f"provider_{i}", "enabled": True}
        for i in range(num_providers)
    ]
    config_manager.get_enabled_providers.return_value = provider_configs
    
    manager = DataSourceManager(config_manager)
    
    # Register collectors with random success/failure
    import random
    for i in range(num_providers):
        if random.random() < failure_rate:
            collector = MockFailingCollector(f"provider_{i}", DataCategory.BUILDINGS)
        else:
            collector = MockSuccessCollector(f"provider_{i}", DataCategory.BUILDINGS)
        manager.register_collector(collector)
    
    # Create test polygon
    polygon = Polygon(
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
    
    # Collect data
    collected, statuses = manager.collect(polygon)
    
    # PROPERTY: All collectors should be queried (tracked in statuses)
    assert len(statuses) == num_providers, \
        f"Expected {num_providers} collectors queried, got {len(statuses)}"
    
    # All provider names should be in statuses
    for i in range(num_providers):
        assert f"provider_{i}" in statuses, \
            f"provider_{i} not tracked in statuses"
    
    # System should not crash regardless of failure rate
    # (this test passes if we get here without exception)


@given(st.just(None))  # Placeholder strategy - just run once
def test_property_partial_success_no_crash(dummy):
    """
    Property: Partial Success Doesn't Crash System
    
    Verify that when some collectors fail and some succeed, 
    the system returns partial results without crashing.
    
    **Validates: Requirements 2.1, 2.2, 2.7**
    """
    config_manager = Mock(spec=ConfigManager)
    config_manager.get_enabled_providers.return_value = [
        {"name": "provider_1", "enabled": True},
        {"name": "provider_2", "enabled": True},
        {"name": "provider_3", "enabled": True}
    ]
    
    manager = DataSourceManager(config_manager)
    
    # Register mix of success and failure
    manager.register_collector(MockSuccessCollector("provider_1", DataCategory.BUILDINGS))
    manager.register_collector(MockFailingCollector("provider_2", DataCategory.LAND_COVER))
    manager.register_collector(MockSuccessCollector("provider_3", DataCategory.ROADS))
    
    polygon = Polygon(
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
    
    # Should not crash
    collected, statuses = manager.collect(polygon)
    
    # Should have partial results
    assert len(collected) > 0, "Should have at least some data"
    assert len(collected) < 3, "Should have fewer results due to failure"
    assert len(statuses) == 3, "Should track all collector attempts"


# ============================================================================
# Property Test 3: Provider Independence in Collection
# ============================================================================

@given(
    num_providers=st.integers(min_value=2, max_value=6),
    failure_rate=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=50, deadline=2000)
def test_property_3_provider_independence(num_providers, failure_rate):
    """
    Property 3: Provider Independence in Collection
    
    For any two different polygons analyzed with different provider 
    availability states, the system should produce results for available 
    providers and skip unavailable ones without crashing or degrading 
    other providers.
    
    **Validates: Requirements 2.5, 2.6**
    """
    import random
    
    config_manager = Mock(spec=ConfigManager)
    
    # Create provider configs
    provider_configs = [
        {"name": f"provider_{i}", "enabled": True}
        for i in range(num_providers)
    ]
    config_manager.get_enabled_providers.return_value = provider_configs
    
    manager = DataSourceManager(config_manager)
    
    # Register collectors with random success/failure
    for i in range(num_providers):
        if random.random() < failure_rate:
            collector = MockFailingCollector(f"provider_{i}", DataCategory.BUILDINGS)
        else:
            collector = MockSuccessCollector(f"provider_{i}", DataCategory.BUILDINGS)
        manager.register_collector(collector)
    
    # Create test polygon
    polygon = Polygon(
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
    
    # Collect data
    collected, statuses = manager.collect(polygon)
    
    # PROPERTY: Failed providers don't affect successful ones
    successful_providers = [name for name, status in statuses.items() if status["success"]]
    failed_providers = [name for name, status in statuses.items() if not status["success"]]
    
    # For each successful provider, verify it has data
    for provider_name in successful_providers:
        assert provider_name in collected, \
            f"Successful provider {provider_name} should have data"
        assert len(collected[provider_name].features) > 0, \
            f"Successful provider {provider_name} should have features"
    
    # For each failed provider, verify it has no data
    for provider_name in failed_providers:
        assert provider_name not in collected, \
            f"Failed provider {provider_name} should not be in results"
    
    # System shouldn't crash with any combination
    assert len(statuses) == num_providers, \
        f"Expected all {num_providers} providers tracked"
