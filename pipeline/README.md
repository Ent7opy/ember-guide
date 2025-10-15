# EmberGuide Pipeline

The pipeline orchestrates the end-to-end flow from raw satellite/weather/terrain data to final nowcast products (GeoTIFFs, tiles, reports).

---

## Overview

The pipeline is a batch processing system that:
1. **Ingests** raw data from external sources (FIRMS, ERA5, SRTM)
2. **Prepares** data by aligning grids, clustering hotspots, defining AOI
3. **Models** fire spread using baseline physics + Monte Carlo uncertainty
4. **Calibrates** probabilities using optional ML post-processing
5. **Produces** GeoTIFFs, map tiles, and JSON reports

**Key principle**: Deterministic and reproducible. Same inputs + config + seed → identical outputs.

---

## Data Layout

```
data/
├── raw/                      # Timestamped inputs (gitignored except .gitkeep)
│   ├── firms/
│   │   └── YYYY-MM-DD_HHmm_region.csv
│   ├── era5/
│   │   └── YYYY-MM-DD_HHmm.grib
│   └── srtm/
│       └── region_dem.tif
├── interim/                  # Aligned/preprocessed grids
│   ├── fire_clusters/
│   ├── weather_grids/
│   └── terrain_grids/
└── products/                 # Final outputs served by API
    ├── index.json           # Catalog of all fires/nowcasts
    ├── fire_001/
    │   ├── metadata.json
    │   ├── nowcast_12h.tif  # Probability raster
    │   ├── direction_12h.tif
    │   ├── nowcast_24h.tif
    │   ├── nowcast_48h.tif
    │   ├── tiles/           # XYZ tiles for web maps
    │   │   └── 12h/{z}/{x}/{y}.png
    │   └── report_12h.json
    └── fire_002/
        └── ...
```

### File Naming Conventions

- **Timestamps**: ISO 8601 format (`YYYY-MM-DDTHH:mm:ssZ`)
- **Region codes**: ISO 3166-1 alpha-2 or bounding box hash
- **Checksums**: SHA256 stored in `.checksums` files alongside data

---

## Pipeline Steps

### 1. Ingest

**Purpose**: Fetch latest data from external sources and cache with timestamps.

**Sources**:
- **FIRMS** (NASA): MODIS/VIIRS active fire hotspots (CSV or JSON)
- **ERA5** (Copernicus): Hourly reanalysis weather (GRIB or NetCDF)
  - Variables: 10m u/v wind, 2m temperature, 2m dewpoint, boundary layer height
- **SRTM** (NASA/USGS): Digital elevation model (GeoTIFF)

**Implementation**:
```bash
python -m src.ingest.firms --region CONUS --since 2024-01-01
python -m src.ingest.era5 --bbox -125,32,-114,42 --date 2024-01-01
python -m src.ingest.srtm --bbox -125,32,-114,42
```

**Outputs**: `data/raw/` with timestamped files and checksums.

**Configuration**: See `configs/ingest.yml` for API credentials (via env vars) and retry logic.

---

### 2. Prep (Preparation)

**Purpose**: Align all data to a common grid, cluster hotspots, define area of interest.

**Sub-steps**:
1. **Reproject/resample**: Align DEM, weather to common CRS and resolution (e.g., 1 km UTM)
2. **Compute terrain derivatives**: Slope, aspect from DEM
3. **Cluster hotspots**: DBSCAN or HDBSCAN to group nearby detections into "fire objects"
4. **Define AOI**: Buffer around each fire cluster (e.g., 50 km) for nowcast domain

**Implementation**:
```bash
python -m src.prep.align --input data/raw --output data/interim
python -m src.prep.cluster_fires --detections data/raw/firms/latest.csv --output data/interim/fire_clusters
```

**Outputs**:
- `data/interim/weather_grids/`: Aligned u, v, temp, dewpoint, RH
- `data/interim/terrain_grids/`: Slope, aspect
- `data/interim/fire_clusters/clusters.geojson`: Fire objects with IDs and bboxes

**Configuration**: `configs/prep.yml` (CRS, resolution, clustering params)

---

### 3. Model (Baseline Spread)

**Purpose**: Compute fire spread using physics-based rules + Monte Carlo uncertainty.

**Algorithm** (simplified):
1. Initialize grid with hotspot seeds
2. For each timestep (hourly over 12/24/48 h):
   - Compute spread potential for each cell:
     - Wind push: `wind_speed * cos(wind_dir - spread_dir)`
     - Slope factor: `max(0, slope_deg / 45)` for upslope cells
     - Dryness: `(100 - RH) / 100`
   - Combine factors: `risk = f(wind, slope, dryness, fuel_continuity)`
   - Update grid: cells above threshold spread to neighbors
