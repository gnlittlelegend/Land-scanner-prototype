"""
Administrative Boundary Rule (ADM-001)

Processes administrative boundary data to identify country, state, and district
information for the analyzed polygon.
"""

import logging
from typing import Dict, Any, List
from shapely.geometry import shape

from backend.models.schemas import (
    StandardizedDataset,
    RuleResult,
    ProcessingStatus,
    DataCategory,
    Feature
)
from backend.rules.rule_engine import Rule

logger = logging.getLogger(__name__)


class AdminBoundaryRule(Rule):
    """
    Administrative Boundary Rule implementation.
    
    Identifies administrative regions intersecting the analyzed polygon.
    """
    
    def __init__(self):
        super().__init__(
            rule_id="ADM-001",
            rule_name="Administrative Boundary Detection",
            required_categories=[DataCategory.ADMIN]
        )
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """
        Execute administrative boundary analysis.
        
        Args:
            standardized_datasets: Dictionary with standardized data
            
        Returns:
            RuleResult with administrative information
        """
        try:
            # Get admin dataset
            admin_dataset = standardized_datasets.get(DataCategory.ADMIN)
            if not admin_dataset or not admin_dataset.features:
                return RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=ProcessingStatus.INSUFFICIENT_DATA,
                    result={},
                    metadata={"data_points_used": 0}
                )
            
            # Extract administrative information from features
            result_data = {
                "administrative_features": [],
                "countries": [],
                "states": [],
                "districts": []
            }
            
            data_points_used = 0
            
            for feature in admin_dataset.features:
                props = feature.properties or {}
                
                # Extract admin levels
                if "country" in props:
                    country = props["country"]
                    if country not in result_data["countries"]:
                        result_data["countries"].append(country)
                
                if "state" in props:
                    state = props["state"]
                    if state not in result_data["states"]:
                        result_data["states"].append(state)
                
                if "district" in props:
                    district = props["district"]
                    if district not in result_data["districts"]:
                        result_data["districts"].append(district)
                
                result_data["administrative_features"].append({
                    "name": props.get("name", "Unknown"),
                    "type": props.get("admin_level", "unknown"),
                    "level": props.get("admin_level", 0)
                })
                
                data_points_used += 1
            
            # Build result
            result_output = {
                "administrative_regions": result_data["administrative_features"],
                "country": result_data["countries"][0] if result_data["countries"] else None,
                "state": result_data["states"][0] if result_data["states"] else None,
                "district": result_data["districts"][0] if result_data["districts"] else None,
                "all_countries": result_data["countries"],
                "all_states": result_data["states"],
                "all_districts": result_data["districts"]
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
