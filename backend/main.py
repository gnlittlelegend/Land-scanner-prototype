"""FastAPI application for Land Scanner"""

import logging
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
import traceback

from backend.config import ConfigManager
from backend.data_models import AnalysisResponse, ProcessingStatus, LandInformation, ProviderStatus
from backend.validators.polygon_validator import PolygonValidator, ValidationError
from backend.managers.data_source_manager import DataSourceManager
from backend.collectors.osm_buildings_collector import OSMBuildingsCollector
from backend.collectors.admin_boundaries_collector import AdminBoundariesCollector
from backend.collectors.road_network_collector import RoadNetworkCollector
from backend.collectors.water_bodies_collector import WaterBodiesCollector
from backend.collectors.elevation_collector import ElevationCollector
from backend.collectors.land_cover_collector import LandCoverCollector
from backend.standardizers.data_standardizer import DataStandardizer, StandardizationError
from backend.rules.rule_engine import RuleEngine
from backend.rules.admin_rule import AdminBoundaryRule
from backend.rules.building_rule import BuildingPresenceRule
from backend.rules.land_cover_rule import LandCoverRule
from backend.rules.road_rule import RoadNetworkRule
from backend.rules.water_rule import WaterFeaturesRule
from backend.rules.elevation_rule import ElevationRule
from backend.output.output_generator import OutputGenerator
from backend.exceptions.error_handler import (
    ErrorMessageSanitizer, ErrorCode, ErrorSeverity, SafeError, log_error
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize application
app = FastAPI(
    title="Land Scanner",
    description="Geospatial data analysis platform",
    version="1.0.0"
)

# Initialize configuration
config_manager = ConfigManager()

# Track application startup time for uptime calculation
app_start_time = time.time()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """
    Comprehensive error handling middleware (Requirement 9.1).
    
    Handles:
    - Validation errors (HTTP 400/422)
    - Real provider failures (HTTP 500 with safe message)
    - Unexpected exceptions (HTTP 500 with generic message)
    
    Ensures:
    - No stack traces exposed to user
    - Full error details logged to server logs
    - Consistent error response format
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"[{request_id}] {request.method} {request.url.path}")
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"[{request_id}] Response: {response.status_code} ({process_time:.2f}s)")
        return response
        
    except HTTPException as e:
        # HTTPException from endpoints - pass through but sanitize if needed
        process_time = time.time() - start_time
        
        # Extract detail if it's a dict (our custom error response)
        if isinstance(e.detail, dict):
            error_detail = e.detail
            error_detail["processing_time_ms"] = int(process_time * 1000)
            if "request_id" not in error_detail:
                error_detail["request_id"] = request_id
            response_content = error_detail
        else:
            # Standard HTTPException with string detail
            response_content = {
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "error_message": str(e.detail),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "processing_time_ms": int(process_time * 1000)
            }
        
        logger.warning(f"[{request_id}] HTTP {e.status_code}: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content=response_content
        )
    
    except ValidationError as e:
        # Polygon validation errors
        process_time = time.time() - start_time
        logger.warning(f"[{request_id}] Validation error: {str(e)}")
        
        # Sanitize validation error for user
        sanitized_message = ErrorMessageSanitizer.sanitize_validation_error(str(e))
        
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error_code": "POLYGON_VALIDATION_ERROR",
                "error_message": sanitized_message,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "processing_time_ms": int(process_time * 1000)
            }
        )
    
    except Exception as e:
        # Unexpected system errors
        process_time = time.time() - start_time
        
        # Log full error details including stack trace (internal only)
        logger.error(
            f"[{request_id}] Unexpected error: {str(e)}",
            exc_info=True,
            extra={
                "exception_type": type(e).__name__,
                "stack_trace": traceback.format_exc()
            }
        )
        
        # Create safe error message for user (no implementation details)
        safe_error_message = ErrorMessageSanitizer.sanitize_system_error(str(e))
        
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_code": "SYSTEM_ERROR",
                "error_message": safe_error_message,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "processing_time_ms": int(process_time * 1000)
            }
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint for service monitoring (Requirement 9.2)
    
    Returns:
    - Service health status
    - Application version
    - Uptime information
    - Basic configuration info (non-sensitive)
    """
    # Calculate uptime in seconds
    uptime_seconds = int(time.time() - app_start_time)
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_days = uptime_hours // 24
    
    # Format uptime string
    if uptime_days > 0:
        uptime_str = f"{uptime_days}d {uptime_hours % 24}h {uptime_minutes % 60}m"
    elif uptime_hours > 0:
        uptime_str = f"{uptime_hours}h {uptime_minutes % 60}m"
    else:
        uptime_str = f"{uptime_minutes}m {uptime_seconds % 60}s"
    
    # Get basic configuration info (non-sensitive)
    enabled_providers = config_manager.get_enabled_providers()
    provider_summary = [
        {
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "optional": p.get("optional", False)
        }
        for p in enabled_providers
    ]
    
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "app_name": config_manager.get_app_name(),
        "version": config_manager.get_app_version(),
        "environment": config_manager.get_environment(),
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": uptime_str,
        "timestamp": datetime.utcnow().isoformat(),
        "configuration": {
            "total_providers": len(enabled_providers),
            "enabled_providers": len(enabled_providers),
            "providers": provider_summary
        }
    }


