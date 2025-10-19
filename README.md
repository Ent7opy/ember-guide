# EmberGuide

**Open-source probabilistic wildfire nowcasts (12–48 h) from satellite hotspots, weather, and terrain.**

> **⚠️ Research preview — not for life-safety decisions.**  
> EmberGuide is a research and communications tool. Always defer to official incident information and evacuation orders.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## What is EmberGuide?

EmberGuide produces **12 to 48-hour probabilistic wildfire spread maps** showing:
- **Direction** of likely spread (aligned with wind and slope)
- **Risk probability** for each grid cell (calibrated 0–1)
- **Uncertainty bands** from Monte Carlo weather perturbations

Unlike tactical fire models, EmberGuide is designed for:
- **Public awareness** and general situational context
- **Research** into fire spread modeling and AI calibration
- **Communication** with media and stakeholders

**Not for:** evacuation planning, firefighting tactics, or operational decisions.

---

## Quick Start (POC)

### Prerequisites
- Python 3.11+
- (Optional) NASA Earthdata account (for FIRMS hotspots)
- (Optional) Copernicus Climate Data Store (CDS) account (for ERA5 weather)

**Note**: POC can run with mock data if API keys are not available!

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ember-guide.git
cd ember-guide

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials (optional - will use mock data if not provided)
cp .env.example .env
# Edit .env with your API keys (or leave empty for mock data)
```

### Run the POC

**Step 1: Generate nowcast data**
```bash
python -m pipeline.run --config configs/active.yml
```

**Step 2: Start the API** (in new terminal)
```bash
make serve-api
# Or: uvicorn api.main:app --port 8000
```

**Step 3: Launch the UI** (in new terminal)
```bash
make serve-ui
# Or: streamlit run ui/app.py --server.port 8501
```

Visit `http://localhost:8501` to see the interactive map!

**Full setup guide**: See [docs/POC_SETUP.md](docs/POC_SETUP.md)

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   INGEST     │────▶│   PIPELINE   │────▶│   PRODUCTS   │
│              │     │              │     │              │
│ FIRMS hotspots│     │ 1. Prep/Grid │     │ prob.tif     │
│ ERA5 weather  │     │ 2. Baseline  │     │ dir.tif      │
│ SRTM DEM      │     │ 3. MC perturb│     │ tiles/       │
└──────────────┘     │ 4. Calibrate │     │ report.json  │
                     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌────────────────────────────┘
                     ▼
          ┌──────────────────┐      ┌──────────────────┐
          │   FastAPI        │◀────▶│   Streamlit UI   │
          │   /fires         │      │                  │
          │   /nowcast/{id}  │      │ Map + Metrics    │
          │   /tiles/...     │      │ Downloads        │
          └──────────────────┘      └──────────────────┘
```

**Key Components:**
- **Pipeline** ([`pipeline/`](pipeline/README.md)): Batch processing from raw data → products
- **API** ([`api/`](api/README.md)): FastAPI backend serving GeoTIFFs, tiles, and metadata
- **UI** ([`ui/`](ui/README.md)): Streamlit frontend with interactive maps and downloads
- **ML Modules** ([`ml/`](ml/README.md)): Optional AI for denoising, calibration, downscaling
- **Data** ([`data/`](data/README.md)): Organized raw/interim/products layout
- **Evaluation** ([`eval/`](eval/README.md)): Metrics and reproducibility framework

---

## How It Works (30-Second Version)

1. **Detect fires** from MODIS/VIIRS satellite hotspots (public, NASA FIRMS)
2. **Get weather** (wind, humidity, temperature) from ERA5 reanalysis (Copernicus)
3. **Terrain** slope and aspect from SRTM DEM (NASA/USGS)
4. **Spread model** combines wind push + slope factor + fuel dryness → baseline risk
5. **Uncertainty** via Monte Carlo: perturb weather slightly across 50–100 runs → probability maps
6. **Calibration** (optional ML): map scores to real-world probabilities (isotonic/logistic)
7. **Serve** as GeoTIFFs, map tiles, and JSON via API; visualize in Streamlit

See [WILDFIRE_101.md](WILDFIRE_101.md) for the full explainer on fire behavior, satellite data, and evaluation.

---

## Documentation

- **[WILDFIRE_101.md](WILDFIRE_101.md)** — Domain concepts, drivers of fire spread, how to read the maps
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Code style, PR workflow, testing requirements
- **[pipeline/README.md](pipeline/README.md)** — Data pipeline deep dive (ingest → tiles)
- **[api/README.md](api/README.md)** — FastAPI backend guide and endpoint contracts
- **[ml/README.md](ml/README.md)** — ML modules (denoiser, calibration, downscaling)
- **[ui/README.md](ui/README.md)** — Streamlit UI setup and design principles
- **[data/README.md](data/README.md)** — Data layout, sources, and licenses
- **[eval/README.md](eval/README.md)** — Evaluation framework and metrics
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Production deployment guide
- **[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)** — Full attribution and licensing

---

## Features

- **Probabilistic outputs**: No hard perimeters; calibrated probabilities with uncertainty bands
- **Multiple horizons**: 12 h, 24 h, 48 h nowcasts
- **Open data**: Public satellite hotspots, reanalysis weather, DEM
- **Deterministic & reproducible**: Fixed random seeds, versioned configs, golden test fixtures
- **Optional AI modules**: Hotspot denoiser (XGBoost), probability calibrator, micro-downscaler — all toggleable
- **GeoTIFF + tile export**: Download rasters or use slippy map tiles
- **Reliability metrics**: CSI/IoU, directional error, calibration plots

---

## Limitations (Be Upfront)

- **Hotspots ≠ fire perimeters**: Coarse (~375–1000 m), intermittent, can miss areas under clouds/smoke
- **Weather resolution**: ERA5 is ~25 km; local canyon winds may be inaccurate
- **Simplified fuel/moisture**: We proxy dryness from RH and optional vegetation indices; no in-situ fuel data
- **Not real-time**: Satellite and reanalysis data have lag (typically 3–6 hours)
- **Research tool**: Not validated for operational firefighting or evacuation decisions

See [Known Limits](WILDFIRE_101.md#known-limits-be-upfront) in WILDFIRE_101.md.

---

## Evaluation

We evaluate on historical fires using:
- **CSI / IoU**: Overlap of predicted high-probability area with observed next-day growth
- **Directional error**: Degrees between predicted and observed spread direction
- **Calibration reliability**: Do pixels at p≈0.6 actually burn ~60% of the time?

**Baselines**: Persistence (no growth), wind-only advection.

```bash
make eval  # Runs on 2 fixed historical fires (no network required)
```

See [eval/README.md](eval/README.md) for details.

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style (ruff, black, mypy)
- Testing requirements (pytest, golden fixtures)
- PR workflow
- How to add new features

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

### Data Attribution

EmberGuide uses public datasets. **You must credit**:
- **FIRMS** (NASA): MODIS/VIIRS active fire data
- **ERA5** (Copernicus Climate Change Service/ECMWF): Weather reanalysis
- **SRTM** (NASA/USGS): Digital elevation model

See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for full citations and license details.

---

## Contact & Citation

- **Issues**: [GitHub Issues](https://github.com/yourusername/ember-guide/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ember-guide/discussions)

If you use EmberGuide in research, please cite:
```bibtex
@software{emberguide2025,
  title={EmberGuide: Open Wildfire Nowcasts},
  author={Your Name},
  year={2025},
  url={https://github.com/yourusername/ember-guide}
}
```

---

**Remember**: This is a research preview. Always rely on official fire agencies for life-safety information.

