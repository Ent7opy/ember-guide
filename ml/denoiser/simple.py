"""Rule-based hotspot denoising filter."""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from pipeline.utils import setup_logger

logger = setup_logger(__name__)


def filter_hotspots(
    detections_df: pd.DataFrame,
    config: dict
) -> pd.DataFrame:
    """
    Filter hotspots using rule-based criteria.
    
    Filters based on:
    1. Confidence threshold
    2. Persistence (multiple detections in same area)
    3. Basic land cover heuristics
    
    Args:
        detections_df: DataFrame with FIRMS hotspot detections
        config: Configuration dict with filter parameters
    
    Returns:
        Filtered DataFrame
    """
    logger.info(f"Filtering {len(detections_df)} hotspots")
    
    if detections_df.empty:
        return detections_df
    
    # Make a copy
    df = detections_df.copy()
    
    # Filter 1: Confidence threshold
    min_confidence = config.get('min_confidence', 75)
    modis_levels = config.get('modis_confidence_levels', ['nominal', 'high'])
    
    if 'confidence' in df.columns:
        # VIIRS: numeric 0-100
        if df['confidence'].dtype in [np.float64, np.int64, np.float32, np.int32]:
            df = df[df['confidence'] >= min_confidence]
        # MODIS: categorical (low/nominal/high)
        else:
            df = df[df['confidence'].isin(modis_levels)]
    
    logger.info(f"After confidence filter: {len(df)} hotspots")
    
    # Filter 2: Persistence (require multiple detections nearby)
    if config.get('persistence_min_detections', 0) > 1:
        df = apply_persistence_filter(
            df,
            min_detections=config['persistence_min_detections'],
            radius_km=config.get('persistence_radius_km', 5.0),
            window_hours=config.get('persistence_window_hours', 48)
        )
        logger.info(f"After persistence filter: {len(df)} hotspots")
    
    # Filter 3: Basic land cover (remove water bodies)
    # For POC, use simple lat/lon heuristics
    # In production, would use actual land cover data
    df = apply_land_cover_filter(df)
    logger.info(f"After land cover filter: {len(df)} hotspots")
    
    logger.info(f"Denoising complete: kept {len(df)}/{len(detections_df)} hotspots")
    
    return df


def apply_persistence_filter(
    df: pd.DataFrame,
    min_detections: int = 2,
    radius_km: float = 5.0,
    window_hours: int = 48
) -> pd.DataFrame:
    """
    Keep only hotspots with multiple detections nearby in time window.
    
    Args:
        df: Hotspots DataFrame
        min_detections: Minimum number of detections required
        radius_km: Search radius in km
        window_hours: Time window in hours
    
    Returns:
        Filtered DataFrame
    """
    if len(df) < min_detections:
        return df
    
    # Parse datetime if not already done
    if 'acq_datetime' not in df.columns:
        df['acq_datetime'] = pd.to_datetime(
            df['acq_date'] + ' ' + df['acq_time'].astype(str).str.zfill(4),
            format='%Y-%m-%d %H%M'
        )
    
    # Build spatial index
    coords = df[['latitude', 'longitude']].values
    tree = cKDTree(coords)
    
    # Convert radius to degrees (approximate)
    radius_deg = radius_km / 111.0
    
    # Find neighbors for each point
    keep_mask = np.zeros(len(df), dtype=bool)
    
    for i, (idx, row) in enumerate(df.iterrows()):
        # Find spatial neighbors
        indices = tree.query_ball_point([row['latitude'], row['longitude']], radius_deg)
        
        # Filter by time window
        time_diffs = [abs((df.iloc[j]['acq_datetime'] - row['acq_datetime']).total_seconds() / 3600) 
                     for j in indices]
        nearby = [j for j, td in zip(indices, time_diffs) if td <= window_hours]
        
        # Keep if enough nearby detections
        if len(nearby) >= min_detections:
            keep_mask[i] = True
    
    return df[keep_mask].reset_index(drop=True)


def apply_land_cover_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove hotspots over obvious water bodies.
    
    Simplified heuristic for POC:
    - Check if lat/lon is in known major water bodies
    - In production, use actual land cover dataset
    
    Args:
        df: Hotspots DataFrame
    
    Returns:
        Filtered DataFrame
    """
    # For POC: very simple heuristic
    # Remove points that are clearly over major water bodies
    # (In production, use MODIS land cover or similar)
    
    # Example: Remove points over Pacific Ocean (far west of California coast)
    keep_mask = df['longitude'] > -125.0  # Rough coastline filter
    
    return df[keep_mask].reset_index(drop=True)

