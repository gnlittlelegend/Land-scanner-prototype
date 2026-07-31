"""
Elevation Rule (ELV-001)

Processes elevation data to calculate min/max/mean elevation and characterize
terrain slope.
"""

import logging
import statistics
from typing import Dict, Any, List, Optional

from backend.models.schemas import (
    StandardizedDataset,
    RuleResult,
    ProcessingStatus,
    DataCategory
)
from backend.rules.rule_engine import Rule

logger = logging.getLogger(__name__)


class ElevationRule(Rule):
    """
    Elevation Rule implementation.
    
    Calculates elevation statistics and characterizes terrain.
    """
    
    def __init__(self):
        super().__init__(
            rule_id="ELV-001",
            rule_name="Elevation Analysis",
            required_categories=[DataCategory.ELEVATION]
        )
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """
        Execute elevation analysis.
        
        Args:
            standardized_datasets: Dictionary with standardized data
            
        Returns:
            RuleResult with elevation information
        """
        try:
            # Get elevation dataset
            elv_dataset = standardized_datasets.get(DataCategory.ELEVATION)
            if not elv_dataset or not elv_dataset.features:
                return RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=ProcessingStatus.INSUFFICIENT_DATA,
                    result={},
                    metadata={"data_points_used": 0}
                )
            
            # Collect elevation values
            elevations = []
            slopes = []
            
            data_points_used = 0
            
            for feature in elv_dataset.features:
                props = feature.properties or {}
                
                # Extract elevation
                if "elevation" in props:
                    try:
                        elev = float(props["elevation"])
                        elevations.append(elev)
                    except (ValueError, TypeError):
                        pass
                
                # Extract slope if available
                if "slope" in props:
                    try:
                        slope = float(props["slope"])
                        slopes.append(slope)
                    except (ValueError, TypeError):
                        pass
                
                data_points_used += 1
            
            # Calculate statistics
            result_output = self._calculate_statistics(elevations, slopes)
            
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                status=ProcessingStatus.SUCCESS,
                result=result_output,
                metadata={"data_points_used": data_points_used}
            )
        
        except Exception as e:
            logger.error(f"Error executing {self.rule_id}: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def _calculate_statistics(elevations: List[float], slopes: List[float]) -> Dict[str, Any]:
        """
        Calculate elevation and slope statistics.
        
        Args:
            elevations: List of elevation values in meters
            slopes: List of slope values
            
        Returns:
            Dictionary with statistics
        """
        result = {
            "elevation_data_available": len(elevations) > 0,
            "min_elevation_m": None,
            "max_elevation_m": None,
            "mean_elevation_m": None,
            "median_elevation_m": None,
            "elevation_range_m": None,
            "terrain_category": "flat",
            "slope_average": None,
            "slope_category": "low"
        }
        
        # Calculate elevation statistics
        if elevations:
            result["min_elevation_m"] = round(min(elevations), 2)
            result["max_elevation_m"] = round(max(elevations), 2)
            result["mean_elevation_m"] = round(statistics.mean(elevations), 2)
            result["elevation_range_m"] = round(result["max_elevation_m"] - result["min_elevation_m"], 2)
            
            if len(elevations) > 1:
                result["median_elevation_m"] = round(statistics.median(elevations), 2)
            
            # Categorize terrain
            result["terrain_category"] = ElevationRule._categorize_terrain(
                result["elevation_range_m"]
            )
        
        # Calculate slope statistics
        if slopes:
            result["slope_average"] = round(statistics.mean(slopes), 2)
            result["slope_category"] = ElevationRule._categorize_slope(result["slope_average"])
        
        return result
    
    @staticmethod
    def _categorize_terrain(elevation_range: Optional[float]) -> str:
        """
        Categorize terrain based on elevation range.
        
        Args:
            elevation_range: Range of elevation in meters
            
        Returns:
            Terrain category (flat, rolling, mountainous)
        """
        if elevation_range is None or elevation_range < 50:
            return "flat"
        elif elevation_range < 500:
            return "rolling"
        else:
            return "mountainous"
    
    @staticmethod
    def _categorize_slope(average_slope: float) -> str:
        """
        Categorize slope steepness.
        
        Args:
            average_slope: Average slope in degrees
            
        Returns:
            Slope category (low, moderate, steep)
        """
        if average_slope < 5:
            return "low"
        elif average_slope < 15:
            return "moderate"
        else:
            return "steep"
