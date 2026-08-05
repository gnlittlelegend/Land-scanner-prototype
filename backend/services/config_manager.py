"""
Configuration manager for Land Scanner Prototype.

Handles loading and managing configuration from external config files.
Supports provider configuration with real API endpoints.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Loads and manages system configuration.
    
    Reads from config/settings.json for general settings and
    config/providers.json for provider specifications with real endpoints.
    """

    def __init__(self, config_dir: str = "config"):
        """
        Initialize ConfigManager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.settings = {}
        self.providers = {}
        self._load_configuration()

    def _load_configuration(self):
        """Load all configuration files."""
        self._load_settings()
        self._load_providers()

    def _load_settings(self):
        """Load general settings from config/settings.json."""
        settings_file = self.config_dir / "settings.json"
        
        if not settings_file.exists():
            logger.warning(f"Settings file not found at {settings_file}, using defaults")
            self.settings = self._get_default_settings()
            return

        try:
            with open(settings_file, 'r') as f:
                self.settings = json.load(f)
            logger.info(f"Loaded settings from {settings_file}")
        except Exception as e:
            logger.error(f"Failed to load settings file: {e}")
            self.settings = self._get_default_settings()

    def _load_providers(self):
        """Load provider configuration from config/providers.json."""
        providers_file = self.config_dir / "providers.json"
        
        if not providers_file.exists():
            logger.warning(f"Providers file not found at {providers_file}, using defaults")
            self.providers = self._get_default_providers()
            return

        try:
            with open(providers_file, 'r') as f:
                data = json.load(f)
            
            # Support both array and dict formats
            if isinstance(data, list):
                # Convert array format to dict using 'id' as key
                self.providers = {item['id']: item for item in data}
            else:
                self.providers = data
                
            logger.info(f"Loaded providers from {providers_file}")
        except Exception as e:
            logger.error(f"Failed to load providers file: {e}")
            self.providers = self._get_default_providers()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Return default settings."""
        return {
            "timeout": 30,
            "retry_count": 3,
            "rate_limit_delay": 2,
            "max_polygon_area_sqkm": 100,
            "min_polygon_area_sqkm": 0.00001,
            "max_vertices": 10000
        }

    def _get_default_providers(self) -> Dict[str, Any]:
        """Return default provider configuration with real production endpoints."""
        return {
            "osm_buildings": {
                "enabled": True,
                "endpoint": "http://overpass-api.de/api/interpreter",
                "name": "OpenStreetMap Buildings",
                "timeout": 30,
                "optional": False
            },
            "admin_boundaries": {
                "enabled": True,
                "endpoint": "http://overpass-api.de/api/interpreter",
                "name": "OpenStreetMap Admin Boundaries",
                "timeout": 30,
                "optional": False
            },
            "land_cover": {
                "enabled": True,
                "endpoint": "https://stac.oam.dev",
                "name": "Copernicus Land Cover",
                "timeout": 60,
                "optional": True
            },
            "roads": {
                "enabled": True,
                "endpoint": "http://overpass-api.de/api/interpreter",
                "name": "OpenStreetMap Roads",
                "timeout": 30,
                "optional": False
            },
            "water": {
                "enabled": True,
                "endpoint": "http://overpass-api.de/api/interpreter",
                "name": "OpenStreetMap Water",
                "timeout": 30,
                "optional": False
            },
            "elevation": {
                "enabled": True,
                "endpoint": "https://epqs.nationalmap.gov/v1/json",
                "name": "USGS Elevation",
                "timeout": 30,
                "optional": False
            }
        }

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)

    def get_provider(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get provider configuration."""
        return self.providers.get(provider_name)

    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled."""
        provider = self.get_provider(provider_name)
        return provider is not None and provider.get("enabled", False)

    def get_enabled_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled providers."""
        return {
            name: config
            for name, config in self.providers.items()
            if config.get("enabled", False)
        }

    def get_provider_endpoint(self, provider_name: str) -> Optional[str]:
        """Get the endpoint URL for a provider."""
        provider = self.get_provider(provider_name)
        return provider.get("endpoint") if provider else None

    def get_provider_timeout(self, provider_name: str) -> int:
        """Get timeout for a provider."""
        provider = self.get_provider(provider_name)
        return provider.get("timeout", self.get_setting("timeout", 30))
