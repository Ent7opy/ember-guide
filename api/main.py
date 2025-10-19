"""EmberGuide FastAPI main application."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

from .contracts import (
    HealthResponse, FireCatalog, Fire, Nowcast, 
    GridMeta, NowcastAssets, NowcastMetrics, FireDetections
)
from .utils import (
    load_products_index, load_fire_metadata, get_geotiff_info,
    get_caveats, get_attribution
)

# Create FastAPI app
app = FastAPI(
    title="EmberGuide API",
    description="Wildfire nowcast API serving probability maps and metadata",
    version="0.1.0-poc"
)

# CORS middleware for Streamlit UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "message": "EmberGuide API",
        "version": "0.1.0-poc",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns system status and timestamp.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        version="0.1.0-poc"
    )


@app.get("/fires", response_model=FireCatalog, tags=["Fires"])
async def list_fires(
    region: Optional[str] = Query(None, description="Filter by region code"),
    since: Optional[str] = Query(None, description="Filter by update time (ISO 8601)")
):
    """
    List all active fires with available nowcasts.
    
    Query Parameters:
    - region: Optional region code filter
    - since: Optional ISO 8601 timestamp filter
    """
    index = load_products_index()
    
    fires = index.get('fires', [])
    
    # Apply filters
    if region:
        fires = [f for f in fires if f.get('region') == region]
    
    if since:
        # Filter by update time (simplified for POC)
        fires = [f for f in fires if f.get('last_updated', '') >= since]
    
    return FireCatalog(
        fires=[Fire(**f) for f in fires],
        count=len(fires),
        generated_at=index.get('generated_at', datetime.utcnow().isoformat() + 'Z')
    )


@app.get("/nowcast/{fire_id}", response_model=Nowcast, tags=["Nowcast"])
async def get_nowcast(
    fire_id: str,
    horizon: int = Query(24, description="Forecast horizon in hours (12, 24, or 48)")
):
    """
    Get nowcast data for a specific fire.
    
    Path Parameters:
    - fire_id: Fire identifier
    
    Query Parameters:
    - horizon: Forecast horizon (default: 24 hours)
    """
    # Load metadata
    metadata = load_fire_metadata(fire_id)
    
    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail=f"Fire {fire_id} not found"
        )
    
    # Check if requested horizon is available
    if metadata['horizon_hours'] != horizon:
        raise HTTPException(
            status_code=404,
            detail=f"Horizon {horizon}h not available for fire {fire_id}"
        )
    
    horizon_str = f"{horizon}h"
    
    # Build assets paths
    products_path = f"/downloads/{fire_id}"
    assets = NowcastAssets(
        prob_tif=f"{products_path}/nowcast_{horizon_str}.tif",
        dir_tif=f"{products_path}/direction_{horizon_str}.tif",
        uncertainty_tif=f"{products_path}/uncertainty_{horizon_str}.tif"
    )
    
    # Build response
    return Nowcast(
        fire_id=fire_id,
        horizon=horizon,
        grid_meta=GridMeta(**metadata['grid_meta']),
        assets=assets,
        detections=FireDetections(**metadata['detections']),
        metrics=NowcastMetrics(**metadata['metrics']),
        caveats=get_caveats(),
        attribution=get_attribution(),
        generated_at=metadata['generated_at']
    )


@app.get("/downloads/{fire_id}/{filename}", tags=["Downloads"])
async def download_file(fire_id: str, filename: str):
    """
    Download GeoTIFF or other data files.
    
    Path Parameters:
    - fire_id: Fire identifier
    - filename: File name to download
    """
    file_path = Path(f"data/products/{fire_id}/{filename}")
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File {filename} not found for fire {fire_id}"
        )
    
    # Determine media type
    if filename.endswith('.tif'):
        media_type = "image/tiff"
    elif filename.endswith('.json'):
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


@app.get("/report/{fire_id}", tags=["Reports"])
async def get_report(fire_id: str, horizon: int = Query(24)):
    """
    Get JSON report with summary and metrics.
    
    Path Parameters:
    - fire_id: Fire identifier
    
    Query Parameters:
    - horizon: Forecast horizon (default: 24)
    """
    metadata = load_fire_metadata(fire_id)
    
    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail=f"Fire {fire_id} not found"
        )
    
    # Build comprehensive report
    report = {
        'fire_id': fire_id,
        'region': metadata['region'],
        'horizon': horizon,
        'summary': {
            'detections_count': metadata['detections']['count'],
            'detections_last_time': metadata['detections']['latest_time'],
            'affected_area_km2': metadata['metrics']['affected_area_km2'],
            'max_probability': metadata['metrics']['max_probability']
        },
        'config': metadata.get('config', {}),
        'caveats': get_caveats(),
        'attribution': get_attribution(),
        'generated_at': metadata['generated_at']
    }
    
    return report


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

