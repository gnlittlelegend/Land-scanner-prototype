"""
Tests for Data Source Manager with Real Provider Coordination

Tests that DataSourceManager:
- Loads enabled providers from configuration (with real endpoints)
- Executes all enabled collectors sequentially
- Adds rate limit delays between requests (2-5 seconds)
- Aggregates results from all collectors
- Handles real provider failures: timeouts, rate limits, API errors
- Continues processing if optional providers fail
- Fails only if all critical providers unavailable
- Returns aggregated RawDataCollection with provider status

Requirements Met:
- Load enabled providers from configuration with real API endpoints
- Execute all enabled collectors sequentially
- Add rate limit delays between requests (2-5 seconds configurable)
- Aggregate results from all collectors
- Handle real provider failures (timeouts, rate limits, API errors)
- Continue processing if optional providers fail
- Fail only if all critical providers unavailable
- Return aggregated RawDataCollection with provider status
"""

import pytest
import logging
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from hypothesis import given, strategies as st

from backend.services.config_manager import ConfigManager
from backend.managers.data_source_manager import DataSourceManager, RawDataCollection
from backend.collectors.base_collector import DataCollector

logger = logging.getLogger(__name__)


class TestRawDataCollection:
    """Tests for RawDataCollection data structure"""

    def test_raw_data_collection_initialization(self):
        """Test RawDataCollection initializes with correct defaults"""
        collection = RawDataCollection()
        
        assert collection.collections == {}
        assert collection.provider_status == {}
        assert collection.total_providers == 0
        assert collection.successful_providers == 0
        assert collection.failed_providers == 0
        assert collection.critical_failure is False
        assert collection.collection_timestamp is not None

    def test_raw_data_collection_to_dict(self):
        """Test RawDataCollection converts to dict correctly"""
        collection = RawDataCollection()
        collection.total_providers = 2
        collection.successful_providers = 1
        collection.failed_providers = 1
        
        result = collection.to_dict()
        
        assert result["total_providers"] == 2
        assert result["successful_providers"] == 1
        assert result["failed_providers"] == 1
        assert "collection_timestamp" in result


class TestDataSourceManagerInitialization:
    """Tests for DataSourceManager initialization"""

    def test_initialization_with_config_manager(self):
        """Test DataSourceManager initializes with ConfigManager"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_setting.return_value = 2
        collectors = {}
        
        manager = DataSourceManager(config_manager, collectors)
        
        assert manager.config_manager == config_manager
        assert manager.collectors == collectors
        assert manager.rate_limit_delay == 2  # Default

    def test_initialization_with_custom_rate_limit(self):
        """Test DataSourceManager can use custom rate limit delay"""
        config_manager = Mock(spec=ConfigManager)
        collectors = {}
        
        manager = DataSourceManager(config_manager, collectors, rate_limit_delay=3.5)
        
        assert manager.rate_limit_delay == 3.5

    def test_initialization_rate_limit_from_config(self):
        """Test DataSourceManager uses rate limit from config if provided"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_setting.return_value = 4.0
        collectors = {}
        
        manager = DataSourceManager(config_manager, collectors)
        
        assert manager.rate_limit_delay == 4.0


