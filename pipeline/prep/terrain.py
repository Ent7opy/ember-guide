"""Terrain feature computation from DEM."""

from pathlib import Path
from typing import Tuple

import numpy as np
import rasterio
from scipy.ndimage import sobel

from ..utils import setup_logger

logger = setup_logger(__name__)


def compute_slope_aspect(
    dem_path: Path,
    output_dir: Path,
    algorithm: str = "horn"
) -> Tuple[Path, Path]:
    """
    Compute slope and aspect from digital elevation model.
    
    Args:
        dem_path: Path to DEM GeoTIFF
        output_dir: Directory to save slope and aspect rasters
        algorithm: Method for gradient calculation ("horn" or "simple")
    
    Returns:
        Tuple of (slope_path, aspect_path)
    """
    logger.info(f"Computing slope and aspect from {dem_path.name}")
    
    with rasterio.open(dem_path) as src:
        elevation = src.read(1)
        transform = src.transform
        profile = src.profile
        
        # Get cell size (assuming square cells)
        cell_size = transform.a  # x resolution
        
        # Compute gradients using Sobel filter (Horn's method approximation)
        if algorithm == "horn":
            dz_dx = sobel(elevation, axis=1) / (8 * cell_size)
            dz_dy = sobel(elevation, axis=0) / (8 * cell_size)
        else:
            # Simple gradient
            dz_dy, dz_dx = np.gradient(elevation, cell_size)
        
        # Compute slope in degrees
        slope = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)) * 180 / np.pi
        slope = slope.astype(np.float32)
        
        # Compute aspect in degrees (0 = North, 90 = East, 180 = South, 270 = West)
        aspect = np.arctan2(-dz_dy, dz_dx) * 180 / np.pi
        aspect = (90 - aspect) % 360  # Convert to compass bearing
        aspect = aspect.astype(np.float32)
        
        # Handle flat areas (slope ~ 0)
        flat_mask = slope < 0.1
        aspect[flat_mask] = -1  # Set to -1 for flat areas
        
        # Save slope
        output_dir.mkdir(parents=True, exist_ok=True)
        slope_path = output_dir / "slope.tif"
        
        with rasterio.open(slope_path, 'w', **profile) as dst:
            dst.write(slope, 1)
            dst.set_band_description(1, "Slope (degrees)")
        
        logger.info(f"Slope saved to {slope_path} (range: {slope.min():.1f}-{slope.max():.1f} deg)")
        
        # Save aspect
        aspect_path = output_dir / "aspect.tif"
        
        with rasterio.open(aspect_path, 'w', **profile) as dst:
            dst.write(aspect, 1)
            dst.set_band_description(1, "Aspect (degrees, -1=flat)")
        
        logger.info(f"Aspect saved to {aspect_path}")
        
        return slope_path, aspect_path

