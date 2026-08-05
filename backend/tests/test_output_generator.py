"""
Comprehensive tests for OutputGenerator.

Tests the complete output generation pipeline including:
- Rule result compilation
- Analysis summary generation
- Processing status tracking
- Provider status handling
- Error summary creation
- Response validation
"""

import pytest
from datetime import datetime
from typing import Dict, List, Any

from backend.output.output_generator import OutputGenerator
from backend.models.schemas import (
    RuleResult,
    ProcessingStatus,
    ProviderStatus,
    AnalysisResponse,
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    DataCategory
)


class TestOutputGeneratorBasics:
    """Test basic OutputGenerator functionality."""
    
    def test_output_generator_initialization(self):
        """Test OutputGenerator can be initialized."""
        generator = OutputGenerator()
        assert generator is not None
        assert generator.request_id is not None
        assert len(generator.request_id) > 0
    
    def test_each_instance_has_unique_request_id(self):
        """Test that each OutputGenerator instance gets a unique request ID."""
        gen1 = OutputGenerator()
        gen2 = OutputGenerator()
        assert gen1.request_id != gen2.request_id


class TestOutputGeneratorStatusDetermination:
    """Test overall status determination logic."""
    
    def test_success_status_all_rules_pass(self):
        """Test success status when all rules pass."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin Rule",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA"}
            ),
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover Rule",
                status=ProcessingStatus.SUCCESS,
                result={"land_cover": "urban"}
            )
        }
        
        status = generator._determine_overall_status(rule_results, None)
        assert status == "success"
    
    def test_partial_status_mixed_results(self):
        """Test partial status when some rules succeed and some fail."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin Rule",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA"}
            ),
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover Rule",
                status=ProcessingStatus.FAILED,
                result={},
                metadata={"error": "Data processing failed"}
            )
        }
        
        status = generator._determine_overall_status(rule_results, None)
        assert status == "partial"
    
    def test_partial_status_with_insufficient_data(self):
        """Test partial status when some rules have insufficient data."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin Rule",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA"}
            ),
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover Rule",
                status=ProcessingStatus.INSUFFICIENT_DATA,
                result={}
            )
        }
        
        status = generator._determine_overall_status(rule_results, None)
        assert status == "partial"
    
    def test_failed_status_all_rules_fail(self):
        """Test failed status when all rules fail."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin Rule",
                status=ProcessingStatus.FAILED,
                result={},
                metadata={"error": "Error 1"}
            ),
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover Rule",
                status=ProcessingStatus.FAILED,
                result={},
                metadata={"error": "Error 2"}
            )
        }
        
        status = generator._determine_overall_status(rule_results, None)
        assert status == "failed"
    
    def test_failed_status_empty_results(self):
        """Test failed status with empty results."""
        generator = OutputGenerator()
        
        status = generator._determine_overall_status({}, None)
        assert status == "failed"
    
    def test_success_with_external_errors_becomes_partial(self):
        """Test that success becomes partial when external errors exist."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin Rule",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA"}
            )
        }
        
        external_errors = [
            {"source": "Provider", "message": "Connection timeout"}
        ]
        
        status = generator._determine_overall_status(rule_results, external_errors)
        assert status == "partial"


class TestLandInformationCompilation:
    """Test land_information compilation from rule results."""
    
    def test_land_information_has_all_categories(self):
        """Test that compiled land_information has all six categories."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin Rule",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA"}
            )
        }
        
        land_info = generator._compile_land_information(rule_results)
        
        assert "administrative" in land_info
        assert "land_cover" in land_info
        assert "buildings" in land_info
        assert "roads" in land_info
        assert "water" in land_info
        assert "elevation" in land_info
    
    def test_successful_rule_included_in_land_info(self):
        """Test that successful rule results are included."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin Rule",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA", "state": "California"}
            )
        }
        
        land_info = generator._compile_land_information(rule_results)
        
        assert land_info["administrative"] is not None
        assert land_info["administrative"]["status"] == "available"
        assert land_info["administrative"]["data"]["country"] == "USA"
    
    def test_insufficient_data_rule_marked_correctly(self):
        """Test that insufficient_data status is marked correctly."""
        generator = OutputGenerator()
        
        rule_results = {
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover Rule",
                status=ProcessingStatus.INSUFFICIENT_DATA,
                result={}
            )
        }
        
        land_info = generator._compile_land_information(rule_results)
        
        assert land_info["land_cover"]["status"] == "insufficient_data"
        assert land_info["land_cover"]["data"] is None
    
    def test_failed_rule_marked_as_error(self):
        """Test that failed rules are marked with error status."""
        generator = OutputGenerator()
        
        error_msg = "Data processing failed"
        rule_results = {
            "BLD-001": RuleResult(
                rule_id="BLD-001",
                rule_name="Building Rule",
                status=ProcessingStatus.FAILED,
                result={},
                metadata={"error": error_msg}
            )
        }
        
        land_info = generator._compile_land_information(rule_results)
        
        assert land_info["buildings"]["status"] == "error"
        assert land_info["buildings"]["data"] is None
        assert error_msg in str(land_info["buildings"]["error"])
    
    def test_all_six_rules_compiled_together(self):
        """Test compilation with all six rules."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA"}
            ),
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover",
                status=ProcessingStatus.SUCCESS,
                result={"dominant": "urban"}
            ),
            "BLD-001": RuleResult(
                rule_id="BLD-001",
                rule_name="Buildings",
                status=ProcessingStatus.INSUFFICIENT_DATA,
                result={}
            ),
            "RD-001": RuleResult(
                rule_id="RD-001",
                rule_name="Roads",
                status=ProcessingStatus.SUCCESS,
                result={"road_count": 5}
            ),
            "WT-001": RuleResult(
                rule_id="WT-001",
                rule_name="Water",
                status=ProcessingStatus.FAILED,
                result={},
                metadata={"error": "Processing error"}
            ),
            "ELV-001": RuleResult(
                rule_id="ELV-001",
                rule_name="Elevation",
                status=ProcessingStatus.SUCCESS,
                result={"min_elevation": 100, "max_elevation": 500}
            )
        }
        
        land_info = generator._compile_land_information(rule_results)
        
        # Verify all categories present with correct status
        assert land_info["administrative"]["status"] == "available"
        assert land_info["land_cover"]["status"] == "available"
        assert land_info["buildings"]["status"] == "insufficient_data"
        assert land_info["roads"]["status"] == "available"
        assert land_info["water"]["status"] == "error"
        assert land_info["elevation"]["status"] == "available"