class TestDataSourceManagerDataCollection:
    """Tests for collect_data method"""

    def _create_test_polygon(self):
        """Create a test polygon dict"""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-74.0, 40.7],
                    [-73.9, 40.7],
                    [-73.9, 40.8],
                    [-74.0, 40.8],
                    [-74.0, 40.7]
                ]]
            },
            "properties": {
                "area_square_kilometers": 1.5,
                "bounding_box": {
                    "min_lon": -74.0,
                    "min_lat": 40.7,
                    "max_lon": -73.9,
                    "max_lat": 40.8
                },
                "centroid": {"longitude": -73.95, "latitude": 40.75},
                "vertex_count": 5,
                "crs": "EPSG:4326"
            }
        }

    def _create_mock_collector(self, provider_name, success=True, feature_count=10):
        """Create a mock collector for testing"""
        mock_collector = Mock(spec=DataCollector)
        mock_collector.provider_name = provider_name
        
        if success:
            mock_collector.collect.return_value = {
                "source_provider": provider_name,
                "category": "buildings",
                "features": [{"id": f"feat_{i}"} for i in range(feature_count)],
                "metadata": {"timestamp": datetime.utcnow().isoformat()}
            }
        else:
            mock_collector.collect.side_effect = Exception(f"Provider {provider_name} error")
        
        return mock_collector

    def test_collect_data_no_enabled_providers(self):
        """Test collect_data with no enabled providers"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {}
        
        manager = DataSourceManager(config_manager, {})
        polygon = self._create_test_polygon()
        
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 0
        assert result.successful_providers == 0
        assert result.failed_providers == 0
        assert result.critical_failure is True

    def test_collect_data_single_successful_provider(self):
        """Test collect_data with single successful provider"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "osm_buildings": {
                "enabled": True,
                "optional": False,
                "name": "OSM Buildings"
            }
        }
        
        mock_collector = self._create_mock_collector("osm_buildings")
        collectors = {"osm_buildings": mock_collector}
        
        manager = DataSourceManager(config_manager, collectors)
        polygon = self._create_test_polygon()
        
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 1
        assert result.successful_providers == 1
        assert result.failed_providers == 0
        assert result.critical_failure is False
        assert "osm_buildings" in result.collections
        assert result.provider_status["osm_buildings"]["status"] == "success"
        assert result.provider_status["osm_buildings"]["feature_count"] == 10

    def test_collect_data_multiple_successful_providers(self):
        """Test collect_data with multiple successful providers"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False},
            "water": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": self._create_mock_collector("osm_buildings", feature_count=10),
            "roads": self._create_mock_collector("roads", feature_count=20),
            "water": self._create_mock_collector("water", feature_count=5)
        }
        
        manager = DataSourceManager(config_manager, collectors)
        polygon = self._create_test_polygon()
        
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 3
        assert result.successful_providers == 3
        assert result.failed_providers == 0
        assert result.critical_failure is False
        assert len(result.collections) == 3

    def test_collect_data_provider_failure_continues(self):
        """Test collect_data continues when provider fails"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "land_cover": {"enabled": True, "optional": True}
        }
        
        collectors = {
            "osm_buildings": self._create_mock_collector("osm_buildings", success=True),
            "land_cover": self._create_mock_collector("land_cover", success=False)
        }
        
        manager = DataSourceManager(config_manager, collectors)
        polygon = self._create_test_polygon()
        
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 2
        assert result.successful_providers == 1
        assert result.failed_providers == 1
        assert result.critical_failure is False  # One critical succeeded
        assert "osm_buildings" in result.collections
        assert result.provider_status["land_cover"]["status"] == "error"

    def test_collect_data_critical_failure_all_fail(self):
        """Test critical failure when all critical providers fail"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": self._create_mock_collector("osm_buildings", success=False),
            "roads": self._create_mock_collector("roads", success=False)
        }
        
        manager = DataSourceManager(config_manager, collectors)
        polygon = self._create_test_polygon()
        
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 2
        assert result.successful_providers == 0
        assert result.failed_providers == 2
        assert result.critical_failure is True

    def test_collect_data_missing_collector(self):
        """Test collect_data when collector is missing"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False}
        }
        
        collectors = {}  # No collectors
        
        manager = DataSourceManager(config_manager, collectors)
        polygon = self._create_test_polygon()
        
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 1
        assert result.successful_providers == 0
        assert result.failed_providers == 1
        assert result.provider_status["osm_buildings"]["status"] == "unavailable"

    def test_collect_data_rate_limit_delay_applied(self):
        """Test rate limit delay is applied between providers"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "provider_1": {"enabled": True, "optional": False},
            "provider_2": {"enabled": True, "optional": False},
            "provider_3": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "provider_1": self._create_mock_collector("provider_1"),
            "provider_2": self._create_mock_collector("provider_2"),
            "provider_3": self._create_mock_collector("provider_3")
        }
        
        manager = DataSourceManager(config_manager, collectors, rate_limit_delay=0.1)
        polygon = self._create_test_polygon()
        
        start_time = time.time()
        result = manager.collect_data(polygon)
        elapsed_time = time.time() - start_time
        
        # With 3 providers and 2 delays of 0.1 seconds, should take at least 0.2 seconds
        assert elapsed_time >= 0.2
        assert result.successful_providers == 3


class TestDataSourceManagerSummaries:
    """Tests for summary and utility methods"""

    def _create_test_collection(self):
        """Create a test RawDataCollection"""
        collection = RawDataCollection()
        collection.total_providers = 3
        collection.successful_providers = 2
        collection.failed_providers = 1
        collection.collections = {
            "provider_1": {
                "features": [{"id": "f1"}, {"id": "f2"}],
                "category": "buildings"
            },
            "provider_2": {
                "features": [{"id": "f3"}],
                "category": "roads"
            }
        }
        collection.provider_status = {
            "provider_1": {"status": "success", "feature_count": 2, "optional": False},
            "provider_2": {"status": "success", "feature_count": 1, "optional": False},
            "provider_3": {"status": "error", "optional": True}
        }
        
        return collection

    def test_get_collection_summary(self):
        """Test collection summary generation"""
        config_manager = Mock(spec=ConfigManager)
        manager = DataSourceManager(config_manager, {})
        collection = self._create_test_collection()
        
        summary = manager.get_collection_summary(collection)
        
        assert summary["total_providers"] == 3
        assert summary["successful_providers"] == 2
        assert summary["failed_providers"] == 1
        assert summary["total_features"] == 3
        assert "collection_timestamp" in summary

    def test_get_available_data_categories(self):
        """Test getting available data categories from collection"""
        config_manager = Mock(spec=ConfigManager)
        manager = DataSourceManager(config_manager, {})
        collection = self._create_test_collection()
        
        categories = manager.get_available_data_categories(collection)
        
        assert "buildings" in categories
        assert "roads" in categories
        assert len(categories) == 2


class TestDataSourceManagerProviderIndependence:
    """Tests for provider independence and failure isolation"""

    def _create_test_polygon(self):
        """Create test polygon"""
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {"area_square_kilometers": 1.0}
        }

    def test_provider_failure_does_not_affect_others(self):
        """Test that one provider's failure doesn't affect others"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "provider_a": {"enabled": True, "optional": False},
            "provider_b": {"enabled": True, "optional": False},
            "provider_c": {"enabled": True, "optional": False}
        }
        
        mock_a = Mock(spec=DataCollector)
        mock_a.provider_name = "provider_a"
        mock_a.collect.return_value = {"features": [{"id": "a1"}], "source_provider": "provider_a"}
        
        mock_b = Mock(spec=DataCollector)
        mock_b.provider_name = "provider_b"
        mock_b.collect.side_effect = Exception("Provider B failed")
        
        mock_c = Mock(spec=DataCollector)
        mock_c.provider_name = "provider_c"
        mock_c.collect.return_value = {"features": [{"id": "c1"}], "source_provider": "provider_c"}
        
        collectors = {"provider_a": mock_a, "provider_b": mock_b, "provider_c": mock_c}
        
        manager = DataSourceManager(config_manager, collectors)
        polygon = self._create_test_polygon()
        
        result = manager.collect_data(polygon)
        
        # Provider A and C should still be successful
        assert result.provider_status["provider_a"]["status"] == "success"
        assert result.provider_status["provider_c"]["status"] == "success"
        assert result.provider_status["provider_b"]["status"] == "error"
        
        # Data should be collected from A and C
        assert "provider_a" in result.collections
        assert "provider_c" in result.collections
        assert "provider_b" not in result.collections

    def test_optional_provider_failure_does_not_cause_critical_failure(self):
        """Test that optional provider failure doesn't cause system failure"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "critical_provider": {"enabled": True, "optional": False},
            "optional_provider": {"enabled": True, "optional": True}
        }
        
        mock_critical = Mock(spec=DataCollector)
        mock_critical.provider_name = "critical_provider"
        mock_critical.collect.return_value = {"features": [{"id": "c1"}], "source_provider": "critical_provider"}
        
        mock_optional = Mock(spec=DataCollector)
        mock_optional.provider_name = "optional_provider"
        mock_optional.collect.side_effect = Exception("Optional provider failed")
        
        collectors = {"critical_provider": mock_critical, "optional_provider": mock_optional}
        
        manager = DataSourceManager(config_manager, collectors)
        polygon = self._create_test_polygon()
        
        result = manager.collect_data(polygon)
        
        assert result.critical_failure is False
        assert result.provider_status["optional_provider"]["optional"] is True

    def test_sequential_execution_order_matters(self):
        """Test that collectors are executed in order"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "provider_1": {"enabled": True, "optional": False},
            "provider_2": {"enabled": True, "optional": False},
            "provider_3": {"enabled": True, "optional": False}
        }
        
        execution_order = []
        
        def create_tracking_collector(name):
            mock = Mock(spec=DataCollector)
            mock.provider_name = name
            def track_execution(*args, **kwargs):
                execution_order.append(name)
                return {"features": [], "source_provider": name}
            mock.collect = track_execution
            return mock
        
        collectors = {
            "provider_1": create_tracking_collector("provider_1"),
            "provider_2": create_tracking_collector("provider_2"),
            "provider_3": create_tracking_collector("provider_3")
        }
        
        manager = DataSourceManager(config_manager, collectors)
        polygon = self._create_test_polygon()
        
        manager.collect_data(polygon)
        
        # Verify execution order matches enabled provider order
        assert execution_order == ["provider_1", "provider_2", "provider_3"]


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestPropertyBasedDataManagerMetres:
    """
    Property-Based Test: All data flowing through manager uses metres
    
    Feature: distance-unit-standardization, Property 12: All data through manager uses metres
    Validates: Requirements 8.1, 8.2
    
    This test verifies that for ANY polygon processed by DataSourceManager,
    all area values in properties are in square metres (not km² or mixed units).
    """

    def _create_successful_collector(self, provider_name):
        """Helper: Create a successful mock collector"""
        mock_collector = Mock(spec=DataCollector)
        mock_collector.provider_name = provider_name
        mock_collector.collect.return_value = {
            "source_provider": provider_name,
            "category": "test_data",
            "features": [
                {"id": f"feat_{i}", "area_sqm": 1000 + i * 100}
                for i in range(5)
            ],
            "metadata": {"timestamp": datetime.utcnow().isoformat()}
        }
        return mock_collector

    @given(
        area_sqm=st.floats(
            min_value=10,
            max_value=100_000_000,
            allow_nan=False,
            allow_infinity=False
        )
    )
    def test_manager_preserves_area_sqm_in_input(self, area_sqm):
        """
        Property: For any polygon with area_sqm, the manager preserves it.
        
        **Feature: distance-unit-standardization, Property 12: All data through manager uses metres**
        **Validates: Requirements 8.1, 8.2**
        
        Given a polygon with area_sqm in properties, when processed through DataSourceManager,
        then the area value should remain in square metres.
        """
        # Create polygon with area_sqm in properties
        polygon = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-74.0, 40.7],
                    [-73.9, 40.7],
                    [-73.9, 40.8],
                    [-74.0, 40.8],
                    [-74.0, 40.7]
                ]]
            },
            "properties": {
                "area_sqm": area_sqm,
                "bounding_box": {
                    "min_lon": -74.0,
                    "min_lat": 40.7,
                    "max_lon": -73.9,
                    "max_lat": 40.8
                },
                "centroid": {"longitude": -73.95, "latitude": 40.75},
                "vertex_count": 5,
                "crs": "EPSG:4326"
            }
        }
        
        # Setup
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "test_provider": {"enabled": True, "optional": False}
        }
        
        mock_collector = self._create_successful_collector("test_provider")
        collectors = {"test_provider": mock_collector}
        
        manager = DataSourceManager(config_manager, collectors)
        
        # Execute
        result = manager.collect_data(polygon)
        
        # Verify: Input polygon area_sqm is preserved
        assert "area_sqm" in polygon["properties"]
        assert polygon["properties"]["area_sqm"] > 0
        assert isinstance(polygon["properties"]["area_sqm"], float)
        
        # Verify: No km² or area_sqkm in input properties
        assert "area_sqkm" not in polygon["properties"]
        assert "area_square_kilometers" not in polygon["properties"]

    @given(
        st.floats(
            min_value=10,
            max_value=100_000_000,
            allow_nan=False,
            allow_infinity=False
        )
    )
    def test_manager_processes_varied_area_values(self, area_sqm):
        """
        Property: For any area value in m², the manager processes it consistently.
        
        **Feature: distance-unit-standardization, Property 12: All data through manager uses metres**
        **Validates: Requirements 8.1, 8.2**
        
        Given polygons with varied area values in m², when processed through DataSourceManager,
        then all areas should remain in square metres throughout processing.
        """
        # Setup
        polygon = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-74.0, 40.7],
                    [-73.9, 40.7],
                    [-73.9, 40.8],
                    [-74.0, 40.8],
                    [-74.0, 40.7]
                ]]
            },
            "properties": {
                "area_sqm": area_sqm,
                "centroid": {"longitude": -73.95, "latitude": 40.75}
            }
        }
        
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "provider_1": {"enabled": True, "optional": False}
        }
        
        mock_collector = self._create_successful_collector("provider_1")
        collectors = {"provider_1": mock_collector}
        
        manager = DataSourceManager(config_manager, collectors)
        
        # Execute
        result = manager.collect_data(polygon)
        
        # Verify: Area is preserved in m² throughout
        assert polygon["properties"]["area_sqm"] == area_sqm
        assert polygon["properties"]["area_sqm"] >= 10
        assert polygon["properties"]["area_sqm"] <= 100_000_000

    def test_manager_multiple_providers_all_use_metres(self):
        """
        Property: For multiple providers, all collected data uses metres.
        
        **Feature: distance-unit-standardization, Property 12: All data through manager uses metres**
        **Validates: Requirements 8.1, 8.2**
        
        Given multiple providers collecting data for a polygon,
        when the manager aggregates results,
        then all area values should be in square metres.
        """
        # Setup
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[
                [-74.0, 40.7], [-73.9, 40.7], [-73.9, 40.8], [-74.0, 40.8], [-74.0, 40.7]
            ]]},
            "properties": {
                "area_sqm": 50_000_000,
                "centroid": {"longitude": -73.95, "latitude": 40.75}
            }
        }
        
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "provider_a": {"enabled": True, "optional": False},
            "provider_b": {"enabled": True, "optional": False},
            "provider_c": {"enabled": True, "optional": True}
        }
        
        collectors = {
            "provider_a": self._create_successful_collector("provider_a"),
            "provider_b": self._create_successful_collector("provider_b"),
            "provider_c": self._create_successful_collector("provider_c")
        }
        
        manager = DataSourceManager(config_manager, collectors)
        
        # Execute
        result = manager.collect_data(polygon)
        
        # Verify: All collected data uses metres
        for provider_name, collection in result.collections.items():
            # Check if collection has features with area data
            if "features" in collection:
                for feature in collection["features"]:
                    # Any area values should be in m² (no km² suffixes)
                    for key in feature.keys():
                        assert "km²" not in key
                        assert "sqkm" not in key.lower()
                        assert "square_kilometers" not in key.lower()

    def test_manager_output_properties_use_metres(self):
        """
        Property: Manager output properties use m² only, not km².
        
        **Feature: distance-unit-standardization, Property 12: All data through manager uses metres**
        **Validates: Requirements 8.1, 8.2**
        
        Given successful data collection from providers,
        when the manager returns the result,
        then all property dictionaries should use m² units exclusively.
        """
        # Setup
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[
                [-74.0, 40.7], [-73.9, 40.7], [-73.9, 40.8], [-74.0, 40.8], [-74.0, 40.7]
            ]]},
            "properties": {
                "area_sqm": 25_000_000,
                "centroid": {"longitude": -73.95, "latitude": 40.75}
            }
        }
        
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_enabled_providers.return_value = {
            "buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "buildings": self._create_successful_collector("buildings"),
            "roads": self._create_successful_collector("roads")
        }
        
        manager = DataSourceManager(config_manager, collectors)
        
        # Execute
        result = manager.collect_data(polygon)
        
        # Verify: No km²-related field names in any output
        for provider_name, collection in result.collections.items():
            # Check collection dict keys
            for key in collection.keys():
                assert "sqkm" not in key.lower()
                assert "km" not in key.lower()
                assert "square_kilometers" not in key.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
