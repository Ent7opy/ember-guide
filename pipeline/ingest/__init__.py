"""Data ingestion modules for FIRMS, ERA5, and SRTM."""

from .firms import fetch_firms_hotspots
from .era5 import fetch_era5_weather
from .srtm import download_srtm_tiles

__all__ = ['fetch_firms_hotspots', 'fetch_era5_weather', 'download_srtm_tiles']

