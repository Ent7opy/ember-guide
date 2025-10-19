# EmberGuide POC Setup Guide

Complete guide for setting up and running the EmberGuide proof-of-concept.

---

## Prerequisites

- **Python 3.11+** installed
- **Git** for cloning repository
- (Optional) **NASA FIRMS API Key** - [Register here](https://firms.modaps.eosdis.nasa.gov/api/)
- (Optional) **Copernicus CDS API Key** - [Register here](https://cds.climate.copernicus.eu/user/register)

**Note for POC**: The system will generate mock data if API keys are not available, allowing you to test the full workflow without external dependencies.

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ember-guide.git
cd ember-guide
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Unix/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: GDAL installation can be tricky. If you encounter issues:

**Windows:**
- Download pre-built GDAL wheel from [https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal](https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal)
- Install: `pip install GDAL‑3.8.0‑cp311‑cp311‑win_amd64.whl`

**Ubuntu/Debian:**
```bash
sudo apt-get install gdal-bin libgdal-dev
pip install GDAL==$(gdal-config --version)
```

**Mac:**
```bash
brew install gdal
pip install GDAL==$(gdal-config --version)
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys (or leave empty to use mock data):

```bash
# Optional: For real FIRMS hotspot data
FIRMS_API_KEY=your_key_here

# Optional: For real ERA5 weather data
CDS_API_KEY=your_key_here
CDS_API_URL=https://cds.climate.copernicus.eu/api/v2
```

---

## Running the POC

### Step 1: Generate Nowcast Data

Run the pipeline to process fire data and generate nowcasts:

```bash
python -m pipeline.run --config configs/active.yml
```

**Expected output:**
```
============================================================
EmberGuide POC Pipeline Starting
============================================================
Processing fire: fire_001
Region: CA_north
...
============================================================
Pipeline Complete!
============================================================
Products saved to: data/products/fire_001
Max probability: 0.873
Affected area: 450.2 km²
```

**Runtime**: ~2-5 minutes for single fire with mock data, ~10-20 minutes with real API data.

**What it does:**
1. Fetches/generates hotspot detections (FIRMS)
2. Fetches/generates weather data (ERA5)
3. Creates synthetic elevation model (SRTM)
4. Clusters hotspots into fire objects
5. Aligns all data to common grid
6. Computes terrain features (slope, aspect)
7. Computes weather features (relative humidity)
8. Runs fire spread model (20 ensemble members)
9. Applies ML calibration
10. Saves probability maps and metadata

### Step 2: Start the API Server

In a **new terminal** (keep virtual environment activated):

```bash
make serve-api
```

Or manually:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
```

**Verify API is running:**
Open browser to [http://localhost:8000/docs](http://localhost:8000/docs) to see interactive API documentation.

**Test endpoints:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/fires
```

### Step 3: Launch the UI

In a **third terminal** (keep virtual environment activated):

```bash
make serve-ui
```

Or manually:
```bash
streamlit run ui/app.py --server.port 8501
```

**Expected output:**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.1.x:8501
```

**Open UI:**
Navigate to [http://localhost:8501](http://localhost:8501) in your browser.

---

## Using the UI

1. **Select Fire**: Choose from dropdown (e.g., "fire_001 (CA_north)")
2. **View Map**: Interactive map shows fire location and probability overlay
3. **Check Metrics**: Right panel displays:
   - Max/mean probability
   - Affected area
   - Hotspot count
4. **Download Data**: Click buttons to download GeoTIFF or JSON report
5. **Read Caveats**: Scroll down to see important limitations

---

## Troubleshooting

### Pipeline Errors

**"FIRMS_API_KEY not found"**
- This is OK for POC - mock data will be generated
- To use real data, register at [https://firms.modaps.eosdis.nasa.gov/api/](https://firms.modaps.eosdis.nasa.gov/api/)

**"No fire clusters found"**
- Check that mock hotspots were created in `data/raw/firms/`
- Try adjusting clustering parameters in `configs/prep.yml` (reduce `min_samples`)

**"Memory error" or slow performance**
- Reduce grid resolution in `configs/active.yml`: `resolution_m: 2000` (instead of 1000)
- Reduce ensemble size: `n_ensemble: 10` (instead of 20)

**"Module not found" errors**
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### API Errors

**"Cannot connect to API"**
- Check API is running: `curl http://localhost:8000/health`
- Verify port 8000 is not in use: `lsof -i :8000` (Unix) or `netstat -ano | findstr :8000` (Windows)
- Check firewall settings

**"404 Fire not found"**
- Run pipeline first: `python -m pipeline.run`
- Check `data/products/index.json` exists and has fire entries

### UI Errors

**"No active fires found"**
- Run pipeline first to generate data
- Check API is reachable: visit [http://localhost:8000/fires](http://localhost:8000/fires)

**"Map not loading"**
- Check browser console for JavaScript errors
- Try refreshing the page
- Check that GeoTIFF files exist in `data/products/fire_001/`

**"Streamlit port already in use"**
- Stop other Streamlit instances
- Or use different port: `streamlit run ui/app.py --server.port 8502`

---

## Customizing the POC

### Change Fire Location

Edit `configs/active.yml`:

```yaml
fire:
  id: fire_002
  region: CO_mountains
  bbox: [-105.5, 39.0, -104.5, 40.5]  # [west, south, east, north]
  since: "2024-10-01T00:00:00Z"
```

Then re-run pipeline.

### Adjust Spread Model Parameters

Edit `configs/spread.yml`:

```yaml
factors:
  wind_weight: 0.6  # Increase wind importance
  slope_weight: 0.3
  dryness_weight: 0.1

thresholds:
  spread_threshold: 0.2  # Lower = more aggressive spread
```

### Change Ensemble Size

Edit `configs/active.yml`:

```yaml
global:
  n_ensemble: 50  # More runs = smoother probabilities but slower
```

---

## Data Outputs

After running the pipeline, you'll find:

```
data/
├── raw/                      # Downloaded/mock input data
│   ├── firms/
│   │   └── mock_firms_hotspots.csv
│   ├── era5/
│   │   └── mock_era5_weather.nc
│   └── srtm/
│       └── srtm_dem_*.tif
├── interim/                  # Intermediate processing files
│   ├── fire_clusters.geojson
│   ├── aligned/
│   └── terrain/
└── products/                 # Final outputs (served by API)
    ├── index.json           # Fire catalog
    └── fire_001/
        ├── metadata.json
        ├── nowcast_24h.tif  # Probability map
        ├── direction_24h.tif
        └── uncertainty_24h.tif
```

---

## API Endpoints

### GET /health
Health check

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-19T12:00:00Z",
  "version": "0.1.0-poc"
}
```

### GET /fires
List active fires

**Response:**
```json
{
  "fires": [
    {
      "id": "fire_001",
      "region": "CA_north",
      "centroid": {"lat": 39.5, "lon": -121.5},
      "bbox": [-122.5, 38.5, -121.0, 40.0],
      "status": "active",
      "nowcast_available": [24],
      "last_updated": "2024-10-19T12:00:00Z"
    }
  ],
  "count": 1
}
```

### GET /nowcast/{fire_id}?horizon=24
Get nowcast data

**Response:**
```json
{
  "fire_id": "fire_001",
  "horizon": 24,
  "grid_meta": {...},
  "assets": {
    "prob_tif": "/downloads/fire_001/nowcast_24h.tif",
    "dir_tif": "/downloads/fire_001/direction_24h.tif",
    "uncertainty_tif": "/downloads/fire_001/uncertainty_24h.tif"
  },
  "metrics": {
    "max_probability": 0.87,
    "mean_probability": 0.12,
    "affected_area_km2": 450.2
  }
}
```

### GET /downloads/{fire_id}/{filename}
Download GeoTIFF or JSON files

---

## Next Steps

### From POC to Production

1. **Real Data**: Register for FIRMS and CDS API keys
2. **Multiple Fires**: Modify `configs/active.yml` to track multiple fires
3. **Scheduled Runs**: Setup cron job to run pipeline every 3-6 hours
4. **Tile Generation**: Add map tile generation for better UI performance
5. **Validation**: Compare nowcasts against observed fire growth
6. **ML Training**: Train calibrator on real historical fire data

### Advanced Features (Not in POC)

- Multiple forecast horizons (12h, 48h)
- Directional spread visualization with arrows
- Time-series animation of spread
- Comparison with observations
- Uncertainty visualization
- Export to GIS formats

---

## Getting Help

- **GitHub Issues**: [https://github.com/yourusername/ember-guide/issues](https://github.com/yourusername/ember-guide/issues)
- **Documentation**: See main [README.md](../README.md) and other docs in `docs/`
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs) when server is running

---

## License

MIT License - See [LICENSE](../LICENSE) for details.

## Data Attribution

When using EmberGuide, always credit:
- **FIRMS** (NASA): Active fire detections
- **ERA5** (Copernicus/ECMWF): Weather reanalysis  
- **SRTM** (NASA/USGS): Terrain data

See [docs/DATA_SOURCES.md](DATA_SOURCES.md) for full attribution requirements.

