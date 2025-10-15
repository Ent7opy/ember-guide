# EmberGuide ML Modules

Optional AI/ML components that enhance the baseline nowcast system through denoising, calibration, and downscaling.

---

## Overview

EmberGuide uses **targeted, auditable ML** for specific tasks where it demonstrably improves nowcast quality. All modules are:
- **Toggleable**: Can be enabled/disabled via config flags
- **Evaluated**: Measured on downstream nowcast metrics (CSI/IoU, reliability), not just proxy metrics
- **Split properly**: Train/test split by fire complex, region, and year (no pixel/time leakage)
- **Documented**: Each module has a MODEL_CARD.md with architecture, data, and limitations

**Modules**:
1. **Hotspot Denoiser** — Filters likely false detections (XGBoost/LightGBM)
2. **Probability Calibrator** — Maps baseline scores to calibrated probabilities (Isotonic/Logistic)
3. **Micro-Downscaler** — Refines coarse weather fields using terrain (RF/GPR) *(optional)*
4. **Learned Growth Kernel** — Neural fire spread predictor (ConvGRU/U-Net) *(experimental)*

---

## 1. Hotspot Denoiser

### Purpose

Classify MODIS/VIIRS hotspot pixels as **likely real** vs **likely artefact** to reduce false seeds in the nowcast.

### Why It Helps

Satellite hotspots have false positives from:
- Reflective surfaces (metal roofs, solar farms)
- Industrial heat sources (refineries, flares)
- Scan-angle artefacts at image edges
- Single-pixel transient spikes

Denoising reduces spurious nowcast seeds → cleaner probability maps.

### Architecture

- **Model**: XGBoost or LightGBM (binary classifier)
- **Features** (per hotspot pixel):
  - **Spatio-temporal**: Cluster persistence (how many nearby detections?), day/night flag
  - **Sensor**: Scan angle, confidence value, satellite (MODIS/VIIRS)
  - **Context**: Land cover type (from MODIS MCD12Q1), slope (fire on steep terrain?), nearby water
  - **Weather**: Wind speed, RH, temperature at detection time
- **Labels** (weak supervision):
  - Positive: Pixel inside burned-area perimeter (from MODIS MCD64A1, lagged by 7–30 days)
  - Negative: Single-pixel detections with no recurrence and no burned area
  - Heuristic: Persistence rule (≥3 detections in 48h within 5 km → positive)

### Training

```bash
# Generate training dataset from historical fires (2018–2023)
python -m ml.denoiser.prepare_data \
  --firms data/historical/firms/ \
  --burned-area data/historical/mcd64a1/ \
  --output ml/data/denoiser_train.parquet

# Train model
python -m ml.denoiser.train \
  --data ml/data/denoiser_train.parquet \
  --splits ml/data/denoiser_splits.json \
  --output ml/models/denoiser_v1.pkl \
  --seed 42

# Evaluate
python -m ml.denoiser.evaluate \
  --model ml/models/denoiser_v1.pkl \
  --test-data ml/data/denoiser_test.parquet \
  --output ml/results/denoiser_v1_eval.json
```

### Splits & Leakage Prevention

**Critical**: Split by **fire complex** and **region**, not randomly:
- Train: 2018–2021 Western US fires
- Validation: 2022 Western US + 2020–2021 Canada
- Test: 2023 Western US + 2022 Canada

**Never**:
- Train and test on same fire (even different time slices)
- Split spatially within a fire (pixels leak context)
- Use future burned-area labels from same fire event

### Evaluation Metrics

**Intrinsic** (denoiser AUC):
- Precision/Recall at threshold (e.g., p≥0.5)
- ROC-AUC, PR-AUC

**Downstream** (what matters):
- Does denoising improve nowcast CSI/IoU?
- Does it reduce false-positive spread predictions?
- Calibration: Does removing detections harm true positives?

### Usage

```python
from ml.denoiser import HotspotDenoiser

denoiser = HotspotDenoiser.load("ml/models/denoiser_v1.pkl")

# Filter hotspots
raw_hotspots = pd.read_csv("data/raw/firms/latest.csv")
filtered = denoiser.filter(raw_hotspots, threshold=0.5)

print(f"Removed {len(raw_hotspots) - len(filtered)} likely false detections")
```