3. Repeat with perturbed weather (Monte Carlo) → ensemble of 50–100 runs
4. Aggregate: probability = fraction of runs where cell burned

**Implementation**:
```bash
python -m src.spread.run \
  --fire-id fire_001 \
  --horizon 24 \
  --n-ensemble 100 \
  --seed 42 \
  --output data/products/fire_001
```

**Outputs**:
- `data/products/fire_001/nowcast_24h.tif`: Probability (0–1) raster
- `data/products/fire_001/direction_24h.tif`: Mean spread direction (0–360°)
- `data/products/fire_001/uncertainty_24h.tif`: Ensemble std dev

**Configuration**: `configs/spread.yml` (thresholds, MC perturbation ranges, timestep)

---

### 4. Calibration (Optional ML)

**Purpose**: Map raw spread scores to well-calibrated probabilities using historical data.

**Method**:
- Isotonic regression or logistic calibration
- Features: baseline score, wind speed, RH, slope variability, time since detection
- Trained on historical fires with observed outcomes (burned/not burned)

**Implementation**:
```bash
python -m src.calibration.apply \
  --input data/products/fire_001/nowcast_24h.tif \
  --model ml/models/calibrator_v1.pkl \
  --output data/products/fire_001/nowcast_24h_calibrated.tif
```

**Toggle**: Set `use_calibration: true` in `configs/ml.yml`.

**Outputs**: Overwrites or creates `*_calibrated.tif` versions.

---

### 5. Tiles (Web Map Generation)

**Purpose**: Convert GeoTIFFs to PNG tiles for web maps (XYZ scheme).

**Implementation**:
```bash
python -m src.tiles.generate \
  --input data/products/fire_001/nowcast_24h.tif \
  --output data/products/fire_001/tiles/24h \
  --zoom 7-12 \
  --colormap hot
```

**Outputs**:
- `data/products/fire_001/tiles/24h/{z}/{x}/{y}.png`
- Tile manifest with bounds and zoom range

**Configuration**: `configs/tiles.yml` (zoom range, colormap, tile size)

---

## Command Contracts (Make/CLI)

### Make Targets

```bash
# Full refresh: ingest latest data, run all steps
make refresh

# Offline evaluation: run on fixed historical snapshot
make eval

# Individual steps
make ingest
make prep
make model
make tiles

# Serve outputs
make serve-api    # Start FastAPI on :8000
make serve-ui     # Start Streamlit on :8501

# Quality checks
make lint         # ruff + black
make typecheck    # mypy
make test         # pytest
```

### CLI (Fine-Grained Control)

```bash
# Run specific fire and horizon
python -m pipeline.run \
  --fire-id fire_001 \
  --horizon 24 \
  --config configs/active.yml \
  --seed 42

# Re-tile without recomputing spread
python -m src.tiles.generate --fire-id fire_001 --horizons 12,24,48
```

---

## Determinism & Reproducibility

### Random Seeds

All stochastic operations (Monte Carlo, ML training) must use fixed seeds:
```python
import numpy as np
import random

def run_monte_carlo(seed: int = 42):
    np.random.seed(seed)
    random.seed(seed)
    # ... ensemble sampling
```

### Versioning

Each product records:
- Code version (git commit hash)
- Config file checksum
- Input data timestamps and checksums
- Random seed

Stored in `metadata.json`:
```json
{
  "fire_id": "fire_001",
  "horizon": 24,
  "generated_at": "2024-01-15T14:30:00Z",
  "code_version": "abc123def",
  "config_checksum": "sha256:...",
  "seed": 42,
  "inputs": {
    "firms": "2024-01-15T12:00:00Z (sha256:...)",
    "era5": "2024-01-15T12:00:00Z (sha256:...)"
  }
}
```

### Golden Fixtures

For testing, we maintain fixed snapshots:
- `eval/snapshot/fire_A/` and `eval/snapshot/fire_B/`
- Small representative cases (e.g., 2020 California fire, 2023 Canada fire)
- Expected outputs in `eval/snapshot/expected/`

Run `make eval` to verify reproducibility without network access.

---

## Configuration

### File Structure

```
configs/
├── active.yml          # Current fires to process
├── ingest.yml          # API endpoints, credentials (via env vars)
├── prep.yml            # CRS, resolution, clustering
├── spread.yml          # Spread model parameters
├── ml.yml              # ML module toggles and paths
└── tiles.yml           # Tile generation settings
```

### Example: `configs/active.yml`

