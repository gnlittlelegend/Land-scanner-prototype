"""
Polygon Validator Module

Validates GeoJSON polygon input and calculates polygon metadata.
"""

from typing import Dict, Any, Tuple
import json
from shapely.geometry import shape, Polygon as ShapelyPolygon, MultiPolygon
from shapely.errors import ShapelyError
import logging

from backend.models import Polygon, ProcessingStatus

logger = logging.getLogger(__name__)


class PolygonValidationError(Exception):
    """Raised when polygon validation fails."""
    pass


class PolygonValidator:
    """Validates GeoJSON polygons and calculates metadata."""
    
    # Valid coordinate ranges
    MIN_LON = -180.0
    MAX_LON = 180.0
    MIN_LAT = -90.0
    MAX_LAT = 90.0
    
    @staticmethod
    def validate(geojson_data: Dict[str, Any]) -> Polygon:
        """
        Validate a GeoJSON polygon and return a Polygon object with metadata.
        
        Args:
            geojson_data: GeoJSON dictionary
            
        Returns:
            Validated Polygon object with metadata
            
        Raises:
            PolygonValidationError: If polygon is invalid
        """
        # Validate GeoJSON structure
        PolygonValidator._validate_geojson_structure(geojson_data)
        
        # Validate geometry type
        geometry_type = geojson_data.get("type")
        if geometry_type not in ["Polygon", "MultiPolygon"]:
            raise PolygonValidationError(
                f"Invalid geometry type: {geometry_type}. "
                f"Must be 'Polygon' or 'MultiPolygon'."
            )
        
        # Validate coordinates
        PolygonValidator._validate_coordinates(geojson_data)
        
        # Create shapely geometry for calculations
        try:
            shapely_geom = shape(geojson_data)
        except (ShapelyError, Exception) as e:
            raise PolygonValidationError(
                f"Invalid polygon geometry: {str(e)}"
            )
        
        # Ensure it's a valid polygon or multipolygon
        if not isinstance(shapely_geom, (ShapelyPolygon, MultiPolygon)):
            raise PolygonValidationError(
                f"Geometry must be Polygon or MultiPolygon, got {type(shapely_geom).__name__}"
            )
        
        # Validate geometry is valid
        if not shapely_geom.is_valid:
            raise PolygonValidationError(
                f"Polygon geometry is invalid: {shapely_geom.validation_warnings if hasattr(shapely_geom, 'validation_warnings') else 'Unknown issue'}"
            )
        
        # Calculate metadata
        bounds = shapely_geom.bounds  # (minx, miny, maxx, maxy)
        centroid = shapely_geom.centroid
        
        # Calculate area in square kilometers
        # Using EPSG:4326 (WGS84) - rough approximation
        # For more accurate results, would need to project to UTM
        area_sqkm = shapely_geom.area * 111.32 * 111.32  # Rough approximation
        
        polygon = Polygon(
            geojson=geojson_data,
            area_sqkm=area_sqkm,
            bounding_box=bounds,
            centroid=(centroid.x, centroid.y),
            crs="EPSG:4326",
            is_valid=True
        )
        
        logger.info(
            f"Polygon validated: area={area_sqkm:.2f} sq km, "
            f"bounds={bounds}, centroid=({centroid.x:.4f}, {centroid.y:.4f})"
        )
        
        return polygon
    
    @staticmethod
    def _validate_geojson_structure(geojson_data: Dict[str, Any]) -> None:
        """
        Validate basic GeoJSON structure.
        
        Args:
            geojson_data: GeoJSON dictionary
            
        Raises:
            PolygonValidationError: If structure is invalid
        """
        if not isinstance(geojson_data, dict):
            raise PolygonValidationError("GeoJSON must be a dictionary")
        
        if "type" not in geojson_data:
            raise PolygonValidationError("GeoJSON must have a 'type' field")
        
        if "coordinates" not in geojson_data:
            raise PolygonValidationError("GeoJSON must have a 'coordinates' field")
        
        if not isinstance(geojson_data["coordinates"], list):
            raise PolygonValidationError("Coordinates must be an array")
    
    @staticmethod
    def _validate_coordinates(geojson_data: Dict[str, Any]) -> None:
        """
        Validate coordinates are valid [lon, lat] pairs.
        
        Args:
            geojson_data: GeoJSON dictionary
            
        Raises:
            PolygonValidationError: If coordinates are invalid
        """
        geometry_type = geojson_data.get("type")
        coordinates = geojson_data.get("coordinates", [])
        
        try:
            if geometry_type == "Polygon":
                PolygonValidator._validate_polygon_coordinates(coordinates)
            elif geometry_type == "MultiPolygon":
                PolygonValidator._validate_multipolygon_coordinates(coordinates)
        except PolygonValidationError:
            raise
        except Exception as e:
            raise PolygonValidationError(f"Invalid coordinates: {str(e)}")
    
    @staticmethod
    def _validate_polygon_coordinates(coordinates: list) -> None:
        """
        Validate Polygon coordinates.
        
        Polygon coordinates should be: [[[lon, lat], [lon, lat], ...]]
        
        Args:
            coordinates: Polygon coordinates
            
        Raises:
            PolygonValidationError: If invalid
        """
        if not coordinates or len(coordinates) == 0:
            raise PolygonValidationError("Polygon must have at least one ring")
        
        # Validate exterior ring (first ring)
        exterior_ring = coordinates[0]
        
        if len(exterior_ring) < 4:
            raise PolygonValidationError(
                "Polygon ring must have at least 4 coordinates "
                "(3 unique points + closing point)"
            )
        
        # Validate all coordinates in all rings
        for ring_idx, ring in enumerate(coordinates):
            for coord_idx, coord in enumerate(ring):
                if not isinstance(coord, (list, tuple)) or len(coord) < 2:
                    raise PolygonValidationError(
                        f"Invalid coordinate at ring {ring_idx}, point {coord_idx}: {coord}"
                    )
                
                lon, lat = coord[0], coord[1]
                
                if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                    raise PolygonValidationError(
                        f"Coordinates must be numbers, got {type(lon).__name__}, {type(lat).__name__}"
                    )
                
                if lon < PolygonValidator.MIN_LON or lon > PolygonValidator.MAX_LON:
                    raise PolygonValidationError(
                        f"Longitude {lon} out of range [{PolygonValidator.MIN_LON}, {PolygonValidator.MAX_LON}]"
                    )
                
                if lat < PolygonValidator.MIN_LAT or lat > PolygonValidator.MAX_LAT:
                    raise PolygonValidationError(
                        f"Latitude {lat} out of range [{PolygonValidator.MIN_LAT}, {PolygonValidator.MAX_LAT}]"
                    )
    
    @staticmethod
    def _validate_multipolygon_coordinates(coordinates: list) -> None:
        """
        Validate MultiPolygon coordinates.
        
        MultiPolygon coordinates should be: [[[[lon, lat], ...]]]
        
        Args:
            coordinates: MultiPolygon coordinates
            
        Raises:
            PolygonValidationError: If invalid
        """
        if not coordinates or len(coordinates) == 0:
            raise PolygonValidationError("MultiPolygon must have at least one polygon")
        
        for polygon_idx, polygon_coords in enumerate(coordinates):
            try:
                PolygonValidator._validate_polygon_coordinates(polygon_coords)
            except PolygonValidationError as e:
                raise PolygonValidationError(
                    f"Invalid polygon {polygon_idx} in MultiPolygon: {str(e)}"
                )