**Config toggle**:
```yaml
# configs/ml.yml
use_denoiser: true
denoiser_model: ml/models/denoiser_v1.pkl
denoiser_threshold: 0.5
```

### Model Card

See [ml/models/DENOISER_MODEL_CARD.md](models/DENOISER_MODEL_CARD.md) for full details.

---

## 2. Probability Calibrator

### Purpose

Map **baseline spread scores** (arbitrary units) to **calibrated probabilities** (p≈0.6 means ~60% of similar pixels burned).

### Why It Helps

The baseline spread model produces risk scores based on physics (wind, slope, dryness), but:
- Scores are not guaranteed to align with observed burn frequencies
- Different regions/fuel types may have different score→probability mappings

Calibration ensures interpretability: "p=0.7" means "70% chance of burning."

### Architecture

- **Model**: Isotonic regression or logistic calibration (scikit-learn)
- **Features**:
  - Baseline spread score (primary)
  - Wind speed, RH, slope
  - Time since detection
  - Optional: Distance from seed, fuel type proxy
- **Target**: Binary (did pixel burn in next 24h?)

### Training

```bash
# Generate calibration dataset from historical fires
python -m ml.calibration.prepare_data \
  --nowcasts data/historical/nowcasts/ \
  --observed data/historical/mcd64a1/ \
  --output ml/data/calibration_train.parquet

# Fit calibrator
python -m ml.calibration.train \
  --data ml/data/calibration_train.parquet \
  --method isotonic \
  --output ml/models/calibrator_v1.pkl

# Evaluate
python -m ml.calibration.evaluate \
  --model ml/models/calibrator_v1.pkl \
  --test-data ml/data/calibration_test.parquet \
  --output ml/results/calibrator_v1_reliability.png
```

### Splits

Same as denoiser: by fire complex/region/year.

### Evaluation Metrics

**Calibration curve**:
- Plot: predicted probability (binned) vs observed frequency
- Ideal: diagonal line (predicted = observed)

**Reliability metrics**:
- Expected Calibration Error (ECE)
- Brier score
- Sharpness (do we still differentiate high/low risk?)

**Downstream**:
- Does calibration improve user trust?
- Do contour lines (e.g., p≥0.5) better match observed perimeters?

### Usage

```python
from ml.calibration import ProbabilityCalibrator
import rasterio

calibrator = ProbabilityCalibrator.load("ml/models/calibrator_v1.pkl")

# Apply to nowcast raster
with rasterio.open("data/products/fire_001/nowcast_24h_raw.tif") as src:
    raw_scores = src.read(1)
    calibrated_probs = calibrator.transform(raw_scores)
    
    # Write calibrated output
    # ... (write to new GeoTIFF)
```

**Config toggle**:
```yaml
# configs/ml.yml
use_calibration: true
calibration_model: ml/models/calibrator_v1.pkl
```

### Model Card

See [ml/models/CALIBRATION_MODEL_CARD.md](models/CALIBRATION_MODEL_CARD.md).

---

## 3. Micro-Downscaler (Optional)

### Purpose

Refine coarse ERA5 weather fields (~25 km) using terrain features to improve local wind/RH estimates.

### Why It Helps

Fire spread is sensitive to wind, but ERA5 misses:
- Canyon channeling
- Downslope katabatic flows
- Terrain-induced speed-up

A learned downscaler can nudge ERA5 toward higher-resolution reality (when ground truth is available).

### Architecture

- **Model**: Random Forest or Gaussian Process Regression
- **Features**: ERA5 u/v/RH + slope, aspect, elevation, roughness, distance to ridge
- **Target**: Observed wind/RH from weather stations (RAWS, ASOS)

### Training

```bash
python -m ml.downscaler.prepare_data \
  --era5 data/historical/era5/ \
  --stations data/historical/raws/ \
  --dem data/srtm/ \
  --output ml/data/downscaler_train.parquet

python -m ml.downscaler.train \
  --data ml/data/downscaler_train.parquet \
  --output ml/models/downscaler_v1.pkl
```

### Critical Constraint

**Only include if it reduces nowcast error, not just wind RMSE.**

- Evaluate on held-out fires: Does downscaled wind improve CSI/IoU?
- If it improves wind metrics but worsens nowcast, **do not use**.

