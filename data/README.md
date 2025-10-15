# EmberGuide Data

Documentation for data layout, sources, licenses, and conventions.

---

## Overview

EmberGuide uses three primary data sources:
1. **FIRMS** (NASA): Satellite hotspot detections (MODIS/VIIRS)
2. **ERA5** (Copernicus/ECMWF): Weather reanalysis
3. **SRTM** (NASA/USGS): Digital elevation model

All data is organized in a structured directory layout for reproducibility and attribution.

---

## Directory Structure

```
data/
├── raw/                      # Original downloaded data (timestamped)
│   ├── firms/
│   │   ├── 2024-01-15T12:00:00Z_CONUS.csv
│   │   ├── 2024-01-15T18:00:00Z_CONUS.csv
│   │   └── .checksums        # SHA256 hashes
│   ├── era5/
│   │   ├── 2024-01-15T00:00:00Z.grib
│   │   ├── 2024-01-15T06:00:00Z.grib
│   │   └── .checksums
│   └── srtm/
│       ├── n39w122.tif       # 1° tiles
│       ├── n40w122.tif
│       └── .checksums
├── interim/                  # Preprocessed/aligned data
│   ├── weather_grids/
│   │   ├── fire_001_u10.tif
│   │   ├── fire_001_v10.tif
│   │   ├── fire_001_temp.tif
│   │   └── fire_001_rh.tif
│   ├── terrain_grids/
│   │   ├── fire_001_slope.tif
│   │   └── fire_001_aspect.tif
│   └── fire_clusters/
│       ├── clusters.geojson
│       └── fire_001_seeds.geojson
└── products/                 # Final outputs (served by API)
    ├── index.json           # Catalog of all fires
    ├── fire_001/
    │   ├── metadata.json
    │   ├── nowcast_12h.tif
    │   ├── nowcast_24h.tif
    │   ├── nowcast_48h.tif
    │   ├── direction_12h.tif
    │   ├── direction_24h.tif
    │   ├── direction_48h.tif
    │   ├── uncertainty_12h.tif
    │   ├── uncertainty_24h.tif
    │   ├── uncertainty_48h.tif
    │   ├── tiles/
    │   │   ├── 12h/{z}/{x}/{y}.png
    │   │   ├── 24h/{z}/{x}/{y}.png
    │   │   └── 48h/{z}/{x}/{y}.png
    │   └── report_24h.json
    └── fire_002/
        └── ...
```

**Note**: `data/raw/` and `data/interim/` are gitignored (too large). Only `data/.gitkeep` and structure documentation are versioned.

---

## Data Sources

### 1. FIRMS (Fire Information for Resource Management System)

**Provider**: NASA LANCE  
**Satellites**: MODIS (Terra/Aqua), VIIRS (Suomi-NPP/NOAA-20)  
**Resolution**: ~375 m (VIIRS), ~1 km (MODIS)  
**Latency**: Near real-time (~3 hours)  
**Format**: CSV or JSON

**Access**:
- API: https://firms.modaps.eosdis.nasa.gov/api/
- Requires free registration: https://firms.modaps.eosdis.nasa.gov/api/

**Attribution**:
> FIRMS data from NASA's Fire Information for Resource Management System (MODIS/VIIRS).  
> Citation: NASA. (2024). MODIS/VIIRS Active Fire Detections. https://firms.modaps.eosdis.nasa.gov/

**License**: Public domain (US government data)

**Fields**:
- `latitude`, `longitude`: Detection location
- `acq_date`, `acq_time`: Detection timestamp
- `confidence`: 0–100 (VIIRS) or low/nominal/high (MODIS)
- `bright_ti4`, `bright_ti5`: Brightness temperature (K)
- `scan`, `track`: Pixel size (m)
- `satellite`: `Aqua`, `Terra`, `Suomi NPP`, `NOAA-20`

**Download**:
```bash
python -m src.ingest.firms \
  --region CONUS \
  --date 2024-01-15 \
  --output data/raw/firms/
```

---

### 2. ERA5 (ECMWF Reanalysis v5)

**Provider**: Copernicus Climate Data Store (CDS) / ECMWF  
**Resolution**: ~25 km (0.25°), hourly  
**Latency**: ~5 days for final data, ~3 hours for preliminary  
**Format**: GRIB or NetCDF

**Access**:
- CDS API: https://cds.climate.copernicus.eu/api/v2
- Requires free registration: https://cds.climate.copernicus.eu/user/register

**Attribution**:
> ERA5 hourly data from Copernicus Climate Change Service (C3S) Climate Data Store (CDS).  
> Hersbach, H. et al. (2020). The ERA5 global reanalysis. Q.J.R. Meteorol. Soc., 146: 1999-2049. https://doi.org/10.1002/qj.3803

