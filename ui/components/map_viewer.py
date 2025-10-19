"""Map visualization using Folium."""

from typing import Dict
import tempfile
from pathlib import Path

import folium
from folium import plugins
import rasterio
from rasterio.warp import transform_bounds
import numpy as np
import streamlit as st
from streamlit_folium import st_folium


def create_fire_map(nowcast_data: Dict, geotiff_path: Path = None) -> folium.Map:
    """
    Create Folium map with fire nowcast visualization.
    
    Args:
        nowcast_data: Nowcast data from API
        geotiff_path: Optional path to probability GeoTIFF for overlay
    
    Returns:
        Folium map object
    """
    # Get fire centroid
    fire_center = [
        nowcast_data['grid_meta']['shape'][0] // 2,  # Approximate center
        nowcast_data['grid_meta']['shape'][1] // 2
    ]
    
    # For now, use bounding box center (simplified for POC)
    # In production, would compute proper center from grid metadata
    
    # Create base map (use OpenStreetMap)
    m = folium.Map(
        location=[39.5, -121.5],  # Default to Northern California
        zoom_start=9,
        tiles='OpenStreetMap'
    )
    
    # Add satellite layer option
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add probability heatmap if GeoTIFF provided
    if geotiff_path and geotiff_path.exists():
        add_probability_overlay(m, geotiff_path)
    
    # Add fire info
    folium.Marker(
        location=[39.5, -121.5],
        popup=f"Fire: {nowcast_data['fire_id']}<br>Max Prob: {nowcast_data['metrics']['max_probability']:.2f}",
        icon=folium.Icon(color='red', icon='fire', prefix='fa')
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m


def add_probability_overlay(map_obj: folium.Map, geotiff_path: Path):
    """
    Add probability raster as overlay to map.
    
    Note: For POC, this is simplified. In production, would generate
    proper tiles or use ImageOverlay with proper bounds.
    
    Args:
        map_obj: Folium map object
        geotiff_path: Path to probability GeoTIFF
    """
    try:
        with rasterio.open(geotiff_path) as src:
            # Read probability data
            prob_data = src.read(1)
            
            # Get bounds in WGS84
            bounds = transform_bounds(src.crs, 'EPSG:4326', *src.bounds)
            
            # Create simple visualization
            # For POC: just mark high probability areas
            # In production: would create proper tile overlay
            
            # Find high probability cells
            high_prob_mask = prob_data > 0.5
            
            if high_prob_mask.any():
                # Add a simple polygon for high risk area (simplified)
                folium.Rectangle(
                    bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
                    color='orange',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.3,
                    popup=f'High risk area ({high_prob_mask.sum()} cells > 0.5)'
                ).add_to(map_obj)
    
    except Exception as e:
        st.warning(f"Could not add probability overlay: {e}")


def render_map(nowcast_data: Dict, prob_tif_bytes: bytes = None):
    """
    Render interactive map in Streamlit.
    
    Args:
        nowcast_data: Nowcast data from API
        prob_tif_bytes: Optional GeoTIFF bytes for probability overlay
    """
    # Save GeoTIFF to temp file if provided
    geotiff_path = None
    if prob_tif_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as f:
            f.write(prob_tif_bytes)
            geotiff_path = Path(f.name)
    
    # Create map
    fire_map = create_fire_map(nowcast_data, geotiff_path)
    
    # Render in Streamlit
    st_folium(fire_map, width=700, height=500)
    
    # Cleanup temp file
    if geotiff_path:
        try:
            geotiff_path.unlink()
        except:
            pass

