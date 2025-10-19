"""Monte Carlo ensemble fire spread modeling for uncertainty quantification."""

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import rasterio

from .baseline import run_baseline_spread
from ..utils import setup_logger

logger = setup_logger(__name__)


def perturb_weather(
    wind_u: np.ndarray,
    wind_v: np.ndarray,
    temp: np.ndarray,
    rh: np.ndarray,
    config: dict,
    seed: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Add random perturbations to weather variables for Monte Carlo.
    
    Args:
        wind_u: East-west wind component
        wind_v: North-south wind component
        temp: Temperature
        rh: Relative humidity
        config: Perturbation configuration
        seed: Random seed
    
    Returns:
        Tuple of perturbed (wind_u, wind_v, temp, rh)
    """
    np.random.seed(seed)
    
    # Perturbation magnitudes (as fraction of value)
    wind_pert = config.get('wind_perturbation', 0.2)
    temp_pert = config.get('temp_perturbation', 0.05)
    rh_pert = config.get('rh_perturbation', 0.1)
    
    # Add perturbations
    wind_u_pert = wind_u * (1 + np.random.uniform(-wind_pert, wind_pert, wind_u.shape))
    wind_v_pert = wind_v * (1 + np.random.uniform(-wind_pert, wind_pert, wind_v.shape))
    temp_pert_val = temp * (1 + np.random.uniform(-temp_pert, temp_pert, temp.shape))
    rh_pert_val = rh * (1 + np.random.uniform(-rh_pert, rh_pert, rh.shape))
    
    # Clip to valid ranges
    rh_pert_val = np.clip(rh_pert_val, 0, 100)
    
    return wind_u_pert, wind_v_pert, temp_pert_val, rh_pert_val


def run_monte_carlo_ensemble(
    hotspots_df: pd.DataFrame,
    wind_u: np.ndarray,
    wind_v: np.ndarray,
    temp: np.ndarray,
    slope: np.ndarray,
    rh: np.ndarray,
    transform: rasterio.Affine,
    model_config: dict,
    mc_config: dict,
    n_ensemble: int = 20,
    base_seed: int = 42,
    n_timesteps: int = 24
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Run Monte Carlo ensemble of fire spread simulations.
    
    Args:
        hotspots_df: DataFrame with hotspot locations
        wind_u: East-west wind component
        wind_v: North-south wind component
        temp: Temperature
        slope: Slope grid
        rh: Relative humidity
        transform: Rasterio affine transform
        model_config: Spread model configuration
        mc_config: Monte Carlo configuration
        n_ensemble: Number of ensemble members
        base_seed: Base random seed
        n_timesteps: Number of timesteps per run
    
    Returns:
        Tuple of (probability map, mean direction, uncertainty)
    """
    logger.info(f"Running Monte Carlo ensemble with {n_ensemble} members")
    
    grid_shape = wind_u.shape
    ensemble_results = np.zeros((n_ensemble, *grid_shape), dtype=np.float32)
    
    # Run ensemble
    for i in range(n_ensemble):
        # Perturb weather
        seed = base_seed + i
        wind_u_pert, wind_v_pert, temp_pert, rh_pert = perturb_weather(
            wind_u, wind_v, temp, rh, mc_config, seed
        )
        
        # Run spread model
        _, max_grid = run_baseline_spread(
            hotspots_df,
            wind_u_pert,
            wind_v_pert,
            slope,
            rh_pert,
            transform,
            model_config,
            n_timesteps
        )
        
        ensemble_results[i] = max_grid
        
        if (i + 1) % 5 == 0:
            logger.info(f"Completed {i+1}/{n_ensemble} ensemble members")
    
    # Compute probability (fraction of runs where cell burned)
    probability = np.mean(ensemble_results > 0, axis=0).astype(np.float32)
    
    # Compute mean intensity (for cells that burned)
    mean_intensity = np.mean(ensemble_results, axis=0).astype(np.float32)
    
    # Compute uncertainty (standard deviation across ensemble)
    uncertainty = np.std(ensemble_results, axis=0).astype(np.float32)
    
    logger.info(f"Ensemble complete. Max probability: {probability.max():.3f}")
    
    return probability, mean_intensity, uncertainty


def compute_spread_direction(
    probability: np.ndarray,
    wind_u: np.ndarray,
    wind_v: np.ndarray
) -> np.ndarray:
    """
    Compute primary spread direction from wind and probability gradient.
    
    Args:
        probability: Fire probability map
        wind_u: East-west wind component
        wind_v: North-south wind component
    
    Returns:
        Direction grid in degrees (0=N, 90=E, 180=S, 270=W)
    """
    # Compute probability gradient
    grad_y, grad_x = np.gradient(probability)
    
    # Combine with wind (wind is primary driver)
    wind_speed = np.sqrt(wind_u**2 + wind_v**2)
    wind_weight = 0.7
    gradient_weight = 0.3
    
    # Weighted average direction
    combined_x = wind_weight * wind_u + gradient_weight * grad_x
    combined_y = wind_weight * wind_v + gradient_weight * grad_y
    
    # Convert to compass bearing
    direction = np.arctan2(combined_x, combined_y) * 180 / np.pi
    direction = (direction + 360) % 360
    
    # Mask out areas with no probability
    direction[probability < 0.01] = -1
    
    return direction.astype(np.float32)

