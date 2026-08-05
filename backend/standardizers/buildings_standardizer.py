"""
Buildings-specific field normalization for data standardization.

Maps provider-specific building fields to common standardized schema.
Handles buildings from OpenStreetMap and other providers.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class BuildingsStandardizer:
    """
    Standardizes building-specific properties from various providers.
    
    Handles:
    - OpenStreetMap buildings
    - Building-specific field names (roof_type, height, levels, etc.)
    - Building classification (residential, commercial, industrial, etc.)
    - Building metrics (area, perimeter, if available)
    """

    # Mapping of provider-specific field names to standardized names
    # Key: tuple of (provider_patterns), Value: standardized_field_name
    FIELD_MAPPINGS = {
        # OSM building type/category fields
        ("building", "building_type", "type"): "building_type",
        ("building:type",): "building_type",
        
        # Building height/levels
        ("building:levels", "levels", "stories", "num_floors"): "building_levels",
        ("building:height", "height", "height_m"): "building_height_m",
        ("roof:height", "roof_height"): "roof_height_m",
        
        # Building materials
        ("building:material", "material", "exterior_material"): "building_material",
        ("roof:material", "roof_type", "roof_material"): "roof_material",
        ("facade:material",): "facade_material",
        
        # Construction and dating
        ("start_date", "construction_date", "building:start_date"): "construction_date",
        ("end_date", "demolition_date", "building:end_date"): "demolition_date",
        ("building:age",): "building_age",
        
        # Building usage/function
        ("usage", "use", "building:use"): "building_use",
        ("building:uses",): "building_uses",
        
        # Occupancy and residents
        ("occupied", "building:occupied"): "occupied",
        ("residents", "num_residents", "population"): "residents",
        
        # Structure properties
        ("roof:shape", "roof_shape"): "roof_shape",
        ("building:structure", "structure"): "building_structure",
        ("building:part",): "building_part",
        
        # Access and connectivity
        ("access", "building:access"): "access",
        ("entrance", "building:entrance"): "entrance",
        
        # Ownership and status
        ("owner", "building:owner"): "owner",
        ("building:status", "status"): "building_status",
        ("historic",): "historic",
        ("protected", "building:protected"): "protected",
        
        # Energy and utilities
        ("building:units", "units", "flats"): "building_units",
        ("building:heating", "heating"): "heating",
        ("building:power_source", "power_source"): "power_source",
        
        # Reference IDs
        ("ref", "reference", "identifier"): "reference_id",
        ("building:ref", "building:identifier"): "building_ref",
        ("cadastre:ref",): "cadastre_ref",
    }

    # Standardized building types mapping from various provider formats
    BUILDING_TYPE_MAPPING = {
        # Residential
        "residential": "residential",
        "house": "residential",
        "apartment": "residential",
        "flats": "residential",
        "family_house": "residential",
        "detached": "residential",
        "semi_detached": "residential",
        "terraced": "residential",
        "terrace": "residential",
        
        # Commercial
        "commercial": "commercial",
        "retail": "commercial",
        "shop": "commercial",
        "office": "commercial",
        "office_building": "commercial",
        "bank": "commercial",
        "restaurant": "commercial",
        "cafe": "commercial",
        "hotel": "commercial",
        "guest_house": "commercial",
        
        # Industrial
        "industrial": "industrial",
        "factory": "industrial",
        "warehouse": "industrial",
        "storage": "industrial",
        "works": "industrial",
        "power_plant": "industrial",
        
        # Public/Institutional
        "public": "public",
        "institutional": "public",
        "government": "public",
        "administration": "public",
        "municipality": "public",
        "courthouse": "public",
        "fire_station": "public",
        "police": "public",
        "prison": "public",
        "civic": "public",
        
        # Educational
        "education": "educational",
        "school": "educational",
        "university": "educational",
        "college": "educational",
        "kindergarten": "educational",
        "library": "educational",
        
        # Healthcare
        "medical": "medical",
        "healthcare": "medical",
        "hospital": "medical",
        "clinic": "medical",
        "doctor": "medical",
        "pharmacy": "medical",
        "dentist": "medical",
        
        # Religious
        "religious": "religious",
        "church": "religious",
        "cathedral": "religious",
        "mosque": "religious",
        "temple": "religious",
        "synagogue": "religious",
        "monastery": "religious",
        
        # Cultural/Recreation
        "cultural": "cultural",
        "entertainment": "cultural",
        "museum": "cultural",
        "theatre": "cultural",
        "cinema": "cultural",
        "gallery": "cultural",
        "stadium": "cultural",
        "sports_center": "cultural",
        "gym": "cultural",
        
        # Utility/Infrastructure
        "utility": "utility",
        "infrastructure": "utility",
        "transformer_station": "utility",
        "telephone_exchange": "utility",
        "water_tower": "utility",
        "parking": "utility",
        "shed": "utility",
        "garage": "utility",
        
        # Agriculture
        "agricultural": "agricultural",
        "farm": "agricultural",
        "barn": "agricultural",
        "greenhouse": "agricultural",
        
        # Transportation
        "transportation": "transportation",
        "railway_station": "transportation",
        "bus_station": "transportation",
        "airport": "transportation",
        
        # Temporary/Other
        "construction": "construction",
        "temporary": "construction",
        "yes": "unclassified",  # Default OSM value
        "other": "other",
    }

    # Standardized material types
    MATERIAL_MAPPING = {
        "brick": "brick",
        "stone": "stone",
        "concrete": "concrete",
        "steel": "steel",
        "glass": "glass",
        "wood": "wood",
        "metal": "metal",
        "plastic": "plastic",
        "tile": "tile",
        "slate": "slate",
        "asbestos": "asbestos",
        "unknown": "unknown",
    }

    @classmethod
    def standardize_properties(
        cls,
        raw_properties: Dict[str, Any],
        provider: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Standardize building-specific properties.
        
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
                    raw_value
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

        # Handle building type normalization
        if field_name == "building_type":
            return cls._normalize_building_type(value)
        
        # Handle material normalization
        if "material" in field_name:
            return cls._normalize_material(value)
        
        # Handle numeric fields
        if field_name in [
            "building_levels",
            "building_height_m",
            "roof_height_m",
            "residents",
            "building_units"
        ]:
            return cls._normalize_numeric(value)
        
        # Handle boolean fields
        if field_name in ["occupied", "historic", "protected"]:
            return cls._normalize_boolean(value)
        
        # Handle date fields
        if "date" in field_name:
            return cls._normalize_date(value)
        
        # Keep as string for other fields
        if isinstance(value, str):
            return value.strip()
        
        return value

    @classmethod
    def _normalize_building_type(cls, value: Any) -> str:
        """
        Normalize building type to standardized category.
        
        Args:
            value: Raw building type value
            
        Returns:
            Standardized building type
        """
        if not value:
            return "unclassified"
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_")
        
        # Check if it's already a standardized type
        if value_str in cls.BUILDING_TYPE_MAPPING.values():
            return value_str
        
        # Check mapping
        return cls.BUILDING_TYPE_MAPPING.get(value_str, "other")

    @classmethod
    def _normalize_material(cls, value: Any) -> str:
        """
        Normalize material type to standardized category.
        
        Args:
            value: Raw material value
            
        Returns:
            Standardized material type
        """
        if not value:
            return "unknown"
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_")
        
        return cls.MATERIAL_MAPPING.get(value_str, "unknown")

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
            # Handle string values with units (e.g., "30m")
            if isinstance(value, str):
                # Remove common units
                value_str = value.strip().lower()
                for unit in ["m", "meter", "meters", "ft", "feet", "'", "cm"]:
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
            return value_lower in ("true", "yes", "1", "occupied", "inhabited")
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return False

    @classmethod
    def _normalize_date(cls, value: Any) -> str:
        """
        Normalize date values to ISO format string.
        
        Args:
            value: Raw date value
            
        Returns:
            ISO format date string
        """
        if not value:
            return None
        
        # If it's already a string, return as-is
        # (assumes provider uses standard date format)
        return str(value).strip()
