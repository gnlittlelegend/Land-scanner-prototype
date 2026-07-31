from pydantic import BaseModel
from typing import Optional

class PolygonRequest(BaseModel):
    polygon: dict
    request_id: Optional[str] = None
    client_version: Optional[str] = None

class PolygonResponse(BaseModel):
    status: str
    request_id: Optional[str] = None
    error_message: Optional[str] = None