class TestAnalysisSummaryGeneration:
    """Test analysis summary generation."""
    
    def test_analysis_summary_has_required_fields(self):
        """Test that analysis summary contains all required fields."""
        generator = OutputGenerator()
        
        polygon_info = {"area_sqkm": 50.5, "bounding_box": [-120.5, 35.0, -120.0, 35.5]}
        rule_results = {}
        
        summary = generator._build_analysis_summary(polygon_info, rule_results, {})
        
        assert "polygon_area_sqkm" in summary
        assert "bounding_box" in summary
        assert "analysis_date" in summary
        assert "primary_land_cover" in summary
        assert "key_findings" in summary
    
    def test_polygon_area_rounded_correctly(self):
        """Test that polygon area is rounded to 2 decimal places."""
        generator = OutputGenerator()
        
        polygon_info = {"area_sqkm": 50.123456, "bounding_box": []}
        
        summary = generator._build_analysis_summary(polygon_info, {}, {})
        
        assert summary["polygon_area_sqkm"] == 50.12
    
    def test_analysis_date_iso8601_format(self):
        """Test that analysis date is in ISO8601 format."""
        generator = OutputGenerator()
        
        polygon_info = {"area_sqkm": 50, "bounding_box": []}
        
        summary = generator._build_analysis_summary(polygon_info, {}, {})
        
        # Should be able to parse as ISO8601
        assert "T" in summary["analysis_date"]
        assert "Z" in summary["analysis_date"]
    
    def test_primary_land_cover_from_rule_result(self):
        """Test that primary land cover is extracted from LC rule."""
        generator = OutputGenerator()
        
        polygon_info = {"area_sqkm": 50, "bounding_box": []}
        rule_results = {
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover",
                status=ProcessingStatus.SUCCESS,
                result={"dominant_land_cover": "agricultural"}
            )
        }
        
        summary = generator._build_analysis_summary(polygon_info, rule_results, {})
        
        assert summary["primary_land_cover"] == "agricultural"
    
    def test_primary_land_cover_unknown_when_no_data(self):
        """Test that primary land cover is Unknown when no LC data."""
        generator = OutputGenerator()
        
        polygon_info = {"area_sqkm": 50, "bounding_box": []}
        rule_results = {
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover",
                status=ProcessingStatus.INSUFFICIENT_DATA,
                result={}
            )
        }
        
        summary = generator._build_analysis_summary(polygon_info, rule_results, {})
        
        assert summary["primary_land_cover"] == "Unknown"


