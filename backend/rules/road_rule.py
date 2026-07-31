"""
Road Network Rule (RD-001)

Processes road data to identify road access and categorize road types.
"""

import logging
from typing import Dict, Any
from collections import Counter

from backend.models.schemas import (
    StandardizedDataset,
    RuleResult,
    ProcessingStatus,
    DataCategory
)
from backend.rules.rule_engine import Rule

logger = logging.getLogger(__name__)


class RoadNetworkRule(Rule):
    """
    Road Network Rule implementation.
    
    Identifies road access and categorizes road types.
    """
    
    def __init__(self):
        super().__init__(
            rule_id="RD-001",
            rule_name="Road Network Analysis",
            required_categories=[DataCategory.ROADS]
        )
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """
        Execute road network analysis.
        
        Args:
            standardized_datasets: Dictionary with standardized data
            
        Returns:
            RuleResult with road information
        """
        try:
            # Get roads dataset
            rd_dataset = standardized_datasets.get(DataCategory.ROADS)
            if not rd_dataset or not rd_dataset.features:
                return RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=ProcessingStatus.INSUFFICIENT_DATA,
                    result={},
                    metadata={"data_points_used": 0}
                )
            
            # Analyze road data
            total_roads = len(rd_dataset.features)
            road_types = Counter()
            total_length = 0
            
            data_points_used = 0
            
            for feature in rd_dataset.features:
                props = feature.properties or {}
                
                # Extract road type and classification
                road_type = props.get("road_type") or props.get("type") or "unknown"
                road_classification = props.get("classification") or props.get("class") or "unclassified"
                
                road_types[road_classification] += 1
                
                # Sum road lengths if available
                if "length" in props:
                    try:
                        total_length += float(props["length"])
                    except (ValueError, TypeError):
                        pass
                
                data_points_used += 1
            
            # Calculate road type percentages
            road_type_breakdown = {}
            if total_roads > 0:
                for road_class, count in road_types.items():
                    road_type_breakdown[road_class] = {
                        "count": count,
                        "percentage": round((count / total_roads) * 100, 2)
                    }
            
            # Determine primary road type
            primary_road_type = road_types.most_common(1)[0][0] if road_types else "unknown"
            
            result_output = {
                "road_access": True if total_roads > 0 else False,
                "total_road_segments": total_roads,
                "total_road_length_km": round(total_length / 1000, 2) if total_length > 0 else 0,
                "road_types": road_type_breakdown,
                "primary_road_type": primary_road_type,
                "accessibility": self._assess_accessibility(total_roads),
                "connectivity_estimate": "good" if total_roads > 5 else ("moderate" if total_roads > 0 else "poor")
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
    def _assess_accessibility(road_count: int) -> str:
        """
        Assess road accessibility based on road count.
        
        Args:
            road_count: Number of road segments
            
        Returns:
            Accessibility level (low, moderate, high)
        """
        if road_count < 3:
            return "low"
        elif road_count < 10:
            return "moderate"
        else:
            return "high"
