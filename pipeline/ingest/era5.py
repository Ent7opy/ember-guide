"""ERA5 weather data ingestion from Copernicus CDS."""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, List

import cdsapi

from ..utils import setup_logger, timestamp_filename, ensure_dir, save_checksum

logger = setup_logger(__name__)


def fetch_era5_weather(
    bbox: Tuple[float, float, float, float],
    date: str,
    variables: List[str],
    api_key: str,
    api_url: str,
    output_dir: Path,
    hours: int = 30,
    max_retries: int = 5,
    retry_delay: int = 10
) -> Path:
    """
    Download ERA5 reanalysis weather data from Copernicus CDS.
    
    Args:
        bbox: Bounding box (west, south, east, north) in WGS84
        date: ISO 8601 date to start fetching
        variables: List of ERA5 variable names
        api_key: CDS API key
        api_url: CDS API URL
        output_dir: Directory to save NetCDF file
        hours: Number of hours to fetch
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Path to saved NetCDF file
    """
    logger.info(f"Fetching ERA5 data: bbox={bbox}, date={date}, variables={variables}")
    
    # Parse date
    start_dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
    
    # Generate time list
    times = [(start_dt + timedelta(hours=i)).strftime("%H:00") for i in range(hours)]
    
    # CDS API request
    west, south, east, north = bbox
    
    request = {
        'product_type': 'reanalysis',
        'format': 'netcdf',
        'variable': variables,
        'year': start_dt.strftime("%Y"),
        'month': start_dt.strftime("%m"),
        'day': start_dt.strftime("%d"),
        'time': times,
        'area': [north, west, south, east],  # CDS uses [N, W, S, E]
    }
    
    # Setup CDS client
    c = cdsapi.Client(url=api_url, key=api_key)
    
    # Output file
    ensure_dir(output_dir)
    filename = timestamp_filename("era5_weather", "nc")
    output_path = output_dir / filename
    
    # Retry logic
    for attempt in range(max_retries):
        try:
            logger.info(f"Requesting ERA5 data (attempt {attempt + 1}/{max_retries})")
            c.retrieve(
                'reanalysis-era5-single-levels',
                request,
                str(output_path)
            )
            
            save_checksum(output_path)
            logger.info(f"Saved ERA5 data to {output_path}")
            return output_path
            
        except Exception as e:
            logger.warning(f"ERA5 request failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to fetch ERA5 data after {max_retries} attempts")
                raise
    
    raise RuntimeError("Failed to fetch ERA5 data")

