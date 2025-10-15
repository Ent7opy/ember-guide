# Wildfire 101 — Concepts Behind EmberGuide (aka "Wildfire Nowcast")

**TL;DR:** We produce 12–48 h probabilistic maps of where a wildfire is most likely to spread next, using public satellite hotspots, weather, terrain—and optional AI modules for denoising and calibration. This is a research/communications tool, not a tactical incident system.

## What is a "nowcast"?

A nowcast is a very-near-term forecast (hours to ~2 days). In this project: 12/24/48 h spread risk with explicit uncertainty.

## The three drivers of fire spread (mental model)

### Fuel (what can burn)

- **Type & load:** grass (fast), shrubs/forest (hotter, longer).
- **Continuity:** continuous fine fuels (dry grass/needles) enable run; breaks (roads, rivers) slow/stop.
- **Moisture:** drier fuel → easier ignition/faster spread. We estimate dryness with proxies (humidity/temperature, optional vegetation indices).

### Weather

- **Wind:** main driver; pushes flames/embers downwind.
- **Relative humidity (RH):** low RH dries fuels → higher spread potential.
- **Temperature:** higher temp → drier fuels.
- **Rain/stability:** recent rain suppresses; boundary-layer mixing affects gustiness/smoke.

### Topography (terrain)

- **Slope:** upslope spreads faster; downslope slower.
- **Aspect:** sun-facing slopes often drier.
- **Barriers:** ridges, rivers, bare ground can limit spread.

## What satellites give us (and what they don't)

### Active fire "hotspots" (MODIS/VIIRS)

Thermally hot pixels at satellite overpass time → "fire is here now" seeds.

- **Pros:** global, frequent, public.
- **Limits:** coarse (~375–1000 m), time gaps, clouds/smoke, occasional false alarms.
  - → We cluster and may AI-filter (denoise) by persistence/context.

### Burned-area products

Maps of where it did burn (lag of days–weeks). Great for evaluation, not for real-time inputs.

## Weather & terrain we use

- **Weather (reanalysis):** Hourly 10 m wind (u/v), 2 m temperature, dew point (→ compute RH), boundary-layer height. Reanalysis is consistent/global but coarse; local winds in complex terrain are imperfect, so we can lightly bias-correct/downscale.

- **Terrain (DEM):** Elevation → slope & aspect, used to modulate spread (upslope boost).

## From inputs to a nowcast (conceptual pipeline)

### 1. Ingest
Fetch latest hotspots (seeds), weather, and terrain; cache with timestamps.

### 2. Prep
Align to a common grid/projection. Cluster hotspots into "fire objects." Define an Area of Interest (AOI).

### 3. Baseline spread model (auditable)
For each grid cell, compute a spread potential combining:

- Wind push (direction & speed),
- Slope factor (upslope > downslope),
- Dryness factor (from RH; optional veg proxy),
- Optional fuel continuity (penalize water/bare ground).

Seed with the hotspot cluster and step forward hour-by-hour (12–48 h).
Add uncertainty by perturbing weather slightly (Monte Carlo) → probability and direction rasters.

### 4. Calibration (tiny post-hoc model)
Raw scores are not guaranteed to be well-calibrated. We fit a small calibration (e.g., isotonic or logistic) on historical cases so "0.7" ≈ "~70% of similar pixels burned next day." The UI shows calibrated probabilities.

### 5. Serve & visualize
Expose GeoTIFFs/tiles/metrics via an API; render in the UI with detections, wind barbs, probability heatmap, and uncertainty bands.

## Where AI fits (useful, auditable pieces)

### Hotspot denoiser (XGBoost/LightGBM)
Classifies hotspot pixels as likely real vs artefact using spatio-temporal features (cluster persistence, day/night, scan angle, land cover, slope, nearby weather). Trained with weak labels from later burned-area maps and persistence rules. Reduces false seeds → cleaner nowcasts.

