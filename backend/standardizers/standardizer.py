"""Core Data Standardizer for normalizing diverse provider formats to common internal model"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pyproj import CRS, Transformer
from backend.data_models import RawDataset, StandardizedDataset, StandardizedFeature
import logging

logger = logging.getLogger(__name__)


class DataStandardizer:
    """Standardize raw data from any provider to common internal format"""

    # Mapping of provider categories
    VALID_CATEGORIES = {"buildings", "land_cover", "roads", "water", "elevation", "admin"}
    VALID_PROVIDERS = {"OSM", "Copernicus", "USGS", "GEBCO"}
    
    # Default target CRS: WGS84
    TARGET_CRS = "EPSG:4326"

    def __init__(self):
        """Initialize standardizer with provider-specific mapping rules"""
        self.provider_normalizers = {
            "OSM": self._normalize_osm_fields,
            "Copernicus": self._normalize_copernicus_fields,
            "USGS": self._normalize_usgs_fields,
            "GEBCO": self._normalize_gebco_fields,
        }

    def standardize(self, raw_dataset: RawDataset) -> StandardizedDataset:
        """
        Convert raw dataset from any provider to standardized format.
        
        Args:
            raw_dataset: RawDataset from a collector
            
        Returns:
            StandardizedDataset with normalized format
            
        Raises:
            ValueError: If dataset is invalid or standardization fails
        """
        # Validate raw dataset
        if not raw_dataset.source_provider in self.VALID_PROVIDERS:
            raise ValueError(f"Unknown provider: {raw_dataset.source_provider}")
        
        if not raw_dataset.category in self.VALID_CATEGORIES:
            raise ValueError(f"Unknown category: {raw_dataset.category}")

        # Standardize each feature
        standardized_features = []
        for feature in raw_dataset.features:
            try:
                standardized_feature = self._standardize_feature(
                    feature,
                    raw_dataset.source_provider,
                    raw_dataset.category,
                    feature.geometry.get("crs", self.TARGET_CRS) if isinstance(feature.geometry, dict) else self.TARGET_CRS
                )
                standardized_features.append(standardized_feature)
            except Exception as e:
                logger.warning(f"Failed to standardize feature {feature.id}: {str(e)}")
                # Continue with other features
                continue

        # Build standardized metadata
        standardized_metadata = self._standardize_metadata(
            raw_dataset.source_provider,
            raw_dataset.metadata,
            len(standardized_features)
        )

        # Create standardized dataset
        standardized_dataset = StandardizedDataset(
            category=raw_dataset.category,
            source_provider=raw_dataset.source_provider,
            features=standardized_features,
            metadata=standardized_metadata
        )

        logger.info(
            f"Standardized {len(standardized_features)} features from {raw_dataset.source_provider} "
            f"({raw_dataset.category})"
        )

        return standardized_dataset

    def _standardize_feature(
        self,
        feature: Dict[str, Any],
        provider: str,
        category: str,
        source_crs: str = TARGET_CRS
    ) -> StandardizedFeature:
        """
        Standardize a single feature.
        
        Args:
            feature: Feature object
            provider: Data provider name
            category: Data category
            source_crs: Original coordinate reference system
            
        Returns:
            StandardizedFeature with normalized format
        """
        # Normalize geometry with CRS conversion
        standardized_geometry = self._normalize_geometry(
            feature.geometry,
            source_crs
        )

        # Normalize properties based on provider and category
        normalizer = self.provider_normalizers.get(provider)
        if normalizer:
            standardized_properties = normalizer(feature.properties, category)
        else:
            # Fallback: just lowercase field names
            standardized_properties = self._normalize_fields_generic(feature.properties)

        # Create standardized feature
        standardized_feature = StandardizedFeature(
            id=feature.id or feature.get("id", str(datetime.utcnow().timestamp())),
            geometry=standardized_geometry,
            properties=standardized_properties
        )

        return standardized_feature

    def _normalize_geometry(
        self,
        geometry: Dict[str, Any],
        source_crs: str = TARGET_CRS
    ) -> Dict[str, Any]:
        """
        Normalize geometry to standard format with WGS84 coordinates.
        
        Args:
            geometry: GeoJSON geometry object
            source_crs: Original CRS
            
        Returns:
            Normalized GeoJSON geometry in WGS84
        """
        if not geometry:
            return {"type": "Point", "coordinates": [0, 0]}

        geom_type = geometry.get("type")
        coordinates = geometry.get("coordinates", [])

        # Transform coordinates if needed
        if source_crs != self.TARGET_CRS:
            try:
                coordinates = self._transform_coordinates(
                    coordinates,
                    source_crs,
                    self.TARGET_CRS,
                    geom_type
                )
            except Exception as e:
                logger.warning(f"Failed to transform coordinates from {source_crs}: {str(e)}")
                # Use coordinates as-is
                pass

        # Return normalized geometry
        return {
            "type": geom_type,
            "coordinates": coordinates
        }

    def _transform_coordinates(
        self,
        coordinates: List[Any],
        from_crs: str,
        to_crs: str,
        geom_type: str
    ) -> List[Any]:
        """
        Transform coordinates from one CRS to another.
        
        Args:
            coordinates: Original coordinates
            from_crs: Source CRS
            to_crs: Target CRS
            geom_type: GeoJSON geometry type
            
        Returns:
            Transformed coordinates
        """
        try:
            transformer = Transformer.from_crs(
                CRS.from_string(from_crs),
                CRS.from_string(to_crs),
                always_xy=True
            )

            if geom_type == "Point":
                # [lon, lat]
                lon, lat = transformer.transform(coordinates[0], coordinates[1])
                return [lon, lat]
            
            elif geom_type == "LineString":
                # [[lon, lat], ...]
                return [list(transformer.transform(coord[0], coord[1])) for coord in coordinates]
            
            elif geom_type == "Polygon":
                # [[[lon, lat], ...], ...]
                return [
                    [list(transformer.transform(coord[0], coord[1])) for coord in ring]
                    for ring in coordinates
                ]
            
            elif geom_type == "MultiPolygon":
                # [[[[lon, lat], ...], ...], ...]
                return [
                    [
                        [list(transformer.transform(coord[0], coord[1])) for coord in ring]
                        for ring in polygon
                    ]
                    for polygon in coordinates
                ]
            
            else:
                return coordinates
                
        except Exception as e:
            logger.error(f"CRS transformation error: {str(e)}")
            raise

    def _normalize_fields_generic(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic field normalization: convert to lowercase underscore.
        
        Args:
            properties: Original properties
            
        Returns:
            Normalized properties
        """
        normalized = {}
        for key, value in properties.items():
            # Convert camelCase/PascalCase to lowercase_underscore
            normalized_key = self._to_lowercase_underscore(key)
            normalized[normalized_key] = value
        return normalized

    def _to_lowercase_underscore(self, name: str) -> str:
        """
        Convert any naming convention to lowercase_underscore.
        
        Examples:
            building_type → building_type
            BuildingType → building_type
            buildingType → building_type
            BUILDING_TYPE → building_type
            building-type → building_type
        """
        import re
        
        # Replace hyphens and spaces with underscores
        name = name.replace("-", "_").replace(" ", "_")
        
        # Insert underscores before uppercase letters in camelCase
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Convert to lowercase
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _normalize_osm_fields(
        self,
        properties: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """
        Normalize OpenStreetMap-specific field names and values.
        
        Maps OSM tags to standardized names based on category.
        Uses category-specific standardizers for comprehensive field mapping.
        """
        from backend.standardizers.buildings_standardizer import BuildingsStandardizer
        from backend.standardizers.admin_standardizer import AdminStandardizer
        from backend.standardizers.roads_standardizer import RoadsStandardizer
        from backend.standardizers.water_standardizer import WaterStandardizer
        
        normalized = {}

        if category == "buildings":
            # Use BuildingsStandardizer for comprehensive field normalization (Task 6.2)
            normalized = BuildingsStandardizer.standardize_properties(properties, provider="OSM")
            # Ensure required fields are present
            if "name" not in normalized:
                normalized["name"] = properties.get("name", "")
            if "building_type" not in normalized:
                normalized["building_type"] = properties.get("building", "unclassified")

        elif category == "admin":
            # Use AdminStandardizer for administrative boundary normalization (Task 6.3)
            normalized = AdminStandardizer.standardize_properties(properties, provider="OSM")
            # Ensure required fields
            if "name" not in normalized:
                normalized["name"] = properties.get("name", "")
            if "admin_level" not in normalized:
                normalized["admin_level"] = properties.get("admin_level", "")
            if "boundary_type" not in normalized:
                normalized["boundary_type"] = properties.get("boundary", "")

        elif category == "roads":
            # Use RoadsStandardizer for road network normalization (Task 6.5)
            normalized = RoadsStandardizer.standardize_properties(properties, provider="OSM")
            # Ensure required fields
            if "name" not in normalized:
                normalized["name"] = properties.get("name", "")
            if "road_type" not in normalized:
                normalized["road_type"] = properties.get("highway", "unknown")

        elif category == "water":
            # Use WaterStandardizer for water bodies normalization (Task 6.6)
            normalized = WaterStandardizer.standardize_properties(properties, provider="OSM")
            # Ensure required fields
            if "name" not in normalized:
                normalized["name"] = properties.get("name", "")
            if "water_type" not in normalized:
                normalized["water_type"] = properties.get("waterway") or properties.get("natural") or "unknown"

        else:
            # Fallback for unknown categories
            normalized = self._normalize_fields_generic(properties)

        return normalized

    def _normalize_copernicus_fields(
        self,
        properties: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """
        Normalize Copernicus-specific field names and values.
        
        Maps Copernicus codes to standardized names.
        """
        normalized = {}

        if category == "land_cover":
            # Copernicus GLC land cover classification
            lc_code = properties.get("LC_TYPE") or properties.get("lc_type") or properties.get("classification", 0)
            normalized["land_cover_type"] = self._normalize_lc_code(lc_code)
            normalized["land_cover_code"] = lc_code
            normalized["confidence_score"] = self._parse_float(properties.get("CONFIDENCE") or properties.get("confidence", 0))
            normalized["pixel_count"] = self._parse_int(properties.get("PIXEL_COUNT") or properties.get("pixel_count", 0))

        else:
            # Fallback
            normalized = self._normalize_fields_generic(properties)

        return normalized

    def _normalize_usgs_fields(
        self,
        properties: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """
        Normalize USGS-specific field names and values.
        
        Maps USGS elevation data to standardized names.
        """
        normalized = {}

        if category == "elevation":
            # USGS elevation data
            normalized["elevation_meters"] = self._parse_float(properties.get("elevation") or properties.get("Elevation", 0))
            normalized["sample_spacing_meters"] = self._parse_float(properties.get("sample_spacing", 30))
            normalized["accuracy_meters"] = self._parse_float(properties.get("accuracy", ""))
            normalized["data_source"] = properties.get("datasource", "USGS 3DEP")

        else:
            # Fallback
            normalized = self._normalize_fields_generic(properties)

        return normalized

    def _normalize_gebco_fields(
        self,
        properties: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """
        Normalize GEBCO-specific field names and values.
        
        Maps GEBCO elevation data to standardized names.
        """
        normalized = {}

        if category == "elevation":
            # GEBCO elevation data (global bathymetry)
            normalized["elevation_meters"] = self._parse_float(properties.get("elevation") or properties.get("z", 0))
            normalized["sample_spacing_meters"] = self._parse_float(properties.get("sample_spacing", 900))
            normalized["is_bathymetric"] = self._parse_float(properties.get("elevation", 0)) < 0
            normalized["data_source"] = "GEBCO"

        else:
            # Fallback
            normalized = self._normalize_fields_generic(properties)

        return normalized

    def _standardize_metadata(
        self,
        provider: str,
        raw_metadata: Dict[str, Any],
        record_count: int
    ) -> Dict[str, Any]:
        """
        Create standardized metadata.
        
        Args:
            provider: Data provider name
            raw_metadata: Original metadata from collector
            record_count: Number of standardized features
            
        Returns:
            Standardized metadata
        """
        return {
            "source_provider": provider,
            "timestamp": raw_metadata.get("timestamp", datetime.utcnow().isoformat()),
            "crs": self.TARGET_CRS,
            "record_count": record_count,
            "source_version": raw_metadata.get("version", "unknown"),
            "data_quality": raw_metadata.get("data_quality", "unknown"),
            "processing_timestamp": datetime.utcnow().isoformat(),
        }

    # Helper methods for parsing and normalization

    def _parse_height(self, height_str: str) -> Optional[float]:
        """Parse height value from various formats (e.g., '30m', '30', '30.5m')"""
        if not height_str:
            return None
        try:
            # Remove 'm' suffix if present
            height_str = str(height_str).replace("m", "").strip()
            return float(height_str)
        except (ValueError, AttributeError):
            return None

    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse integer value safely"""
        if value is None:
            return None
        try:
            return int(float(str(value)))
        except (ValueError, AttributeError):
            return None

    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse float value safely"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, AttributeError):
            return None

    def _normalize_road_class(self, highway_type: str) -> str:
        """Normalize OSM highway tag to standard road class"""
        classification = {
            "motorway": "primary",
            "trunk": "primary",
            "primary": "primary",
            "secondary": "secondary",
            "tertiary": "secondary",
            "unclassified": "local",
            "residential": "local",
            "service": "local",
            "footway": "pedestrian",
            "path": "pedestrian",
            "track": "agricultural",
        }
        return classification.get(highway_type, "other")

    def _admin_level_to_jurisdiction(self, admin_level: int) -> str:
        """Map OSM admin_level to jurisdiction type"""
        mapping = {
            2: "country",
            3: "region",
            4: "state",
            5: "province",
            6: "district",
            7: "county",
            8: "municipality",
            9: "city",
            10: "suburb",
        }
        return mapping.get(admin_level, "unknown")

    def _normalize_lc_code(self, code: Any) -> str:
        """Map Copernicus land cover code to standard name"""
        code = self._parse_int(code) or 0
        mapping = {
            0: "no_data",
            10: "urban_buildup",
            20: "agriculture",
            30: "forest",
            40: "grassland",
            50: "shrubland",
            60: "sparsely_vegetated",
            70: "bare_rock",
            80: "permanent_water",
            90: "herbaceous_wetland",
            100: "mangrove",
            110: "moss_lichen",
        }
        return mapping.get(code, "unknown")
