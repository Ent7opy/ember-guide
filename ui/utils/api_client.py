"""API client for EmberGuide backend."""

import os
from typing import List, Dict, Optional

import requests
import streamlit as st

# API base URL from environment or default
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_fires() -> List[Dict]:
    """
    Fetch list of active fires from API.
    
    Returns:
        List of fire dictionaries
    """
    try:
        response = requests.get(f"{API_BASE_URL}/fires", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('fires', [])
    except requests.RequestException as e:
        st.error(f"Failed to load fires: {e}")
        return []


@st.cache_data(ttl=300)
def get_nowcast(fire_id: str, horizon: int = 24) -> Optional[Dict]:
    """
    Fetch nowcast data for a specific fire.
    
    Args:
        fire_id: Fire identifier
        horizon: Forecast horizon in hours
    
    Returns:
        Nowcast dictionary or None if not found
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/nowcast/{fire_id}",
            params={'horizon': horizon},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to load nowcast: {e}")
        return None


def download_geotiff(fire_id: str, filename: str) -> Optional[bytes]:
    """
    Download GeoTIFF file from API.
    
    Args:
        fire_id: Fire identifier
        filename: File name to download
    
    Returns:
        File contents as bytes or None
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/downloads/{fire_id}/{filename}",
            timeout=30
        )
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        st.error(f"Failed to download file: {e}")
        return None


def get_report(fire_id: str, horizon: int = 24) -> Optional[Dict]:
    """
    Get JSON report for a fire.
    
    Args:
        fire_id: Fire identifier
        horizon: Forecast horizon
    
    Returns:
        Report dictionary or None
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/report/{fire_id}",
            params={'horizon': horizon},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to load report: {e}")
        return None


def check_health() -> bool:
    """
    Check if API is healthy.
    
    Returns:
        True if API is responding, False otherwise
    """
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False

