"""SRTM digital elevation model data ingestion."""

import os
import time
from pathlib import Path
from typing import Tuple, List
import tempfile

import requests
import rasterio
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling

from ..utils import setup_logger, timestamp_filename, ensure_dir, save_checksum

logger = setup_logger(__name__)


def get_srtm_tile_names(bbox: Tuple[float, float, float, float]) -> List[str]:
    """
    Determine which SRTM tiles are needed for a bounding box.
    
    SRTM tiles are named like: srtm_01_02.tif (longitude_01, latitude_02)
    
    Args:
        bbox: Bounding box (west, south, east, north) in WGS84
    
    Returns:
        List of tile names needed
    """
    west, south, east, north = bbox
    
    # SRTM tiles are 5x5 degrees
    # Tile indices: 1-72 for longitude, 1-24 for latitude
    # Longitude: -180 to +180 maps to 1-72 (each tile is 5 degrees)
    # Latitude: -60 to +60 maps to 1-24 (each tile is 5 degrees)
    
    lon_tiles = range(int((west + 180) // 5) + 1, int((east + 180) // 5) + 2)
    lat_tiles = range(int((south + 60) // 5) + 1, int((north + 60) // 5) + 2)
    
    tiles = []
    for lon_idx in lon_tiles:
        for lat_idx in lat_tiles:
            tiles.append(f"srtm_{lon_idx:02d}_{lat_idx:02d}")
    
    return tiles


def download_srtm_tiles(
    bbox: Tuple[float, float, float, float],
    output_dir: Path,
    max_retries: int = 3,
    retry_delay: int = 5
) -> Path:
    """
    Download SRTM DEM tiles and mosaic them.
    
    For POC, we'll use a simple approach: use elevation data from SRTM via
    a public source or create a synthetic DEM if unavailable.
    
    Args:
        bbox: Bounding box (west, south, east, north) in WGS84
        output_dir: Directory to save DEM file
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Path to saved DEM GeoTIFF
    """
    logger.info(f"Preparing SRTM DEM for bbox={bbox}")
    
    # For POC: Create a synthetic DEM based on location
    # In production, would download from https://srtm.csi.cgiar.org/ or USGS
    
    ensure_dir(output_dir)
    filename = timestamp_filename("srtm_dem", "tif")
    output_path = output_dir / filename
    
    # Create synthetic elevation model (simple gradient)
    # California typically has west (coast, low) to east (mountains, high)
    west, south, east, north = bbox
    
    # Create a simple elevation model
    import numpy as np
    
    # Grid dimensions (approximate 90m resolution)
    height = int((north - south) * 111000 / 90)  # ~111km per degree
    width = int((east - west) * 111000 / 90)
    
    # Create synthetic elevation (0-3000m gradient west to east)
    x = np.linspace(0, 3000, width)
    y = np.linspace(0, 500, height)
    elevation = np.outer(np.ones(height), x) + np.outer(y, np.ones(width))
    elevation = elevation.astype(np.float32)
    
    # Add some noise for realistic terrain
    np.random.seed(42)
    noise = np.random.normal(0, 50, elevation.shape).astype(np.float32)
    elevation += noise
    elevation = np.clip(elevation, 0, None)
    
    # Create GeoTIFF
    from rasterio.transform import from_bounds
    
    transform = from_bounds(west, south, east, north, width, height)
    
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=np.float32,
        crs='EPSG:4326',
        transform=transform,
        compress='lzw'
    ) as dst:
        dst.write(elevation, 1)
    
    save_checksum(output_path)
    logger.info(f"Created synthetic SRTM DEM at {output_path}")
    logger.warning("Using synthetic DEM for POC - replace with real SRTM data for production")
    
    return output_path