### Usage

```python
from ml.downscaler import WeatherDownscaler

downscaler = WeatherDownscaler.load("ml/models/downscaler_v1.pkl")

# Refine ERA5 wind
u_coarse, v_coarse = era5_data["u10"], era5_data["v10"]
u_fine, v_fine = downscaler.refine(u_coarse, v_coarse, dem, slope, aspect)
```

**Config toggle**:
```yaml
# configs/ml.yml
use_downscaler: false  # Default off; enable only if validated
downscaler_model: ml/models/downscaler_v1.pkl
```

---

## 4. Learned Growth Kernel (Experimental)

### Purpose

Replace or augment the baseline spread model with a learned neural predictor.

### Why It's Experimental

- More complex (harder to interpret than physics-based)
- Requires large training set with diverse fires
- Risk of overfitting to training regions/years
- Must beat baseline on held-out fires to justify complexity

### Architecture

- **ConvGRU** or **U-Net** with temporal encoding
- **Input**: Sequence of hotspot grids + wind/RH/slope (multi-channel)
- **Output**: Next-hour fire spread probability grid

### Guardrails

1. **Strict splits**: Train on 2018–2020 fires, validate on 2021, test on 2022–2023
2. **Region holdout**: Train on California, test on Oregon/Washington
3. **Evaluation**: Must beat baseline on CSI, directional error, and calibration
4. **Fallback**: If it fails on test set, revert to baseline

### Not Yet Implemented

This module is a placeholder for future research. Include only if:
- You have ≥100 diverse training fires
- Held-out evaluation shows consistent improvement
- Calibration is maintained or improved

---

## Module Toggle Flags

**`configs/ml.yml`**:
```yaml
ml_modules:
  use_denoiser: true
  denoiser_model: ml/models/denoiser_v1.pkl
  denoiser_threshold: 0.5
  
  use_calibration: true
  calibration_model: ml/models/calibrator_v1.pkl
  
  use_downscaler: false  # Experimental
  downscaler_model: ml/models/downscaler_v1.pkl
  
  use_learned_kernel: false  # Not implemented
```

**Pipeline integration**:
```python
from ml import get_ml_config, HotspotDenoiser, ProbabilityCalibrator

config = get_ml_config("configs/ml.yml")

# Step 1: Denoise hotspots (if enabled)
if config.use_denoiser:
    denoiser = HotspotDenoiser.load(config.denoiser_model)
    hotspots = denoiser.filter(hotspots, threshold=config.denoiser_threshold)

# Step 2: Run baseline spread model
spread_scores = run_baseline_model(hotspots, weather, terrain)

# Step 3: Calibrate probabilities (if enabled)
if config.use_calibration:
    calibrator = ProbabilityCalibrator.load(config.calibration_model)
    probabilities = calibrator.transform(spread_scores)
else:
    probabilities = spread_scores  # Use raw scores
```

---

## Data Splits & Leakage Prevention

### Golden Rule

**Never** train and test on:
- Same fire complex (even different days)
- Same region in same year (spatial leakage)
- Future labels from same fire (temporal leakage)

### Recommended Splits

**Temporal**:
- Train: 2018–2021
- Validation: 2022
- Test: 2023

**Geographic**:
- Train: California + Nevada
- Validation: Oregon + Washington
- Test: Canada + Southwest US

**Fire-level**:
- Assign each fire complex a unique ID
- Split complexes, not pixels or time slices

### Example Split Config

**`ml/data/splits.json`**:
```json
{
  "train": {
    "years": [2018, 2019, 2020, 2021],
    "regions": ["CA", "NV"]
  },
  "val": {
    "years": [2022],
    "regions": ["OR", "WA"]
  },
  "test": {
    "years": [2023],
    "regions": ["CA", "NV", "OR", "WA"]
  }
}
```

---

## Evaluation Framework

### Metrics

**Intrinsic** (ML model quality):
- Denoiser: AUC, precision@recall
- Calibrator: ECE, Brier score, reliability curve
- Downscaler: Wind RMSE, RH MAE

**Downstream** (nowcast quality):
- CSI / IoU at p≥0.5 threshold
- Directional error (degrees)
- Distance-to-perimeter (meters)
- Calibration reliability (do p=0.6 pixels burn 60% of time?)

