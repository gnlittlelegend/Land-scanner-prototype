"""
Configuration Manager for Land Scanner Prototype.
Loads and manages application settings and provider configuration.
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class ConfigManager:
    """Manages application configuration from external files."""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.settings = {}
        self.providers = {}
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load all configuration from files."""
        settings_file = self.config_dir / "settings.json"
        providers_file = self.config_dir / "providers.json"
        
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                self.settings = json.load(f)
        else:
            self._create_default_settings()
        
        if providers_file.exists():
            with open(providers_file, 'r') as f:
                providers_config = json.load(f)
                self.providers = {p["name"]: p for p in providers_config}
        else:
            self._create_default_providers()
    
    def _create_default_settings(self) -> None:
        """Create default settings if file doesn't exist."""
        self.settings = {
            "app": {
                "name": "Land Scanner",
                "version": "1.0.0",
                "debug": False
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000
            }
        }
        self._save_settings()
    
    def _create_default_providers(self) -> None:
        """Create default provider configuration if file doesn't exist."""
        default_providers = [
            {
                "name": "osm_buildings",
                "enabled": True,
                "category": "buildings",
                "timeout_seconds": 30,
                "retry_count": 2,
                "collector_class": "OSMBuildingsCollector"
            },
            {
                "name": "admin_boundaries",
                "enabled": True,
                "category": "admin",
                "timeout_seconds": 30,
                "retry_count": 2,
                "collector_class": "AdminBoundariesCollector"
            },
            {
                "name": "land_cover",
                "enabled": True,
                "category": "land_cover",
                "timeout_seconds": 60,
                "retry_count": 2,
                "collector_class": "LandCoverCollector"
            },
            {
                "name": "osm_roads",
                "enabled": True,
                "category": "roads",
                "timeout_seconds": 30,
                "retry_count": 2,
                "collector_class": "OSMRoadsCollector"
            },
            {
                "name": "osm_water",
                "enabled": True,
                "category": "water",
                "timeout_seconds": 30,
                "retry_count": 2,
                "collector_class": "OSMWaterCollector"
            },
            {
                "name": "elevation",
                "enabled": True,
                "category": "elevation",
                "timeout_seconds": 60,
                "retry_count": 2,
                "collector_class": "ElevationCollector"
            }
        ]
        
        self.providers = {p["name"]: p for p in default_providers}
        self._save_providers()
    
    def _save_settings(self) -> None:
        """Save settings to file."""
        self.config_dir.mkdir(exist_ok=True, parents=True)
        with open(self.config_dir / "settings.json", 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def _save_providers(self) -> None:
        """Save provider configuration to file."""
        self.config_dir.mkdir(exist_ok=True, parents=True)
        providers_list = list(self.providers.values())
        with open(self.config_dir / "providers.json", 'w') as f:
            json.dump(providers_list, f, indent=2)
    
    def get_setting(self, path: str, default: Any = None) -> Any:
        """
        Get a setting value using dot notation.
        
        Args:
            path: Setting path (e.g., "app.name" or "api.port")
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        keys = path.split(".")
        value = self.settings
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_enabled_providers(self) -> List[Dict[str, Any]]:
        """
        Get list of enabled data providers.
        
        Returns:
            List of enabled provider configurations
        """
        return [p for p in self.providers.values() if p.get("enabled", True)]
    
    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider configuration or None if not found
        """
        return self.providers.get(provider_name)
    
    def is_provider_enabled(self, provider_name: str) -> bool:
        """
        Check if a provider is enabled.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            True if provider is enabled, False otherwise
        """
        provider = self.get_provider_config(provider_name)
        return provider is not None and provider.get("enabled", True)
    
    def enable_provider(self, provider_name: str) -> None:
        """Enable a data provider."""
        if provider_name in self.providers:
            self.providers[provider_name]["enabled"] = True
            self._save_providers()
    
    def disable_provider(self, provider_name: str) -> None:
        """Disable a data provider."""
        if provider_name in self.providers:
            self.providers[provider_name]["enabled"] = False
            self._save_providers()
    
    def get_app_version(self) -> str:
        """Get application version."""
        return self.get_setting("app.version", "1.0.0")
    
    def get_app_name(self) -> str:
        """Get application name."""
        return self.get_setting("app.name", "Land Scanner")
    
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get_setting("app.debug", False)
