"""
Water Bodies-specific field normalization.

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
    - OpenStreetMap water features
    - Water type classification
    - Water body attributes (depth, temperature, etc.)
    """

    # Standardized water types
    WATER_TYPES = {
        # Natural water bodies
        "river": "river",
        "stream": "stream",
        "creek": "stream",
        "brook": "stream",
        "canal": "canal",
        "drain": "drain",
        "ditch": "ditch",
        
        # Lakes and reservoirs
        "lake": "lake",
        "pond": "pond",
        "water_tank": "pond",
        "reservoir": "reservoir",
        "dam": "dam",
        
        # Wetlands
        "wetland": "wetland",
        "marsh": "wetland",
        "swamp": "wetland",
        "bog": "wetland",
        "fen": "wetland",
        "mangrove": "wetland",
        
        # Coastal and tidal
        "bay": "bay",
        "estuary": "estuary",
        "lagoon": "lagoon",
        "moat": "moat",
        
        # Other
        "water": "water",
        "waterway": "water",
        "unknown": "unknown",
    }

    # Water feature types
    FEATURE_TYPES = {
        "waterway": "waterway",
        "natural": "natural",
        "water": "water",
        "man_made": "man_made",
    }

    # Mapping of provider-specific field names to standardized names
    FIELD_MAPPINGS = {
        # Water type and classification
        ("water", "type", "water_type", "waterway"): "water_type",
        ("water:type",): "water_type",
        ("name",): "name",
        
        # Feature type
        ("feature_type", "feature", "primary_tag"): "feature_type",
        
        # Water characteristics
        ("depth", "depth_m", "max_depth"): "depth_m",
        ("depth_min", "min_depth"): "min_depth_m",
        ("width", "width_m", "avg_width"): "width_m",
        ("length", "length_km"): "length_km",
        ("area", "area_sqkm"): "area_sqkm",
        ("volume", "volume_cubic_m"): "volume_cubic_m",
        
        # Flow characteristics
        ("flow", "permanent", "intermittent"): "flow_type",
        ("tidal", "is_tidal"): "tidal",
        ("salt_water", "saline", "is_saline"): "saline",
        ("seasonal", "is_seasonal"): "seasonal",
        
        # Water quality
        ("water_quality", "quality"): "water_quality",
        ("temperature", "temperature_c"): "temperature_c",
        ("ph",): "ph",
        
        # Use and access
        ("use", "water_use", "usage"): "use",
        ("access", "public_access"): "access",
        ("swimming", "is_swimmable"): "swimming",
        ("fishing", "is_fishable"): "fishing",
        ("boating", "is_boatable"): "boating",
        
        # Management
        ("owner", "ownership"): "owner",
        ("managed_by", "manager"): "managed_by",
        ("protected_status",): "protected_status",
        ("conservation_status",): "conservation_status",
        
        # Environmental info
        ("species", "flora", "fauna"): "species",
        ("habitat",): "habitat",
        ("contamination", "pollution_level"): "contamination",
        
        # Source and data
        ("source", "data_source", "provider"): "source",
        ("version",): "version",
        ("timestamp",): "timestamp",
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

        # Map provider-specific fields to standardized names
        for raw_key, raw_value in raw_properties.items():
            standardized_key = cls._get_standardized_key(raw_key)
            
            if standardized_key:
                # Apply value normalization based on field type
                standardized_value = cls._normalize_value(
                    standardized_key,
                    raw_value
                )
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
    def _normalize_value(cls, field_name: str, value: Any) -> Any:
        """
        Normalize property values based on field type.
        
        Args:
            field_name: Standardized field name
            value: Raw value from provider
            
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
            "seasonal",
            "swimming",
            "fishing",
            "boating"
        ]:
            return cls._normalize_boolean(value)
        
        # Handle flow type normalization
        if field_name == "flow_type":
            return cls._normalize_flow_type(value)
        
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
        if value_str in cls.WATER_TYPES.values():
            return value_str
        
        # Check mapping
        return cls.WATER_TYPES.get(value_str, "unknown")

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
        
        return cls.FEATURE_TYPES.get(value_str, value_str)

    @classmethod
    def _normalize_numeric(cls, value: Any) -> float:
        """
        Normalize numeric values.
        
        Args:
            value: Raw numeric value
            
        Returns:
            Normalized numeric value, or None if cannot convert
        """
        try:
            return float(value)
        except (ValueError, TypeError):
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
    def _normalize_flow_type(cls, value: Any) -> str:
        """
        Normalize flow type.
        
        Args:
            value: Raw flow type
            
        Returns:
            Standardized flow type
        """
        if not value:
            return None
        
        value_str = str(value).lower().strip()
        
        flow_types = {
            "permanent": "permanent",
            "intermittent": "intermittent",
            "seasonal": "seasonal",
            "tidal": "tidal",
        }
        
        return flow_types.get(value_str, value_str)

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
        
        access_types = {
            "public": "public",
            "private": "private",
            "permit": "permit",
            "restricted": "restricted",
        }
        
        return access_types.get(value_str, value_str)

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
        
        use_types = {
            "drinking_water": "drinking_water",
            "irrigation": "irrigation",
            "industrial": "industrial",
            "recreation": "recreation",
            "navigation": "navigation",
            "power_generation": "power_generation",
            "aquaculture": "aquaculture",
            "waste": "waste",
            "other": "other",
        }
        
        return use_types.get(value_str, value_str)