@app.get("/status")
async def system_status():
    """
    System status and configuration information endpoint (Requirement 9.3)
    
    Returns:
    - Prototype version and environment info
    - List of enabled data providers
    - List of available rules
    - Configuration summary (timeouts, retries, rate limits)
    """
    logger.info("Status check requested")
    
    # Get provider information
    enabled_providers = config_manager.get_enabled_providers()
    all_providers = config_manager.get_providers()
    
    # Define available rules
    available_rules = [
        {
            "id": "ADM-001",
            "name": "Administrative Boundaries",
            "description": "Identifies country, state, and district from polygon location",
            "required_data": ["admin"],
            "status": "available"
        },
        {
            "id": "LC-001",
            "name": "Land Cover Summary",
            "description": "Summarizes dominant land cover types and coverage percentages",
            "required_data": ["land_cover"],
            "status": "available"
        },
        {
            "id": "BLD-001",
            "name": "Building Presence",
            "description": "Detects presence of buildings and provides statistics",
            "required_data": ["buildings"],
            "status": "available"
        },
        {
            "id": "RD-001",
            "name": "Road Network",
            "description": "Identifies road access and categorizes road types",
            "required_data": ["roads"],
            "status": "available"
        },
        {
            "id": "WT-001",
            "name": "Water Features",
            "description": "Identifies water features and estimates water coverage",
            "required_data": ["water"],
            "status": "available"
        },
        {
            "id": "ELV-001",
            "name": "Elevation Analysis",
            "description": "Calculates elevation statistics and terrain characteristics",
            "required_data": ["elevation"],
            "status": "available"
        }
    ]
    
    # Build configuration summary
    configuration_summary = {
        "providers_enabled": len(enabled_providers),
        "providers_total": len(all_providers),
        "rules_available": len(available_rules),
        "default_timeout_seconds": 30,
        "max_polygon_vertices": 10000,
        "polygon_area_min_sqm": 10,
        "polygon_area_max_sqkm": 100,
        "rate_limiting": {
            "default_delay_ms": 2000,
            "description": "Delay between provider requests to respect rate limits"
        }
    }
    
    # Build provider details with configuration
    provider_details = []
    for p in enabled_providers:
        provider_details.append({
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "optional": p.get("optional", False),
            "timeout_seconds": p.get("timeout_seconds", 30),
            "retry_count": p.get("retry_count", 2),
            "api_endpoint": p.get("api_endpoint", "")
        })
    
    return {
        "app_name": config_manager.get_app_name(),
        "version": config_manager.get_app_version(),
        "environment": config_manager.get_environment(),
        "timestamp": datetime.utcnow().isoformat(),
        "system_status": "operational",
        "enabled_providers": provider_details,
        "available_rules": available_rules,
        "configuration_summary": configuration_summary
    }


