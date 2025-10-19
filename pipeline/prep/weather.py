"""Weather data processing and feature computation."""

from pathlib import Path

import numpy as np
import xarray as xr
import rasterio

from ..utils import setup_logger

logger = setup_logger(__name__)


def compute_rh(
    temp_path: Path,
    dewpoint_path: Path,
    output_path: Path
) -> Path:
    """
    Compute relative humidity from temperature and dewpoint using Magnus formula.
    
    RH = 100 * exp((b * T_d) / (c + T_d)) / exp((b * T) / (c + T))
    
    where:
    - T = temperature in Celsius
    - T_d = dewpoint in Celsius
    - b = 17.27
    - c = 237.7
    
    Args:
        temp_path: Path to temperature raster (Kelvin)
        dewpoint_path: Path to dewpoint raster (Kelvin)
        output_path: Path to save RH raster (%)
    
    Returns:
        Path to RH raster
    """
    logger.info("Computing relative humidity from T and Td")
    
    # Read temperature and dewpoint
    with rasterio.open(temp_path) as src_t:
        temp_k = src_t.read(1)
        profile = src_t.profile
    
    with rasterio.open(dewpoint_path) as src_d:
        dewpoint_k = src_d.read(1)
    
    # Convert Kelvin to Celsius
    temp_c = temp_k - 273.15
    dewpoint_c = dewpoint_k - 273.15
    
    # Magnus formula constants
    b = 17.27
    c = 237.7
    
    # Compute RH
    rh = 100 * np.exp((b * dewpoint_c) / (c + dewpoint_c)) / np.exp((b * temp_c) / (c + temp_c))
    rh = np.clip(rh, 0, 100).astype(np.float32)
    
    # Save RH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(rh, 1)
        dst.set_band_description(1, "Relative Humidity (%)")
    
    logger.info(f"RH saved to {output_path} (range: {rh.min():.1f}-{rh.max():.1f}%)")
    
    return output_path


def extract_weather_variables(
    netcdf_path: Path,
    output_dir: Path,
    variables: dict = None
) -> dict:
    """
    Extract weather variables from ERA5 NetCDF to individual GeoTIFFs.
    
    Args:
        netcdf_path: Path to ERA5 NetCDF file
        output_dir: Directory to save extracted variables
        variables: Dict mapping NetCDF variable names to output names
    
    Returns:
        Dict of {variable_name: output_path}
    """
    if variables is None:
        variables = {
            'u10': 'wind_u',
            'v10': 'wind_v',
            't2m': 'temp_2m',
            'd2m': 'dewpoint_2m'
        }
    
    logger.info(f"Extracting weather variables from {netcdf_path.name}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    extracted = {}
    
    # Open NetCDF
    ds = xr.open_dataset(netcdf_path)
    
    # Take mean over time dimension (simplification for POC)
    ds_mean = ds.mean(dim='time')
    
    for nc_var, out_name in variables.items():
        if nc_var not in ds_mean:
            logger.warning(f"Variable {nc_var} not found in NetCDF")
            continue
        
        data = ds_mean[nc_var].values
        
        # Get geospatial info
        lats = ds.latitude.values
        lons = ds.longitude.values
        
        # Create GeoTIFF
        from rasterio.transform import from_bounds
        
        transform = from_bounds(
            lons.min(), lats.min(), lons.max(), lats.max(),
            len(lons), len(lats)
        )
        
        output_path = output_dir / f"{out_name}.tif"
        
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs='EPSG:4326',
            transform=transform
        ) as dst:
            dst.write(data, 1)
        
        extracted[out_name] = output_path
        logger.info(f"Extracted {out_name} to {output_path}")
    
    ds.close()
    
    return extracted

