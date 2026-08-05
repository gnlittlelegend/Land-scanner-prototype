"""
Test the /status endpoint implementation (Task 10.3)
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_status_endpoint_returns_200(client):
    """Verify /status endpoint returns HTTP 200"""
    response = client.get("/status")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


def test_status_endpoint_returns_json(client):
    """Verify /status endpoint returns valid JSON"""
    response = client.get("/status")
    data = response.json()
    assert isinstance(data, dict), "Response should be JSON object"


def test_status_endpoint_has_required_fields(client):
    """Verify /status endpoint returns all required fields (Requirement 9.3)"""
    response = client.get("/status")
    data = response.json()
    
    required_fields = [
        "app_name",
        "version",
        "environment",
        "timestamp",
        "system_status",
        "enabled_providers",
        "available_rules",
        "configuration_summary"
    ]
    
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_status_endpoint_has_prototype_version(client):
    """Verify /status endpoint returns prototype version"""
    response = client.get("/status")
    data = response.json()
    
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


def test_status_endpoint_lists_enabled_providers(client):
    """Verify /status endpoint lists enabled data providers"""
    response = client.get("/status")
    data = response.json()
    
    # Should have enabled_providers list
    assert "enabled_providers" in data
    assert isinstance(data["enabled_providers"], list)
    assert len(data["enabled_providers"]) > 0, "Should have at least one enabled provider"
    
    # Each provider should have required fields
    for provider in data["enabled_providers"]:
        required_provider_fields = ["id", "name", "category", "optional", "timeout_seconds", "retry_count", "api_endpoint"]
        for field in required_provider_fields:
            assert field in provider, f"Provider missing field: {field}"


def test_status_endpoint_lists_available_rules(client):
    """Verify /status endpoint lists available rules (Requirement 9.3)"""
    response = client.get("/status")
    data = response.json()
    
    # Should have available_rules list
    assert "available_rules" in data
    assert isinstance(data["available_rules"], list)
    
    # Should have exactly 6 rules
    assert len(data["available_rules"]) == 6, f"Expected 6 rules, got {len(data['available_rules'])}"
    
    # Each rule should have required fields
    for rule in data["available_rules"]:
        required_rule_fields = ["id", "name", "description", "required_data", "status"]
        for field in required_rule_fields:
            assert field in rule, f"Rule missing field: {field}"
    
    # Verify specific rules are present
    rule_ids = [r["id"] for r in data["available_rules"]]
    expected_rules = ["ADM-001", "LC-001", "BLD-001", "RD-001", "WT-001", "ELV-001"]
    for expected_id in expected_rules:
        assert expected_id in rule_ids, f"Missing rule: {expected_id}"


def test_status_endpoint_returns_configuration_summary(client):
    """Verify /status endpoint returns system configuration summary (Requirement 9.3)"""
    response = client.get("/status")
    data = response.json()
    
    # Should have configuration_summary
    assert "configuration_summary" in data
    assert isinstance(data["configuration_summary"], dict)
    
    # Configuration should have expected fields
    config = data["configuration_summary"]
    required_config_fields = [
        "providers_enabled",
        "providers_total",
        "rules_available",
        "default_timeout_seconds",
        "max_polygon_vertices",
        "polygon_area_min_sqm",
        "polygon_area_max_sqkm",
        "rate_limiting"
    ]
    
    for field in required_config_fields:
        assert field in config, f"Configuration missing field: {field}"


def test_status_endpoint_configuration_values_are_valid(client):
    """Verify /status endpoint configuration values are reasonable"""
    response = client.get("/status")
    data = response.json()
    config = data["configuration_summary"]
    
    # Verify numeric values are reasonable
    assert config["default_timeout_seconds"] > 0
    assert config["max_polygon_vertices"] == 10000
    assert config["polygon_area_min_sqm"] == 10
    assert config["polygon_area_max_sqkm"] == 100
    assert config["rules_available"] == 6


def test_status_endpoint_all_rules_have_consistent_structure(client):
    """Verify all rules in /status endpoint have consistent structure"""
    response = client.get("/status")
    data = response.json()
    
    rules = data["available_rules"]
    
    # All rules should have consistent structure
    for rule in rules:
        # All have these fields
        assert "id" in rule and isinstance(rule["id"], str)
        assert "name" in rule and isinstance(rule["name"], str)
        assert "description" in rule and isinstance(rule["description"], str)
        assert "required_data" in rule and isinstance(rule["required_data"], list)
        assert "status" in rule and rule["status"] in ["available", "unavailable"]
        
        # Names and descriptions should be non-empty
        assert len(rule["name"]) > 0
        assert len(rule["description"]) > 0


def test_status_endpoint_providers_have_timeout_values(client):
    """Verify all providers have timeout values from configuration"""
    response = client.get("/status")
    data = response.json()
    
    providers = data["enabled_providers"]
    
    for provider in providers:
        assert "timeout_seconds" in provider
        assert isinstance(provider["timeout_seconds"], int)
        assert provider["timeout_seconds"] > 0, f"Provider {provider['id']} has invalid timeout"
        assert provider["retry_count"] in [0, 1, 2, 3], f"Provider {provider['id']} has invalid retry count"
