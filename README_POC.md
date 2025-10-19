# EmberGuide POC - Quick Reference

This is a **proof-of-concept** implementation of EmberGuide with simplified features for demonstration.

## What's Included

✅ **Data Ingestion**: FIRMS, ERA5, SRTM (with mock data fallback)  
✅ **Fire Spread Model**: Simplified physics-based model with Monte Carlo ensemble  
✅ **ML Modules**: Rule-based denoiser + isotonic calibrator  
✅ **FastAPI Backend**: RESTful API serving nowcast products  
✅ **Streamlit UI**: Interactive map with Folium visualization  

## What's Simplified/Missing (vs Full System)

⚠️ **Single fire only** (no parallel processing)  
⚠️ **24h horizon only** (no 12h/48h)  
⚠️ **Small ensemble** (20 runs vs 100)  
⚠️ **No map tiles** (direct GeoTIFF overlay)  
⚠️ **Synthetic DEM** (not real SRTM downloads)  
⚠️ **Mock training data** for calibrator  
⚠️ **No evaluation framework** (no historical validation)  

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Run pipeline
python -m pipeline.run

# 3. Start API (new terminal)
make serve-api

# 4. Launch UI (new terminal)
make serve-ui
```

Then open: http://localhost:8501

## File Structure

```
ember-guide/
├── api/              # FastAPI backend
│   ├── main.py      # API endpoints
│   ├── contracts.py # Pydantic models
│   └── utils.py     # Helper functions
├── ui/               # Streamlit frontend
│   ├── app.py       # Main UI
│   ├── components/  # Map viewer
│   └── utils/       # API client
├── pipeline/         # Data processing
│   ├── ingest/      # FIRMS, ERA5, SRTM
│   ├── prep/        # Clustering, alignment
│   ├── spread/      # Fire model
│   └── run.py       # Main orchestrator
├── ml/               # ML modules
│   ├── denoiser/    # Hotspot filter
│   └── calibration/ # Probability calibration
├── configs/          # YAML configurations
└── data/             # Data directory (gitignored)
    ├── raw/         # Input data
    ├── interim/     # Processed data
    └── products/    # Output nowcasts
```

## Configuration

Edit `configs/active.yml` to change fire location:

```yaml
fire:
  id: fire_001
  region: CA_north
  bbox: [-122.5, 38.5, -121.0, 40.0]  # [west, south, east, north]
  since: "2024-10-01T00:00:00Z"
  horizon: 24
```

## Troubleshooting

**"No fire clusters found"**
→ Check `data/raw/firms/` has hotspot data

**"Cannot connect to API"**
→ Make sure API server is running: `make serve-api`

**"No active fires found" in UI**
→ Run pipeline first: `python -m pipeline.run`

**Import errors**
→ Reinstall: `pip install -r requirements.txt`

## Full Documentation

- [Complete Setup Guide](docs/POC_SETUP.md)
- [Data Sources](docs/DATA_SOURCES.md)
- [API Documentation](http://localhost:8000/docs) (when API running)

## Next Steps

To move from POC to production:

1. Get real API keys (FIRMS, CDS)
2. Add multiple fire support
3. Implement tile generation
4. Add evaluation framework
5. Train calibrator on real data
6. Deploy to server

---

**Remember**: This is a research preview, not for life-safety decisions!