### Probability calibration (Isotonic/Logistic)
Maps the baseline spread score + context features (wind, RH, slope variability, time since detection) to well-calibrated probabilities. Improves interpretability (p≈0.6 ≈ 60%).

### Micro-downscaling / bias-correction (RF/GPR) (optional)
Nudges coarse ERA5 wind/RH using terrain cues or nearby stations (when available). Target: lower nowcast error, not just lower wind RMSE.

### Learned growth kernel (ConvGRU/U-Net) (experimental)
Predicts next-hour growth from sequences of hotspots + met + slope. Evaluated with strict region/year held-out splits; included only if it beats the baseline on CSI/IoU and maintains calibration.

### Guardrails:

- Split data by fire complex/region/year (no pixel/time leakage).
- Optimize for downstream nowcast metrics (CSI/IoU, directional error, reliability), not just denoiser AUC.
- Keep AI modules toggleable and documented (model cards).

## Key derived variables

- **Relative Humidity (RH):** computed from temperature & dew point; lower RH → drier fuels.
- **Vegetation/moisture proxies (optional):** NDVI/NDMI anomalies can modulate dryness.
- **Fire-weather summaries (optional):** e.g., Haines Index, components of Canadian FWI for context.

## How to read our maps (for non-experts)

- **Warm colors** = higher calibrated probability that an area will be involved within the chosen horizon.
- **Arrows/barbs** = wind direction & speed; spread tends to align with wind and upslope.
- **Contours** (e.g., p≥0.3 / 0.5 / 0.7) show conservative vs aggressive envelopes.
- **Always check timestamps** ("last updated" for detections & weather).

## How we evaluate (so it's scientific, not vibes)

- **CSI / IoU:** overlap of predicted high-probability area with next-day observed growth.
- **Directional error (°):** difference between predicted and observed spread direction.
- **Distance-to-perimeter (m):** how far the predicted front is from observed growth.
- **Calibration reliability:** do pixels at p≈0.6 actually burn ~60% of the time?

### Baselines to beat:

- Persistence (no growth)
- Wind-only advection (direction with minimal physics)

## Uncertainty: what it means here

We report probabilities, not hard perimeters. Uncertainty arises from:

- Coarse weather fields (local winds/gusts unresolved),
- Satellite detection gaps (cloud/smoke timing),
- Simplified fuels/moisture representation.

UI shows probability bands (e.g., p≥0.3 / 0.5 / 0.7) and reliability plots in the Metrics page.

## Known limits (be upfront)

- **Hotspots ≠ perimeters** (coarse, intermittent, can miss under cloud/smoke).
- **Weather resolution is coarse** (canyon/downslope winds may be wrong).
- **Fuel moisture is proxied** (limited in-situ data).
- **Not a tactical tool:** for research/communication only; defer to official incident info.

## How to verify us (fast, local)

We provide a tiny, fixed evaluation snapshot (2 historical fires).

- Run `make eval` to reproduce our metrics and a demo map without downloading live data.
- Check reliability diagrams and before/after toggles for the denoiser/calibrator.

## Minimal glossary

- **Nowcast** — very-short-term forecast (hours to ~2 days).
- **Hotspot** — satellite pixel flagged as actively burning at overpass time.
- **Perimeter** — mapped outer boundary of the burned area (usually lagged).
- **DEM / Slope / Aspect** — elevation and its derivatives; slope impacts spread rate.
- **RH (Relative Humidity)** — air moisture measure; lower RH → drier fuels.
- **Calibration** — mapping model scores to real-world probabilities.
- **Uncertainty band / Quantile** — range of plausible outcomes (e.g., 20th–80th percentile).
- **Denoiser** — classifier that filters likely false hotspots to clean seeds.

## Responsible use & attribution

- **Scope disclaimer:** "Research preview — not for life-safety decisions."
- **Transparency:** versioned code/models, fixed random seeds, documented data sources and licenses.
- **Attribution:** credit satellite/weather/terrain providers in the UI footer and docs.

