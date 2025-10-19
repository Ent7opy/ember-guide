"""Baseline physics-based fire spread model."""

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import binary_dilation

from ..utils import setup_logger

logger = setup_logger(__name__)


def initialize_grid(
    hotspots_df: pd.DataFrame,
    grid_shape: Tuple[int, int],
    transform: rasterio.Affine,
    seed_strength: float = 1.0
) -> np.ndarray:
    """
    Initialize fire grid from hotspot locations.
    
    Args:
        hotspots_df: DataFrame with 'latitude' and 'longitude' columns
        grid_shape: (height, width) of output grid
        transform: Rasterio affine transform for grid
        seed_strength: Initial intensity value for seeds
    
    Returns:
        Grid with seeds marked
    """
    grid = np.zeros(grid_shape, dtype=np.float32)
    
    # Convert lat/lon to pixel coordinates
    from rasterio.transform import rowcol
    
    for _, hotspot in hotspots_df.iterrows():
        try:
            row, col = rowcol(
                transform,
                hotspot['longitude'],
                hotspot['latitude']
            )
            
            if 0 <= row < grid_shape[0] and 0 <= col < grid_shape[1]:
                grid[row, col] = seed_strength
        except Exception as e:
            continue
    
    logger.info(f"Initialized {np.sum(grid > 0)} seed cells")
    return grid


def compute_spread_potential(
    wind_u: np.ndarray,
    wind_v: np.ndarray,
    slope: np.ndarray,
    rh: np.ndarray,
    config: dict
) -> np.ndarray:
    """
    Compute fire spread potential based on weather and terrain.
    
    Simplified model:
    - Wind component: Wind speed favors spread in wind direction
    - Slope component: Upslope spread is faster
    - Dryness component: Low RH increases spread
    
    Args:
        wind_u: East-west wind component (m/s)
        wind_v: North-south wind component (m/s)
        slope: Slope in degrees
        rh: Relative humidity (%)
        config: Configuration dict with weights and thresholds
    
    Returns:
        Spread potential grid [0-1]
    """
    # Wind speed
    wind_speed = np.sqrt(wind_u**2 + wind_v**2)
    wind_factor = np.clip(wind_speed / 20.0, 0, 1)  # Normalize to ~20 m/s max
    
    # Slope factor (upslope increases spread)
    slope_factor = np.clip(slope / config.get('slope_max_deg', 45.0), 0, 1)
    
    # Dryness factor (low RH increases spread)
    rh_threshold = config.get('rh_dry_threshold', 30.0)
    dryness_factor = np.clip((100 - rh) / 100.0, 0, 1)
    
    # Combine factors with weights
    potential = (
        config.get('wind_weight', 0.5) * wind_factor +
        config.get('slope_weight', 0.3) * slope_factor +
        config.get('dryness_weight', 0.2) * dryness_factor
    )
    
    return np.clip(potential, 0, 1)


def propagate_spread(
    current_grid: np.ndarray,
    spread_potential: np.ndarray,
    threshold: float = 0.3,
    neighbors: int = 8
) -> np.ndarray:
    """
    Propagate fire to neighboring cells based on spread potential.
    
    Args:
        current_grid: Current fire state [0-1]
        spread_potential: Spread potential for each cell [0-1]
        threshold: Minimum potential needed to spread
        neighbors: 4 (cardinal) or 8 (cardinal + diagonal)
    
    Returns:
        Updated fire grid
    """
    # Find active fire cells
    active_mask = current_grid > 0
    
    # Dilate to find neighboring cells
    if neighbors == 4:
        structure = np.array([[0, 1, 0],
                            [1, 1, 1],
                            [0, 1, 0]])
    else:  # 8 neighbors
        structure = np.ones((3, 3))
    
    neighbor_mask = binary_dilation(active_mask, structure=structure)
    
    # Spread to neighbors if potential exceeds threshold
    can_spread = (spread_potential > threshold) & neighbor_mask & ~active_mask
    
    # Update grid
    new_grid = current_grid.copy()
    new_grid[can_spread] = spread_potential[can_spread]
    
    return new_grid


def run_baseline_spread(
    hotspots_df: pd.DataFrame,
    wind_u: np.ndarray,
    wind_v: np.ndarray,
    slope: np.ndarray,
    rh: np.ndarray,
    transform: rasterio.Affine,
    config: dict,
    n_timesteps: int = 24
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Run baseline fire spread model.
    
    Args:
        hotspots_df: DataFrame with hotspot locations
        wind_u: East-west wind component grid (m/s)
        wind_v: North-south wind component grid (m/s)
        slope: Slope grid (degrees)
        rh: Relative humidity grid (%)
        transform: Rasterio affine transform
        config: Model configuration
        n_timesteps: Number of hourly timesteps to simulate
    
    Returns:
        Tuple of (final fire grid, max intensity grid)
    """
    logger.info(f"Running baseline spread model for {n_timesteps} timesteps")
    
    # Initialize grid
    grid_shape = wind_u.shape
    current_grid = initialize_grid(hotspots_df, grid_shape, transform, 
                                   config.get('seed_strength', 1.0))
    
    # Track maximum intensity over time
    max_grid = current_grid.copy()
    
    # Compute spread potential (static for simplified model)
    spread_potential = compute_spread_potential(wind_u, wind_v, slope, rh, config)
    
    # Time evolution
    for t in range(n_timesteps):
        # Propagate fire
        current_grid = propagate_spread(
            current_grid,
            spread_potential,
            threshold=config.get('spread_threshold', 0.3),
            neighbors=config.get('neighbors', 8)
        )
        
        # Update maximum
        max_grid = np.maximum(max_grid, current_grid)
        
        # Log progress
        if (t + 1) % 6 == 0:
            active_cells = np.sum(current_grid > 0)
            logger.info(f"Timestep {t+1}/{n_timesteps}: {active_cells} active cells")
    
    final_cells = np.sum(current_grid > 0)
    logger.info(f"Spread complete: {final_cells} total affected cells")
    
    return current_grid, max_grid

