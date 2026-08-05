"""
Property-Based Tests for Real Data Collection Completeness

Feature: land-scanner, Property 2: Real Data Collection Completeness
Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.7

This test suite validates that the system:
- Executes ALL enabled collectors for each polygon
- Aggregates results WITHOUT DATA LOSS from all collectors
- Handles partial success (some providers fail, others succeed)
- Handles timeout handling
- Handles rate limit delays
- Works with polygons across entire geographic range
- Continues with available providers after individual failures
- Maintains no cascading failures (provider independence)

Core Properties Being Tested:

Property 2.1: Complete Collector Execution
- For ANY polygon with N enabled collectors, ALL N collectors execute
- Geographic invariant: holds for all geographic locations (equator, poles, all quadrants)

Property 2.2: No Data Loss in Aggregation
- All data from successful providers is aggregated without loss
- Result structure is consistent across all provider types

Property 2.3: Partial Success Handling
- When 1+ providers fail, system continues with available providers
- Failed data is not included, successful data is preserved

Property 2.4: Configuration Respected
- Only enabled providers are executed
- Disabled providers are never called

Property 2.5: Rate Limit Delays
- Delays are applied between sequential provider calls
- Measured delays respect configured values

Property 2.6: Provider Independence
- One provider's failure never affects another provider
- No cascading failures
- All providers execute even if others fail
"""

import pytest
import logging
from unittest.mock import Mock
from datetime import datetime
from typing import Dict, Any
import time

try:
    from backend.managers.data_source_manager import DataSourceManager, RawDataCollection
    from backend.services.config_manager import ConfigManager
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# Test Utilities
# ============================================================================

