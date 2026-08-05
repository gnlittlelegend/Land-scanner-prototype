"""
Output Generator for Land Scanner Prototype.

Compiles rule results, provider status, and processing information into a
structured AnalysisResponse suitable for API responses and frontend display.

Responsibilities:
- Compile rule results into land_information section
- Build analysis_summary with key findings
- Create processing_status for each module
- Track provider status and availability
- Generate error summary if failures occurred
- Return valid, well-formatted AnalysisResponse
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from backend.models.schemas import (
    AnalysisResponse,
    RuleResult,
    ProviderStatus,
    ProcessingStatus,
    StandardizedDataset,
    DataCategory
)

logger = logging.getLogger(__name__)


class OutputGenerator:
    """
    Generates structured output from processing pipeline results.
    
    Takes rule results, provider status, and processing metadata and produces
    a complete AnalysisResponse ready for API responses.
    """
    
    def __init__(self):
        """Initialize the Output Generator."""
        self.request_id = str(uuid.uuid4())
    
    def generate(
        self,
        rule_results: Dict[str, RuleResult],
        provider_status: List[ProviderStatus],
        polygon_info: Dict[str, Any],
        processing_status: Dict[str, str],
        processing_time_ms: float,
        standardized_datasets: Optional[Dict[DataCategory, StandardizedDataset]] = None,
        errors: Optional[List[Dict[str, str]]] = None
    ) -> AnalysisResponse:
        """
        Generate complete AnalysisResponse from processing results.
        
        Args:
            rule_results: Dictionary mapping rule_id to RuleResult
            provider_status: List of ProviderStatus objects
            polygon_info: Information about input polygon (area, bounds, etc.)
            processing_status: Dictionary mapping module name to status string
            processing_time_ms: Total time to process polygon in milliseconds
            standardized_datasets: Optional dict of standardized datasets (for analysis summary)
            errors: Optional list of error dictionaries
            
        Returns:
            AnalysisResponse with all required sections
        """
        logger.info(f"Generating output for request {self.request_id}")
        
        # Determine overall status
        overall_status = self._determine_overall_status(rule_results, errors)
        
        # Build land_information from rule results
        land_information = self._compile_land_information(rule_results)
        
        # Build analysis_summary
        analysis_summary = self._build_analysis_summary(
            polygon_info,
            rule_results,
            standardized_datasets or {}
        )
        
        # Build error summary
        error_summary = self._build_error_summary(rule_results, errors)
        
        # Create response
        response = AnalysisResponse(
            status=overall_status,
            polygon_info=polygon_info,
            analysis_summary=analysis_summary,
            land_information=land_information,
            processing_status=processing_status,
            provider_status=provider_status,
            error_summary=error_summary if error_summary else None,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        logger.info(f"Output generated successfully with status: {overall_status}")
        
        return response
    
    def _determine_overall_status(
        self,
        rule_results: Dict[str, RuleResult],
        errors: Optional[List[Dict[str, str]]]
    ) -> str:
        """
        Determine overall analysis status.
        
        Rules:
        - "success": All rules succeeded, no errors
        - "partial": Some rules succeeded, some failed/insufficient or some providers failed
        - "failed": All rules failed or critical failure occurred
        
        Args:
            rule_results: Dictionary of rule results
            errors: Optional error list
            
        Returns:
            Overall status string
        """
        if not rule_results:
            return "failed"
        
        # Count rule statuses
        success_count = sum(
            1 for r in rule_results.values()
            if r.status == ProcessingStatus.SUCCESS
        )
        failed_count = sum(
            1 for r in rule_results.values()
            if r.status == ProcessingStatus.FAILED
        )
        
        total_rules = len(rule_results)
        
        # If all succeeded and no external errors
        if success_count == total_rules and (not errors or len(errors) == 0):
            return "success"
        
        # If all failed
        if failed_count == total_rules:
            return "failed"
        
        # If mixed or some errors
        return "partial"
    
    def _compile_land_information(
        self,
        rule_results: Dict[str, RuleResult]
    ) -> Dict[str, Any]:
        """
        Compile land_information from rule results.
        
        Converts rule results into user-facing land information structure.
        
        Args:
            rule_results: Dictionary mapping rule_id to RuleResult
            
        Returns:
            Dictionary with land information by category
        """
        land_information = {
            "administrative": None,
            "land_cover": None,
            "buildings": None,
            "roads": None,
            "water": None,
            "elevation": None
        }
        
        # Map rule results to land categories
        rule_to_category = {
            "ADM-001": "administrative",
            "LC-001": "land_cover",
            "BLD-001": "buildings",
            "RD-001": "roads",
            "WT-001": "water",
            "ELV-001": "elevation"
        }
        
        for rule_id, rule_result in rule_results.items():
            category = rule_to_category.get(rule_id)
            
            if category:
                # Include result only if rule succeeded
                if rule_result.status == ProcessingStatus.SUCCESS:
                    land_information[category] = {
                        "status": "available",
                        "data": rule_result.result,
                        "metadata": rule_result.metadata
                    }
                elif rule_result.status == ProcessingStatus.INSUFFICIENT_DATA:
                    land_information[category] = {
                        "status": "insufficient_data",
                        "data": None,
                        "reason": "Required data not available from providers"
                    }
                else:  # FAILED
                    land_information[category] = {
                        "status": "error",
                        "data": None,
                        "error": rule_result.metadata.get("error", "Unknown error")
                    }
        
        return land_information
    
    def _build_analysis_summary(
        self,
        polygon_info: Dict[str, Any],
        rule_results: Dict[str, RuleResult],
        standardized_datasets: Dict[DataCategory, StandardizedDataset]
    ) -> Dict[str, Any]:
        """
        Build analysis_summary with key findings.
        
        Args:
            polygon_info: Input polygon information
            rule_results: Rule execution results
            standardized_datasets: Standardized datasets used
            
        Returns:
            Dictionary with analysis summary
        """
        # Extract polygon area
        polygon_area_sqkm = polygon_info.get("area_sqkm", 0)
        bounding_box = polygon_info.get("bounding_box", [])
        
        # Determine primary land cover
        primary_land_cover = "Unknown"
        lc_result = rule_results.get("LC-001")
        if lc_result and lc_result.status == ProcessingStatus.SUCCESS:
            lc_data = lc_result.result
            if "dominant_land_cover" in lc_data:
                primary_land_cover = lc_data["dominant_land_cover"]
            elif "land_cover_summary" in lc_data and isinstance(lc_data["land_cover_summary"], list):
                if len(lc_data["land_cover_summary"]) > 0:
                    primary_land_cover = lc_data["land_cover_summary"][0].get("type", "Unknown")
        
        # Generate key findings
        key_findings = self._generate_key_findings(rule_results, standardized_datasets)
        
        return {
            "polygon_area_sqkm": round(polygon_area_sqkm, 2),
            "bounding_box": bounding_box,
            "analysis_date": datetime.utcnow().isoformat() + "Z",
            "primary_land_cover": primary_land_cover,
            "key_findings": key_findings
        }
    
    def _generate_key_findings(
        self,
        rule_results: Dict[str, RuleResult],
        standardized_datasets: Dict[DataCategory, StandardizedDataset]
    ) -> List[str]:
        """
        Generate key findings from rule results.
        
        Args:
            rule_results: Rule execution results
            standardized_datasets: Standardized datasets
            
        Returns:
            List of key finding strings
        """
        findings = []
        
        # Administrative findings
        adm_result = rule_results.get("ADM-001")
        if adm_result and adm_result.status == ProcessingStatus.SUCCESS:
            adm_data = adm_result.result
            if adm_data.get("country"):
                findings.append(f"Located in {adm_data.get('country')}")
            if adm_data.get("state"):
                findings.append(f"Part of {adm_data.get('state')} state/province")
        
        # Building findings
        bld_result = rule_results.get("BLD-001")
        if bld_result and bld_result.status == ProcessingStatus.SUCCESS:
            bld_data = bld_result.result
            building_count = bld_data.get("building_count", 0)
            if building_count > 0:
                findings.append(f"Contains approximately {building_count} buildings")
        
        # Land cover findings
        lc_result = rule_results.get("LC-001")
        if lc_result and lc_result.status == ProcessingStatus.SUCCESS:
            lc_data = lc_result.result
            if "dominant_land_cover" in lc_data:
                findings.append(f"Dominated by {lc_data.get('dominant_land_cover')} land cover")
        
        # Road findings
        rd_result = rule_results.get("RD-001")
        if rd_result and rd_result.status == ProcessingStatus.SUCCESS:
            rd_data = rd_result.result
            if rd_data.get("road_access", False):
                findings.append("Has accessible road network")
        
        # Water findings
        wt_result = rule_results.get("WT-001")
        if wt_result and wt_result.status == ProcessingStatus.SUCCESS:
            wt_data = wt_result.result
            if wt_data.get("has_water", False):
                findings.append("Contains water bodies")
        
        # Elevation findings
        elv_result = rule_results.get("ELV-001")
        if elv_result and elv_result.status == ProcessingStatus.SUCCESS:
            elv_data = elv_result.result
            min_elv = elv_data.get("min_elevation")
            max_elv = elv_data.get("max_elevation")
            if min_elv is not None and max_elv is not None:
                elevation_range = int(max_elv - min_elv)
                if elevation_range > 0:
                    findings.append(f"Elevation ranges over {elevation_range}m")
        
        return findings
    
    def _build_error_summary(
        self,
        rule_results: Dict[str, RuleResult],
        errors: Optional[List[Dict[str, str]]]
    ) -> Optional[Dict[str, Any]]:
        """
        Build error summary if any failures occurred.
        
        Args:
            rule_results: Rule execution results
            errors: Optional external errors
            
        Returns:
            Error summary dict or None if no errors
        """
        error_list = []
        
        # Collect rule errors
        for rule_id, rule_result in rule_results.items():
            if rule_result.status == ProcessingStatus.FAILED:
                error_msg = rule_result.metadata.get("error", "Unknown error")
                error_list.append({
                    "source": f"Rule {rule_id}",
                    "message": error_msg,
                    "type": "rule_failure"
                })
            elif rule_result.status == ProcessingStatus.INSUFFICIENT_DATA:
                error_list.append({
                    "source": f"Rule {rule_id}",
                    "message": "Required data not available",
                    "type": "insufficient_data"
                })
        
        # Add external errors
        if errors:
            error_list.extend(errors)
        
        if error_list:
            return {
                "error_count": len(error_list),
                "errors": error_list
            }
        
        return None

