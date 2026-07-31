"""
Land Cover Summary Rule (LC-001)

Processes land cover data to summarize dominant land cover types and calculate
coverage percentages.
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


class LandCoverRule(Rule):
    """
    Land Cover Summary Rule implementation.
    
    Summarizes land cover types and calculates coverage percentages.
    """
    
    def __init__(self):
        super().__init__(
            rule_id="LC-001",
            rule_name="Land Cover Summary",
            required_categories=[DataCategory.LAND_COVER]
        )
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """
        Execute land cover analysis.
        
        Args:
            standardized_datasets: Dictionary with standardized data
            
        Returns:
            RuleResult with land cover information
        """
        try:
            # Get land cover dataset
            lc_dataset = standardized_datasets.get(DataCategory.LAND_COVER)
            if not lc_dataset or not lc_dataset.features:
                return RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=ProcessingStatus.INSUFFICIENT_DATA,
                    result={},
                    metadata={"data_points_used": 0}
                )
            
            # Collect land cover types and their frequencies
            land_cover_types = []
            land_cover_counts = Counter()
            
            data_points_used = 0
            
            for feature in lc_dataset.features:
                props = feature.properties or {}
                
                # Extract land cover type and classification
                lc_type = props.get("land_cover_type") or props.get("type") or "Unknown"
                lc_classification = props.get("classification") or props.get("class") or "Unclassified"
                
                land_cover_types.append({
                    "type": lc_type,
                    "classification": lc_classification,
                    "confidence": props.get("confidence", 0.0)
                })
                
                land_cover_counts[lc_classification] += 1
                data_points_used += 1
            
            # Calculate percentages (simplified - based on feature count)
            total_features = len(lc_dataset.features)
            coverage_summary = {}
            
            if total_features > 0:
                for lc_class, count in land_cover_counts.items():
                    coverage_summary[lc_class] = {
                        "count": count,
                        "percentage": round((count / total_features) * 100, 2)
                    }
            
            # Determine primary land cover type
            primary_lc = land_cover_counts.most_common(1)[0][0] if land_cover_counts else "Unknown"
            
            result_output = {
                "primary_land_cover": primary_lc,
                "land_cover_types": land_cover_types[:10],  # Limit to top 10 for readability
                "coverage_breakdown": coverage_summary,
                "total_features_analyzed": total_features,
                "dominant_coverage_percentage": coverage_summary.get(primary_lc, {}).get("percentage", 0.0)
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
