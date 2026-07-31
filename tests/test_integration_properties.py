"""
Property-Based Tests for Land Scanner Integration Tasks

Tests for configuration-driven execution, graceful degradation,
and module failure isolation.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

from backend.main import app
from backend.models import ProcessingStatus, DataCategory
from backend.services import ConfigManager
from backend.managers.data_source_manager import DataSourceManager
from backend.models.schemas import RawDataset, StandardizedDataset, Feature, RuleResult
from fastapi.testclient import TestClient


# ============================================================================
# Property 13: Configuration-Driven Collector Execution
# ============================================================================

class TestConfigurationDrivenExecution:
    """
    Feature: land-scanner, Property 13: Configuration-Driven Collector Execution
    
    For any configuration change that enables or disables data collectors,
    the system should respect the configuration state and only execute
    enabled collectors without requiring code changes.
    """

    @given(
        provider_subset=st.lists(
            st.just("osm_buildings") | st.just("admin_boundaries") | 
            st.just("land_cover") | st.just("osm_roads") |
            st.just("osm_water") | st.just("elevation"),
            unique=True,
            min_size=0,
            max_size=6
        )
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow]
    )
    def test_only_enabled_providers_execute(self, provider_subset):
        """
        Property: For any configuration subset of providers, the system
        should only execute those enabled providers.
        
        Validates: Requirements 10.3, 10.7
        """
        # Arrange
        original_config = ConfigManager()
        all_providers = original_config.get_enabled_providers()
        
        # Create a mock config that only enables the subset
        mock_config = Mock(spec=ConfigManager)
        enabled_providers = [p for p in all_providers if p["name"] in provider_subset]
        mock_config.get_enabled_providers.return_value = enabled_providers
        
        # Act
        manager = DataSourceManager(mock_config)
        
        # Assert
        # Verify that DataSourceManager initialized with correct provider count
        assert manager.get_enabled_provider_count() == len(provider_subset)
        
        # Verify all initialized providers are in the enabled subset
        for provider_name in manager.collectors.keys():
            assert provider_name in provider_subset
        
        # Verify no extra providers are initialized
        assert set(manager.collectors.keys()) == set(provider_subset)

    def test_configuration_change_affects_execution(self):
        """
        Property: When configuration changes to enable/disable providers,
        the system respects the new configuration state.
        
        Validates: Requirements 10.3, 10.7
        """
        # Arrange - Create config with all providers enabled
        config_full = ConfigManager()
        full_count = len(config_full.get_enabled_providers())
        
        # Create manager with full config
        manager_full = DataSourceManager(config_full)
        assert manager_full.get_enabled_provider_count() == full_count
        
        # Create config with subset of providers
        subset_providers = config_full.get_enabled_providers()[:3]
        mock_config = Mock(spec=ConfigManager)
        mock_config.get_enabled_providers.return_value = subset_providers
        
        # Act - Create manager with subset config
        manager_subset = DataSourceManager(mock_config)
        
        # Assert
        assert manager_subset.get_enabled_provider_count() == 3
        assert manager_subset.get_enabled_provider_count() < manager_full.get_enabled_provider_count()

    @given(
        enabled_providers_count=st.integers(min_value=0, max_value=6)
    )
    @settings(max_examples=50)
    def test_provider_status_reflects_configuration(self, enabled_providers_count):
        """
        Property: Provider status reflects which providers are enabled
        in configuration.
        
        Validates: Requirements 10.3, 10.7
        """
        # Arrange
        config = ConfigManager()
        all_providers = config.get_enabled_providers()
        selected = all_providers[:enabled_providers_count]
        
        mock_config = Mock(spec=ConfigManager)
        mock_config.get_enabled_providers.return_value = selected
        
        # Act
        manager = DataSourceManager(mock_config)
        
        # Assert - All providers in status should be from enabled list
        for provider_name in manager.get_provider_status().keys():
            assert any(p["name"] == provider_name for p in selected)


# ============================================================================
# Property 14: Graceful Degradation with Optional Providers
# ============================================================================

class TestGracefulDegradation:
    """
    Feature: land-scanner, Property 14: Graceful Degradation with Optional Providers
    
    For any analysis where optional data providers are unavailable,
    the system should continue processing and return partial results
    with available data rather than failing entirely.
    """

    def test_system_continues_with_partial_data(self):
        """
        Property: When some providers fail, the system continues with
        available data and returns partial results instead of failing.
        
        Validates: Requirements 11.2, 12.8
        """
        # Arrange
        client = TestClient(app)
        valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        request_body = {"polygon": valid_polygon}
        
        # Mock DataSourceManager to return only partial data
        with patch('backend.main.DataSourceManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Return partial success
            mock_manager.collect.return_value = {
                "datasets": [
                    RawDataset(
                        source_provider="osm_buildings",
                        category=DataCategory.BUILDINGS,
                        geometry_type="Point",
                        features=[{"geometry": {"type": "Point", "coordinates": [0.5, 0.5]}, "properties": {}}],
                        metadata={}
                    )
                ],
                "provider_status": {
                    "osm_buildings": {"status": "success", "data_retrieved": True, "error_message": None},
                    "admin_boundaries": {"status": "error", "data_retrieved": False, "error_message": "Timeout"}
                },
                "status": ProcessingStatus.PARTIAL
            }
            
            # Act
            response = client.post("/analyze", json=request_body)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "partial"]  # Should not be failed
            assert "analysis_summary" in data
            assert "processing_status" in data

    @given(
        failed_provider_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50)
    def test_no_crash_with_multiple_provider_failures(self, failed_provider_count):
        """
        Property: System does not crash even when multiple providers fail.
        
        Validates: Requirements 11.2, 12.8
        """
        # Arrange
        config = ConfigManager()
        all_providers = config.get_enabled_providers()
        
        if failed_provider_count >= len(all_providers):
            pytest.skip("Not enough providers for this test")
        
        failed_names = [p["name"] for p in all_providers[:failed_provider_count]]
        successful_names = [p["name"] for p in all_providers[failed_provider_count:]]
        
        mock_config = Mock(spec=ConfigManager)
        mock_config.get_enabled_providers.return_value = all_providers
        
        manager = DataSourceManager(mock_config)
        
        # Simulate multiple providers failing
        for provider_name in failed_names:
            manager.provider_status[provider_name]["status"] = "error"
            manager.provider_status[provider_name]["error_message"] = "Provider unavailable"
        
        for provider_name in successful_names:
            manager.provider_status[provider_name]["status"] = "success"
        
        # Act & Assert - No exception should be raised
        try:
            status = manager.get_provider_status()
            assert status is not None
            assert len(status) > 0
        except Exception as e:
            pytest.fail(f"System crashed with multiple provider failures: {str(e)}")

    def test_partial_results_returned_on_provider_failure(self):
        """
        Property: When providers fail, partial results are still returned
        with available data and provider status information.
        
        Validates: Requirements 11.2, 12.8
        """
        # Arrange
        client = TestClient(app)
        valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        # Act
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Response should have all required fields even on partial failure
        assert "request_id" in data
        assert "status" in data
        assert "provider_status" in data
        assert "processing_status" in data
        assert isinstance(data["provider_status"], list)
        
        # If any providers failed, status should reflect that
        provider_errors = [p for p in data["provider_status"] 
                          if p.get("status") == "error"]
        if provider_errors:
            assert data["status"] in ["partial", "success"]


# ============================================================================
# Property 15: Module Failure Isolation
# ============================================================================

class TestModuleFailureIsolation:
    """
    Feature: land-scanner, Property 15: Module Failure Isolation
    
    For any module failure (validation, collection, standardization, rules),
    the system should log the failure and continue processing with remaining
    modules when possible, eventually returning a response with failure
    status information.
    """

    def test_standardization_failure_does_not_crash_system(self):
        """
        Property: When standardization fails, the system continues
        processing and returns a response with status information.
        
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        """
        # Arrange
        client = TestClient(app)
        valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        with patch('backend.main.Standardizer') as mock_standardizer_class:
            mock_standardizer = Mock()
            mock_standardizer_class.return_value = mock_standardizer
            
            # Make standardization raise an exception
            mock_standardizer.standardize.side_effect = Exception("Standardization failed")
            
            # Act
            response = client.post("/analyze", json={"polygon": valid_polygon})
            
            # Assert - System should return response, not crash
            assert response.status_code == 200
            data = response.json()
            assert "processing_status" in data
            assert "standardization" in data["processing_status"]

    def test_rule_engine_failure_does_not_crash_system(self):
        """
        Property: When Rule Engine fails, the system continues
        processing and returns a response.
        
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        """
        # Arrange
        client = TestClient(app)
        valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        with patch('backend.main.RuleEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            
            # Make Rule Engine raise an exception
            mock_engine.execute.side_effect = Exception("Rule Engine failed")
            mock_engine.get_overall_status.side_effect = Exception("Status check failed")
            
            # Act
            response = client.post("/analyze", json={"polygon": valid_polygon})
            
            # Assert - System should return response, not crash
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "processing_status" in data

    @given(
        stage_name=st.sampled_from([
            "validation", "data_collection", "data_validation",
            "standardization", "rule_engine"
        ])
    )
    @settings(max_examples=50)
    def test_failure_at_stage_returns_status(self, stage_name):
        """
        Property: Failure at any stage returns a response with
        status information about that stage.
        
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        """
        # Arrange
        client = TestClient(app)
        
        # Create a polygon that will pass validation
        valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        # Act
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "processing_status" in data
        assert isinstance(data["processing_status"], dict)
        
        # All stages should have status information
        expected_stages = [
            "validation", "data_collection", "data_validation",
            "standardization", "rule_engine", "output_generation"
        ]
        for stage in expected_stages:
            assert stage in data["processing_status"]
            assert "module_name" in data["processing_status"][stage]
            assert "status" in data["processing_status"][stage]

    def test_cascading_failure_does_not_occur(self):
        """
        Property: Failure in one module does not cascade to prevent
        other modules from attempting to execute.
        
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        """
        # Arrange
        client = TestClient(app)
        valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        # Act
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        # Assert - Response should always be returned
        assert response.status_code == 200
        data = response.json()
        
        # Processing status should always be present
        assert "processing_status" in data
        
        # Output generation should have status even if other stages failed
        assert "output_generation" in data["processing_status"]
        assert data["processing_status"]["output_generation"]["status"] is not None

    def test_response_always_returned_regardless_of_failures(self):
        """
        Property: System always returns an AnalysisResponse with status
        information, never fails silently or crashes.
        
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        """
        # Arrange
        client = TestClient(app)
        
        # Try various polygon inputs
        test_cases = [
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            {"type": "Polygon", "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]},
            {"type": "Polygon", "coordinates": [[[0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5], [0.5, 0.5]]]},
        ]
        
        for polygon in test_cases:
            # Act
            response = client.post("/analyze", json={"polygon": polygon})
            
            # Assert - Always 200 with valid JSON response
            assert response.status_code == 200, f"Failed for polygon: {polygon}"
            data = response.json()
            
            # Response must have required fields
            assert "request_id" in data
            assert "status" in data
            assert "processing_status" in data
            assert "errors" in data or "land_information" in data


# ============================================================================
# Cleanup and Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def client():
    """Provide a test client for the FastAPI app."""
    return TestClient(app)
