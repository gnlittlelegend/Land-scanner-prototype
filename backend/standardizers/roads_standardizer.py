"""
Road Network-specific field normalization.

Maps provider-specific road fields to common standardized schema.
Handles road data from OpenStreetMap and other providers.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class RoadsStandardizer:
    """
    Standardizes road network properties from various providers.
    
    Handles:
    - OpenStreetMap road data
    - Road classification and hierarchy
    - Road surface and condition
    - Traffic information
    """

    # Standardized road types hierarchy
    ROAD_TYPES = {
        # Major highways
        "motorway": "motorway",
        "motorway_link": "motorway",
        "trunk": "trunk",
        "trunk_link": "trunk",
        
        # Primary roads
        "primary": "primary",
        "primary_link": "primary",
        
        # Secondary roads
        "secondary": "secondary",
        "secondary_link": "secondary",
        
        # Tertiary roads
        "tertiary": "tertiary",
        "tertiary_link": "tertiary",
        
        # Local roads
        "unclassified": "local",
        "residential": "local",
        "living_street": "local",
        "service": "service",
        "track": "track",
        "path": "path",
        "footway": "footway",
        "cycleway": "cycleway",
        "pedestrian": "pedestrian",
        
        # Other
        "road": "road",
        "unknown": "unknown",
    }

    # Road surface types
    SURFACE_TYPES = {
        "asphalt": "paved",
        "concrete": "paved",
        "paving_stones": "paved",
        "cobblestone": "paved",
        "sett": "paved",
        "brick": "paved",
        "compacted": "unpaved",
        "dirt": "unpaved",
        "earth": "unpaved",
        "gravel": "unpaved",
        "pebblestone": "unpaved",
        "sand": "unpaved",
        "unpaved": "unpaved",
        "unknown": "unknown",
    }

    # Mapping of provider-specific field names to standardized names
    FIELD_MAPPINGS = {
        # Road type/classification
        ("highway", "road_type", "classification"): "road_type",
        ("highway:type",): "road_type",
        
        # Road name and designation
        ("name", "road_name"): "name",
        ("ref", "designation", "route_number"): "ref",
        ("route_number",): "ref",
        
        # Road metrics
        ("lanes", "num_lanes", "lanes:forward", "lanes:backward"): "lanes",
        ("length", "length_km"): "length_km",
        ("width", "width_m"): "width_m",
        ("maxspeed", "speed_limit", "max_speed"): "max_speed_kmh",
        
        # Road surface
        ("surface", "surface_type", "paving"): "surface",
        ("smoothness",): "smoothness",
        
        # Accessibility
        ("oneway", "one_way"): "oneway",
        ("access", "vehicle_access"): "access",
        ("foot", "foot_access"): "foot",
        ("bicycle", "bicycle_access"): "bicycle",
        ("motor_vehicle", "motorcar"): "motor_vehicle",
        
        # Condition and maintenance
        ("condition", "road_condition"): "condition",
        ("informal", "is_informal"): "informal",
        ("lit", "street_lights", "is_lit"): "lit",
        
        # Toll and payment
        ("toll", "has_toll", "toll_road"): "toll",
        
        # Traffic information
        ("maxaxleload", "max_axle_load"): "max_axle_load",
        ("maxweight", "max_weight"): "max_weight_kg",
        ("maxheight", "max_height"): "max_height_m",
        ("maxwidth", "max_width"): "max_width_m",
        
        # Historical and administrative
        ("destination", "route_destination"): "destination",
        ("route", "route_ref"): "route",
        ("network", "road_network"): "network",
        
        # Metadata
        ("source", "data_source"): "source",
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
        Standardize road network properties.
        
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

        # Handle road type normalization
        if field_name == "road_type":
            return cls._normalize_road_type(value)
        
        # Handle surface normalization
        if field_name == "surface":
            return cls._normalize_surface(value)
        
        # Handle numeric fields
        if field_name in [
            "lanes",
            "length_km",
            "width_m",
            "max_speed_kmh",
            "max_axle_load",
            "max_weight_kg",
            "max_height_m",
            "max_width_m"
        ]:
            return cls._normalize_numeric(value)
        
        # Handle boolean fields
        if field_name in ["oneway", "toll", "informal", "lit", "motor_vehicle"]:
            return cls._normalize_boolean(value)
        
        # Handle access type normalization
        if "access" in field_name:
            return cls._normalize_access(value)
        
        # Handle condition normalization
        if field_name == "condition":
            return cls._normalize_condition(value)
        
        # Handle smoothness
        if field_name == "smoothness":
            return cls._normalize_smoothness(value)
        
        # Keep as string for other fields
        if isinstance(value, str):
            return value.strip()
        
        return value

    @classmethod
    def _normalize_road_type(cls, value: Any) -> str:
        """
        Normalize road type to standardized category.
        
        Args:
            value: Raw road type value
            
        Returns:
            Standardized road type
        """
        if not value:
            return "unknown"
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_")
        
        # Check if already standardized
        if value_str in cls.ROAD_TYPES.values():
            return value_str
        
        # Check mapping
        return cls.ROAD_TYPES.get(value_str, "unknown")

    @classmethod
    def _normalize_surface(cls, value: Any) -> str:
        """
        Normalize surface type to paved/unpaved category.
        
        Args:
            value: Raw surface value
            
        Returns:
            Standardized surface type
        """
        if not value:
            return "unknown"
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_")
        
        # Check mapping
        return cls.SURFACE_TYPES.get(value_str, "unknown")

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
            # Handle string values with units (e.g., "30m", "50km/h")
            if isinstance(value, str):
                value_str = value.strip().lower()
                # Remove common units
                for unit in ["m", "meter", "meters", "km", "kilometer", "kilometers", 
                           "ft", "feet", "'", "cm", "kmh", "km/h", "mph"]:
                    if value_str.endswith(unit):
                        value_str = value_str[:-len(unit)].strip()
                        break
                numeric_value = float(value_str)
            else:
                numeric_value = float(value)
            
            # Ensure non-negative for physical measurements
            if numeric_value < 0:
                return None
            return numeric_value
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
            return value_lower in ("true", "yes", "1", "-1")
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return False

    @classmethod
    def _normalize_access(cls, value: Any) -> str:
        """
        Normalize access type value.
        
        Args:
            value: Raw access value
            
        Returns:
            Normalized access value
        """
        if not value:
            return None
        
        value_str = str(value).lower().strip()
        
        # Common access values
        access_types = {
            "yes": "yes",
            "no": "no",
            "permit": "permit",
            "customers": "customers",
            "private": "private",
            "unknown": "unknown",
        }
        
        return access_types.get(value_str, value_str)

    @classmethod
    def _normalize_condition(cls, value: Any) -> str:
        """
        Normalize road condition.
        
        Args:
            value: Raw condition value
            
        Returns:
            Normalized condition
        """
        if not value:
            return None
        
        value_str = str(value).lower().strip()
        
        # Standardize condition values
        conditions = {
            "excellent": "excellent",
            "good": "good",
            "intermediate": "intermediate",
            "poor": "poor",
            "very_poor": "very_poor",
            "impassable": "impassable",
        }
        
        return conditions.get(value_str, value_str)

    @classmethod
    def _normalize_smoothness(cls, value: Any) -> str:
        """
        Normalize smoothness value.
        
        Args:
            value: Raw smoothness value
            
        Returns:
            Normalized smoothness
        """
        if not value:
            return None
        
        value_str = str(value).lower().strip()
        
        # OSM smoothness scale
        smoothness_types = {
            "excellent": "excellent",
            "good": "good",
            "intermediate": "intermediate",
            "bad": "bad",
            "very_bad": "very_bad",
            "horrible": "horrible",
            "very_horrible": "very_horrible",
            "impassable": "impassable",
        }
        
        return smoothness_types.get(value_str, value_str)