**License**: Copernicus License (free for research/commercial with attribution)  
See: https://cds.climate.copernicus.eu/api/v2#!/terms/

**Variables**:
- `u10`, `v10`: 10-m wind components (m/s)
- `t2m`: 2-m temperature (K)
- `d2m`: 2-m dew point temperature (K)
- `blh`: Boundary layer height (m) *(optional)*

**Download**:
```bash
python -m src.ingest.era5 \
  --bbox -125,32,-114,42 \
  --date 2024-01-15 \
  --variables u10,v10,t2m,d2m \
  --output data/raw/era5/
```

**Derived variables**:
- **Relative Humidity (RH)**: Computed from `t2m` and `d2m` using Magnus formula

---

### 3. SRTM (Shuttle Radar Topography Mission)

**Provider**: NASA / USGS  
**Resolution**: ~90 m (3 arc-second) or ~30 m (1 arc-second, US only)  
**Coverage**: 60°N to 56°S (nearly global)  
**Format**: GeoTIFF

**Access**:
- OpenTopography: https://portal.opentopography.org/
- USGS EarthExplorer: https://earthexplorer.usgs.gov/

**Attribution**:
> SRTM elevation data courtesy of NASA/USGS.  
> Citation: NASA JPL (2013). NASA Shuttle Radar Topography Mission Global 3 arc second. NASA EOSDIS Land Processes DAAC.

**License**: Public domain (US government data)

**Derived products**:
- **Slope** (degrees): Rate of elevation change
- **Aspect** (degrees): Compass direction of slope

**Download**:
```bash
python -m src.ingest.srtm \
  --bbox -125,32,-114,42 \
  --resolution 90m \
  --output data/raw/srtm/
```

---

## Optional Data Sources

### Burned Area (for Evaluation)

**Source**: MODIS MCD64A1 (500 m monthly burned area)  
**Use**: Training labels for denoiser and calibrator; evaluation ground truth  
**Access**: https://lpdaac.usgs.gov/products/mcd64a1v006/

### Land Cover (for Denoiser)

**Source**: MODIS MCD12Q1 (500 m annual land cover)  
**Use**: Feature for hotspot denoising (e.g., "is this industrial area?")  
**Access**: https://lpdaac.usgs.gov/products/mcd12q1v006/

### Weather Stations (for Downscaler)

**Source**: RAWS (Remote Automated Weather Stations), ASOS  
**Use**: Ground truth for micro-downscaling ERA5 wind/RH  
**Access**: https://raws.dri.edu/

---

## File Naming Conventions

### Timestamps

All filenames use **ISO 8601 format**:
- `YYYY-MM-DDTHH:MM:SSZ` (UTC)
- Example: `2024-01-15T12:00:00Z_CONUS.csv`

### Regions

- ISO 3166-1 alpha-2 codes: `US`, `CA`, `AU`
- Subnational: `CA_north`, `CO_front_range`
- Bounding box hash (for custom AOIs): `bbox_abc123`

### Checksums

Each directory has a `.checksums` file:
```
sha256:a3f2... 2024-01-15T12:00:00Z_CONUS.csv
sha256:7d91... 2024-01-15T18:00:00Z_CONUS.csv
```

Generate:
```bash
sha256sum *.csv > .checksums
```

Verify:
```bash
sha256sum -c .checksums
```

---

## Data Versioning

Each `products/fire_*/metadata.json` records:
```json
{
  "fire_id": "fire_001",
  "generated_at": "2024-01-15T14:30:00Z",
  "code_version": "abc123def",
  "config_checksum": "sha256:...",
  "inputs": {
    "firms": {
      "file": "2024-01-15T12:00:00Z_CONUS.csv",
      "checksum": "sha256:...",
      "timestamp": "2024-01-15T12:00:00Z"
    },
    "era5": {
      "file": "2024-01-15T09:00:00Z.grib",
      "checksum": "sha256:...",
      "timestamp": "2024-01-15T09:00:00Z"
    },
    "srtm": {
      "tiles": ["n39w122.tif", "n40w122.tif"],
      "checksum": "sha256:..."
    }
  },
  "seed": 42
}
```

---

## Coordinate Reference Systems (CRS)

### Raw Data

- **FIRMS**: WGS84 (EPSG:4326) lat/lon
- **ERA5**: WGS84 (EPSG:4326) lat/lon grid
- **SRTM**: WGS84 (EPSG:4326)

### Interim/Products

