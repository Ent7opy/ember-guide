"""Pydantic models for API request/response schemas."""

from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel, Field


class FireDetections(BaseModel):
    """Fire detection summary."""
    count: int = Field(..., description="Number of hotspot detections")
    last_time: Optional[str] = Field(None, description="Most recent detection timestamp")


class Fire(BaseModel):
    """Fire catalog entry."""
    id: str = Field(..., description="Unique fire identifier")
    region: str = Field(..., description="Region code or name")
    centroid: Dict[str, float] = Field(..., description="Fire center lat/lon")
    bbox: List[float] = Field(..., description="Bounding box [west, south, east, north]")
    status: str = Field(..., description="Fire status: active | contained | out")
    nowcast_available: List[int] = Field(..., description="Available forecast horizons (hours)")
    last_updated: str = Field(..., description="Last update timestamp")


class FireCatalog(BaseModel):
    """List of fires."""
    fires: List[Fire]
    count: int
    generated_at: str


class GridMeta(BaseModel):
    """Grid metadata."""
    crs: str = Field(..., description="Coordinate reference system")
    resolution_m: float = Field(..., description="Grid resolution in meters")
    shape: List[int] = Field(..., description="Grid shape [height, width]")


class NowcastAssets(BaseModel):
    """Nowcast data assets."""
    prob_tif: str = Field(..., description="Probability GeoTIFF path")
    dir_tif: str = Field(..., description="Direction GeoTIFF path")
    uncertainty_tif: str = Field(..., description="Uncertainty GeoTIFF path")


class NowcastMetrics(BaseModel):
    """Nowcast metrics."""
    max_probability: float
    mean_probability: float
    affected_area_km2: float


class Nowcast(BaseModel):
    """Nowcast response."""
    fire_id: str
    horizon: int
    grid_meta: GridMeta
    assets: NowcastAssets
    detections: FireDetections
    metrics: NowcastMetrics
    caveats: List[str]
    attribution: List[str]
    generated_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str = "0.1.0-poc"

