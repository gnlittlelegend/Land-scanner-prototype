"""Polygon Validator - Validates GeoJSON polygon inputs."""

from typing import Dict, Tuple, Any, Optional, List
from dataclasses import dataclass
from shapely.geometry import shape, MultiPolygon, Polygon as ShapelyPolygon
from shapely.validation import make_valid
import json


class ValidationError(Exception):
    """Raised when polygon validation fails."""
    pass


@dataclass
class PolygonMetadata:
    """Metadata extracted during polygon validation."""
    area_sqkm: float
    area_sqm: float
    bounding_box: Tuple[float, float, float, float]  # (minx, miny, maxx, maxy)
    centroid: Tuple[float, float]  # (lon, lat)
    num_vertices: int
    geom_type: str  # "Polygon" or "MultiPolygon"
    is_valid: bool
    crs: str  # "EPSG:4326"


class PolygonValidator:
    """Validates GeoJSON polygon inputs with comprehensive checking."""
    
    # Constants for validation limits
    MIN_AREA_SQM = 10  # 10 square meters
    MAX_AREA_SQM = 100 * 1e6  # 100 square kilometers in square meters
    MIN_AREA_SQKM = MIN_AREA_SQM / 1e6
    MAX_AREA_SQKM = MAX_AREA_SQM / 1e6
    MAX_VERTICES = 10_000
    
    # Coordinate bounds
    MIN_LON = -180.0
    MAX_LON = 180.0
    MIN_LAT = -90.0
    MAX_LAT = 90.0
    
    def validate(self, geojson_input: Dict[str, Any]) -> PolygonMetadata:
        """
        Validate a GeoJSON polygon and return metadata.
        
        Args:
            geojson_input: GeoJSON dictionary
            
        Returns:
            PolygonMetadata with polygon information
            
        Raises:
            ValidationError: If polygon is invalid
        """
        # Step 1: Validate GeoJSON structure
        self._validate_geojson_structure(geojson_input)
        
        # Step 2: Extract geometry
        geometry = geojson_input.get("geometry")
        if not geometry:
            raise ValidationError("Missing 'geometry' field in GeoJSON")
        
        # Step 3: Validate geometry type
        geom_type = geometry.get("type")
        self._validate_geometry_type(geom_type)
        
        # Step 4: Extract and validate coordinates
        coordinates = geometry.get("coordinates")
        if coordinates is None:
            raise ValidationError("Missing 'coordinates' field in geometry")
        
        # Step 5: Create Shapely geometry
        try:
            shapely_geom = shape(geometry)
        except Exception as e:
            raise ValidationError(f"Invalid geometry: {str(e)}")
        
        # Step 6: Validate Shapely geometry
        if not shapely_geom.is_valid:
            raise ValidationError("Geometry is not valid (invalid structure or self-intersections)")
        
        # Step 7: Validate geometry is Polygon or MultiPolygon
        if not isinstance(shapely_geom, (ShapelyPolygon, MultiPolygon)):
            raise ValidationError(f"Geometry type '{geom_type}' is not supported. Must be Polygon or MultiPolygon.")
        
        # Step 8: Handle MultiPolygon
        if isinstance(shapely_geom, MultiPolygon):
            shapely_geom = self._validate_multipolygon(shapely_geom)
        
        # Step 9: Validate coordinates within bounds
        self._validate_coordinate_bounds(shapely_geom)
        
        # Step 10: Validate linear rings are closed
        self._validate_rings_closed(geometry)
        
        # Step 11: Validate vertex count
        num_vertices = self._count_vertices(shapely_geom)
        if num_vertices > self.MAX_VERTICES:
            raise ValidationError(
                f"Polygon has {num_vertices} vertices, exceeds maximum of {self.MAX_VERTICES}"
            )
        if num_vertices < 3:
            raise ValidationError(
                f"Polygon must have at least 3 vertices, found {num_vertices}"
            )
        
        # Step 12: Validate polygon area
        area_sqm = shapely_geom.area * 111320 * 110540  # Approximate conversion at equator
        # For more accurate area, use geospatial projection
        area_sqm = self._calculate_area_sqm(shapely_geom)
        area_sqkm = area_sqm / 1e6
        
        if area_sqm < self.MIN_AREA_SQM:
            raise ValidationError(
                f"Polygon area {area_sqm:.2f} m² is below minimum of {self.MIN_AREA_SQM} m²"
            )
        if area_sqm > self.MAX_AREA_SQM:
            raise ValidationError(
                f"Polygon area {area_sqkm:.2f} km² exceeds maximum of {self.MAX_AREA_SQKM:.2f} km²"
            )
        
        # Step 13: Calculate metadata
        bounds = shapely_geom.bounds  # (minx, miny, maxx, maxy)
        centroid = (shapely_geom.centroid.x, shapely_geom.centroid.y)
        
        return PolygonMetadata(
            area_sqkm=area_sqkm,
            area_sqm=area_sqm,
            bounding_box=bounds,
            centroid=centroid,
            num_vertices=num_vertices,
            geom_type=geom_type,
            is_valid=True,
            crs="EPSG:4326"
        )
    
    def _validate_geojson_structure(self, geojson_input: Dict[str, Any]) -> None:
        """Validate basic GeoJSON structure (RFC 7946 compliance)."""
        if not isinstance(geojson_input, dict):
            raise ValidationError("Input must be a JSON object (dictionary)")
        
        # Check for required fields
        if "type" not in geojson_input:
            raise ValidationError("Missing 'type' field in GeoJSON object")
        
        # For Feature, extract geometry
        if geojson_input.get("type") == "Feature":
            if "geometry" not in geojson_input:
                raise ValidationError("Feature object missing 'geometry' field")
        elif geojson_input.get("type") not in ["Polygon", "MultiPolygon", "FeatureCollection"]:
            if "geometry" not in geojson_input:
                raise ValidationError("GeoJSON object missing 'geometry' field")
    
    def _validate_geometry_type(self, geom_type: str) -> None:
        """Validate geometry type is Polygon or MultiPolygon."""
        if geom_type not in ["Polygon", "MultiPolygon"]:
            raise ValidationError(
                f"Invalid geometry type '{geom_type}'. Must be 'Polygon' or 'MultiPolygon'"
            )
    
    def _validate_multipolygon(self, geom: MultiPolygon) -> ShapelyPolygon:
        """Validate MultiPolygon and optionally merge into single Polygon."""
        if len(geom.geoms) == 0:
            raise ValidationError("MultiPolygon contains no polygons")
        
        # For validation purposes, we'll work with the unioned geometry
        # to treat multiple polygons as a single area
        try:
            merged = geom.union(geom)  # Validate structure
            if not merged.is_valid:
                raise ValidationError("MultiPolygon geometry is invalid")
        except Exception as e:
            raise ValidationError(f"MultiPolygon validation failed: {str(e)}")
        
        return geom  # Return as is for further processing
    
    def _validate_coordinate_bounds(self, geom) -> None:
        """Validate all coordinates are within valid geographic bounds."""
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        minx, miny, maxx, maxy = bounds
        
        # Check latitude bounds (special case for crossing antimeridian)
        if miny < self.MIN_LAT or maxy > self.MAX_LAT:
            raise ValidationError(
                f"Latitude values out of range [-90, 90]. "
                f"Found: min={miny}, max={maxy}"
            )
        
        # For longitude, allow crossing antimeridian (minx > maxx means crossing)
        # but validate individual coordinate values
        if minx < self.MIN_LON - 0.0001 or maxx > self.MAX_LON + 0.0001:
            # Check if this is actually a valid antimeridian crossing
            if not (minx > 0 and maxx < 0):  # Not a valid antimeridian crossing
                raise ValidationError(
                    f"Longitude values out of range [-180, 180]. "
                    f"Found: min={minx}, max={maxx}"
                )
    
    def _validate_rings_closed(self, geometry: Dict[str, Any]) -> None:
        """Validate that all linear rings are properly closed."""
        geom_type = geometry.get("type")
        coordinates = geometry.get("coordinates", [])
        
        if geom_type == "Polygon":
            for ring_idx, ring in enumerate(coordinates):
                if len(ring) < 3:
                    raise ValidationError(
                        f"Ring {ring_idx} has fewer than 3 vertices"
                    )
                if ring[0] != ring[-1]:
                    raise ValidationError(
                        f"Ring {ring_idx} is not closed (first and last coordinates differ)"
                    )
        
        elif geom_type == "MultiPolygon":
            for poly_idx, polygon in enumerate(coordinates):
                for ring_idx, ring in enumerate(polygon):
                    if len(ring) < 3:
                        raise ValidationError(
                            f"Polygon {poly_idx}, ring {ring_idx} has fewer than 3 vertices"
                        )
                    if ring[0] != ring[-1]:
                        raise ValidationError(
                            f"Polygon {poly_idx}, ring {ring_idx} is not closed"
                        )
    
    def _count_vertices(self, geom) -> int:
        """Count total vertices in geometry."""
        if isinstance(geom, ShapelyPolygon):
            # Count all coordinates in exterior and interior rings
            count = len(geom.exterior.coords) - 1  # Subtract 1 for closed ring duplication
            for interior in geom.interiors:
                count += len(interior.coords) - 1
            return count
        
        elif isinstance(geom, MultiPolygon):
            total = 0
            for poly in geom.geoms:
                total += len(poly.exterior.coords) - 1
                for interior in poly.interiors:
                    total += len(interior.coords) - 1
            return total
        
        return 0
    
    def _calculate_area_sqm(self, geom) -> float:
        """
        Calculate polygon area in square meters.
        Uses Shapely's calculation which works in decimal degrees.
        Converts to approximate square meters.
        """
        # Shapely returns area in square degrees (not square meters)
        # This is an approximation - at the equator:
        # 1 degree latitude ≈ 111 km = 111,000 meters
        # 1 degree longitude ≈ 111 km = 111,000 meters at equator
        
        area_sq_degrees = geom.area
        
        # Get the centroid latitude to adjust longitude conversion
        if isinstance(geom, ShapelyPolygon):
            lat = geom.centroid.y
        elif isinstance(geom, MultiPolygon):
            # Use the centroid of the first polygon
            lat = geom.geoms[0].centroid.y
        else:
            lat = 0
        
        # Adjust for latitude
        lat_rad = abs(lat) * 3.14159 / 180.0
        cos_lat = abs(__import__('math').cos(lat_rad))
        
        # Meters per degree at this latitude
        meters_per_degree_lat = 111320  # Constant
        meters_per_degree_lon = 111320 * cos_lat
        
        # Convert to square meters
        area_sqm = area_sq_degrees * meters_per_degree_lat * meters_per_degree_lon
        
        return area_sqm
