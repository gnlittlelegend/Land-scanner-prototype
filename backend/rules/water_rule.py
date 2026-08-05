"""
Water Features Rule (WT-001)

Processes water bodies data to identify water features and estimate coverage.
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


class WaterFeaturesRule(Rule):
    """
    Water Features Rule implementation.
    
    Identifies water features and estimates coverage.
    """
    
    def __init__(self):
        super().__init__(
            rule_id="WT-001",
            rule_name="Water Features Analysis",
            required_categories=[DataCategory.WATER]
        )
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """
        Execute water features analysis.
        
        Args:
            standardized_datasets: Dictionary with standardized data
            
        Returns:
            RuleResult with water information
        """
        try:
            # Get water dataset
            wt_dataset = standardized_datasets.get(DataCategory.WATER)
            if not wt_dataset or not wt_dataset.features:
                return RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=ProcessingStatus.INSUFFICIENT_DATA,
                    result={},
                    metadata={"data_points_used": 0}
                )
            
            # Analyze water data
            total_water_features = len(wt_dataset.features)
            water_types = Counter()
            total_area = 0
            
            data_points_used = 0
            
            for feature in wt_dataset.features:
                props = feature.properties or {}
                
                # Extract water feature type
                water_type = props.get("water_type") or props.get("type") or "water"
                water_types[water_type] += 1
                
                # Sum water area if available
                if "area" in props:
                    try:
                        total_area += float(props["area"])
                    except (ValueError, TypeError):
                        pass
                
                data_points_used += 1
            
            # Calculate water type breakdown
            water_type_breakdown = {}
            if total_water_features > 0:
                for wtype, count in water_types.items():
                    water_type_breakdown[wtype] = {
                        "count": count,
                        "percentage": round((count / total_water_features) * 100, 2)
                    }
            
            # Determine primary water type
            primary_water_type = water_types.most_common(1)[0][0] if water_types else "unknown"
            
            result_output = {
                "water_features_detected": True if total_water_features > 0 else False,
                "total_water_features": total_water_features,
                "water_types": water_type_breakdown,
                "primary_water_type": primary_water_type,
                "total_water_area_sqkm": round(total_area / 1_000_000, 2) if total_area > 0 else 0,
                "water_coverage_category": self._categorize_coverage(total_area),
                "hydrological_features": self._identify_features(water_types)
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
    def _categorize_coverage(area_sqm: float) -> str:
        """
        Categorize water coverage based on area.
        
        Args:
            area_sqm: Total water area in square meters
            
        Returns:
            Coverage category (minimal, moderate, significant)
        """
        area_sqkm = area_sqm / 1_000_000
        if area_sqkm < 0.1:
            return "minimal"
        elif area_sqkm < 1.0:
            return "moderate"
        else:
            return "significant"
    
    @staticmethod
    def _identify_features(water_types: Counter) -> list:
        """
        Identify specific hydrological features from water types.
        
        Args:
            water_types: Counter of water types
            
        Returns:
            List of identified features
        """
        features = []
        type_names = {
            "river": "River",
            "stream": "Stream",
            "lake": "Lake",
            "pond": "Pond",
            "canal": "Canal",
            "reservoir": "Reservoir",
            "waterway": "Waterway",
            "water": "Water body",
            "drain": "Drain",
            "ditch": "Ditch",
            "channel": "Channel",
            "estuary": "Estuary",
            "lagoon": "Lagoon",
            "bay": "Bay",
            "wetland": "Wetland",
            "marsh": "Marsh",
            "swamp": "Swamp",
            "bog": "Bog"
        }
        
        for wtype in water_types:
            feature_name = type_names.get(wtype.lower(), wtype.title())
            if feature_name not in features:
                features.append(feature_name)
        
        return features
