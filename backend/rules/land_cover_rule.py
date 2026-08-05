"""
Land Cover Summary Rule (LC-001)

Processes land cover data to identify dominant land surface categories and
calculate coverage percentages by category.
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


class LandCoverRule(Rule):
    """
    Land Cover Summary Rule implementation.
    
    Identifies dominant land cover types and calculates coverage percentages.
    """
    
    # Land cover categories mapping from provider codes to standardized names
    LAND_COVER_CATEGORIES = {
        "urban": ["urban", "built-up", "settlement", "urban_area", "town", "city"],
        "agricultural": ["cropland", "agricultural", "crop", "arable", "cultivated", "farmland", "crops"],
        "forest": ["forest", "tree_cover", "woodland", "deciduous", "coniferous", "mixed_forest"],
        "grassland": ["grassland", "grass", "meadow", "pasture", "shrubland", "savanna"],
        "water": ["water", "water_body", "lake", "river", "ocean", "sea", "wetland"],
        "barren": ["barren", "bare", "rock", "desert", "unvegetated", "sand"],
        "wetland": ["wetland", "marsh", "swamp", "bog", "fen"]
    }
    
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
            
            # Analyze land cover data
            category_coverage = {}
            total_coverage = 0
            data_points_used = 0
            
            for feature in lc_dataset.features:
                props = feature.properties or {}
                
                # Extract land cover type
                lc_type = self._extract_land_cover_type(props)
                
                # Initialize category if not seen before
                if lc_type not in category_coverage:
                    category_coverage[lc_type] = {"count": 0, "percentage": 0}
                
                # Increment count
                category_coverage[lc_type]["count"] += 1
                
                # Try to extract coverage or area information
                if "coverage" in props:
                    try:
                        category_coverage[lc_type]["percentage"] += float(props["coverage"])
                    except (ValueError, TypeError):
                        pass
                
                data_points_used += 1
            
            # Normalize percentages
            if category_coverage:
                total_count = sum(cat["count"] for cat in category_coverage.values())
                for category in category_coverage.values():
                    if category["percentage"] > 0:
                        # Already has percentage from coverage data
                        total_coverage += category["percentage"]
                    else:
                        # Calculate percentage from count
                        category["percentage"] = round((category["count"] / total_count) * 100, 2)
            
            # Normalize if total exceeds 100 (from coverage data)
            if total_coverage > 100:
                for category in category_coverage.values():
                    category["percentage"] = round((category["percentage"] / total_coverage) * 100, 2)
            
            # Determine dominant cover type
            dominant_type = None
            max_percentage = 0
            for category, data in category_coverage.items():
                if data["percentage"] > max_percentage:
                    max_percentage = data["percentage"]
                    dominant_type = category
            
            # Build result output
            result_output = {
                "dominant_land_cover": dominant_type or "Unknown",
                "dominant_coverage_percentage": max_percentage,
                "land_cover_summary": {
                    category: {
                        "count": data["count"],
                        "percentage": data["percentage"]
                    }
                    for category, data in sorted(category_coverage.items(), 
                                                 key=lambda x: x[1]["percentage"], 
                                                 reverse=True)
                },
                "land_cover_categories_detected": list(category_coverage.keys()),
                "total_categories_identified": len(category_coverage)
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
    
    def _extract_land_cover_type(self, properties: Dict[str, Any]) -> str:
        """
        Extract land cover type from feature properties.
        
        Handles various provider-specific naming conventions and normalizes
        to standard categories.
        
        Args:
            properties: Feature properties from standardized dataset
            
        Returns:
            Standardized land cover category name
        """
        # Check for common land cover property names
        lc_type = None
        
        # Try standard field names
        if "land_cover_type" in properties:
            lc_type = properties["land_cover_type"]
        elif "land_cover" in properties:
            lc_type = properties["land_cover"]
        elif "type" in properties:
            lc_type = properties["type"]
        elif "class" in properties:
            lc_type = properties["class"]
        elif "category" in properties:
            lc_type = properties["category"]
        elif "cover_type" in properties:
            lc_type = properties["cover_type"]
        else:
            return "unknown"
        
        if not lc_type:
            return "unknown"
        
        # Normalize the type to lowercase
        lc_type = str(lc_type).lower().strip()
        
        # Map to standard categories
        for standard_category, variations in self.LAND_COVER_CATEGORIES.items():
            for variation in variations:
                if variation in lc_type or lc_type == variation:
                    return standard_category
        
        # If no match found, return the normalized type as-is
        return lc_type
