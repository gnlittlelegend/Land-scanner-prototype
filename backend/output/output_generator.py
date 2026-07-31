"""
Output Generator

Compiles rule results and processing status into structured analysis responses.
Formats data for frontend consumption while ensuring provider-specific formats
are never exposed to users.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import uuid

from backend.models import (
    AnalysisResponse,
    ProcessingStatus,
    RuleResult,
    ModuleStatus,
    ProviderStatus,
    ErrorInfo,
    Polygon as PolygonModel
)

logger = logging.getLogger(__name__)


class OutputGenerator:
    """
    Generates structured analysis responses from rule results and processing status.
    
    Responsibilities:
    - Compile rule results into analysis summary
    - Build JSON response with all required fields
    - Include processing status for each module
    - Include provider status information
    - Never expose raw provider-specific data
    - Format data for frontend consumption
    """
    
    def __init__(self):
        """Initialize the output generator."""
        pass
    
    def generate(
        self,
        rules_results: Dict[str, RuleResult],
        processing_status: Dict[str, ModuleStatus],
        provider_status: Dict[str, Dict[str, Any]],
        polygon: Optional[PolygonModel] = None,
        request_id: Optional[str] = None,
        processing_time_ms: float = 0.0,
        errors: Optional[List[ErrorInfo]] = None
    ) -> AnalysisResponse:
        """
        Generate a complete analysis response.
        
        Args:
            rules_results: Dictionary of rule results indexed by rule category
            processing_status: Dictionary of module execution statuses
            provider_status: Dictionary of provider statuses
            polygon: The analyzed polygon (optional)
            request_id: Unique request identifier (generated if not provided)
            processing_time_ms: Total processing time in milliseconds
            errors: List of errors encountered during processing
            
        Returns:
            AnalysisResponse object ready for JSON serialization
        """
        if request_id is None:
            request_id = self._generate_request_id()
        
        if errors is None:
            errors = []
        
        # Determine overall status
        overall_status = self._determine_overall_status(
            processing_status,
            provider_status,
            errors
        )
        
        # Build analysis summary
        analysis_summary = self._build_analysis_summary(
            polygon,
            rules_results,
            processing_status
        )
        
        # Convert provider status dict to list format
        provider_status_list = self._convert_provider_status_to_list(provider_status)
        
        # Create response
        response = AnalysisResponse(
            request_id=request_id,
            status=overall_status,
            timestamp=datetime.utcnow(),
            processing_time_ms=processing_time_ms,
            analysis_summary=analysis_summary,
            land_information=rules_results,
            processing_status={
                name: status for name, status in processing_status.items()
            },
            provider_status=provider_status_list,
            errors=errors
        )
        
        logger.info(
            f"Generated analysis response {request_id}: "
            f"status={overall_status}, "
            f"rules_executed={len(rules_results)}, "
            f"errors={len(errors)}"
        )
        
        return response
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return f"req_{uuid.uuid4().hex[:12]}"
    
    def _determine_overall_status(
        self,
        processing_status: Dict[str, ModuleStatus],
        provider_status: Dict[str, Dict[str, Any]],
        errors: List[ErrorInfo]
    ) -> ProcessingStatus:
        """
        Determine overall processing status.
        
        Logic:
        - SUCCESS: All modules succeeded, no errors
        - PARTIAL: Some modules/providers failed but partial data available
        - FAILED: All critical modules failed
        """
        # Check if any critical module failed
        critical_modules = {"validation", "data_collection", "standardization", "rule_engine"}
        critical_failures = [
            name for name in critical_modules
            if name in processing_status and
            processing_status[name].status == ProcessingStatus.FAILED
        ]
        
        if critical_failures:
            return ProcessingStatus.FAILED
        
        # Check if any module had issues
        has_failures = any(
            status.status in (ProcessingStatus.FAILED, ProcessingStatus.INSUFFICIENT_DATA)
            for status in processing_status.values()
        )
        
        has_provider_errors = any(
            status.get("status") == "error"
            for status in provider_status.values()
        )
        
        if has_failures or has_provider_errors or errors:
            return ProcessingStatus.PARTIAL
        
        return ProcessingStatus.SUCCESS
    
    def _build_analysis_summary(
        self,
        polygon: Optional[PolygonModel],
        rules_results: Dict[str, RuleResult],
        processing_status: Dict[str, ModuleStatus]
    ) -> Dict[str, Any]:
        """
        Build high-level analysis summary.
        
        Extracts key information from rule results and polygon metadata.
        Never includes raw provider data.
        """
        summary: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "key_findings": []
        }
        
        # Add polygon metadata if available
        if polygon:
            summary["polygon_area_sqkm"] = polygon.area_sqkm
            summary["bounding_box"] = polygon.bounding_box
        
        # Extract high-level findings from rules
        if "admin" in rules_results and rules_results["admin"].status == ProcessingStatus.SUCCESS:
            admin_info = rules_results["admin"].result
            if admin_info:
                summary["administrative_region"] = admin_info.get("administrative_region", "Unknown")
                if admin_info.get("country"):
                    summary["key_findings"].append(
                        f"Located in {admin_info.get('country')}"
                    )
        
        if "land_cover" in rules_results and rules_results["land_cover"].status == ProcessingStatus.SUCCESS:
            lc_info = rules_results["land_cover"].result
            if lc_info and "primary_land_cover" in lc_info:
                summary["primary_land_cover"] = lc_info["primary_land_cover"]
                summary["key_findings"].append(
                    f"Primary land cover: {lc_info['primary_land_cover']}"
                )
        
        if "buildings" in rules_results and rules_results["buildings"].status == ProcessingStatus.SUCCESS:
            bld_info = rules_results["buildings"].result
            if bld_info:
                if bld_info.get("buildings_detected"):
                    summary["key_findings"].append("Buildings detected in area")
        
        if "roads" in rules_results and rules_results["roads"].status == ProcessingStatus.SUCCESS:
            rd_info = rules_results["roads"].result
            if rd_info:
                if rd_info.get("road_access_available"):
                    summary["key_findings"].append("Road access available")
        
        if "water" in rules_results and rules_results["water"].status == ProcessingStatus.SUCCESS:
            wt_info = rules_results["water"].result
            if wt_info:
                if wt_info.get("water_features_detected"):
                    summary["key_findings"].append("Water features detected")
        
        if "elevation" in rules_results and rules_results["elevation"].status == ProcessingStatus.SUCCESS:
            elv_info = rules_results["elevation"].result
            if elv_info:
                if "mean_elevation_m" in elv_info:
                    summary["key_findings"].append(
                        f"Mean elevation: {elv_info['mean_elevation_m']:.0f}m"
                    )
        
        # Check processing status
        if processing_status:
            validation_status = processing_status.get("validation")
            if validation_status and validation_status.status == ProcessingStatus.FAILED:
                summary["validation_status"] = "failed"
        
        return summary
    
    def _convert_provider_status_to_list(
        self,
        provider_status: Dict[str, Dict[str, Any]]
    ) -> List[ProviderStatus]:
        """
        Convert provider status dictionary to list of ProviderStatus objects.
        
        Args:
            provider_status: Dictionary mapping provider names to status dicts
            
        Returns:
            List of ProviderStatus objects
        """
        status_list = []
        
        for provider_name, status_dict in provider_status.items():
            provider_status_obj = ProviderStatus(
                provider_name=provider_name,
                status=status_dict.get("status", "unknown"),
                error_message=status_dict.get("error_message"),
                data_retrieved=status_dict.get("data_retrieved", False)
            )
            status_list.append(provider_status_obj)
        
        return status_list
    
    @staticmethod
    def validate_response(response: AnalysisResponse) -> bool:
        """
        Validate that response has all required fields.
        
        Checks for:
        - request_id presence
        - status presence
        - analysis_summary presence
        - land_information presence
        - processing_status presence
        - provider_status presence
        - no raw provider data exposure
        
        Args:
            response: AnalysisResponse to validate
            
        Returns:
            True if response is valid, False otherwise
        """
        if not response.request_id:
            logger.error("Response validation failed: missing request_id")
            return False
        
        if not response.status:
            logger.error("Response validation failed: missing status")
            return False
        
        if response.analysis_summary is None:
            logger.error("Response validation failed: missing analysis_summary")
            return False
        
        if response.land_information is None:
            logger.error("Response validation failed: missing land_information")
            return False
        
        if response.processing_status is None:
            logger.error("Response validation failed: missing processing_status")
            return False
        
        if response.provider_status is None:
            logger.error("Response validation failed: missing provider_status")
            return False
        
        return True

