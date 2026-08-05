"""Configuration management for Land Scanner"""

import json
import os
from typing import Any, Dict, List, Optional


class ConfigManager:
    """Load and manage application configuration"""

    def __init__(self, config_path: str = "config/settings.json"):
        """Initialize config manager with path to settings file"""
        self.config_path = config_path
        self.config = self._load_config()
        self.providers = self._load_providers()

    def _load_config(self) -> Dict[str, Any]:
        """Load settings from JSON config file"""
        if not os.path.exists(self.config_path):
            return self._get_default_config()

        with open(self.config_path, "r") as f:
            return json.load(f)

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "app": {
                "name": "Land Scanner",
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development"),
            }
        }

    def _load_providers(self) -> List[Dict[str, Any]]:
        """Load provider configurations"""
        # Try to load from external file first
        providers_path = "config/providers.json"
        if os.path.exists(providers_path):
            with open(providers_path, "r") as f:
                data = json.load(f)
                # Handle both list and dict formats
                if isinstance(data, dict):
                    # Convert dict of providers to list
                    return list(data.values())
                else:
                    # Already a list
                    return data

        # Return default provider configuration
        return self._get_default_providers()

    def _get_default_providers(self) -> List[Dict[str, Any]]:
        """Return default provider configurations with real production endpoints"""
        return [
            {
                "id": "osm_buildings",
                "name": "OSM Buildings",
                "enabled": True,
                "category": "buildings",
                "api_endpoint": "http://overpass-api.de/api/interpreter",
                "timeout_seconds": 30,
                "retry_count": 2,
                "rate_limit_delay_ms": 2000,
                "optional": False,
            },
            {
                "id": "admin_boundaries",
                "name": "Admin Boundaries",
                "enabled": True,
                "category": "admin",
                "api_endpoint": "http://overpass-api.de/api/interpreter",
                "timeout_seconds": 30,
                "retry_count": 2,
                "rate_limit_delay_ms": 2000,
                "optional": False,
            },
            {
                "id": "land_cover",
                "name": "Copernicus Land Cover",
                "enabled": True,
                "category": "land_cover",
                "api_endpoint": "https://services.sentinel-hub.com/api/v1/",
                "timeout_seconds": 45,
                "retry_count": 2,
                "optional": True,
            },
            {
                "id": "roads",
                "name": "OSM Roads",
                "enabled": True,
                "category": "roads",
                "api_endpoint": "http://overpass-api.de/api/interpreter",
                "timeout_seconds": 30,
                "retry_count": 2,
                "rate_limit_delay_ms": 2000,
                "optional": False,
            },
            {
                "id": "water",
                "name": "OSM Water",
                "enabled": True,
                "category": "water",
                "api_endpoint": "http://overpass-api.de/api/interpreter",
                "timeout_seconds": 30,
                "retry_count": 2,
                "rate_limit_delay_ms": 2000,
                "optional": False,
            },
            {
                "id": "elevation",
                "name": "USGS Elevation",
                "enabled": True,
                "category": "elevation",
                "api_endpoint": "https://epqs.nationalmap.gov/v1/json",
                "timeout_seconds": 45,
                "retry_count": 2,
                "optional": False,
            },
        ]

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        return self.config

    def get_providers(self) -> List[Dict[str, Any]]:
        """Get all provider configurations"""
        return self.providers

    def get_enabled_providers(self) -> List[Dict[str, Any]]:
        """Get only enabled providers"""
        return [p for p in self.providers if p.get("enabled", False)]

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get specific provider configuration by ID"""
        for provider in self.providers:
            if provider["id"] == provider_id:
                return provider
        return None

    def is_provider_enabled(self, provider_id: str) -> bool:
        """Check if provider is enabled"""
        provider = self.get_provider(provider_id)
        return provider.get("enabled", False) if provider else False

    def is_provider_optional(self, provider_id: str) -> bool:
        """Check if provider is optional"""
        provider = self.get_provider(provider_id)
        return provider.get("optional", False) if provider else False

    def get_app_name(self) -> str:
        """Get application name"""
        return self.config.get("app", {}).get("name", "Land Scanner")

    def get_app_version(self) -> str:
        """Get application version"""
        return self.config.get("app", {}).get("version", "1.0.0")

    def get_environment(self) -> str:
        """Get current environment"""
        return self.config.get("app", {}).get("environment", "development")

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)
        self.config = config

    def save_providers(self, providers: List[Dict[str, Any]]) -> None:
        """Save provider configuration to file"""
        providers_path = "config/providers.json"
        os.makedirs(os.path.dirname(providers_path), exist_ok=True)
        with open(providers_path, "w") as f:
            json.dump(providers, f, indent=2)
        self.providers = providers
