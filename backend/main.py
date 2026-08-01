"""
Land Scanner Prototype - Main FastAPI Application

A geospatial data analysis platform that collects information from multiple
open geospatial data sources and transforms it into useful land intelligence
using rule-based processing.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import os
import time
import logging
from datetime import datetime

from backend.models import (
    AnalysisResponse, 
    ValidationError, 
    ProcessingStatus, 
    Polygon as PolygonModel,
    ErrorInfo,
    ModuleStatus,
    DataCategory
)
from backend.models.schemas import RuleResult, StandardizedDataset
from backend.services import ConfigManager
from backend.validators.polygon_validator import PolygonValidator, PolygonValidationError
from backend.validators.data_validator import DataValidator
from backend.managers.data_source_manager import DataSourceManager
from backend.standardizers.standardizer import Standardizer
from backend.rules.rule_engine import RuleEngine
from backend.exceptions.error_handler import (
    SafeError,
    ErrorCode,
    ErrorSeverity,
    sanitize_error_message,
    create_error_response,
    http_status_for_error,
    log_error
)
from backend.exceptions.response_formatter import (
    format_error_response,
    format_success_response,
    format_validation_error_response,
    format_processing_status
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

config = ConfigManager()

app = FastAPI(
    title="Land Scanner Prototype",
    description="A geospatial data analysis platform",
    version=config.get_app_version()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def error_handler_middleware(request: Request, call_next):
    """
    Global error handling middleware that wraps all requests.
    
    Catches exceptions at the application level and returns
    safe error responses without exposing implementation details.
    """
    request_id = f"req_{int(time.time() * 1000)}"
    
    try:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        return response
    except HTTPException as http_exc:
        logger.warning(f"[{request_id}] HTTP exception: {http_exc.status_code} - {http_exc.detail}")
        return JSONResponse(
            status_code=http_exc.status_code,
            content=http_exc.detail if isinstance(http_exc.detail, dict) else {
                "status": "error",
                "error_code": "HTTP_ERROR",
                "error_message": str(http_exc.detail),
                "request_id": request_id
            }
        )
    except PolygonValidationError as e:
        logger.warning(f"[{request_id}] Polygon validation error: {str(e)}")
        safe_error = SafeError(
            error_code=ErrorCode.POLYGON_VALIDATION_ERROR,
            user_message=str(e),
            module="polygon_validator",
            stage="validation",
            severity=ErrorSeverity.ERROR
        )
        status_code = http_status_for_error(safe_error.error_code)
        return JSONResponse(
            status_code=status_code,
            content=create_error_response(status_code, safe_error, request_id)
        )
    except ValueError as e:
        logger.warning(f"[{request_id}] Validation error: {str(e)}")
        safe_error = SafeError(
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message=sanitize_error_message(str(e)),
            module="validation",
            severity=ErrorSeverity.ERROR
        )
        status_code = http_status_for_error(safe_error.error_code)
        return JSONResponse(
            status_code=status_code,
            content=create_error_response(status_code, safe_error, request_id)
        )
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected exception: {type(e).__name__}", exc_info=True)
        safe_error = SafeError(
            error_code=ErrorCode.INTERNAL_ERROR,
            user_message="An unexpected error occurred. Please try again later.",
            module="system",
            severity=ErrorSeverity.CRITICAL
        )
        status_code = http_status_for_error(safe_error.error_code)
        return JSONResponse(
            status_code=status_code,
            content=create_error_response(status_code, safe_error, request_id)
        )


@app.post("/analyze")
async def analyze_polygon(request: Dict[str, Any]) -> AnalysisResponse:
    """
    Analyze a geographic polygon.
    
    Accepts a GeoJSON polygon, validates it, collects data from multiple
    open data providers, standardizes the data, processes it through the
    Rule Engine, and returns structured land information.
    
    Pipeline stages:
    1. Polygon validation
    2. Data collection (from all enabled providers)
    3. Data validation (verify collected data structure)
    4. Data standardization (convert to common format - WGS84)
    5. Rule Engine processing (apply analysis rules)
    6. Output generation (compile results)
    
    Args:
        request: Dictionary with 'polygon' key containing GeoJSON
        
    Returns:
        AnalysisResponse with analysis results or error information
    """
    start_time = time.time()
    request_id = f"req_{int(time.time() * 1000)}"
    
    logger.info(f"Received analysis request: {request_id}")
    
    module_statuses = {
        "validation": ProcessingStatus.FAILED,
        "data_collection": ProcessingStatus.FAILED,
        "data_validation": ProcessingStatus.FAILED,
        "standardization": ProcessingStatus.FAILED,
        "rule_engine": ProcessingStatus.FAILED,
        "output_generation": ProcessingStatus.FAILED
    }
    
    errors: List[ErrorInfo] = []
    provider_statuses = {}
    land_information: Dict[str, RuleResult] = {}
    analysis_summary: Dict[str, Any] = {}
    
    try:
        logger.info(f"[{request_id}] STAGE 1: Validating polygon...")
        
        if not request or "polygon" not in request:
            logger.warning(f"Request {request_id} missing polygon field")
            error_response = format_validation_error_response(
                "Request must include 'polygon' field with valid GeoJSON",
                request_id
            )
            raise HTTPException(status_code=422, detail=error_response)
        
        polygon_data = request.get("polygon")
        
        try:
            validated_polygon = PolygonValidator.validate(polygon_data)
            logger.info(
                f"[{request_id}] Polygon validated: "
                f"area={validated_polygon.area_sqkm:.2f} sq km"
            )
            module_statuses["validation"] = ProcessingStatus.SUCCESS
            analysis_summary["polygon_area_sqkm"] = validated_polygon.area_sqkm
            analysis_summary["bounding_box"] = validated_polygon.bounding_box
            analysis_summary["analysis_date"] = datetime.utcnow().isoformat()
            
        except PolygonValidationError as e:
            logger.warning(f"Polygon validation failed for request {request_id}: {str(e)}")
            error_response = format_validation_error_response(str(e), request_id)
            raise HTTPException(status_code=400, detail=error_response)
        
        logger.info(f"[{request_id}] STAGE 2: Collecting data from providers...")
        
        try:
            data_source_manager = DataSourceManager(config)
            collection_result = data_source_manager.collect(validated_polygon)
            
            collected_datasets = collection_result.get("datasets", [])
            provider_statuses = collection_result.get("provider_status", {})
            collection_status = collection_result.get("status", ProcessingStatus.FAILED)
            
            module_statuses["data_collection"] = collection_status
            
            logger.info(
                f"[{request_id}] Data collection complete: "
                f"{len(collected_datasets)} datasets collected"
            )
            
            if not collected_datasets:
                logger.warning(f"[{request_id}] No data collected from any provider")
                errors.append(ErrorInfo(
                    module="data_collection",
                    message="No data collected from available providers",
                    severity="error"
                ))
                module_statuses["data_collection"] = ProcessingStatus.FAILED
                
        except Exception as e:
            logger.error(
                f"[{request_id}] Data collection failed: {str(e)}",
                exc_info=True
            )
            module_statuses["data_collection"] = ProcessingStatus.FAILED
            errors.append(ErrorInfo(
                module="data_collection",
                message=f"Data collection error: {sanitize_error_message(str(e))}",
                severity="error"
            ))
            collected_datasets = []
        
        logger.info(f"[{request_id}] STAGE 3: Validating collected data...")
        
        try:
            if collected_datasets:
                validation_results = DataValidator.validate_collection(collected_datasets)
                validation_summary = DataValidator.get_validation_summary(validation_results)
                data_validation_status = validation_summary.get("overall_status", ProcessingStatus.FAILED)
                module_statuses["data_validation"] = ProcessingStatus.SUCCESS
                
                logger.info(
                    f"[{request_id}] Data validation complete: "
                    f"{validation_summary.get('successful_datasets', 0)} successful, "
                    f"{validation_summary.get('failed_datasets', 0)} failed"
                )
                
                if validation_summary.get("failed_datasets", 0) > 0:
                    errors.append(ErrorInfo(
                        module="data_validation",
                        message=f"Some datasets failed validation ({validation_summary.get('failed_datasets', 0)})",
                        severity="warning"
                    ))
            else:
                module_statuses["data_validation"] = ProcessingStatus.SKIPPED
                logger.info(f"[{request_id}] Data validation skipped (no datasets)")
                
        except Exception as e:
            logger.error(
                f"[{request_id}] Data validation error: {str(e)}",
                exc_info=True
            )
            module_statuses["data_validation"] = ProcessingStatus.FAILED
            errors.append(ErrorInfo(
                module="data_validation",
                message=f"Validation error: {sanitize_error_message(str(e))}",
                severity="error"
            ))
        
        logger.info(f"[{request_id}] STAGE 4: Standardizing data to common format...")
        
        try:
            standardizer = Standardizer()
            standardized_datasets: Dict[DataCategory, StandardizedDataset] = {}
            
            for raw_dataset in collected_datasets:
                try:
                    standardized = standardizer.standardize(raw_dataset)
                    standardized_datasets[standardized.category] = standardized
                    logger.debug(
                        f"[{request_id}] Standardized {raw_dataset.source_provider} "
                        f"({raw_dataset.category}): {len(standardized.features)} features"
                    )
                except Exception as e:
                    logger.warning(
                        f"[{request_id}] Failed to standardize {raw_dataset.source_provider}: {str(e)}"
                    )
                    errors.append(ErrorInfo(
                        module="standardization",
                        message=f"Failed to standardize {raw_dataset.source_provider}",
                        severity="warning"
                    ))
            
            if standardized_datasets:
                module_statuses["standardization"] = ProcessingStatus.SUCCESS
                logger.info(
                    f"[{request_id}] Standardization complete: "
                    f"{len(standardized_datasets)} datasets standardized"
                )
            else:
                module_statuses["standardization"] = ProcessingStatus.FAILED
                logger.warning(f"[{request_id}] No datasets standardized")
                
        except Exception as e:
            logger.error(
                f"[{request_id}] Standardization error: {str(e)}",
                exc_info=True
            )
            module_statuses["standardization"] = ProcessingStatus.FAILED
            errors.append(ErrorInfo(
                module="standardization",
                message=f"Standardization error: {sanitize_error_message(str(e))}",
                severity="error"
            ))
            standardized_datasets = {}
        
        logger.info(f"[{request_id}] STAGE 5: Processing with Rule Engine...")
        
        try:
            if standardized_datasets:
                rule_engine = RuleEngine(config={"request_id": request_id})
                
                rule_results = rule_engine.execute(standardized_datasets)
                
                for rule_id, rule_result in rule_results.items():
                    land_information[rule_id] = rule_result
                
                engine_status = rule_engine.get_overall_status(rule_results)
                module_statuses["rule_engine"] = engine_status
                
                logger.info(
                    f"[{request_id}] Rule Engine complete: "
                    f"{len(rule_results)} rules executed"
                )
            else:
                module_statuses["rule_engine"] = ProcessingStatus.SKIPPED
                logger.info(f"[{request_id}] Rule Engine skipped (no standardized data)")
                
        except Exception as e:
            logger.error(
                f"[{request_id}] Rule Engine error: {str(e)}",
                exc_info=True
            )
            module_statuses["rule_engine"] = ProcessingStatus.FAILED
            errors.append(ErrorInfo(
                module="rule_engine",
                message=f"Rule Engine error: {sanitize_error_message(str(e))}",
                severity="error"
            ))
        
        logger.info(f"[{request_id}] STAGE 6: Generating output...")
        
        try:
            if module_statuses["validation"] == ProcessingStatus.SUCCESS:
                if module_statuses["data_collection"] == ProcessingStatus.SUCCESS:
                    overall_status = ProcessingStatus.SUCCESS
                else:
                    overall_status = ProcessingStatus.PARTIAL
            else:
                overall_status = ProcessingStatus.FAILED
            
            if not analysis_summary.get("key_findings"):
                analysis_summary["key_findings"] = []
                if land_information:
                    for rule_id, rule_result in land_information.items():
                        if rule_result.status == ProcessingStatus.SUCCESS:
                            analysis_summary["key_findings"].append(rule_result.rule_name)
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            processing_status_list = {
                name: ModuleStatus(
                    module_name=name,
                    status=status
                )
                for name, status in module_statuses.items()
            }
            
            provider_status_list = [
                {
                    "provider_name": provider_name,
                    "status": status_info.get("status", "unknown"),
                    "data_retrieved": status_info.get("data_retrieved", False),
                    "error_message": status_info.get("error_message")
                }
                for provider_name, status_info in provider_statuses.items()
            ]
            
            response = AnalysisResponse(
                request_id=request_id,
                status=overall_status,
                timestamp=datetime.utcnow(),
                processing_time_ms=processing_time_ms,
                analysis_summary=analysis_summary,
                land_information=land_information,
                processing_status=processing_status_list,
                provider_status=provider_status_list,
                errors=errors
            )
            
            module_statuses["output_generation"] = ProcessingStatus.SUCCESS
            
            logger.info(
                f"[{request_id}] Analysis complete: "
                f"status={overall_status.value}, "
                f"time={processing_time_ms:.2f}ms"
            )
            
            return response
            
        except Exception as e:
            logger.error(
                f"[{request_id}] Output generation error: {str(e)}",
                exc_info=True
            )
            module_statuses["output_generation"] = ProcessingStatus.FAILED
            errors.append(ErrorInfo(
                module="output_generation",
                message=f"Output generation error: {sanitize_error_message(str(e))}",
                severity="error"
            ))
            
            processing_time_ms = (time.time() - start_time) * 1000
            response = AnalysisResponse(
                request_id=request_id,
                status=ProcessingStatus.FAILED,
                timestamp=datetime.utcnow(),
                processing_time_ms=processing_time_ms,
                analysis_summary=analysis_summary,
                land_information=land_information,
                processing_status={
                    name: ModuleStatus(module_name=name, status=status)
                    for name, status in module_statuses.items()
                },
                provider_status=provider_status_list if provider_statuses else [],
                errors=errors
            )
            
            return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze endpoint [{request_id}]: {str(e)}", exc_info=True)
        processing_time_ms = (time.time() - start_time) * 1000
        
        error_response = AnalysisResponse(
            request_id=request_id,
            status=ProcessingStatus.FAILED,
            timestamp=datetime.utcnow(),
            processing_time_ms=processing_time_ms,
            analysis_summary={},
            land_information={},
            processing_status={
                "validation": ModuleStatus(module_name="validation", status=ProcessingStatus.FAILED),
                "data_collection": ModuleStatus(module_name="data_collection", status=ProcessingStatus.FAILED),
                "data_validation": ModuleStatus(module_name="data_validation", status=ProcessingStatus.FAILED),
                "standardization": ModuleStatus(module_name="standardization", status=ProcessingStatus.FAILED),
                "rule_engine": ModuleStatus(module_name="rule_engine", status=ProcessingStatus.FAILED),
                "output_generation": ModuleStatus(module_name="output_generation", status=ProcessingStatus.FAILED),
            },
            errors=[ErrorInfo(
                module="analyze_endpoint",
                message="An unexpected error occurred during analysis",
                severity="error"
            )]
        )
        
        return error_response


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": config.get_app_name(),
        "version": config.get_app_version(),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/status")
async def get_status() -> Dict[str, Any]:
    enabled_providers = config.get_enabled_providers()
    
    return {
        "prototype_name": config.get_app_name(),
        "version": config.get_app_version(),
        "timestamp": datetime.utcnow().isoformat(),
        "enabled_providers": [p["name"] for p in enabled_providers],
        "provider_count": len(enabled_providers),
        "debug_mode": config.is_debug_mode()
    }


if __name__ == "__main__":
    import uvicorn
    
    host = config.get_setting("api.host", "0.0.0.0")
    port = config.get_setting("api.port", 8000)
    debug = config.is_debug_mode()
    
    logger.info(f"Starting {config.get_app_name()} v{config.get_app_version()}")
    logger.info(f"Server: {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug
    )