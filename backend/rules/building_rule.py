"""
Building Presence Rule (BLD-001)

Detects presence of buildings in the polygon area and estimates building count
and coverage.
"""

import logging
from typing import Dict, Any

from backend.models.schemas import (
    StandardizedDataset,
    RuleResult,
    ProcessingStatus,
    DataCategory
)
from backend.rules.rule_engine import Rule

logger = logging.getLogger(__name__)


class BuildingPresenceRule(Rule):
    """
    Building Presence Rule implementation.
    
    Detects infrastructure (buildings) presence and estimates coverage.
    """
    
    def __init__(self):
        super().__init__(
            rule_id="BLD-001",
            rule_name="Building Presence Detection",
            required_categories=[DataCategory.BUILDINGS]
        )
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """
        Execute building presence analysis.
        
        Args:
            standardized_datasets: Dictionary with standardized data
            
        Returns:
            RuleResult with building information
        """
        try:
            # Get buildings dataset
            bld_dataset = standardized_datasets.get(DataCategory.BUILDINGS)
            if not bld_dataset or not bld_dataset.features:
                return RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=ProcessingStatus.INSUFFICIENT_DATA,
                    result={},
                    metadata={"data_points_used": 0}
                )
            
            # Analyze building data
            total_buildings = len(bld_dataset.features)
            building_types = {}
            total_area = 0
            
            data_points_used = 0
            
            for feature in bld_dataset.features:
                props = feature.properties or {}
                
                # Extract building type
                bld_type = props.get("building_type") or props.get("type") or "residential"
                if bld_type not in building_types:
                    building_types[bld_type] = {"count": 0, "names": []}
                
                building_types[bld_type]["count"] += 1
                
                # Track building names if available
                if "name" in props and props["name"]:
                    building_types[bld_type]["names"].append(props["name"])
                
                # Estimate area if available
                if "area" in props:
                    try:
                        total_area += float(props["area"])
                    except (ValueError, TypeError):
                        pass
                
                data_points_used += 1
            
            # Determine primary building type
            primary_type = max(building_types.items(), key=lambda x: x[1]["count"])[0] if building_types else "unknown"
            
            result_output = {
                "buildings_detected": True if total_buildings > 0 else False,
                "total_building_count": total_buildings,
                "building_types": {
                    btype: {
                        "count": info["count"],
                        "percentage": round((info["count"] / total_buildings) * 100, 2) if total_buildings > 0 else 0
                    }
                    for btype, info in building_types.items()
                },
                "primary_building_type": primary_type,
                "total_building_area_sqm": round(total_area, 2) if total_area > 0 else None,
                "building_density_estimate": self._calculate_density(total_buildings),
                "infrastructure_present": total_buildings > 0
            }
            
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
    def _calculate_density(building_count: int) -> str:
        """
        Categorize building density based on count.
        
        Args:
            building_count: Number of buildings detected
            
        Returns:
            Density category (low, medium, high)
        """
        if building_count < 10:
            return "low"
        elif building_count < 100:
            return "medium"
        else:
            return "high"
