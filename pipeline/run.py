"""Main pipeline orchestrator for EmberGuide POC."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import click
import numpy as np
import pandas as pd
import rasterio
from dotenv import load_dotenv

from pipeline.ingest import fetch_firms_hotspots, fetch_era5_weather, download_srtm_tiles
from pipeline.prep import cluster_hotspots, determine_utm_zone, align_to_grid, compute_slope_aspect, compute_rh
from pipeline.prep.weather import extract_weather_variables
from pipeline.spread import run_monte_carlo_ensemble, compute_spread_direction
from pipeline.utils import setup_logger, load_config, ensure_dir

from ml.denoiser.simple import filter_hotspots
from ml.calibration.isotonic import create_mock_calibrator, apply_calibration

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)


@click.command()
@click.option('--config', default='configs/active.yml', help='Path to configuration file')
@click.option('--fire-id', default=None, help='Fire ID override (otherwise from config)')
def main(config: str, fire_id: str):
    """Run the EmberGuide pipeline to generate fire nowcasts."""
    
    logger.info("="*60)
    logger.info("EmberGuide POC Pipeline Starting")
    logger.info("="*60)
    
    # Load configurations
    active_config = load_config(config)
    ingest_config = load_config('configs/ingest.yml')
    prep_config = load_config('configs/prep.yml')
    spread_config = load_config('configs/spread.yml')
    ml_config = load_config('configs/ml.yml')
    
    fire_config = active_config['fire']
    global_config = active_config['global']
    
    fire_id = fire_id or fire_config['id']
    
    logger.info(f"Processing fire: {fire_id}")
    logger.info(f"Region: {fire_config['region']}")
    logger.info(f"Bounding box: {fire_config['bbox']}")
    
    # Setup directories
    raw_dir = Path('data/raw')
    interim_dir = Path('data/interim')
    products_dir = Path('data/products') / fire_id
    
    ensure_dir(raw_dir)
    ensure_dir(interim_dir)
    ensure_dir(products_dir)
    
    # === STEP 1: INGEST DATA ===
    logger.info("\n" + "="*60)
    logger.info("STEP 1: Data Ingestion")
    logger.info("="*60)
    
    # Get API keys
    firms_key = os.getenv('FIRMS_API_KEY')
    cds_key = os.getenv('CDS_API_KEY')
    cds_url = os.getenv('CDS_API_URL', 'https://cds.climate.copernicus.eu/api/v2')
    
    # For POC: Always use mock data to ensure demo works
    logger.info("Using mock FIRMS data for POC demonstration")
    firms_csv = create_mock_firms_data(raw_dir / 'firms', fire_config['bbox'])
    
    # Uncomment below to use real API when key is available:
    # if not firms_key:
    #     logger.info("For POC, creating mock data")
    #     firms_csv = create_mock_firms_data(raw_dir / 'firms', fire_config['bbox'])
    # else:
    #     firms_csv = fetch_firms_hotspots(
    #         bbox=tuple(fire_config['bbox']),
    #         since=fire_config['since'],
    #         api_key=firms_key,
    #         output_dir=raw_dir / 'firms',
    #         source=ingest_config['firms'].get('source', 'VIIRS_NOAA20_NRT'),
    #         max_retries=ingest_config['firms'].get('max_retries', 3),
    #         retry_delay=ingest_config['firms'].get('retry_delay_seconds', 5)
    #     )
    
    # Fetch ERA5 weather (or create mock)
    if not cds_key or ':' not in cds_key:  # Check for valid key format
        logger.warning("CDS_API_KEY not found or invalid - creating mock ERA5 data")
        era5_nc = create_mock_era5_data(raw_dir / 'era5', fire_config['bbox'])
    else:
        era5_nc = fetch_era5_weather(
            bbox=tuple(fire_config['bbox']),
            date=fire_config['since'],
            variables=ingest_config['era5']['variables'],
            api_key=cds_key,
            api_url=cds_url,
            output_dir=raw_dir / 'era5',
            hours=ingest_config['era5'].get('hours', 30),
            max_retries=ingest_config['era5'].get('max_retries', 5),
            retry_delay=ingest_config['era5'].get('retry_delay_seconds', 10)
        )
    
    # Download SRTM DEM (synthetic for POC)
    srtm_tif = download_srtm_tiles(
        bbox=tuple(fire_config['bbox']),
        output_dir=raw_dir / 'srtm'
    )
    
    # === STEP 2: PREP DATA ===
    logger.info("\n" + "="*60)
    logger.info("STEP 2: Data Preparation")
    logger.info("="*60)
    
    # Cluster hotspots
    hotspots_df, fires_dict = cluster_hotspots(
        detections_csv=firms_csv,
        eps_km=prep_config['clustering']['eps_km'],
        min_samples=prep_config['clustering']['min_samples'],
        output_path=interim_dir / 'fire_clusters.geojson'
    )
    
    if len(fires_dict) == 0:
        logger.error("No fire clusters found!")
        return
    
    # Use first cluster for POC
    fire_info = list(fires_dict.values())[0]
    centroid = fire_info['centroid']
    
    logger.info(f"Fire centroid: {centroid['lat']:.4f}, {centroid['lon']:.4f}")
    
    # Apply ML denoiser if enabled
    if ml_config['denoiser']['enabled']:
        logger.info("Applying hotspot denoiser")
        hotspots_df = filter_hotspots(hotspots_df, ml_config['denoiser'])
    
    # Determine UTM zone for projection
    target_crs = determine_utm_zone(centroid['lon'], centroid['lat'])
    logger.info(f"Target CRS: {target_crs}")
    
    # Extract and align weather variables
    weather_vars = extract_weather_variables(
        era5_nc,
        interim_dir / 'weather',
        variables={
            'u10': 'wind_u',
            'v10': 'wind_v',
            't2m': 'temp_2m',
            'd2m': 'dewpoint_2m'
        }
    )
    
    # Align all grids to common projection
    logger.info("Aligning grids to common projection")
    
    # First align DEM to establish reference grid
    dem_aligned = interim_dir / 'aligned' / 'dem_aligned.tif'
    align_to_grid(
        srtm_tif, dem_aligned, target_crs,
        resolution_m=global_config['resolution_m'],
        bbox=tuple(fire_config['bbox'])
    )
    
    # Get reference grid shape from DEM
    with rasterio.open(dem_aligned) as ref:
        ref_transform = ref.transform
        ref_width = ref.width
        ref_height = ref.height
        ref_bounds = ref.bounds
    
    # Align all weather variables to match DEM grid exactly
    aligned_weather = {}
    for name, path in weather_vars.items():
        aligned_path = interim_dir / 'aligned' / f"{name}_aligned.tif"
        # Use reference grid dimensions
        with rasterio.open(path) as src:
            from rasterio.warp import reproject, Resampling
            
            # Create output matching reference grid
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': target_crs,
                'transform': ref_transform,
                'width': ref_width,
                'height': ref_height
            })
            
            with rasterio.open(aligned_path, 'w', **kwargs) as dst:
                reproject(
                    source=rasterio.band(src, 1),
                    destination=rasterio.band(dst, 1),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=ref_transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear
                )
        
        aligned_weather[name] = aligned_path
        logger.info(f"Aligned {name} to reference grid ({ref_height}x{ref_width})")
    
    # Compute terrain features (slope computed on aligned DEM, so already same grid)
    slope_path, aspect_path = compute_slope_aspect(
        dem_aligned,
        interim_dir / 'terrain'
    )
    
    # Slope is already on the reference grid (computed from aligned DEM)
    # Just copy/link it
    slope_aligned = slope_path  # Already aligned
    
    # Compute relative humidity from already-aligned temp and dewpoint
    rh_path = interim_dir / 'weather' / 'rh.tif'
    compute_rh(
        aligned_weather['temp_2m'],
        aligned_weather['dewpoint_2m'],
        rh_path
    )
    
    # RH computed from aligned grids, so already on reference grid
    rh_aligned = rh_path  # Already aligned
    
    # === STEP 3: RUN SPREAD MODEL ===
    logger.info("\n" + "="*60)
    logger.info("STEP 3: Fire Spread Modeling")
    logger.info("="*60)
    
    # Load aligned grids
    with rasterio.open(aligned_weather['wind_u']) as src:
        wind_u = src.read(1)
        transform = src.transform
        profile = src.profile
    
    with rasterio.open(aligned_weather['wind_v']) as src:
        wind_v = src.read(1)
    
    with rasterio.open(aligned_weather['temp_2m']) as src:
        temp = src.read(1)
    
    with rasterio.open(slope_aligned) as src:
        slope = src.read(1)
    
    with rasterio.open(rh_aligned) as src:
        rh = src.read(1)
    
    # Filter hotspots to current cluster
    cluster_hotspots_df = hotspots_df[hotspots_df['cluster_id'] == fire_info['cluster_id']]
    
    # Run Monte Carlo ensemble
    probability, mean_intensity, uncertainty = run_monte_carlo_ensemble(
        cluster_hotspots_df,
        wind_u, wind_v, temp, slope, rh,
        transform,
        spread_config['model'],
        spread_config['monte_carlo'],
        n_ensemble=global_config['n_ensemble'],
        base_seed=global_config['seed'],
        n_timesteps=fire_config['horizon']
    )
    
    # Compute spread direction
    direction = compute_spread_direction(probability, wind_u, wind_v)
    
    # === STEP 4: APPLY CALIBRATION ===
    logger.info("\n" + "="*60)
    logger.info("STEP 4: Probability Calibration")
    logger.info("="*60)
    
    if ml_config['calibration']['enabled']:
        calibrator_path = Path(ml_config['calibration']['model_path'])
        
        # Create mock calibrator if it doesn't exist
        if not calibrator_path.exists() and ml_config['calibration'].get('create_mock_model', True):
            logger.info("Creating mock calibrator")
            create_mock_calibrator(calibrator_path)
        
        if calibrator_path.exists():
            probability = apply_calibration(probability, calibrator_path)
    
    # === STEP 5: SAVE PRODUCTS ===
    logger.info("\n" + "="*60)
    logger.info("STEP 5: Saving Products")
    logger.info("="*60)
    
    horizon_str = f"{fire_config['horizon']}h"
    
    # Save probability
    prob_path = products_dir / f"nowcast_{horizon_str}.tif"
    with rasterio.open(prob_path, 'w', **profile) as dst:
        dst.write(probability, 1)
        dst.set_band_description(1, f"Fire probability {horizon_str}")
    logger.info(f"Saved probability map: {prob_path}")
    
    # Save direction
    dir_path = products_dir / f"direction_{horizon_str}.tif"
    with rasterio.open(dir_path, 'w', **profile) as dst:
        dst.write(direction, 1)
        dst.set_band_description(1, f"Spread direction {horizon_str}")
    logger.info(f"Saved direction map: {dir_path}")
    
    # Save uncertainty
    unc_path = products_dir / f"uncertainty_{horizon_str}.tif"
    with rasterio.open(unc_path, 'w', **profile) as dst:
        dst.write(uncertainty, 1)
        dst.set_band_description(1, f"Uncertainty {horizon_str}")
    logger.info(f"Saved uncertainty map: {unc_path}")
    
    # Save metadata
    metadata = {
        'fire_id': fire_id,
        'region': fire_config['region'],
        'centroid': centroid,
        'bbox': fire_config['bbox'],
        'horizon_hours': fire_config['horizon'],
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'grid_meta': {
            'crs': target_crs,
            'resolution_m': global_config['resolution_m'],
            'shape': list(probability.shape)
        },
        'detections': {
            'count': len(cluster_hotspots_df),
            'latest_time': cluster_hotspots_df['acq_date'].max() if len(cluster_hotspots_df) > 0 else None
        },
        'metrics': {
            'max_probability': float(probability.max()),
            'mean_probability': float(probability.mean()),
            'affected_area_km2': float(np.sum(probability > 0.5) * (global_config['resolution_m'] / 1000) ** 2)
        },
        'config': {
            'n_ensemble': global_config['n_ensemble'],
            'seed': global_config['seed'],
            'denoiser_enabled': ml_config['denoiser']['enabled'],
            'calibration_enabled': ml_config['calibration']['enabled']
        }
    }
    
    metadata_path = products_dir / 'metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved metadata: {metadata_path}")
    
    # Update index
    update_products_index(fire_id, metadata)
    
    logger.info("\n" + "="*60)
    logger.info("Pipeline Complete!")
    logger.info("="*60)
    logger.info(f"Products saved to: {products_dir}")
    logger.info(f"Max probability: {probability.max():.3f}")
    logger.info(f"Affected area: {metadata['metrics']['affected_area_km2']:.1f} km²")


def update_products_index(fire_id: str, metadata: dict):
    """Update the products index.json file."""
    index_path = Path('data/products/index.json')
    
    if index_path.exists():
        with open(index_path, 'r') as f:
            index = json.load(f)
    else:
        index = {'fires': [], 'generated_at': None}
    
    # Update or add fire entry
    fire_entry = {
        'id': fire_id,
        'region': metadata['region'],
        'centroid': metadata['centroid'],
        'bbox': metadata['bbox'],
        'status': 'active',
        'nowcast_available': [metadata['horizon_hours']],
        'last_updated': metadata['generated_at']
    }
    
    # Remove old entry if exists
    index['fires'] = [f for f in index['fires'] if f['id'] != fire_id]
    index['fires'].append(fire_entry)
    index['generated_at'] = datetime.utcnow().isoformat() + 'Z'
    
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)
    
    logger.info(f"Updated products index: {index_path}")


def create_mock_firms_data(output_dir: Path, bbox: list) -> Path:
    """Create mock FIRMS data for testing when API key unavailable."""
    logger.info("Creating mock FIRMS data for POC")
    
    ensure_dir(output_dir)
    
    # Generate synthetic hotspots in tight clusters
    west, south, east, north = bbox
    
    # Create 2-3 fire clusters with multiple hotspots each
    lats = []
    lons = []
    
    # Cluster 1: Near center-west
    center1_lat = south + (north - south) * 0.4
    center1_lon = west + (east - west) * 0.3
    for i in range(8):
        lats.append(center1_lat + np.random.normal(0, 0.02))  # ~2km spread
        lons.append(center1_lon + np.random.normal(0, 0.02))
    
    # Cluster 2: Near center-east
    center2_lat = south + (north - south) * 0.6
    center2_lon = west + (east - west) * 0.7
    for i in range(7):
        lats.append(center2_lat + np.random.normal(0, 0.02))
        lons.append(center2_lon + np.random.normal(0, 0.02))
    
    # Cluster 3: Near north-center
    center3_lat = south + (north - south) * 0.8
    center3_lon = west + (east - west) * 0.5
    for i in range(6):
        lats.append(center3_lat + np.random.normal(0, 0.015))
        lons.append(center3_lon + np.random.normal(0, 0.015))
    
    n_hotspots = len(lats)
    
    data = {
        'latitude': lats,
        'longitude': lons,
        'brightness': [320 + i * 2 for i in range(n_hotspots)],
        'confidence': [85] * n_hotspots,
        'acq_date': ['2024-10-15'] * n_hotspots,
        'acq_time': ['1200'] * n_hotspots,
        'satellite': ['NOAA-20'] * n_hotspots
    }
    
    df = pd.DataFrame(data)
    output_path = output_dir / 'mock_firms_hotspots.csv'
    df.to_csv(output_path, index=False)
    
    logger.info(f"Created mock FIRMS data with {n_hotspots} hotspots in 3 clusters: {output_path}")
    return output_path


def create_mock_era5_data(output_dir: Path, bbox: list) -> Path:
    """Create mock ERA5 data for testing."""
    import xarray as xr
    import numpy as np
    
    logger.info("Creating mock ERA5 data for POC")
    
    ensure_dir(output_dir)
    
    west, south, east, north = bbox
    
    # Create grid
    lats = np.linspace(south, north, 20)
    lons = np.linspace(west, east, 20)
    time = pd.date_range('2024-10-15', periods=24, freq='1H')
    
    # Create synthetic data
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing='ij')
    
    ds = xr.Dataset({
        'u10': (['time', 'latitude', 'longitude'], 
                np.random.uniform(2, 8, (len(time), len(lats), len(lons)))),
        'v10': (['time', 'latitude', 'longitude'],
                np.random.uniform(1, 5, (len(time), len(lats), len(lons)))),
        't2m': (['time', 'latitude', 'longitude'],
                np.random.uniform(290, 305, (len(time), len(lats), len(lons)))),
        'd2m': (['time', 'latitude', 'longitude'],
                np.random.uniform(280, 295, (len(time), len(lats), len(lons))))
    }, coords={
        'time': time,
        'latitude': lats,
        'longitude': lons
    })
    
    output_path = output_dir / 'mock_era5_weather.nc'
    ds.to_netcdf(output_path)
    
    logger.info(f"Created mock ERA5 data: {output_path}")
    return output_path


if __name__ == '__main__':
    main()

