"""Grid alignment and reprojection utilities."""

from pathlib import Path
from typing import Tuple

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj import CRS

from ..utils import setup_logger

logger = setup_logger(__name__)


def determine_utm_zone(lon: float, lat: float) -> str:
    """
    Determine UTM zone EPSG code from longitude and latitude.
    
    Args:
        lon: Longitude in decimal degrees
        lat: Latitude in decimal degrees
    
    Returns:
        EPSG code string (e.g., "EPSG:32610")
    """
    zone_number = int((lon + 180) / 6) + 1
    
    # Determine hemisphere
    if lat >= 0:
        epsg = 32600 + zone_number  # Northern hemisphere
    else:
        epsg = 32700 + zone_number  # Southern hemisphere
    
    return f"EPSG:{epsg}"


def align_to_grid(
    input_path: Path,
    output_path: Path,
    target_crs: str,
    resolution_m: float,
    bbox: Tuple[float, float, float, float] = None
) -> Path:
    """
    Reproject and resample raster to target CRS and resolution.
    
    Args:
        input_path: Input raster file
        output_path: Output raster file
        target_crs: Target CRS (e.g., "EPSG:32610")
        resolution_m: Target resolution in meters
        bbox: Optional bounding box to clip (west, south, east, north)
    
    Returns:
        Path to output raster
    """
    logger.info(f"Aligning {input_path.name} to {target_crs} at {resolution_m}m resolution")
    
    with rasterio.open(input_path) as src:
        # Calculate transform for target CRS
        if bbox:
            # If bbox provided, use it
            west, south, east, north = bbox
            
            # Transform bbox to target CRS
            from pyproj import Transformer
            transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
            west_proj, south_proj = transformer.transform(west, south)
            east_proj, north_proj = transformer.transform(east, north)
            
            width = int((east_proj - west_proj) / resolution_m)
            height = int((north_proj - south_proj) / resolution_m)
            
            from rasterio.transform import from_bounds
            transform = from_bounds(west_proj, south_proj, east_proj, north_proj, width, height)
            
        else:
            # Use full extent
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds,
                resolution=resolution_m
            )
        
        # Setup output
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Reproject
        with rasterio.open(output_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear
                )
    
    logger.info(f"Aligned raster saved to {output_path}")
    return output_path

