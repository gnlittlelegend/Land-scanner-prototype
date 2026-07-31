import json
import uvicorn
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators.polygon_validator import validate_geojson, validate_coordinates

app = FastAPI(
    title="Land Scanner Prototype",
    version="1.0.0",
    description="Geospatial data analysis platform"
)

config = None
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.json'), 'r') as f:
    config = json.load(f)

class PolygonRequest(BaseModel):
    polygon: Dict[str, Any]
    request_id: Optional[str] = None
    client_version: Optional[str] = None

class AnalysisResponse(BaseModel):
    status: str
    request_id: Optional[str] = None
    processing_time: Optional[float] = None
    analysis: Optional[Dict[str, Any]] = None
    providers: Optional[list] = None
    rules: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Land Scanner", "timestamp": datetime.now().isoformat()}

@app.get("/status")
async def status():
    return {
        "status": "operational",
        "version": config.get("app_version", "1.0.0"),
        "service": "Land Scanner Prototype",
        "enabled_providers": config.get("enabled_providers", [])
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: PolygonRequest):
    start_time = datetime.now()
    request_id = request.request_id or f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    is_valid, message = validate_geojson(request.polygon)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    is_valid, message = validate_coordinates(request.polygon)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    providers = [
        {"name": "administrative_boundaries", "status": "pending"},
        {"name": "land_cover", "status": "pending"},
        {"name": "buildings", "status": "pending"},
        {"name": "roads", "status": "pending"},
        {"name": "water_bodies", "status": "pending"},
        {"name": "elevation", "status": "pending"}
    ]
    
    rules = [
        {"id": "ADM-001", "name": "Administrative Boundary Detection", "status": "pending"},
        {"id": "LC-001", "name": "Land Cover Summary", "status": "pending"},
        {"id": "BLD-001", "name": "Building Presence", "status": "pending"},
        {"id": "RD-001", "name": "Road Detection", "status": "pending"},
        {"id": "WT-001", "name": "Water Feature Detection", "status": "pending"},
        {"id": "ELV-001", "name": "Elevation Summary", "status": "pending"}
    ]
    
    processing_time = (datetime.now() - start_time).total_seconds()
    
    return AnalysisResponse(
        status="success",
        request_id=request_id,
        processing_time=processing_time,
        analysis={"message": "Workflow initialized - collectors and rules pending implementation"},
        providers=providers,
        rules=rules,
        metadata={
            "prototype_version": config.get("app_version", "1.0.0"),
            "timestamp": datetime.now().isoformat(),
            "processing_status": "initialized"
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)