class TestKeyFindingsGeneration:
    """Test key findings generation."""
    
    def test_key_findings_empty_initially(self):
        """Test that key findings start empty with no successful rules."""
        generator = OutputGenerator()
        
        findings = generator._generate_key_findings({}, {})
        
        assert isinstance(findings, list)
        assert len(findings) == 0
    
    def test_admin_finding_generated(self):
        """Test that administrative finding is generated."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin",
                status=ProcessingStatus.SUCCESS,
                result={"country": "France", "state": "Île-de-France"}
            )
        }
        
        findings = generator._generate_key_findings(rule_results, {})
        
        assert any("France" in f for f in findings)
        assert any("Île-de-France" in f for f in findings)
    
    def test_building_finding_generated(self):
        """Test that building finding is generated."""
        generator = OutputGenerator()
        
        rule_results = {
            "BLD-001": RuleResult(
                rule_id="BLD-001",
                rule_name="Buildings",
                status=ProcessingStatus.SUCCESS,
                result={"building_count": 150}
            )
        }
        
        findings = generator._generate_key_findings(rule_results, {})
        
        assert any("150 buildings" in f for f in findings)
    
    def test_land_cover_finding_generated(self):
        """Test that land cover finding is generated."""
        generator = OutputGenerator()
        
        rule_results = {
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover",
                status=ProcessingStatus.SUCCESS,
                result={"dominant_land_cover": "forest"}
            )
        }
        
        findings = generator._generate_key_findings(rule_results, {})
        
        assert any("forest" in f.lower() for f in findings)
    
    def test_road_finding_generated(self):
        """Test that road finding is generated."""
        generator = OutputGenerator()
        
        rule_results = {
            "RD-001": RuleResult(
                rule_id="RD-001",
                rule_name="Roads",
                status=ProcessingStatus.SUCCESS,
                result={"road_access": True}
            )
        }
        
        findings = generator._generate_key_findings(rule_results, {})
        
        assert any("road" in f.lower() for f in findings)
    
    def test_water_finding_generated(self):
        """Test that water finding is generated."""
        generator = OutputGenerator()
        
        rule_results = {
            "WT-001": RuleResult(
                rule_id="WT-001",
                rule_name="Water",
                status=ProcessingStatus.SUCCESS,
                result={"has_water": True}
            )
        }
        
        findings = generator._generate_key_findings(rule_results, {})
        
        assert any("water" in f.lower() for f in findings)
    
    def test_elevation_finding_generated(self):
        """Test that elevation finding is generated."""
        generator = OutputGenerator()
        
        rule_results = {
            "ELV-001": RuleResult(
                rule_id="ELV-001",
                rule_name="Elevation",
                status=ProcessingStatus.SUCCESS,
                result={"min_elevation": 100, "max_elevation": 500}
            )
        }
        
        findings = generator._generate_key_findings(rule_results, {})
        
        assert any("400m" in f for f in findings)  # 500 - 100 = 400
    
    def test_no_finding_when_no_buildings(self):
        """Test that no building finding when count is zero."""
        generator = OutputGenerator()
        
        rule_results = {
            "BLD-001": RuleResult(
                rule_id="BLD-001",
                rule_name="Buildings",
                status=ProcessingStatus.SUCCESS,
                result={"building_count": 0}
            )
        }
        
        findings = generator._generate_key_findings(rule_results, {})
        
        assert not any("building" in f.lower() for f in findings)


class TestErrorSummaryGeneration:
    """Test error summary generation."""
    
    def test_error_summary_none_when_no_errors(self):
        """Test that error summary is None when no errors."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin",
                status=ProcessingStatus.SUCCESS,
                result={}
            )
        }
        
        error_summary = generator._build_error_summary(rule_results, None)
        
        assert error_summary is None
    
    def test_error_summary_includes_failed_rules(self):
        """Test that error summary includes failed rules."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin",
                status=ProcessingStatus.FAILED,
                result={},
                metadata={"error": "Admin data retrieval failed"}
            )
        }
        
        error_summary = generator._build_error_summary(rule_results, None)
        
        assert error_summary is not None
        assert error_summary["error_count"] == 1
        assert len(error_summary["errors"]) == 1
        assert "ADM-001" in error_summary["errors"][0]["source"]
    
    def test_error_summary_includes_insufficient_data(self):
        """Test that error summary includes insufficient data issues."""
        generator = OutputGenerator()
        
        rule_results = {
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover",
                status=ProcessingStatus.INSUFFICIENT_DATA,
                result={}
            )
        }
        
        error_summary = generator._build_error_summary(rule_results, None)
        
        assert error_summary is not None
        assert error_summary["error_count"] == 1
        assert "insufficient_data" in error_summary["errors"][0]["type"]
    
    def test_error_summary_combines_multiple_errors(self):
        """Test that error summary combines multiple errors."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin",
                status=ProcessingStatus.FAILED,
                result={},
                metadata={"error": "Error 1"}
            ),
            "LC-001": RuleResult(
                rule_id="LC-001",
                rule_name="Land Cover",
                status=ProcessingStatus.INSUFFICIENT_DATA,
                result={}
            )
        }
        
        error_summary = generator._build_error_summary(rule_results, None)
        
        assert error_summary["error_count"] == 2
        assert len(error_summary["errors"]) == 2
    
    def test_error_summary_includes_external_errors(self):
        """Test that error summary includes external errors."""
        generator = OutputGenerator()
        
        rule_results = {}
        external_errors = [
            {"source": "Provider", "message": "Connection timeout"},
            {"source": "API", "message": "Rate limit exceeded"}
        ]
        
        error_summary = generator._build_error_summary(rule_results, external_errors)
        
        assert error_summary is not None
        assert error_summary["error_count"] == 2