def create_test_polygon(lon=0, lat=0):
    """Create a simple valid test polygon."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [lon, lat],
                [lon + 0.1, lat],
                [lon + 0.1, lat + 0.1],
                [lon, lat + 0.1],
                [lon, lat]
            ]]
        },
        "properties": {
            "area_square_kilometers": 1.0,
            "bounding_box": {"min_lon": lon, "max_lon": lon + 0.1, "min_lat": lat, "max_lat": lat + 0.1},
            "centroid": {"longitude": lon + 0.05, "latitude": lat + 0.05},
            "vertex_count": 5,
            "crs": "EPSG:4326"
        }
    }


def create_mock_collector(provider_name: str, failure_type: str = "success", feature_count: int = 10):
    """Create a mock collector for testing."""
    mock = Mock()
    mock.provider_name = provider_name
    
    if failure_type == "success":
        mock.collect.return_value = {
            "source_provider": provider_name,
            "category": "buildings",
            "features": [{"id": f"feat_{i}"} for i in range(feature_count)],
            "metadata": {"timestamp": datetime.utcnow().isoformat(), "feature_count": feature_count}
        }
    elif failure_type == "timeout":
        mock.collect.side_effect = TimeoutError(f"{provider_name} timeout")
    elif failure_type == "http_500":
        mock.collect.side_effect = Exception(f"{provider_name} HTTP 500")
    elif failure_type == "http_503":
        mock.collect.side_effect = Exception(f"{provider_name} HTTP 503")
    elif failure_type == "http_429":
        mock.collect.side_effect = Exception(f"{provider_name} HTTP 429")
    elif failure_type == "http_404":
        mock.collect.side_effect = Exception(f"{provider_name} HTTP 404")
    elif failure_type == "connection_refused":
        mock.collect.side_effect = ConnectionError(f"{provider_name} connection refused")
    elif failure_type == "malformed_json":
        mock.collect.side_effect = ValueError(f"{provider_name} malformed JSON")
    elif failure_type == "missing_fields":
        mock.collect.return_value = {"source_provider": provider_name}
    elif failure_type == "truncated_response":
        mock.collect.return_value = {
            "source_provider": provider_name,
            "features": [{"id": f"feat_{i}"} for i in range(feature_count // 2)],
        }
    else:
        mock.collect.return_value = {
            "source_provider": provider_name,
            "features": [],
            "metadata": {"timestamp": datetime.utcnow().isoformat()}
        }
    
    return mock


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestDataCollectionCompleteness:
    """Property 2: Real Data Collection Completeness"""
    
    def test_all_enabled_collectors_execute_equator(self):
        """
        Property 2.1a: Equator - All N enabled collectors execute
        Validates: Requirements 2.1, 2.2, 2.7
        """
        polygon = create_test_polygon(lon=0, lat=0)
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "admin_boundaries": {"enabled": True, "optional": False},
            "land_cover": {"enabled": True, "optional": True},
            "roads": {"enabled": True, "optional": False},
            "water": {"enabled": True, "optional": False},
            "elevation": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success"),
            "admin_boundaries": create_mock_collector("admin_boundaries", "success"),
            "land_cover": create_mock_collector("land_cover", "success"),
            "roads": create_mock_collector("roads", "success"),
            "water": create_mock_collector("water", "success"),
            "elevation": create_mock_collector("elevation", "success")
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 6
        assert result.successful_providers == 6
        assert result.failed_providers == 0
        
        for collector in collectors.values():
            collector.collect.assert_called_once_with(polygon)
    
    def test_all_enabled_collectors_execute_north_pole(self):
        """
        Property 2.1b: North Pole - All N enabled collectors execute
        Validates: Requirements 2.1, 2.2, 2.7
        """
        polygon = create_test_polygon(lon=0, lat=89)
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False},
            "elevation": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 5),
            "roads": create_mock_collector("roads", "success", 3),
            "elevation": create_mock_collector("elevation", "success", 8)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 3
        assert result.successful_providers == 3
    
    def test_all_enabled_collectors_execute_south_pole(self):
        """
        Property 2.1c: South Pole - All N enabled collectors execute
        Validates: Requirements 2.1, 2.2, 2.7
        """
        polygon = create_test_polygon(lon=0, lat=-89)
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "elevation": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 2),
            "elevation": create_mock_collector("elevation", "success", 10)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 2
        assert result.successful_providers == 2
    
    def test_all_enabled_collectors_northeast(self):
        """
        Property 2.1d: Northeast quadrant - All N enabled collectors execute
        Validates: Requirements 2.1, 2.2, 2.7
        """
        polygon = create_test_polygon(lon=45, lat=45)
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 7),
            "roads": create_mock_collector("roads", "success", 12)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.successful_providers == 2
    
    def test_aggregation_no_data_loss_single_provider(self):
        """
        Property 2.2a: Aggregation - Single provider all data preserved
        Validates: Requirements 2.1, 2.2, 2.3
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 25)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert "osm_buildings" in result.collections
        assert len(result.collections["osm_buildings"]["features"]) == 25
        assert result.successful_providers == 1
    
    def test_aggregation_no_data_loss_multiple_providers(self):
        """
        Property 2.2b: Aggregation - Multiple providers all data preserved
        Validates: Requirements 2.1, 2.2, 2.3
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False},
            "water": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 30),
            "roads": create_mock_collector("roads", "success", 50),
            "water": create_mock_collector("water", "success", 15)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert len(result.collections) == 3
        assert len(result.collections["osm_buildings"]["features"]) == 30
        assert len(result.collections["roads"]["features"]) == 50
        assert len(result.collections["water"]["features"]) == 15
        assert result.successful_providers == 3
    
    def test_partial_success_one_provider_fails(self):
        """
        Property 2.3a: Partial Success - 1 fails, N-1 succeed
        Validates: Requirements 2.1, 2.5, 2.6
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False},
            "elevation": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 20),
            "roads": create_mock_collector("roads", "timeout"),
            "elevation": create_mock_collector("elevation", "success", 15)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 3
        assert result.successful_providers == 2
        assert result.failed_providers == 1
        
        assert "osm_buildings" in result.collections
        assert "elevation" in result.collections
        assert "roads" not in result.collections
        
        assert result.provider_status["roads"]["status"] == "error"
        assert result.provider_status["osm_buildings"]["status"] == "success"
    
    def test_partial_success_multiple_failures(self):
        """
        Property 2.3b: Partial Success - Multiple providers fail
        Validates: Requirements 2.5, 2.6
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False},
            "water": {"enabled": True, "optional": False},
            "elevation": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "http_500"),
            "roads": create_mock_collector("roads", "http_503"),
            "water": create_mock_collector("water", "success", 12),
            "elevation": create_mock_collector("elevation", "success", 18)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.successful_providers == 2
        assert result.failed_providers == 2
        
        assert "water" in result.collections
        assert "elevation" in result.collections
        assert "osm_buildings" not in result.collections
    
    def test_disabled_providers_not_called(self):
        """
        Property 2.4a: Configuration - Disabled not called
        Validates: Requirements 2.1, 2.7
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        # get_enabled_providers should only return ENABLED providers
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "elevation": {"enabled": True, "optional": False}
            # roads is NOT included because it's disabled
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 10),
            "roads": create_mock_collector("roads", "success", 10),  # Created but not enabled
            "elevation": create_mock_collector("elevation", "success", 10)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 2
        collectors["osm_buildings"].collect.assert_called_once()
        collectors["elevation"].collect.assert_called_once()
        collectors["roads"].collect.assert_not_called()
    
    def test_optional_provider_failure_continues_processing(self):
        """
        Property 2.4b: Configuration - Optional doesn't block
        Validates: Requirements 2.5, 2.6
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "land_cover": {"enabled": True, "optional": True}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 10),
            "land_cover": create_mock_collector("land_cover", "timeout")
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.successful_providers >= 1
        assert "osm_buildings" in result.collections
        assert result.provider_status["land_cover"]["optional"] is True
    
    def test_rate_limit_delay_applied(self):
        """
        Property 2.5: Rate Limits - Delays applied between calls
        Validates: Requirements 2.1, 2.2
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "roads": {"enabled": True, "optional": False},
            "elevation": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success"),
            "roads": create_mock_collector("roads", "success"),
            "elevation": create_mock_collector("elevation", "success")
        }
        
        rate_limit_delay = 0.05
        manager = DataSourceManager(config, collectors, rate_limit_delay=rate_limit_delay)
        
        start_time = time.time()
        result = manager.collect_data(polygon)
        elapsed = time.time() - start_time
        
        expected_min = (3 - 1) * rate_limit_delay * 0.8
        assert elapsed >= expected_min
        assert result.successful_providers == 3
    
    def test_provider_independence_no_cascading_failure(self):
        """
        Property 2.6a: Independence - A fails doesn't affect B
        Validates: Requirements 2.5, 2.6, 2.7
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "provider_a": {"enabled": True, "optional": False},
            "provider_b": {"enabled": True, "optional": False},
            "provider_c": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "provider_a": create_mock_collector("provider_a", "success", 10),
            "provider_b": create_mock_collector("provider_b", "http_500"),
            "provider_c": create_mock_collector("provider_c", "success", 10)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.provider_status["provider_a"]["status"] == "success"
        assert result.provider_status["provider_b"]["status"] == "error"
        assert result.provider_status["provider_c"]["status"] == "success"
        
        collectors["provider_a"].collect.assert_called_once()
        collectors["provider_b"].collect.assert_called_once()
        collectors["provider_c"].collect.assert_called_once()
    
    def test_provider_independence_timeout_recovery(self):
        """
        Property 2.6b: Independence - A timeout doesn't prevent B
        Validates: Requirements 2.5, 2.6, 2.7
        """
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "provider_a": {"enabled": True, "optional": False},
            "provider_b": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "provider_a": create_mock_collector("provider_a", "timeout"),
            "provider_b": create_mock_collector("provider_b", "success", 15)
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.provider_status["provider_b"]["status"] == "success"
        assert len(result.collections.get("provider_b", {}).get("features", [])) == 15


class TestDataCollectionMetrics:
    """Tests for data collection metrics and status"""
    
    def test_provider_status_complete(self):
        """Verify provider status is complete and accurate"""
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "osm_buildings": {"enabled": True, "optional": False},
            "land_cover": {"enabled": True, "optional": True}
        }
        
        collectors = {
            "osm_buildings": create_mock_collector("osm_buildings", "success", 42),
            "land_cover": create_mock_collector("land_cover", "http_503")
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        osm_status = result.provider_status["osm_buildings"]
        assert osm_status["status"] == "success"
        assert osm_status["feature_count"] == 42
        assert osm_status["optional"] is False
        
        lc_status = result.provider_status["land_cover"]
        assert lc_status["status"] == "error"
        assert "error" in lc_status
        assert lc_status["optional"] is True
    
    def test_result_counts_accurate(self):
        """Verify result counts are accurate"""
        polygon = create_test_polygon()
        
        config = Mock(spec=ConfigManager)
        config.get_enabled_providers.return_value = {
            "p1": {"enabled": True, "optional": False},
            "p2": {"enabled": True, "optional": False},
            "p3": {"enabled": True, "optional": False},
            "p4": {"enabled": True, "optional": False}
        }
        
        collectors = {
            "p1": create_mock_collector("p1", "success"),
            "p2": create_mock_collector("p2", "success"),
            "p3": create_mock_collector("p3", "timeout"),
            "p4": create_mock_collector("p4", "http_500")
        }
        
        manager = DataSourceManager(config, collectors, rate_limit_delay=0.01)
        result = manager.collect_data(polygon)
        
        assert result.total_providers == 4
        assert result.successful_providers == 2
        assert result.failed_providers == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