@app.post("/analyze")
async def analyze_polygon(data: dict):
    """
    Analyze a polygon by collecting, standardizing, and processing data from multiple providers
    (Requirement 9.1, 9.4, 9.5, and Task 10.1 integration)
    
    Full pipeline:
    1. Validate polygon geometry and constraints
    2. Collect data from multiple providers (real APIs)
    3. Standardize all provider data to common format
    4. Execute rule engine on standardized data
    5. Generate structured output response
    
    Request body:
    {
        "polygon": {GeoJSON polygon}
    }
    
    Returns:
    {
        "request_id": "uuid",
        "status": "success|partial|error",
        "timestamp": "ISO8601",
        "processing_time_ms": integer,
        "analysis_summary": {...},
        "land_information": {...},
        "processing_status": {...},
        "provider_status": {...},
        "errors": [...]
    }
    """
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Analysis request received")
    
    start_time = time.time()
    errors = []
    processing_status_dict = {}
    
    try:
        # Validate request structure
        if not data or "polygon" not in data:
            logger.warning(f"[{request_id}] Missing polygon in request")
            error_msg = "Request must include 'polygon' field with GeoJSON polygon"
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "error_code": "VALIDATION_ERROR",
                    "error_message": error_msg,
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": request_id
                }
            )
        
        polygon_geojson = data["polygon"]
        
        # ========== STEP 1: Validate polygon geometry (Requirements 1.1-1.6) ==========
        try:
            logger.info(f"[{request_id}] Step 1: Validating polygon geometry")
            validator = PolygonValidator()
            polygon_metadata = validator.validate(polygon_geojson)
            logger.info(f"[{request_id}] ✓ Polygon validation successful: {polygon_metadata.area_sqkm:.2f} km²")
            processing_status_dict["validation"] = "success"
            
        except ValidationError as e:
            # Polygon validation failed - return error immediately
            logger.warning(f"[{request_id}] ✗ Polygon validation failed: {str(e)}")
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "POLYGON_VALIDATION_ERROR",
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": request_id,
                    "processing_time_ms": processing_time_ms
                }
            )
        
        # ========== STEP 2: Collect data from multiple providers (Requirements 2.1-2.7) ==========
        logger.info(f"[{request_id}] Step 2: Starting data collection from {len(config_manager.get_enabled_providers())} providers")
        
        raw_collection = None
        provider_status = {}
        
        try:
            # Prepare collectors - IDs must match config/providers.json keys
            collectors = {
                "osm_buildings": OSMBuildingsCollector(timeout=30),
                "admin_boundaries": AdminBoundariesCollector(timeout=30),
                "roads": RoadNetworkCollector(timeout=30),
                "water": WaterBodiesCollector(timeout=30),
                "elevation": ElevationCollector(timeout=45),
                "land_cover": LandCoverCollector(timeout=45),
            }
            
            # Create data source manager
            manager = DataSourceManager(config_manager, collectors, rate_limit_delay=2)
            
            # Collect data from all enabled providers
            raw_collection = manager.collect_data(polygon_metadata)
            logger.info(f"[{request_id}] ✓ Data collection completed")
            logger.info(f"[{request_id}] Providers: {raw_collection.successful_providers}/{raw_collection.total_providers} successful")
            
            # Build provider status summary
            for provider_name, status in raw_collection.provider_status.items():
                provider_status[provider_name] = {
                    "available": status.get("success", False),
                    "records": status.get("record_count", 0),
                    "error": status.get("error_message", None) if not status.get("success", False) else None
                }
            
            data_collection_status = "partial" if raw_collection.failed_providers > 0 else "success"
            processing_status_dict["data_collection"] = data_collection_status
            
        except Exception as e:
            # Provider error - sanitize for user display (Requirement 8.2)
            logger.error(f"[{request_id}] ✗ Data collection failed: {str(e)}", exc_info=True)
            
            # Create safe error message without implementation details
            safe_message = ErrorMessageSanitizer.sanitize_system_error(str(e))
            errors.append(safe_message)
            
            processing_status_dict["data_collection"] = "error"
            provider_status = {}
            raw_collection = None
        
        # ========== STEP 3: Standardize collected data (Requirements 4.1-4.6) ==========
        standardized_datasets = {}
        
        if raw_collection and raw_collection.collections:
            try:
                logger.info(f"[{request_id}] Step 3: Standardizing collected data")
                standardizer = DataStandardizer()
                
                # Standardize each collected dataset
                for category, dataset in raw_collection.collections.items():
                    try:
                        standardized = standardizer.standardize(dataset)
                        standardized_datasets[category] = standardized
                        logger.debug(f"[{request_id}] Standardized {category}: {len(standardized.features)} features")
                    except StandardizationError as e:
                        logger.warning(f"[{request_id}] Failed to standardize {category}: {str(e)}")
                        errors.append(f"Standardization error for {category}: {str(e)}")
                        continue
                
                logger.info(f"[{request_id}] ✓ Standardization completed: {len(standardized_datasets)} datasets")
                processing_status_dict["standardization"] = "success" if standardized_datasets else "partial"
                
            except Exception as e:
                logger.error(f"[{request_id}] ✗ Standardization failed: {str(e)}", exc_info=True)
                safe_message = ErrorMessageSanitizer.sanitize_system_error(str(e))
                errors.append(safe_message)
                processing_status_dict["standardization"] = "error"
        else:
            logger.warning(f"[{request_id}] No data to standardize (collection failed)")
            processing_status_dict["standardization"] = "skipped"
        
        # ========== STEP 4: Execute rule engine on standardized data (Requirements 5.1-5.11) ==========
        rule_results = {}
        
        if standardized_datasets:
            try:
                logger.info(f"[{request_id}] Step 4: Executing rule engine on {len(standardized_datasets)} datasets")
                
                # Initialize rule engine
                rule_engine = RuleEngine()
                
                # Register all rules
                rule_engine.register_rules([
                    AdminBoundaryRule(),      # ADM-001
                    LandCoverRule(),          # LC-001
                    BuildingPresenceRule(),   # BLD-001
                    RoadNetworkRule(),        # RD-001
                    WaterFeaturesRule(),      # WT-001
                    ElevationRule()           # ELV-001
                ])
                
                # Execute all rules on standardized data
                rule_results = rule_engine.execute(standardized_datasets)
                logger.info(f"[{request_id}] ✓ Rule engine completed: {len(rule_results)} rules executed")
                
                # Count results by status
                success_count = sum(1 for r in rule_results.values() if r.status == "success")
                insufficient_count = sum(1 for r in rule_results.values() if r.status == "insufficient_data")
                failed_count = sum(1 for r in rule_results.values() if r.status == "failed")
                
                logger.info(f"[{request_id}] Rule results: {success_count} success, {insufficient_count} insufficient_data, {failed_count} failed")
                
                # Determine rule engine status
                if success_count == len(rule_results):
                    rule_engine_status = "success"
                elif success_count > 0:
                    rule_engine_status = "partial"
                else:
                    rule_engine_status = "insufficient_data" if insufficient_count > 0 else "error"
                
                processing_status_dict["rule_engine"] = rule_engine_status
                
            except Exception as e:
                logger.error(f"[{request_id}] ✗ Rule engine execution failed: {str(e)}", exc_info=True)
                safe_message = ErrorMessageSanitizer.sanitize_system_error(str(e))
                errors.append(safe_message)
                processing_status_dict["rule_engine"] = "error"
        else:
            logger.warning(f"[{request_id}] Skipping rule engine (no standardized data)")
            processing_status_dict["rule_engine"] = "skipped"
        
        # ========== STEP 5: Generate output response (Requirements 6.1-6.8) ==========
        try:
            logger.info(f"[{request_id}] Step 5: Generating output response")
            
            output_generator = OutputGenerator()
            
            # Build polygon info for output
            polygon_info = {
                "area_sqkm": polygon_metadata.area_sqkm,
                "bounding_box": polygon_metadata.bounding_box,
                "centroid": polygon_metadata.centroid,
                "vertices": polygon_metadata.num_vertices
            }
            
            # Convert processing_status_dict to ProcessingStatus model
            processing_status_model = ProcessingStatus(
                validation=processing_status_dict.get("validation", "pending"),
                data_collection=processing_status_dict.get("data_collection", "pending"),
                standardization=processing_status_dict.get("standardization", "pending"),
                rule_engine=processing_status_dict.get("rule_engine", "pending"),
                output_generation="in_progress"
            )
            
            # Generate complete response
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Determine overall status
            validation_ok = processing_status_dict.get("validation") == "success"
            collection_ok = processing_status_dict.get("data_collection") in ["success", "partial"]
            
            if validation_ok and collection_ok and rule_results:
                # Check if we have any successful rules
                success_rules = sum(1 for r in rule_results.values() if r.status == "success")
                if success_rules > 0:
                    overall_status = "success"
                else:
                    overall_status = "partial"
            elif validation_ok and collection_ok:
                overall_status = "partial"
            else:
                overall_status = "error"
            
            # Build land_information from rule results
            land_information = LandInformation()
            for rule_id, rule_result in rule_results.items():
                if hasattr(rule_result, 'output'):
                    # Map rule IDs to land_information fields
                    if rule_id == "ADM-001":
                        land_information.administrative = rule_result.output
                    elif rule_id == "LC-001":
                        land_information.land_cover = rule_result.output
                    elif rule_id == "BLD-001":
                        land_information.buildings = rule_result.output
                    elif rule_id == "RD-001":
                        land_information.roads = rule_result.output
                    elif rule_id == "WT-001":
                        land_information.water = rule_result.output
                    elif rule_id == "ELV-001":
                        land_information.elevation = rule_result.output
            
            # Create final response
            response = AnalysisResponse(
                request_id=request_id,
                status=overall_status,
                timestamp=datetime.utcnow(),
                processing_time_ms=processing_time_ms,
                land_information=land_information,
                processing_status=processing_status_model,
                provider_status=provider_status,
                errors=errors
            )
            
            processing_status_model.output_generation = "success"
            
            logger.info(f"[{request_id}] ✓ Analysis complete ({processing_time_ms}ms, status={overall_status})")
            return response.model_dump()
            
        except Exception as e:
            logger.error(f"[{request_id}] ✗ Output generation failed: {str(e)}", exc_info=True)
            safe_message = ErrorMessageSanitizer.sanitize_system_error(str(e))
            errors.append(safe_message)
            
            # Return error response with what we have
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            response = AnalysisResponse(
                request_id=request_id,
                status="error",
                timestamp=datetime.utcnow(),
                processing_time_ms=processing_time_ms,
                processing_status=ProcessingStatus(
                    validation=processing_status_dict.get("validation", "pending"),
                    data_collection=processing_status_dict.get("data_collection", "pending"),
                    standardization=processing_status_dict.get("standardization", "pending"),
                    rule_engine=processing_status_dict.get("rule_engine", "pending"),
                    output_generation="error"
                ),
                provider_status=provider_status,
                errors=errors
            )
            
            return response.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        # Unexpected error - let middleware handle it
        logger.error(f"[{request_id}] ✗ Unexpected error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
