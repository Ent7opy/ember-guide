"""FIRMS (Fire Information for Resource Management System) data ingestion."""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests

from ..utils import setup_logger, timestamp_filename, ensure_dir, save_checksum

logger = setup_logger(__name__)


def fetch_firms_hotspots(
    bbox: Tuple[float, float, float, float],
    since: str,
    api_key: str,
    output_dir: Path,
    source: str = "VIIRS_NOAA20_NRT",
    max_retries: int = 3,
    retry_delay: int = 5
) -> Path:
    """
    Fetch MODIS/VIIRS hotspot detections from NASA FIRMS API.
    
    Args:
        bbox: Bounding box (west, south, east, north) in WGS84
        since: ISO 8601 timestamp to fetch data since
        api_key: FIRMS API key
        output_dir: Directory to save CSV file
        source: Data source (VIIRS_NOAA20_NRT, MODIS_NRT, etc.)
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Path to saved CSV file
    """
    logger.info(f"Fetching FIRMS hotspots: bbox={bbox}, since={since}, source={source}")
    
    # Parse since date
    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
    now_dt = datetime.now(since_dt.tzinfo)  # Make timezone-aware
    days_back = max(1, (now_dt - since_dt).days + 1)
    
    # FIRMS API endpoint
    west, south, east, north = bbox
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{api_key}/{source}/{west},{south},{east},{north}/{days_back}"
    )
    
    # Retry logic
    for attempt in range(max_retries):
        try:
            logger.info(f"Requesting FIRMS data (attempt {attempt + 1}/{max_retries})")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            if df.empty:
                logger.warning("No hotspots found in specified area/timerange")
            else:
                logger.info(f"Retrieved {len(df)} hotspot detections")
            
            # Save to file
            ensure_dir(output_dir)
            filename = timestamp_filename("firms_hotspots", "csv")
            output_path = output_dir / filename
            
            df.to_csv(output_path, index=False)
            save_checksum(output_path)
            
            logger.info(f"Saved FIRMS data to {output_path}")
            return output_path
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to fetch FIRMS data after {max_retries} attempts")
                raise
    
    raise RuntimeError("Failed to fetch FIRMS data")


def filter_recent_hotspots(csv_path: Path, hours: int = 48) -> pd.DataFrame:
    """
    Filter hotspots to only recent detections.
    
    Args:
        csv_path: Path to FIRMS CSV file
        hours: Keep hotspots from last N hours
    
    Returns:
        Filtered DataFrame
    """
    df = pd.read_csv(csv_path)
    
    # Parse acquisition datetime
    df['acq_datetime'] = pd.to_datetime(df['acq_date'] + ' ' + df['acq_time'].astype(str).str.zfill(4), 
                                        format='%Y-%m-%d %H%M')
    
    # Filter by time
    cutoff = datetime.now() - timedelta(hours=hours)
    df_recent = df[df['acq_datetime'] >= cutoff]
    
    logger.info(f"Filtered to {len(df_recent)} hotspots from last {hours} hours")
    return df_recent

