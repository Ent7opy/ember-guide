# Getting Started with EmberGuide POC

Welcome! This guide will get you up and running with EmberGuide in 10 minutes.

## Prerequisites

- **Python 3.11+**
- **10-20 minutes** of your time
- (Optional) API keys for real data - [see below](#optional-real-data-setup)

## Installation (5 minutes)

### 1. Setup Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If GDAL fails to install, see [troubleshooting](docs/POC_SETUP.md#troubleshooting).

### 3. Verify Setup

```bash
python test_setup.py
```

You should see: ✅ All tests passed!

## Quick Demo (5 minutes)

### Option A: Automated Demo

```bash
python run_poc_demo.py
```

This guided script will:
1. ✓ Check your setup
2. ✓ Run the pipeline
3. ✓ Show you how to start API and UI

### Option B: Manual Steps

**Terminal 1** - Run Pipeline:
```bash
python -m pipeline.run
```
Wait ~3-5 minutes. You'll see "Pipeline Complete!"

**Terminal 2** - Start API:
```bash
make serve-api
# Or: uvicorn api.main:app --port 8000
```

**Terminal 3** - Start UI:
```bash
make serve-ui
# Or: streamlit run ui/app.py
```

**Browser** - Open UI:
```
http://localhost:8501
```

## What You'll See

The UI shows:
- 🗺️ **Interactive map** with fire location
- 📊 **Metrics**: Max probability, affected area, hotspot count
- ⬇️ **Downloads**: GeoTIFF probability maps and JSON reports
- ⚠️ **Disclaimers**: Important caveats about model limitations

## Optional: Real Data Setup

The POC works with mock data by default. For real wildfire data:

### 1. Get API Keys

**FIRMS (Satellite Hotspots)**:
- Register: https://firms.modaps.eosdis.nasa.gov/api/
- Free, instant approval

**ERA5 (Weather Data)**:
- Register: https://cds.climate.copernicus.eu/user/register  
- Free, may take 1-2 days for approval

### 2. Configure Keys

Edit `.env` file:
```bash
FIRMS_API_KEY=your_firms_key_here
CDS_API_KEY=your_cds_key_here:cds_api_url_here
```

### 3. Re-run Pipeline

```bash
python -m pipeline.run
```

Now it will fetch real data!

## Customization

### Change Fire Location

Edit `configs/active.yml`:
```yaml
fire:
  bbox: [-122.5, 38.5, -121.0, 40.0]  # [west, south, east, north]
```

### Adjust Model Parameters

Edit `configs/spread.yml`:
```yaml
factors:
  wind_weight: 0.6  # Increase wind influence
thresholds:
  spread_threshold: 0.2  # Lower = more aggressive spread
```

### Change Ensemble Size

Edit `configs/active.yml`:
```yaml
global:
  n_ensemble: 50  # More runs = smoother probabilities
```

## Next Steps

- 📖 **Full Setup Guide**: [docs/POC_SETUP.md](docs/POC_SETUP.md)
- 🔬 **POC Overview**: [README_POC.md](README_POC.md)
- 📋 **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- 🌐 **API Docs**: http://localhost:8000/docs (when API running)

## Common Issues

**"No module named 'rasterio'"**
→ Run: `pip install -r requirements.txt`

**"No fire clusters found"**
→ Normal for mock data with small bbox. Check `data/raw/firms/` has data.

**"Cannot connect to API"**
→ Make sure API is running: `curl http://localhost:8000/health`

**"Port already in use"**
→ Stop other services or use different port

## Help & Support

- 🐛 **Issues**: Check [docs/POC_SETUP.md](docs/POC_SETUP.md) troubleshooting section
- 📚 **Documentation**: See `docs/` folder
- 💬 **Questions**: Open a GitHub issue

---

**Important**: EmberGuide is a research preview — not for life-safety decisions!

Enjoy exploring wildfire nowcasts! 🔥