```yaml
fires:
  - id: fire_001
    region: CA_north
    bbox: [-122.5, 38.5, -121.0, 40.0]
    since: "2024-01-01T00:00:00Z"
    horizons: [12, 24, 48]
  
  - id: fire_002
    region: CO_front_range
    bbox: [-105.5, 39.0, -104.5, 40.5]
    since: "2024-01-10T00:00:00Z"
    horizons: [24]

global:
  resolution_m: 1000
  seed: 42
  n_ensemble: 100
```

### Environment Variables

Credentials should **never** be hardcoded. Use `.env`:
```bash
FIRMS_API_KEY=your_key_here
CDS_API_KEY=your_key_here
CDS_API_URL=https://cds.climate.copernicus.eu/api/v2
```

Load with `python-dotenv` or shell export.

---

## Monitoring & Logging

### Logging Format

Use structured logging (JSON) for production:
```python
import logging
import json

logger = logging.getLogger(__name__)
logger.info(json.dumps({
    "event": "spread_model_start",
    "fire_id": "fire_001",
    "horizon": 24,
    "timestamp": "2024-01-15T14:30:00Z"
}))
```

### Metrics to Track

- **Ingest**: Data freshness, API response times, download sizes
- **Prep**: Number of hotspots, cluster count, AOI size
- **Model**: Ensemble run time, mean probability, max spread distance
- **Tiles**: Tile generation time, tile count, storage size

Optionally export to Prometheus/Grafana (see `docs/DEPLOYMENT.md`).

---

## Error Handling

### Common Errors

1. **Missing data**: FIRMS API timeout → retry with exponential backoff
2. **CRS mismatch**: Reprojection failure → check bbox validity
3. **Empty clusters**: No hotspots detected → skip fire or expand time range
4. **Memory issues**: Large rasters → use windowed reads (see `src/utils/raster.py`)

### Failure Modes

- If a single fire fails, log error and continue processing other fires
- Write partial outputs with status flag: `"status": "failed", "error": "..."`
- API should return `4xx` for failed fires, not crash

---

## Performance Tips

### Parallel Processing

Use `multiprocessing` for independent fires or ensemble runs:
```python
from multiprocessing import Pool

def process_fire(fire_id):
    # ... run pipeline for one fire
    pass

with Pool(processes=4) as pool:
    pool.map(process_fire, fire_ids)
```

### Raster I/O

Avoid loading entire rasters into memory. Use GDAL windowed reads:
```python
import rasterio

with rasterio.open("large.tif") as src:
    for window in src.block_windows(1):
        data = src.read(1, window=window)
        # ... process chunk
```

### Caching

- Cache DEM tiles (they don't change)
- Cache weather data for overlapping fire AOIs
- Use HTTP caching headers for API responses

---

## Testing

### Unit Tests

Test individual components in isolation:
```bash
pytest tests/unit/test_spread.py
pytest tests/unit/test_clustering.py
```

### Integration Tests

Test full pipeline on small synthetic data:
```bash
pytest tests/integration/test_pipeline_end_to_end.py
```

### Evaluation (Golden Fixtures)

```bash
make eval  # Runs on eval/snapshot, compares to eval/snapshot/expected
```

Checks:
- GeoTIFF checksums match exactly
- Metrics (CSI, directional error) within tolerance
- Tile PNGs are pixel-identical (or within small RMSE for compression)

---

## Troubleshooting

### "Ingest failed: FIRMS API returned 401"

**Solution**: Check `FIRMS_API_KEY` in `.env`. Register at https://firms.modaps.eosdis.nasa.gov/api/

### "Spread model produces all zeros"

**Solution**: 
- Check hotspot seeds (empty cluster?)
- Verify wind/RH data is valid (not all NaN)
- Inspect `configs/spread.yml` thresholds (too high?)

### "Tiles are blank/black"

**Solution**:
- Check GeoTIFF data range (all zeros or NaN?)
- Verify colormap range in `configs/tiles.yml`
- Use `gdalinfo data/products/fire_001/nowcast_24h.tif` to inspect

### "Pipeline is slow"

**Solution**:
- Profile with `python -m cProfile pipeline/run.py`
- Use parallel processing for multiple fires
- Reduce ensemble size (`n_ensemble`) for testing
- Cache DEM and weather grids in `data/interim`

---

## Next Steps

- **API Integration**: See [api/README.md](../api/README.md) for serving products
- **UI Visualization**: See [ui/README.md](../ui/README.md) for map rendering
- **ML Modules**: See [ml/README.md](../ml/README.md) for denoiser and calibration
- **Deployment**: See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for production setup

---

## References

- [WILDFIRE_101.md](../WILDFIRE_101.md) — Domain concepts and evaluation
- [CONTRIBUTING.md](../CONTRIBUTING.md) — Code style and testing standards
- [data/README.md](../data/README.md) — Data sources and layout

