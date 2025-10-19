"""Clustering of hotspot detections into fire objects."""

import json
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from ..utils import setup_logger

logger = setup_logger(__name__)


def cluster_hotspots(
    detections_csv: Path,
    eps_km: float = 5.0,
    min_samples: int = 3,
    output_path: Path = None
) -> Tuple[pd.DataFrame, dict]:
    """
    Cluster hotspot detections into fire objects using DBSCAN.
    
    Args:
        detections_csv: Path to FIRMS CSV file
        eps_km: Maximum distance between points in cluster (km)
        min_samples: Minimum points to form a cluster
        output_path: Optional path to save clusters GeoJSON
    
    Returns:
        Tuple of (clustered DataFrame, fire metadata dict)
    """
    logger.info(f"Clustering hotspots: eps={eps_km}km, min_samples={min_samples}")
    
    # Load detections
    df = pd.read_csv(detections_csv)
    
    if df.empty:
        logger.warning("No hotspots to cluster")
        return df, {}
    
    # Extract coordinates
    coords = df[['latitude', 'longitude']].values
    
    # Convert km to degrees (approximate at mid-latitude)
    # 1 degree ≈ 111 km
    eps_deg = eps_km / 111.0
    
    # DBSCAN clustering
    clustering = DBSCAN(eps=eps_deg, min_samples=min_samples, metric='euclidean')
    labels = clustering.fit_predict(coords)
    
    df['cluster_id'] = labels
    
    # Get fire centroids and metadata
    fires = {}
    valid_clusters = df[df['cluster_id'] != -1]  # Exclude noise (-1)
    
    for cluster_id in valid_clusters['cluster_id'].unique():
        cluster_data = df[df['cluster_id'] == cluster_id]
        
        centroid_lat = cluster_data['latitude'].mean()
        centroid_lon = cluster_data['longitude'].mean()
        
        bbox = [
            cluster_data['longitude'].min(),
            cluster_data['latitude'].min(),
            cluster_data['longitude'].max(),
            cluster_data['latitude'].max()
        ]
        
        fires[f"fire_{int(cluster_id):03d}"] = {
            'cluster_id': int(cluster_id),
            'centroid': {'lat': centroid_lat, 'lon': centroid_lon},
            'bbox': bbox,
            'detection_count': len(cluster_data),
            'latest_detection': cluster_data['acq_date'].max()
        }
    
    logger.info(f"Identified {len(fires)} fire clusters")
    logger.info(f"Noise points (unclustered): {len(df[df['cluster_id'] == -1])}")
    
    # Save GeoJSON if requested
    if output_path:
        geojson = {
            'type': 'FeatureCollection',
            'features': []
        }
        
        for fire_id, fire_data in fires.items():
            feature = {
                'type': 'Feature',
                'properties': {
                    'fire_id': fire_id,
                    'detection_count': fire_data['detection_count'],
                    'latest_detection': fire_data['latest_detection']
                },
                'geometry': {
                    'type': 'Point',
                    'coordinates': [fire_data['centroid']['lon'], fire_data['centroid']['lat']]
                }
            }
            geojson['features'].append(feature)
        
        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        logger.info(f"Saved fire clusters to {output_path}")
    
    return df, fires