Reprojected to **UTM** (appropriate zone for fire location):
- Example: UTM Zone 10N (EPSG:32610) for California
- Resolution: 1000 m (configurable in `configs/prep.yml`)

**Why UTM?**
- Equal-area projection (important for spread calculations)
- Meters (easier than degrees for distance/speed)
- Less distortion than Web Mercator in mid-latitudes

---

## Data Refresh Strategy

### Development/Evaluation

Use **fixed snapshots** (no network):
```bash
make eval  # Uses eval/snapshot/ only
```

### Production

**Scheduled refresh** (e.g., cron every 3 hours):
```bash
# Cron: 0 */3 * * * /path/to/venv/bin/make refresh
make refresh  # Fetch latest FIRMS/ERA5, run pipeline
```

**Incremental updates**:
- FIRMS: Fetch last 24 hours (avoids re-downloading entire archive)
- ERA5: Fetch only new hours since last run
- SRTM: Cache indefinitely (static)

---

## Storage Requirements

### Estimates (per fire)

- **Raw FIRMS**: ~1 KB per hotspot × 100–1000 hotspots = 100 KB – 1 MB
- **Raw ERA5**: ~10 MB per hour × 48 hours = 480 MB (for 500×500 km region)
- **Raw SRTM**: ~25 MB per 1° tile × 4 tiles = 100 MB (cached)
- **Interim grids**: ~50 MB (aligned/resampled)
- **Products (GeoTIFFs)**: ~20 MB per horizon × 3 = 60 MB
- **Tiles**: ~500 KB per zoom level × 5 levels = 2.5 MB

**Total per fire**: ~650 MB  
**For 10 active fires**: ~6.5 GB

**Optimization**:
- Compress GeoTIFFs (LZW or DEFLATE)
- Use Cloud-Optimized GeoTIFF (COG) for streaming
- Purge raw data older than 30 days

---

## Data Retention Policy

### Development

Keep everything for reproducibility.

### Production

- **Raw data**: Keep 30 days, then archive or delete
- **Interim data**: Keep 7 days (can regenerate from raw)
- **Products**: Keep indefinitely (small, valuable)
- **Tiles**: Keep indefinitely or regenerate on demand

---

## Data Privacy & Security

- **No PII**: All data is environmental (no personal information)
- **Public sources**: FIRMS/ERA5/SRTM are public datasets
- **API keys**: Store in `.env` (gitignored); never hardcode
- **Checksums**: Verify integrity to detect corruption or tampering

---

## Troubleshooting

### "FIRMS API returns 401 Unauthorized"

**Solution**:
- Check `FIRMS_API_KEY` in `.env`
- Verify key is valid: https://firms.modaps.eosdis.nasa.gov/api/

### "ERA5 download times out"

**Solution**:
- CDS can be slow during peak hours; retry later
- Reduce spatial extent or time range
- Use preliminary data (`reanalysis-era5-single-levels-preliminary-back-extension`)

### "SRTM tiles missing for region"

**Solution**:
- Check coverage: SRTM only covers 60°N to 56°S
- For higher latitudes, use ASTER GDEM or ALOS World 3D

### "Checksums don't match"

**Solution**:
- File may be corrupted; re-download
- Check for line-ending differences (CRLF vs LF) in CSV files
- Regenerate checksums if intentional update

---

## Best Practices

### 1. Always Timestamp

Every file should have a creation/modification timestamp:
- In filename (ISO 8601)
- In metadata JSON

### 2. Verify Integrity

Check SHA256 before processing:
```python
import hashlib

def verify_checksum(filepath, expected_hash):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    assert sha256.hexdigest() == expected_hash, "Checksum mismatch!"
```

### 3. Document Provenance

In `metadata.json`, record:
- Source (FIRMS/ERA5/SRTM)
- Download timestamp
- File checksums
- Code version that processed it

### 4. Separate Raw and Processed

Never overwrite raw data. Always write to `interim/` or `products/`.

---

## Next Steps

- **Pipeline**: See [pipeline/README.md](../pipeline/README.md) for data processing
- **API**: See [api/README.md](../api/README.md) for serving products
- **Attribution**: See [docs/DATA_SOURCES.md](../docs/DATA_SOURCES.md) for full citations

---

## References

- **FIRMS**: https://firms.modaps.eosdis.nasa.gov/
- **ERA5**: https://cds.climate.copernicus.eu/
- **SRTM**: https://www2.jpl.nasa.gov/srtm/
- **Copernicus License**: https://cds.climate.copernicus.eu/api/v2#!/terms/
- [WILDFIRE_101.md](../WILDFIRE_101.md) — Domain background

