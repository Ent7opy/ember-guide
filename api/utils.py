"""Utility functions for the API."""

import json
from pathlib import Path
from typing import Optional, Dict

import rasterio


def load_products_index() -> dict:
    """Load the products index.json file."""
    index_path = Path('data/products/index.json')
    
    if not index_path.exists():
        return {'fires': [], 'generated_at': None}
    
    with open(index_path, 'r') as f:
        return json.load(f)


def load_fire_metadata(fire_id: str) -> Optional[dict]:
    """Load metadata for a specific fire."""
    metadata_path = Path(f'data/products/{fire_id}/metadata.json')
    
    if not metadata_path.exists():
        return None
    
    with open(metadata_path, 'r') as f:
        return json.load(f)


def get_geotiff_info(tif_path: Path) -> dict:
    """Get information about a GeoTIFF file."""
    with rasterio.open(tif_path) as src:
        return {
            'shape': [src.height, src.width],
            'crs': str(src.crs),
            'bounds': list(src.bounds),
            'transform': list(src.transform)
        }


def get_caveats() -> list:
    """Return standard caveats list."""
    return [
        "Research preview — not for life-safety decisions.",
        "Hotspot detection has 3–6 hour lag.",
        "Weather resolution is coarse (~25 km for ERA5).",
        "Model uses simplified physics - not a tactical fire model."
    ]


def get_attribution() -> list:
    """Return data attribution list."""
    return [
        "FIRMS (NASA): Active fire detections",
        "ERA5 (Copernicus/ECMWF): Weather reanalysis",
        "SRTM (NASA/USGS): Terrain data"
    ]