### Evaluation Script

```bash
# Run full evaluation on test set
python -m ml.evaluate_all \
  --config configs/ml.yml \
  --test-fires ml/data/test_fires.json \
  --output ml/results/full_eval_$(date +%Y%m%d).json

# Compare baseline vs ML-enhanced
python -m ml.compare_baselines \
  --baseline-dir data/products_baseline/ \
  --ml-enhanced-dir data/products_ml/ \
  --output ml/results/comparison.html
```

---

## Model Cards

Each trained model must have a `MODEL_CARD.md` documenting:
- Architecture and hyperparameters
- Training data (date range, regions, fire count)
- Splits (train/val/test)
- Evaluation metrics (intrinsic + downstream)
- Known limitations and failure modes
- Versioning and reproducibility (random seed, code commit)

**Template**: See [models/MODEL_CARD_TEMPLATE.md](models/MODEL_CARD_TEMPLATE.md).

---

## Training Best Practices

### Determinism

```python
import random
import numpy as np
import torch  # If using PyTorch

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
```

### Hyperparameter Tuning

Use validation set (not test!):
```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    "max_depth": [3, 5, 7],
    "learning_rate": [0.01, 0.1],
    "n_estimators": [100, 200]
}

grid = GridSearchCV(model, param_grid, cv=3, scoring="roc_auc")
grid.fit(X_train, y_train)

best_model = grid.best_estimator_
```

### Versioning

Tag models with git commit + date:
```bash
# Save model with metadata
python -m ml.denoiser.train \
  --output ml/models/denoiser_$(git rev-parse --short HEAD)_$(date +%Y%m%d).pkl
```

Store metadata in model file:
```python
import joblib

model_artifact = {
    "model": trained_model,
    "features": feature_names,
    "version": "v1.2.3",
    "git_commit": "abc123",
    "trained_at": "2024-01-15T14:30:00Z",
    "seed": 42
}

joblib.dump(model_artifact, "ml/models/denoiser_v1.pkl")
```

---

## Testing

### Unit Tests

Test individual components:
```python
import pytest
from ml.denoiser import extract_features

def test_feature_extraction():
    hotspot = {
        "lat": 39.5, "lon": -121.5,
        "scan_angle": 15.2, "confidence": 85
    }
    features = extract_features(hotspot, context_data)
    assert "scan_angle" in features
    assert 0 <= features["confidence"] <= 100
```

### Integration Tests

Test full pipeline with ML modules:
```bash
pytest tests/integration/test_ml_pipeline.py
```

### Golden Fixtures

For calibration, store expected reliability curves:
- Input: Test scores
- Expected: Calibrated probabilities (within tolerance)

---

## Performance Optimization

### Inference Speed

- Use CPU-optimized models (XGBoost, LightGBM)
- Batch predictions (don't loop over pixels)
- Cache model loading (load once, reuse)

### Memory

For large rasters, process in chunks:
```python
import rasterio
from rasterio.windows import Window

with rasterio.open("large_raster.tif") as src:
    for window in src.block_windows(1):
        chunk = src.read(1, window=window)
        calibrated_chunk = calibrator.transform(chunk)
        # ... write to output
```

---

## Troubleshooting

### "Model produces all zeros"

**Solution**:
- Check input feature ranges (scaling issue?)
- Verify model loaded correctly (joblib/pickle version mismatch?)
- Test on training data (should work if trained correctly)

### "Calibration makes predictions worse"

**Solution**:
- Plot reliability curve: Is training set representative?
- Check test set split: Leakage or different distribution?
- Try simpler calibration (isotonic vs logistic)

### "Denoiser removes too many real hotspots"

**Solution**:
- Lower threshold (trade precision for recall)
- Inspect feature importance: Which features dominate?
- Retrain with balanced classes (if severe class imbalance)

---

## Next Steps

- **Pipeline Integration**: See [pipeline/README.md](../pipeline/README.md)
- **Evaluation**: See [eval/README.md](../eval/README.md) for metrics framework
- **Model Deployment**: See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)

---

## References

- [WILDFIRE_101.md](../WILDFIRE_101.md) — Domain background
- [Scikit-learn Calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- Model cards: [models/](models/)

