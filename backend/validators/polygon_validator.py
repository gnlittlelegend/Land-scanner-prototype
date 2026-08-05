"""Polygon Validator - Validates GeoJSON polygon inputs."""

from typing import Dict, Tuple, Any, Optional, List
from dataclasses import dataclass
import math
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
        
        # Step 5: Validate geometry structure
        self._validate_coordinates_structure(coordinates, geom_type)
        
        # Step 6: Validate geometry is valid
        if not self._is_valid_geometry(coordinates, geom_type):
            raise ValidationError("Geometry is not valid (invalid structure or self-intersections)")
        
        # Step 7: Validate coordinates within bounds
        self._validate_coordinate_bounds(coordinates, geom_type)
        
        # Step 8: Validate linear rings are closed
        self._validate_rings_closed(coordinates, geom_type)
        
        # Step 9: Validate vertex count
        num_vertices = self._count_vertices(coordinates, geom_type)
        if num_vertices > self.MAX_VERTICES:
            raise ValidationError(
                f"Polygon has {num_vertices} vertices, exceeds maximum of {self.MAX_VERTICES}"
            )
        if num_vertices < 3:
            raise ValidationError(
                f"Polygon must have at least 3 vertices, found {num_vertices}"
            )
        
        # Step 10: Validate polygon area
        area_sqm = self._calculate_area_sqm(coordinates, geom_type)
        area_sqkm = area_sqm / 1e6
        
        if area_sqm < self.MIN_AREA_SQM:
            raise ValidationError(
                f"Polygon area {area_sqm:.2f} m² is below minimum of {self.MIN_AREA_SQM} m²"
            )
        if area_sqm > self.MAX_AREA_SQM:
            raise ValidationError(
                f"Polygon area {area_sqkm:.2f} km² exceeds maximum of {self.MAX_AREA_SQKM:.2f} km²"
            )
        
        # Step 11: Calculate metadata
        bounds = self._get_bounds(coordinates, geom_type)
        centroid = self._calculate_centroid(coordinates, geom_type)
        
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
    
    def _validate_coordinates_structure(self, coordinates: Any, geom_type: str) -> None:
        """Validate coordinate structure."""
        if geom_type == "Polygon":
            if not isinstance(coordinates, list) or len(coordinates) < 1:
                raise ValidationError("Polygon coordinates must be a non-empty array")
            for ring in coordinates:
                if not isinstance(ring, list):
                    raise ValidationError("Ring must be an array")
        
        elif geom_type == "MultiPolygon":
            if not isinstance(coordinates, list) or len(coordinates) < 1:
                raise ValidationError("MultiPolygon coordinates must be a non-empty array")
            for polygon in coordinates:
                if not isinstance(polygon, list):
                    raise ValidationError("Polygon must be an array")
    
    def _is_valid_geometry(self, coordinates: Any, geom_type: str) -> bool:
        """Simple geometry validation."""
        try:
            if geom_type == "Polygon":
                # Check outer ring has at least 3 unique points
                if len(coordinates[0]) < 4:  # 4 because ring is closed
                    return False
            elif geom_type == "MultiPolygon":
                for polygon in coordinates:
                    if len(polygon[0]) < 4:
                        return False
            return True
        except:
            return False
    
    def _validate_coordinate_bounds(self, coordinates: Any, geom_type: str) -> None:
        """Validate all coordinates are within valid geographic bounds."""
        bounds = self._get_bounds(coordinates, geom_type)
        minx, miny, maxx, maxy = bounds
        
        # Check latitude bounds
        if miny < self.MIN_LAT or maxy > self.MAX_LAT:
            raise ValidationError(
                f"Latitude values out of range [-90, 90]. "
                f"Found: min={miny}, max={maxy}"
            )
        
        # For longitude, allow crossing antimeridian
        if minx < self.MIN_LON - 0.0001 or maxx > self.MAX_LON + 0.0001:
            if not (minx > 0 and maxx < 0):  # Not a valid antimeridian crossing
                raise ValidationError(
                    f"Longitude values out of range [-180, 180]. "
                    f"Found: min={minx}, max={maxx}"
                )
    
    def _validate_rings_closed(self, coordinates: Any, geom_type: str) -> None:
        """Validate that all linear rings are properly closed."""
        if geom_type == "Polygon":
            for ring_idx, ring in enumerate(coordinates):
                if len(ring) < 3:
                    raise ValidationError(f"Ring {ring_idx} has fewer than 3 vertices")
                if ring[0] != ring[-1]:
                    raise ValidationError(f"Ring {ring_idx} is not closed")
        
        elif geom_type == "MultiPolygon":
            for poly_idx, polygon in enumerate(coordinates):
                for ring_idx, ring in enumerate(polygon):
                    if len(ring) < 3:
                        raise ValidationError(f"Polygon {poly_idx}, ring {ring_idx} has fewer than 3 vertices")
                    if ring[0] != ring[-1]:
                        raise ValidationError(f"Polygon {poly_idx}, ring {ring_idx} is not closed")
    
    def _count_vertices(self, coordinates: Any, geom_type: str) -> int:
        """Count total vertices in geometry."""
        count = 0
        if geom_type == "Polygon":
            for ring in coordinates:
                count += len(ring) - 1  # Subtract 1 for closed ring duplication
        elif geom_type == "MultiPolygon":
            for polygon in coordinates:
                for ring in polygon:
                    count += len(ring) - 1
        return count
    
    def _get_bounds(self, coordinates: Any, geom_type: str) -> Tuple[float, float, float, float]:
        """Get bounding box (minx, miny, maxx, maxy)."""
        all_coords = []
        
        if geom_type == "Polygon":
            for ring in coordinates:
                all_coords.extend(ring)
        elif geom_type == "MultiPolygon":
            for polygon in coordinates:
                for ring in polygon:
                    all_coords.extend(ring)
        
        if not all_coords:
            raise ValidationError("No coordinates found")
        
        lons = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        
        return (min(lons), min(lats), max(lons), max(lats))
    
    def _calculate_centroid(self, coordinates: Any, geom_type: str) -> Tuple[float, float]:
        """Calculate polygon centroid."""
        all_coords = []
        
        if geom_type == "Polygon":
            all_coords = coordinates[0]  # Use outer ring
        elif geom_type == "MultiPolygon":
            all_coords = coordinates[0][0]  # Use outer ring of first polygon
        
        if not all_coords:
            return (0, 0)
        
        lon_avg = sum(c[0] for c in all_coords) / len(all_coords)
        lat_avg = sum(c[1] for c in all_coords) / len(all_coords)
        
        return (lon_avg, lat_avg)
    
    def _calculate_area_sqm(self, coordinates: Any, geom_type: str) -> float:
        """
        Calculate polygon area in square meters using Shoelace formula.
        Works with lat/lon coordinates.
        """
        if geom_type == "Polygon":
            outer_ring = coordinates[0]
            area = self._shoelace_area(outer_ring)
            
            # Subtract interior rings (holes)
            for inner_ring in coordinates[1:]:
                area -= self._shoelace_area(inner_ring)
        
        elif geom_type == "MultiPolygon":
            area = 0
            for polygon in coordinates:
                outer_ring = polygon[0]
                area += self._shoelace_area(outer_ring)
                for inner_ring in polygon[1:]:
                    area -= self._shoelace_area(inner_ring)
        
        else:
            area = 0
        
        return max(0, area)  # Ensure non-negative
    
    def _shoelace_area(self, ring: List[Tuple[float, float]]) -> float:
        """Calculate area using shoelace formula for lat/lon coordinates."""
        n = len(ring)
        if n < 3:
            return 0
        
        # Convert degrees to radians
        area = 0
        for i in range(n - 1):
            lon1, lat1 = ring[i]
            lon2, lat2 = ring[i + 1]
            
            # Simple equirectangular projection for area
            # Meters per degree (approximation)
            lat_rad = math.radians((lat1 + lat2) / 2)
            m_per_deg_lat = 111320
            m_per_deg_lon = 111320 * math.cos(lat_rad)
            
            dx = (lon2 - lon1) * m_per_deg_lon
            dy = (lat2 - lat1) * m_per_deg_lat
            
            area += dx * dy
        
        return abs(area) / 2
