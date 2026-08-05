"""
Water Bodies-specific field normalization for data standardization.

Maps provider-specific water fields to common standardized schema.
Handles water data from OpenStreetMap and other providers.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class WaterStandardizer:
    """
    Standardizes water body properties from various providers.
    
    Handles:
    - OpenStreetMap water features (rivers, streams, lakes, reservoirs, canals, wetlands)
    - Water type classification (natural vs man-made)
    - Water body attributes (depth, width, flow type, salinity, etc.)
    - Water use and access information
    """

    # Standardized water types mapping from various provider formats
    WATER_TYPE_MAPPING = {
        # Natural flowing water
        "river": "river",
        "stream": "stream",
        "creek": "stream",
        "brook": "stream",
        "tributary": "stream",
        "arroyo": "stream",
        "wadi": "stream",
        
        # Man-made water features
        "canal": "canal",
        "drain": "drain",
        "ditch": "ditch",
        "channel": "channel",
        
        # Still water bodies - natural
        "lake": "lake",
        "pond": "pond",
        "water": "water_body",  # Generic water
        
        # Still water bodies - man-made
        "reservoir": "reservoir",
        "dam": "dam",
        "water_tank": "water_tank",
        "pool": "pool",
        
        # Wetlands
        "wetland": "wetland",
        "marsh": "wetland",
        "swamp": "wetland",
        "bog": "wetland",
        "fen": "wetland",
        "mangrove": "wetland",
        "salt_marsh": "wetland",
        
        # Coastal and tidal
        "bay": "bay",
        "estuary": "estuary",
        "lagoon": "lagoon",
        "gulf": "bay",
        "moat": "moat",
        
        # Other
        "waterway": "waterway",
        "unknown": "unknown",
        "other": "other",
    }

    # Feature type classification
    FEATURE_TYPE_MAPPING = {
        "waterway": "waterway",
        "natural": "natural",
        "water": "water",
        "man_made": "man_made",
        "water_well": "water_well",
        "spring": "spring",
    }

    # Flow type classification
    FLOW_TYPE_MAPPING = {
        "permanent": "permanent",
        "intermittent": "intermittent",
        "seasonal": "seasonal",
        "ephemeral": "ephemeral",
        "tidal": "tidal",
        "yes": "intermittent",  # "intermittent: yes" means is intermittent
        "no": "permanent",      # "intermittent: no" means is permanent
    }

    # Access type standardization
    ACCESS_MAPPING = {
        "public": "public",
        "private": "private",
        "permit": "permit",
        "restricted": "restricted",
        "designated": "designated",
        "unknown": "unknown",
    }

    # Water use classification
    USE_MAPPING = {
        "drinking_water": "drinking_water",
        "drinking": "drinking_water",
        "irrigation": "irrigation",
        "industrial": "industrial",
        "recreation": "recreation",
        "navigation": "navigation",
        "fishing": "fishing",
        "power_generation": "power_generation",
        "aquaculture": "aquaculture",
        "hydroelectric": "power_generation",
        "waste": "waste",
        "other": "other",
    }

    # Mapping of provider-specific field names to standardized names
    # Key: tuple of (provider_patterns), Value: standardized_field_name
    FIELD_MAPPINGS = {
        # Water type and classification
        ("waterway", "water:type", "water_type", "type"): "water_type",
        
        # Name
        ("name",): "name",
        
        # Feature type (how water is categorized)
        ("feature_type", "feature", "primary_tag"): "feature_type",
        
        # Water characteristics - dimensions
        ("depth", "depth_m", "max_depth", "water:depth"): "depth_m",
        ("depth_min", "min_depth", "water:depth_min"): "min_depth_m",
        ("width", "width_m", "avg_width", "water:width"): "width_m",
        ("length", "length_km", "length", "water:length"): "length_km",
        ("area", "area_sqkm", "area_km2", "water:area"): "area_sqkm",
        ("volume", "volume_cubic_m", "volume_m3"): "volume_cubic_m",
        
        # Flow characteristics
        ("intermittent", "seasonal", "flow", "water:intermittent"): "flow_type",
        ("tidal", "is_tidal", "water:tidal"): "tidal",
        ("salt_water", "saline", "is_saline", "water:saline"): "saline",
        
        # Water quality
        ("water_quality", "quality", "water_quality_grade"): "water_quality",
        ("temperature", "temperature_c", "temp_c", "water:temperature"): "temperature_c",
        ("ph", "ph_value", "water:ph"): "ph",
        
        # Use and access
        ("use", "water_use", "usage", "water:use"): "use",
        ("access", "public_access", "water:access"): "access",
        ("swimming", "is_swimmable", "water:swimming"): "swimming",
        ("fishing", "is_fishable", "water:fishing"): "fishing",
        ("boating", "is_boatable", "water:boating"): "boating",
        
        # Management
        ("owner", "ownership", "water:owner"): "owner",
        ("managed_by", "manager", "water:managed_by"): "managed_by",
        ("protected_status", "protection_level"): "protected_status",
        ("conservation_status", "conservation"): "conservation_status",
        
        # Environmental info
        ("species", "flora", "fauna"): "species",
        ("habitat", "ecosystem", "water:habitat"): "habitat",
        ("contamination", "pollution_level", "water:pollution"): "contamination",
        
        # Source and data
        ("source", "data_source", "provider", "ref", "reference"): "source",
        ("version", "data_version"): "version",
        ("timestamp", "date", "last_updated"): "timestamp",
    }

    @classmethod
    def standardize_properties(
        cls,
        raw_properties: Dict[str, Any],
        provider: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Standardize water body properties.
        
        Args:
            raw_properties: Raw properties from provider
            provider: Provider name (for logging)
            
        Returns:
            Standardized properties dictionary
        """
        standardized = {}

        # Always include name if present
        if "name" in raw_properties and raw_properties["name"]:
            standardized["name"] = str(raw_properties["name"]).strip()

        # Map provider-specific fields to standardized names
        for raw_key, raw_value in raw_properties.items():
            if raw_key == "name":
                continue  # Already handled
                
            standardized_key = cls._get_standardized_key(raw_key)
            
            if standardized_key:
                # Apply value normalization based on field type
                standardized_value = cls._normalize_value(
                    standardized_key,
                    raw_value,
                    raw_key
                )
                if standardized_value is not None:
                    standardized[standardized_key] = standardized_value

        return standardized

    @classmethod
    def _get_standardized_key(cls, raw_key: str) -> str:
        """
        Map a raw property key to standardized name.
        
        Args:
            raw_key: Raw property key from provider
            
        Returns:
            Standardized key name, or empty string if not recognized
        """
        raw_key_lower = raw_key.lower().replace("-", "_").replace(".", "_").replace(" ", "_")
        
        # Check direct mapping
        for provider_keys, standardized_key in cls.FIELD_MAPPINGS.items():
            if raw_key_lower in provider_keys:
                return standardized_key
        
        # No mapping found
        return ""

    @classmethod
    def _normalize_value(cls, field_name: str, value: Any, raw_key: str = "") -> Any:
        """
        Normalize property values based on field type.
        
        Args:
            field_name: Standardized field name
            value: Raw value from provider
            raw_key: Original raw field name (for context)
            
        Returns:
            Normalized value
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        # Handle water type normalization
        if field_name == "water_type":
            return cls._normalize_water_type(value)
        
        # Handle feature type normalization
        if field_name == "feature_type":
            return cls._normalize_feature_type(value)
        
        # Handle numeric fields (measurements)
        if field_name in [
            "depth_m",
            "min_depth_m",
            "width_m",
            "length_km",
            "area_sqkm",
            "volume_cubic_m",
            "temperature_c",
            "ph"
        ]:
            return cls._normalize_numeric(value)
        
        # Handle boolean fields
        if field_name in [
            "tidal",
            "saline",
            "swimming",
            "fishing",
            "boating"
        ]:
            return cls._normalize_boolean(value)
        
        # Handle flow type normalization (special handling for raw key)
        if field_name == "flow_type":
            return cls._normalize_flow_type(value, raw_key)
        
        # Handle access normalization
        if field_name == "access":
            return cls._normalize_access(value)
        
        # Handle use normalization
        if field_name == "use":
            return cls._normalize_use(value)
        
        # Keep as string for other fields
        if isinstance(value, str):
            return value.strip()
        
        return value

    @classmethod
    def _normalize_water_type(cls, value: Any) -> str:
        """
        Normalize water type to standardized category.
        
        Args:
            value: Raw water type value
            
        Returns:
            Standardized water type
        """
        if not value:
            return "unknown"
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_")
        
        # Check if already standardized
        if value_str in cls.WATER_TYPE_MAPPING.values():
            return value_str
        
        # Check mapping
        return cls.WATER_TYPE_MAPPING.get(value_str, "unknown")

    @classmethod
    def _normalize_feature_type(cls, value: Any) -> str:
        """
        Normalize feature type.
        
        Args:
            value: Raw feature type
            
        Returns:
            Standardized feature type
        """
        if not value:
            return None
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_")
        
        return cls.FEATURE_TYPE_MAPPING.get(value_str, value_str)

    @classmethod
    def _normalize_numeric(cls, value: Any) -> float:
        """
        Normalize numeric values.
        
        Args:
            value: Raw numeric value (can include units like "30m")
            
        Returns:
            Normalized numeric value, or None if cannot convert
        """
        try:
            # Handle string values with units (e.g., "30m")
            if isinstance(value, str):
                # Remove common units
                value_str = value.strip().lower()
                for unit in ["m", "meter", "meters", "ft", "feet", "'", "cm", "km"]:
                    if value_str.endswith(unit):
                        value_str = value_str[:-len(unit)].strip()
                        break
                return float(value_str)
            return float(value)
        except (ValueError, TypeError, AttributeError):
            return None

    @classmethod
    def _normalize_boolean(cls, value: Any) -> bool:
        """
        Normalize boolean values.
        
        Args:
            value: Raw boolean value
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower()
            return value_lower in ("true", "yes", "1")
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return False

    @classmethod
    def _normalize_flow_type(cls, value: Any, raw_key: str = "") -> str:
        """
        Normalize flow type.
        
        Special handling:
        - If raw_key is "seasonal" and value is "yes", return "seasonal"
        - If raw_key is "intermittent" and value is "no", return "permanent"
        - If raw_key is "intermittent" and value is "yes", return "intermittent"
        
        Args:
            value: Raw flow type
            raw_key: Original raw field name (for context)
            
        Returns:
            Standardized flow type
        """
        if not value:
            return None
        
        raw_key_lower = str(raw_key).lower() if raw_key else ""
        value_str = str(value).lower().strip()
        
        # Special handling: if field name indicates the flow type, use that
        if raw_key_lower == "seasonal":
            # "seasonal" field with "yes" means seasonal flow
            if value_str in ("yes", "true", "1"):
                return "seasonal"
            else:
                return "permanent"  # "seasonal: no" means permanent
        
        if raw_key_lower == "intermittent":
            # "intermittent" field
            if value_str in ("yes", "true", "1"):
                return "intermittent"
            else:
                return "permanent"  # "intermittent: no" means permanent
        
        # Default mapping for other flow field names
        return cls.FLOW_TYPE_MAPPING.get(value_str, value_str)

    @classmethod
    def _normalize_access(cls, value: Any) -> str:
        """
        Normalize access value.
        
        Args:
            value: Raw access value
            
        Returns:
            Normalized access
        """
        if not value:
            return None
        
        value_str = str(value).lower().strip()
        
        return cls.ACCESS_MAPPING.get(value_str, value_str)

    @classmethod
    def _normalize_use(cls, value: Any) -> str:
        """
        Normalize water use/purpose.
        
        Args:
            value: Raw use value
            
        Returns:
            Normalized use
        """
        if not value:
            return None
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_").strip()
        
        return cls.USE_MAPPING.get(value_str, value_str)