class TestCompleteGeneration:
    """Test complete output generation."""
    
    def test_generate_returns_analysis_response(self):
        """Test that generate returns AnalysisResponse."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA"}
            )
        }
        
        provider_status = [
            ProviderStatus(
                provider_name="Overpass",
                status="available",
                feature_count=100
            )
        ]
        
        polygon_info = {"area_sqkm": 50, "bounding_box": [-120, 35, -119, 36]}
        processing_status = {"validation": "success", "collection": "success"}
        
        response = generator.generate(
            rule_results=rule_results,
            provider_status=provider_status,
            polygon_info=polygon_info,
            processing_status=processing_status,
            processing_time_ms=1234.5
        )
        
        assert isinstance(response, AnalysisResponse)
    
    def test_generate_includes_all_required_fields(self):
        """Test that generated response has all required fields."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin",
                status=ProcessingStatus.SUCCESS,
                result={"country": "USA"}
            )
        }
        
        provider_status = [
            ProviderStatus(provider_name="OSM", status="available", feature_count=10)
        ]
        
        polygon_info = {"area_sqkm": 50, "bounding_box": []}
        processing_status = {"validation": "success"}
        
        response = generator.generate(
            rule_results=rule_results,
            provider_status=provider_status,
            polygon_info=polygon_info,
            processing_status=processing_status,
            processing_time_ms=1000
        )
        
        assert response.status is not None
        assert response.polygon_info is not None
        assert response.analysis_summary is not None
        assert response.land_information is not None
        assert response.processing_status is not None
        assert response.provider_status is not None
        assert response.timestamp is not None
    
    def test_generate_with_empty_errors(self):
        """Test generation with no errors."""
        generator = OutputGenerator()
        
        response = generator.generate(
            rule_results={},
            provider_status=[],
            polygon_info={"area_sqkm": 10},
            processing_status={},
            processing_time_ms=100
        )
        
        # Should return failed status but valid response
        assert response.status == "failed"
        assert response.error_summary is None
    
    def test_generate_with_errors(self):
        """Test generation with errors included."""
        generator = OutputGenerator()
        
        rule_results = {
            "ADM-001": RuleResult(
                rule_id="ADM-001",
                rule_name="Admin",
                status=ProcessingStatus.FAILED,
                result={},
                metadata={"error": "Processing failed"}
            )
        }
        
        response = generator.generate(
            rule_results=rule_results,
            provider_status=[],
            polygon_info={"area_sqkm": 10},
            processing_status={},
            processing_time_ms=100
        )
        
        assert response.status == "failed"
        assert response.error_summary is not None

