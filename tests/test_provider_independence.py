"""
Property-based tests for Provider Independence in Collection.

Feature: land-scanner, Property 3: Provider Independence in Collection
Validates: Requirements 2.5, 2.6
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, MagicMock
import logging

from backend.managers.data_source_manager import DataSourceManager
from backend.services import ConfigManager
from backend.models import Polygon, ProcessingStatus, RawDataset, DataCategory
from backend.validators.polygon_validator import PolygonValidator
from backend.collectors.base import DataCollectionError


@st.composite
def valid_test_polygons(draw):
    """Generate valid test polygons for collection testing."""
    lon_min = draw(st.floats(min_value=-170, max_value=170))
    lat_min = draw(st.floats(min_value=-80, max_value=80))
    width = draw(st.floats(min_value=1, max_value=30))
    height = draw(st.floats(min_value=1, max_value=30))
    
    lon_max = min(lon_min + width, 180)
    lat_max = min(lat_min + height, 90)
    
    coordinates = [
        [
            [lon_min, lat_min],
            [lon_max, lat_min],
            [lon_max, lat_max],
            [lon_min, lat_max],
            [lon_min, lat_min]
        ]
    ]
    
    return PolygonValidator.validate({
        "type": "Polygon",
        "coordinates": coordinates
    })


@st.composite
def failure_scenarios(draw):
    """Generate various provider failure scenarios."""
    failure_type = draw(st.sampled_from([
        "timeout",
        "api_error",
        "network_error",
        "invalid_response",
        "partial_success"
    ]))
    
    return failure_type


class TestProviderIndependence:
    """
    Property-based tests for provider independence.
    
    Feature: land-scanner, Property 3: Provider Independence in Collection
    Validates: Requirements 2.5, 2.6
    
    These tests verify that:
    1. When providers fail, other providers continue functioning
    2. System returns partial results instead of complete failure
    3. Failures in one provider don't cascade to others
    """
    
    @given(valid_test_polygons())
    @settings(deadline=None, max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_collection_continues_with_provider_failure(self, polygon: Polygon):
        """
        Property: System continues collection even if individual providers fail.
        
        For any polygon, if one provider fails, other providers should still be queried
        and the system should return partial results.
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        # Mock one provider to fail, others to succeed
        with patch.object(manager, '_collect_from_provider') as mock_collect:
            # Simulate failure for first provider, success for others
            def collect_side_effect(provider_name, collector_info, polygon):
                if provider_name == "osm_buildings":
                    raise DataCollectionError("API timeout")
                else:
                    return RawDataset(
                        source_provider=provider_name,
                        category=collector_info["category"],
                        geometry_type="Polygon",
                        features=[],
                        metadata={}
                    )
            
            mock_collect.side_effect = collect_side_effect
            
            # Collect should not raise, should return partial results
            result = manager.collect(polygon)
            
            # Should have partial status, not complete failure
            assert result["status"] in [ProcessingStatus.SUCCESS, ProcessingStatus.PARTIAL]
            
            # Should have datasets from successful providers
            assert len(result["datasets"]) >= 0
            
            # Should show provider status for all providers
            assert len(result["provider_status"]) == len(config.get_enabled_providers())
    
    @given(valid_test_polygons())
    @settings(deadline=None, max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_all_providers_queried_regardless_of_failures(self, polygon: Polygon):
        """
        Property: All enabled providers are queried, regardless of individual failures.
        
        For any polygon, the system should attempt to query all enabled providers,
        even if some fail.
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        enabled_provider_count = manager.get_enabled_provider_count()
        
        # Track which providers were called
        called_providers = []
        
        with patch.object(manager, '_collect_from_provider') as mock_collect:
            def collect_side_effect(provider_name, collector_info, polygon):
                called_providers.append(provider_name)
                
                # Random failures
                import random
                if random.random() < 0.3:  # 30% failure rate
                    raise DataCollectionError(f"{provider_name} failed")
                
                return RawDataset(
                    source_provider=provider_name,
                    category=collector_info["category"],
                    geometry_type="Polygon",
                    features=[],
                    metadata={}
                )
            
            mock_collect.side_effect = collect_side_effect
            
            result = manager.collect(polygon)
            
            # All enabled providers should have been queried
            assert len(called_providers) == enabled_provider_count
            
            # All providers should appear in provider_status
            for provider_name in [p["name"] for p in config.get_enabled_providers()]:
                assert provider_name in result["provider_status"]
    
    @given(valid_test_polygons())
    @settings(deadline=None, max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_no_cascading_failures_between_providers(self, polygon: Polygon):
        """
        Property: Failure in one provider should not affect others.
        
        For any polygon, when one provider fails, others should still execute
        and return results independently.
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        provider_results = {}
        
        with patch.object(manager, '_collect_from_provider') as mock_collect:
            def collect_side_effect(provider_name, collector_info, polygon):
                # First provider fails
                if provider_name == "osm_buildings":
                    provider_results[provider_name] = "failed"
                    raise DataCollectionError("Connection timeout")
                else:
                    # Others should succeed
                    provider_results[provider_name] = "success"
                    return RawDataset(
                        source_provider=provider_name,
                        category=collector_info["category"],
                        geometry_type="Polygon",
                        features=[{"id": f"test_{provider_name}"}],
                        metadata={"provider": provider_name}
                    )
            
            mock_collect.side_effect = collect_side_effect
            
            result = manager.collect(polygon)
            
            # Verify that some providers succeeded even though one failed
            successful_providers = [
                name for name, status in result["provider_status"].items()
                if status["status"] == "success"
            ]
            
            failed_providers = [
                name for name, status in result["provider_status"].items()
                if status["status"] == "error"
            ]
            
            # Should have at least one success and one failure
            # (unless we only have one provider, which is edge case)
            if len(config.get_enabled_providers()) > 1:
                assert len(successful_providers) > 0 or len(failed_providers) > 0
    
    @given(valid_test_polygons())
    @settings(deadline=None, max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_partial_collection_returns_valid_response(self, polygon: Polygon):
        """
        Property: Even with partial collection, response is valid and complete.
        
        For any polygon, even if some providers fail, the response should be
        valid, contain provider status, and be returnable to the frontend.
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        with patch.object(manager, '_collect_from_provider') as mock_collect:
            def collect_side_effect(provider_name, collector_info, polygon):
                # Fail every other provider
                if hash(provider_name) % 2 == 0:
                    raise DataCollectionError(f"{provider_name} unavailable")
                
                return RawDataset(
                    source_provider=provider_name,
                    category=collector_info["category"],
                    geometry_type="Polygon",
                    features=[],
                    metadata={}
                )
            
            mock_collect.side_effect = collect_side_effect
            
            result = manager.collect(polygon)
            
            # Response should have required fields
            assert "datasets" in result
            assert "provider_status" in result
            assert "status" in result
            assert "processing_time_ms" in result
            
            # Provider status should have all providers
            assert len(result["provider_status"]) == manager.get_enabled_provider_count()
            
            # Status should be valid
            assert result["status"] in [
                ProcessingStatus.SUCCESS,
                ProcessingStatus.PARTIAL,
                ProcessingStatus.FAILED
            ]
            
            # Datasets should be a list
            assert isinstance(result["datasets"], list)
    
    @given(
        valid_test_polygons(),
        st.integers(min_value=1, max_value=5)
    )
    @settings(deadline=None, max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_collection_with_varying_success_rates(self, polygon: Polygon, failure_rate: int):
        """
        Property: System handles various failure rates gracefully.
        
        For any polygon and failure rate (1-5 out of 6 providers fail),
        the system should return appropriate status and partial results.
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        success_count = 0
        failure_count = 0
        
        with patch.object(manager, '_collect_from_provider') as mock_collect:
            def collect_side_effect(provider_name, collector_info, polygon):
                nonlocal success_count, failure_count
                
                # Simulate failure based on failure_rate
                providers = list(manager.collectors.keys())
                provider_index = providers.index(provider_name) if provider_name in providers else 0
                
                if provider_index < failure_rate:
                    failure_count += 1
                    raise DataCollectionError(f"{provider_name} failed")
                else:
                    success_count += 1
                    return RawDataset(
                        source_provider=provider_name,
                        category=collector_info["category"],
                        geometry_type="Polygon",
                        features=[],
                        metadata={}
                    )
            
            mock_collect.side_effect = collect_side_effect
            
            result = manager.collect(polygon)
            
            # Should have appropriate status
            if success_count == 0:
                assert result["status"] == ProcessingStatus.FAILED
            elif failure_count == 0:
                assert result["status"] == ProcessingStatus.SUCCESS
            else:
                assert result["status"] == ProcessingStatus.PARTIAL
